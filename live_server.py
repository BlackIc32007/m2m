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
import argparse
import atexit
import importlib
import inspect
import json
import os
import subprocess
import tempfile
import time
import pkgutil
import signal
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
from src.model.zone_policies import RulePolicy, TokenLLMPolicy
from src.llm import token_decision
from src.llm.zone_context import BLOCKS

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


# Режимы в интерфейсе:
#   passive         -- узлы/зоны не принимают решений
#   autonomous      -- решают по правилу (пороги)
#   autonomous_llm  -- только модели конфликта: решает локальная LLM одним
#                      токеном (debias + случайный выбор с вероятностью P(ДА),
#                      иначе qwen2.5:1.5b почти всегда отвечает ACCEPT --
#                      см. docs/llm_experiment_report.md)
UI_MODES = ("passive", "autonomous", "autonomous_llm")


def _llm_policy():
    return TokenLLMPolicy(blocks=BLOCKS, debias=True, sample=True)


def _ollama_ok() -> bool:
    try:
        import requests
        return requests.get(f"{token_decision.OLLAMA_HOST}/api/version", timeout=2).ok
    except Exception:
        return False


def _apply_decision_mode(model) -> None:
    # режим сохраняется при пересоздании модели; у цепочек LLM нет --
    # для них "autonomous_llm" означает обычный автономный режим (правило)
    if not hasattr(model, "set_decision_mode"):
        return
    mode = state["decision_mode"]
    if mode == "autonomous_llm" and isinstance(model, ConflictModel):
        model.zone_policy = _llm_policy()
    elif isinstance(model, ConflictModel):
        model.zone_policy = RulePolicy()
    model.set_decision_mode("passive" if mode == "passive" else "autonomous")


def _ui_mode(model):
    mode = getattr(model, "decision_mode", None)
    if mode == "autonomous" and isinstance(getattr(model, "zone_policy", None), TokenLLMPolicy):
        return "autonomous_llm"
    return mode

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
        "decision_mode": _ui_mode(model),
        "llm_available": isinstance(model, ConflictModel),  # пункт "автономный (LLM)" -- только у конфликтных
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
    """Переключить режим: "passive", "autonomous" (правило) или
    "autonomous_llm" (решает локальная LLM; только модели конфликта).
    Действует сразу, без пересоздания модели."""
    body = request.get_json(force=True)
    mode = body.get("mode")
    if mode not in UI_MODES:
        return jsonify({"error": f"unknown decision_mode '{mode}', expected one of {UI_MODES}"}), 400
    with model_lock:
        model = state["model"]
        if not hasattr(model, "set_decision_mode"):
            return jsonify({"error": "у этой модели нет режимов работы узлов"}), 400
        if mode == "autonomous_llm":
            if not isinstance(model, ConflictModel):
                return jsonify({"error": "LLM подключена только к моделям конфликта"}), 400
            if not _ollama_ok():
                return jsonify({"error": "Ollama недоступна -- запустите `ollama serve`"}), 400
        state["decision_mode"] = mode
        _apply_decision_mode(model)
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


PORT = 5050


def start_ngrok(port: int, password: str | None) -> str:
    """Поднять туннель ngrok к локальному порту и вернуть публичный URL.

    Токен ngrok берётся из переменной NGROK_AUTHTOKEN, а если её нет -- из
    конфига ngrok (`ngrok config add-authtoken <токен>`); в репозиторий он не
    попадает. password -- пароль на вход (логин m2m) через правило
    basic-auth ngrok; без него страница открыта всем, у кого есть ссылка.
    """
    cmd = ["ngrok", "http", str(port), "--log", "stdout", "--log-format", "json"]
    token = os.environ.get("NGROK_AUTHTOKEN", "").strip()
    if token:
        # сам ngrok эту переменную не читает, а в аргументах командной строки
        # токен был бы виден в списке процессов -- передаём временным конфигом
        conf = tempfile.NamedTemporaryFile("w", suffix=".yml", delete=False)
        os.chmod(conf.name, 0o600)
        conf.write(f'version: "3"\nagent:\n  authtoken: {json.dumps(token)}\n')
        conf.close()
        atexit.register(os.unlink, conf.name)
        cmd += ["--config", conf.name]
    if password:
        if len(password) < 8:
            raise SystemExit("Пароль для ngrok должен быть не короче 8 символов.")
        policy = {"on_http_request": [{"actions": [
            {"type": "basic-auth", "config": {"credentials": [f"m2m:{password}"]}}]}]}
        policy_file = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        json.dump(policy, policy_file)
        policy_file.close()
        atexit.register(os.unlink, policy_file.name)
        cmd += ["--traffic-policy-file", policy_file.name]

    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    except FileNotFoundError:
        raise SystemExit("ngrok не найден: установите его (https://ngrok.com/download).")
    atexit.register(proc.terminate)

    # ngrok пишет журнал строками JSON; ждём строку с URL или с ошибкой
    deadline = time.time() + 20
    for line in proc.stdout:
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("url", "").startswith("https://"):
            # дальше журнал ngrok не нужен, но его надо вычитывать, иначе
            # переполненный буфер остановит процесс
            threading.Thread(target=lambda: [None for _ in proc.stdout], daemon=True).start()
            return rec["url"]
        if rec.get("lvl") in ("eror", "crit") or "ERR_NGROK" in line:
            proc.terminate()
            raise SystemExit(f"ngrok не запустился: {rec.get('err') or rec.get('msg') or line.strip()}")
        if time.time() > deadline:
            break
    proc.terminate()
    raise SystemExit("ngrok не вернул адрес туннеля за 20 с.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Веб-визуализация Mesa-модели")
    parser.add_argument("--ngrok", action="store_true",
                        help="открыть доступ с других устройств через туннель ngrok")
    parser.add_argument("--password", default=os.environ.get("LIVE_PASSWORD"),
                        help="пароль на вход через ngrok (логин m2m), не короче 8 символов; "
                             "можно задать переменной LIVE_PASSWORD")
    args = parser.parse_args()

    # LIVE_HOST=0.0.0.0 -- доступ снаружи (в Docker). Отладчик Flask включён
    # только для чисто локального запуска: он позволяет выполнять код из
    # браузера, поэтому через Docker или ngrok он выключен.
    host = os.environ.get("LIVE_HOST", "127.0.0.1")
    debug = host == "127.0.0.1" and not args.ngrok
    print(f"Live viewer: http://localhost:{PORT}")
    if args.ngrok:
        # kill / закрытие терминала (SIGTERM, SIGHUP) по умолчанию не вызывают
        # atexit -- туннель остался бы открытым; превращаем их в обычный выход
        for sig in (signal.SIGTERM, signal.SIGHUP):
            signal.signal(sig, lambda *_: sys.exit(0))
        url = start_ngrok(PORT, args.password)
        print(f"С других устройств: {url}")
        if args.password:
            print("Вход: логин m2m и пароль из --password / LIVE_PASSWORD")
        else:
            print("Внимание: пароля нет -- управлять моделью может любой, у кого есть ссылка "
                  "(добавьте --password).")
    app.run(host=host, port=PORT, debug=debug, use_reloader=False)
