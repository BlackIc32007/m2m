"""
sandbox -- всё, что нужно веб-интерфейсу (live_server.py), чтобы работать
как песочница:

  MODELS            -- какие модели можно создать и с какими параметрами
                       (схема полей для формы + фабрика);
  editable(node)    -- какие параметры узла можно менять на ходу;
  apply_params(...) -- проверить и применить новые значения;
  metrics(model)    -- метрики шага для графиков в интерфейсе.

Схема поля: name, label, type ("int" | "float" | "choice"), value/default,
min, max, step, options (для choice). Проверка значений -- на сервере.
"""
from src.agents.endpoint_agents import InputAgent, OutputAgent
from src.agents.node_agent import NodeAgent
from src.agents.valve_agent import ValveAgent
from src.agents.valve_agent_fixed import ValveAgentModify, ValveAgentRefuse
from src.model.conflict_model import ConflictModel, HubAgent, SourceAgent, ZoneAgent
from src.model.factory_model import FactoryModel
from src.model.pipeline_model import PipelineModel


def F(name, label, type_, value, lo=None, hi=None, step=None, options=None):
    d = {"name": name, "label": label, "type": type_, "value": value}
    if lo is not None:
        d["min"] = lo
    if hi is not None:
        d["max"] = hi
    if step is not None:
        d["step"] = step
    if options is not None:
        d["options"] = options
    return d


SEED = F("seed", "сид (случайность)", "int", 42, 0, 10**6, 1)

_CHAIN = [F("queue_capacity", "ёмкость очереди узла", "int", 10, 1, 100, 1), SEED]
_CONFLICT = [
    F("supply", "воды от источника за шаг", "float", 6.0, 0, 100, 0.5),
    F("tank_capacity", "ёмкость общего бака", "float", 12.0, 1, 500, 1),
    F("tank_initial_fill", "начальное заполнение бака (доля)", "float", 0.5, 0, 1, 0.05),
    SEED,
]


def _conflict(scheme, policy="proportional"):
    return lambda p: ConflictModel(scheme, policy=policy, supply=p["supply"],
                                   tank_capacity=p["tank_capacity"], seed=p["seed"],
                                   tank_initial_fill=p["tank_initial_fill"])


MODELS = {
    "factory": {
        "label": "Завод: Input → Machine_A → Buffer → Machine_B → Output",
        "params": [F("task_arrival_interval", "новая задача раз в N шагов", "int", 2, 1, 50, 1),
                   F("processing_time", "время обработки на станке (шагов)", "int", 2, 1, 50, 1)] + _CHAIN,
        "make": lambda p: FactoryModel(task_arrival_interval=p["task_arrival_interval"],
                                       processing_time=p["processing_time"],
                                       queue_capacity=p["queue_capacity"], rng=p["seed"]),
    },
    "pipeline": {
        "label": "Трубопровод: Input → Pump → Valve → Tank → Output",
        "params": [F("flow_arrival_interval", "новая порция потока раз в N шагов", "int", 1, 1, 50, 1),
                   F("pump_processing_time", "время насоса (шагов)", "int", 1, 1, 50, 1),
                   F("valve_processing_time", "время клапана (шагов)", "int", 3, 1, 50, 1),
                   F("tank_processing_time", "время бака (шагов)", "int", 1, 1, 50, 1),
                   F("valve_safety_threshold", "порог перегрузки клапана", "float", 0.5, 0, 1, 0.05)] + _CHAIN,
        "make": lambda p: PipelineModel(flow_arrival_interval=p["flow_arrival_interval"],
                                        pump_processing_time=p["pump_processing_time"],
                                        valve_processing_time=p["valve_processing_time"],
                                        tank_processing_time=p["tank_processing_time"],
                                        valve_safety_threshold=p["valve_safety_threshold"],
                                        queue_capacity=p["queue_capacity"], rng=p["seed"]),
    },
    "conflict_distributor_prop": {"label": "Вода: арбитр — пропорционально запросу",
                                  "params": _CONFLICT, "make": _conflict("distributor", "proportional")},
    "conflict_distributor_equal": {"label": "Вода: арбитр — поровну",
                                   "params": _CONFLICT, "make": _conflict("distributor", "equal")},
    "conflict_distributor_priority": {"label": "Вода: арбитр — по приоритету",
                                      "params": _CONFLICT, "make": _conflict("distributor", "priority")},
    "conflict_shared_tank": {"label": "Вода: общий бак (без координатора)",
                             "params": _CONFLICT, "make": _conflict("shared_tank")},
    "conflict_auction": {"label": "Вода: аукцион", "params": _CONFLICT, "make": _conflict("auction")},
}


# ------------------------------------------------------------------ #
# Параметры узлов, которые можно менять на ходу
# ------------------------------------------------------------------ #
def _base_time_attr(node):
    """Где у узла хранится «обычное» время обработки (у клапанов оно
    отдельно от текущего, которое может быть замедлено)."""
    if isinstance(node, ValveAgent):
        return "base_processing_time"
    if isinstance(node, ValveAgentModify):
        return "_base_processing_time"
    return "processing_time"


def editable(node):
    """Список полей узла, которые можно менять (с текущими значениями)."""
    if isinstance(node, InputAgent):
        return [F("arrival_interval", "новая задача раз в N шагов (0 — остановить)", "int",
                  node.arrival_interval, 0, 50, 1)]
    if isinstance(node, OutputAgent):
        return []
    if isinstance(node, NodeAgent):
        fields = [
            F("processing_time", "время обработки (шагов)", "int", getattr(node, _base_time_attr(node)), 1, 50, 1),
            F("queue_capacity", "ёмкость очереди", "int", node.queue_capacity, 1, 100, 1),
            F("stop_threshold", "автономный: отказ при очереди ≥", "float", node.stop_threshold, 0, 1, 0.05),
            F("resume_threshold", "автономный: снова принимать при <", "float", node.resume_threshold, 0, 1, 0.05),
        ]
        if isinstance(node, ValveAgent):
            fields += [F("safety_threshold", "клапан: дросселировать при очереди ≥", "float",
                         node.safety_threshold, 0, 1, 0.05),
                       F("throttled_processing_time", "клапан: время при дросселировании", "int",
                         node.throttled_processing_time, 1, 100, 1)]
        if isinstance(node, ValveAgentRefuse):
            fields += [F("safety_threshold", "клапан: отказ при очереди ≥", "float", node.safety_threshold, 0, 1, 0.05),
                       F("recovery_threshold", "клапан: снова принимать при <", "float",
                         node.recovery_threshold, 0, 1, 0.05)]
        if isinstance(node, ValveAgentModify):
            fields += [F("safety_threshold", "клапан: замедлять при очереди ≥", "float", node.safety_threshold, 0, 1, 0.05),
                       F("throttle_factor", "клапан: во сколько раз медленнее", "int", node.throttle_factor, 1, 20, 1)]
        return fields
    if isinstance(node, SourceAgent):
        return [F("supply", "воды за шаг", "float", node.supply, 0, 100, 0.5)]
    if isinstance(node, HubAgent):
        if node.kind == "distributor":
            return [F("mode", "правило делёжа", "choice", node.mode,
                      options=[["proportional", "пропорционально запросу"], ["equal", "поровну"],
                               ["priority", "по приоритету"]])]
        if node.kind == "tank":
            return [F("capacity", "ёмкость бака", "float", node.capacity, 1, 500, 1)]
        return []
    if isinstance(node, ZoneAgent):
        return [
            F("priority", "ценность культуры (приоритет)", "float", node.priority, 0.1, 10, 0.5),
            F("arrival_rate", "приход потребности за шаг (в среднем)", "float", node.arrival_rate, 0, 50, 0.5),
            F("max_intake", "максимум воды за шаг", "float", node.max_intake, 0.5, 50, 0.5),
            F("capacity", "ёмкость очереди потребности", "float", node.capacity, 1, 500, 1),
            F("refuse_threshold", "автономный: уступить, если запас < доли ёмкости", "float",
              node.refuse_threshold, 0, 1, 0.05),
            F("inflate_after", "автономный: завысить после N шагов нехватки", "int", node.inflate_after, 1, 50, 1),
            F("inflate_factor", "автономный: во сколько раз завысить", "float", node.inflate_factor, 1, 10, 0.5),
        ]
    return []


def _coerce(field, raw):
    if field["type"] == "choice":
        allowed = [o[0] for o in field["options"]]
        if raw not in allowed:
            raise ValueError(f"{field['label']}: допустимо {allowed}")
        return raw
    try:
        v = float(raw)
    except (TypeError, ValueError):
        raise ValueError(f"{field['label']}: нужно число")
    if field["type"] == "int":
        if v != int(v):
            raise ValueError(f"{field['label']}: нужно целое число")
        v = int(v)
    if "min" in field and v < field["min"] or "max" in field and v > field["max"]:
        raise ValueError(f"{field['label']}: допустимо от {field.get('min')} до {field.get('max')}")
    return v


def validate(fields, values):
    """values (dict) -> проверенные значения; неизвестные поля -- ошибка."""
    by_name = {f["name"]: f for f in fields}
    unknown = set(values) - set(by_name)
    if unknown:
        raise ValueError(f"нельзя менять: {', '.join(sorted(unknown))}")
    return {k: _coerce(by_name[k], v) for k, v in values.items()}


def model_params(name, values):
    """Параметры создания модели: значения по умолчанию + переданные."""
    spec = MODELS[name]
    clean = validate(spec["params"], values or {})
    return {f["name"]: clean.get(f["name"], f["value"]) for f in spec["params"]}


def apply_params(node, values):
    """Проверить и применить новые параметры узла (всё или ничего)."""
    new = validate(editable(node), values)
    merged = {f["name"]: f["value"] for f in editable(node)} | new
    for lo, hi in (("resume_threshold", "stop_threshold"), ("recovery_threshold", "safety_threshold")):
        if lo in merged and hi in merged and merged[lo] > merged[hi]:
            raise ValueError(f"{lo} не может быть больше {hi}")

    for key, value in new.items():
        if key == "processing_time":
            attr = _base_time_attr(node)
            setattr(node, attr, value)
            # текущее время меняем, только если узел сейчас не замедлен
            if attr != "processing_time" and getattr(node, "mode", "ACCEPT") == "ACCEPT" \
                    and not (isinstance(node, ValveAgentModify) and node.load >= node.safety_threshold):
                node.processing_time = value
        else:
            setattr(node, key, value)
    if isinstance(node, ZoneAgent) and node.queue > node.capacity:
        node.lost_demand += node.queue - node.capacity
        node.queue = node.capacity
    if isinstance(node, HubAgent) and "mode" in new:
        # правило хранится и в модели (заголовок панели, текст контекста LLM)
        node.model.policy = new["mode"]
    if isinstance(node, HubAgent) and node.kind == "tank":
        node.level = min(node.level, node.capacity)
    return new


# ------------------------------------------------------------------ #
# Метрики шага для графиков
# ------------------------------------------------------------------ #
def metrics(model):
    if isinstance(model, ConflictModel):
        zones = model.zones
        return {"step": model.steps,
                "efficiency": round(model.efficiency, 4),
                "fairness": round(model.fairness, 4),
                "deficit": round(sum(z.need - z.allocated for z in zones), 3),
                "wasted": round(model.cum_wasted, 3)}
    workers = [n for n in model.nodes if not n.is_endpoint]
    return {"step": model.steps,
            "completed": model.completed_tasks,
            "queued": sum(len(n.queue) for n in workers),
            "blocked": sum(n.state == "blocked" for n in workers),
            "dropped": getattr(model.input, "dropped", 0)}
