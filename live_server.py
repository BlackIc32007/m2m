"""
live_server.py -- лёгкий локальный сервер для живого просмотра и управления
РЕАЛЬНО РАБОТАЮЩЕЙ Mesa-моделью (PipelineModel / FactoryModel) через браузер.

Специально не использует Solara/ipyvue/ipyvuetify -- именно эта связка
ломалась весь этот разговор (баг с GlobalVue.use). Здесь обычный Flask +
обычный HTML/JS, который просто опрашивает HTTP API. Меньше возможностей,
чем у полноценного SolaraViz, зато работает предсказуемо и не зависит от
версий фронтенд-пакетов Jupyter-экосистемы.

Запуск:
    cd m2m_project/project
    pip install flask
    python live_server.py

Потом открыть в браузере: http://localhost:5050
"""
import importlib
import inspect
import pkgutil
import sys
import threading
from pathlib import Path

# гарантируем, что пакет "src" виден независимо от того, откуда запущен файл
sys.path.insert(0, str(Path(__file__).resolve().parent))

from flask import Flask, jsonify, request, send_from_directory

from src.agents.node_agent import NodeAgent
from src.model.pipeline_model import PipelineModel
from src.model.factory_model import FactoryModel
from src.model.conflict_model import ConflictModel

app = Flask(__name__, static_folder=None)

MODEL_FACTORIES = {
    "pipeline": lambda: PipelineModel(
        flow_arrival_interval=1,
        pump_processing_time=1,
        valve_processing_time=3,
        tank_processing_time=1,
        queue_capacity=10,
        valve_safety_threshold=0.5,
    ),
    "factory": lambda: FactoryModel(
        task_arrival_interval=2,
        processing_time=2,
        queue_capacity=10,
    ),
    # --- модели конфликта "узел vs система" (см. src/model/conflict_model.py) ---
    "conflict_distributor_prop": lambda: ConflictModel("distributor", policy="proportional"),
    "conflict_distributor_equal": lambda: ConflictModel("distributor", policy="equal"),
    "conflict_distributor_priority": lambda: ConflictModel("distributor", policy="priority"),
    "conflict_shared_tank": lambda: ConflictModel("shared_tank"),
    "conflict_auction": lambda: ConflictModel("auction"),
}

MODEL_LABELS = {
    "pipeline": "pipeline (Pump/Valve/Tank)",
    "factory": "factory (Machine A/Buffer/B)",
    "conflict_distributor_prop": "A. Арбитр -- пропорционально спросу",
    "conflict_distributor_equal": "A. Арбитр -- поровну",
    "conflict_distributor_priority": "A. Арбитр -- по приоритету",
    "conflict_shared_tank": "B. Общий резервуар",
    "conflict_auction": "C. Аукцион",
}

state = {"model_name": "pipeline", "model": MODEL_FACTORIES["pipeline"](), "decision_mode": "passive"}


def _apply_decision_mode(model) -> None:
    # режим (пассивный / автономный) сохраняется при пересоздании модели
    if hasattr(model, "set_decision_mode"):
        model.set_decision_mode(state["decision_mode"])

# Flask по умолчанию обрабатывает запросы в разных потоках, а модель одна и
# общая: без блокировки "Пуск" (POST /api/step) и параллельный GET /api/state
# могли бы застать модель посреди шага. Все обращения к модели -- под lock.
model_lock = threading.RLock()

# Общие для всех NodeAgent параметры -- показываем их в интерфейсе отдельно
# от специфичных для конкретного класса (safety_threshold и т.п.), потому
# что они объявлены в NodeAgent.__init__, а не в подклассах (подклассы
# принимают их через **kwargs).
NODE_BASE_PARAMS = [
    {"name": "processing_time", "default": 2},
    {"name": "queue_capacity", "default": 10},
]
_SIGNATURE_SKIP = {"self", "model", "name", "downstream", "logger", "args", "kwargs"}
_BASE_PARAM_NAMES = {p["name"] for p in NODE_BASE_PARAMS}


def discover_node_classes() -> dict:
    """Сканирует src/agents/*.py и находит все классы -- наследники
    NodeAgent (включая сам NodeAgent). Благодаря этому новый тип узла,
    созданный через scaffold_node.py, сразу становится доступен в
    интерфейсе без правки этого файла."""
    import src.agents as agents_pkg

    classes = {"NodeAgent": NodeAgent}
    package_dir = Path(agents_pkg.__file__).resolve().parent
    for _, module_name, is_pkg in pkgutil.iter_modules([str(package_dir)]):
        if is_pkg:
            continue
        full_name = f"src.agents.{module_name}"
        try:
            module = importlib.import_module(full_name)
        except Exception:
            continue
        for attr_name, obj in vars(module).items():
            if (
                inspect.isclass(obj)
                and issubclass(obj, NodeAgent)
                and not obj.is_endpoint
                and obj.__module__ == full_name
            ):
                classes[obj.__name__] = obj
    return classes


def edges_for(model) -> list:
    """Список связей строится из model.nodes -- у каждого узла есть
    .downstream (следующий узел в цепочке) либо None (конец цепочки)."""
    edges = []
    for node in model.nodes:
        # у всех узлов есть список .downstreams (NodeAgent и ConflictAgent)
        for t in node.downstreams:
            edges.append({"from": node.name, "to": t.name})
    return edges


def serialize() -> dict:
    model = state["model"]
    return {
        "step": model.steps,
        "model_name": state["model_name"],
        "available_models": list(MODEL_FACTORIES.keys()),
        "model_labels": MODEL_LABELS,
        "conflict": model.conflict_metrics() if hasattr(model, "conflict_metrics") else None,
        "completed": getattr(model, "completed_tasks", 0),
        "decision_mode": getattr(model, "decision_mode", None),  # None -- модель без режимов (конфликтные)
        "nodes": [node.state_dict() for node in model.nodes],
        "edges": edges_for(model),
    }


@app.route("/api/state")
def api_state():
    with model_lock:
        return jsonify(serialize())


@app.route("/api/step", methods=["POST"])
def api_step():
    body = request.get_json(silent=True) or {}
    n = int(body.get("n", 1))
    with model_lock:
        for _ in range(max(1, n)):
            state["model"].step()
        return jsonify(serialize())


@app.route("/api/reset", methods=["POST"])
def api_reset():
    body = request.get_json(silent=True) or {}
    name = body.get("model_name", state["model_name"])
    if name not in MODEL_FACTORIES:
        return jsonify({"error": f"unknown model '{name}', available: {list(MODEL_FACTORIES.keys())}"}), 400
    with model_lock:
        state["model_name"] = name
        state["model"] = MODEL_FACTORIES[name]()
        _apply_decision_mode(state["model"])
        return jsonify(serialize())


@app.route("/api/decision_mode", methods=["POST"])
def api_decision_mode():
    """Переключить режим узлов: "passive" (узлы только передают поток) или
    "autonomous" (узлы сами принимают решения). Действует сразу, без
    пересоздания модели."""
    body = request.get_json(force=True)
    mode = body.get("mode")
    with model_lock:
        model = state["model"]
        if not hasattr(model, "set_decision_mode"):
            return jsonify({"error": "у этой модели нет режимов работы узлов"}), 400
        try:
            model.set_decision_mode(mode)
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        state["decision_mode"] = mode
        return jsonify(serialize())


@app.route("/api/fail", methods=["POST"])
def api_fail():
    body = request.get_json(force=True)
    node_name = body["node"]
    if body.get("permanent"):
        duration = float("inf")  # не восстановится сам -- только через /api/recover
    else:
        duration = int(body.get("duration", 5))
    with model_lock:
        try:
            state["model"].trigger_failure(node_name, duration)
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        return jsonify(serialize())


@app.route("/api/recover", methods=["POST"])
def api_recover():
    body = request.get_json(force=True)
    with model_lock:
        try:
            state["model"].force_recover(body["node"])
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        return jsonify(serialize())


@app.route("/api/node_types")
def api_node_types():
    """Отдаёт список доступных классов узлов (включая созданные через
    scaffold_node.py) вместе с параметрами их конструктора -- фронтенд
    строит по этому форму добавления узла."""
    classes = discover_node_classes()
    result = []
    for class_name, cls in sorted(classes.items()):
        extra_params = []
        try:
            sig = inspect.signature(cls.__init__)
            for pname, p in sig.parameters.items():
                if pname in _SIGNATURE_SKIP or pname in _BASE_PARAM_NAMES:
                    continue
                if p.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
                    continue
                default = None if p.default is inspect._empty else p.default
                extra_params.append({"name": pname, "default": default})
        except (TypeError, ValueError):
            pass
        result.append({
            "class_name": class_name,
            "common_params": NODE_BASE_PARAMS,
            "extra_params": extra_params,
        })
    return jsonify(result)


@app.route("/api/add_node", methods=["POST"])
def api_add_node():
    """Добавляет новый узел в текущую модель "на лету".

    Тело запроса:
        class_name   -- имя класса из /api/node_types (например "ValveAgent")
        name         -- имя нового узла, должно быть уникальным
        insert_after -- имя существующего узла, после которого встраивается
                        новый (если пусто/не указано -- в конец цепочки)
        mode         -- "insert" (по умолчанию: встроить в цепочку после
                        insert_after) или "branch" (добавить как ещё одну
                        ветку от insert_after, не разрывая существующую связь)
        params       -- dict с доп. параметрами конструктора (safety_threshold,
                        processing_time и т.п.)
    """
    body = request.get_json(force=True)
    class_name = body.get("class_name")
    node_name = (body.get("name") or "").strip()
    insert_after = body.get("insert_after") or None
    params = body.get("params") or {}
    mode = body.get("mode") or "insert"

    if not node_name:
        return jsonify({"error": "укажите имя узла"}), 400

    classes = discover_node_classes()
    if class_name not in classes:
        return jsonify({"error": f"unknown class '{class_name}', available: {list(classes.keys())}"}), 400
    cls = classes[class_name]

    with model_lock:
        model = state["model"]
        try:
            model.add_node(cls, node_name, insert_after=insert_after,
                           extra_kwargs=params, mode=mode)
        except Exception as e:
            return jsonify({"error": str(e)}), 400
        return jsonify(serialize())


@app.route("/")
def index():
    return send_from_directory(Path(__file__).resolve().parent, "live_viewer.html")


if __name__ == "__main__":
    print("Live viewer: http://localhost:5050")
    app.run(host="127.0.0.1", port=5050, debug=True, use_reloader=False)
