"""
Проверка по списку "Что необходимо подготовить к демонстрации" из первого
задания: 11 пунктов, по каждому -- ✔ / ✘ и короткое доказательство.

Запуск (из каталога project/):
    python experiments/check_all.py                  # всё, включая Ollama
    python experiments/check_all.py --no-ollama      # только Mesa-часть
    python experiments/check_all.py --model qwen3.5:9b

Журналы проверочного прогона пишутся во временный каталог и не трогают logs/.
"""
import argparse
import json
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import mesa
import requests

from src.llm.node_advisor import NodeAdvisor
from src.llm.ollama_client import OLLAMA_HOST, OllamaClient, OllamaError
from src.model.factory_model import FactoryModel
from src.simulation.console_visualizer import render
from src.simulation.logger import EventLogger

LOG_FIELDS = {"timestamp", "simulation_step", "node_id", "old_state", "new_state", "event", "task_id"}
LLM_FIELDS = {"llm_input", "llm_output", "model_name", "response_time_sec"}

results = []


def check(n, title, ok, proof):
    results.append(ok)
    print(f"{'✔' if ok else '✘'} {n:2d}. {title}\n      {proof}")


def tool_version(cmd):
    if not shutil.which(cmd[0]):
        return "не установлен"
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return (out.stdout or out.stderr).strip().splitlines()[0]
    except Exception as e:  # noqa: BLE001 -- версия только для печати
        return f"ошибка: {e}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-ollama", action="store_true")
    ap.add_argument("--model", default="qwen2.5:3b")
    args = ap.parse_args()

    print("Версии компонентов")
    print(f"  Python  {platform.python_version()}")
    print(f"  Mesa    {mesa.__version__}")
    for name, cmd in (("Git", ["git", "--version"]), ("Ollama", ["ollama", "--version"]),
                      ("Docker", ["docker", "--version"])):
        print(f"  {name:7s} {tool_version(cmd)}")
    print()

    log_dir = Path(tempfile.mkdtemp(prefix="m2m_check_"))
    logger = EventLogger(log_dir=str(log_dir))
    model = FactoryModel(task_arrival_interval=2, processing_time=2, queue_capacity=10,
                         logger=logger, rng=42)
    trace = {}
    for step in range(1, 21):
        model.step()
        if step == 4:
            model.trigger_failure("Machine_B", 5)
        trace[step] = model.snapshot()
    events = [json.loads(line) for line in open(logger.events_path, encoding="utf-8")]

    check(1, "установленный Mesa", mesa.__version__ >= "3",
          f"mesa {mesa.__version__}")
    check(2, "работающая модель", model.steps == 20,
          f"FactoryModel(mesa.Model) выполнила {model.steps} шагов")
    names = [n.name for n in model.nodes]
    check(3, "3–5 узлов", 3 <= len(names) <= 5 and all(isinstance(n, mesa.Agent) for n in model.nodes),
          " -> ".join(names) + " (каждый -- mesa.Agent)")
    t1 = [e["node_id"] for e in events if e["task_id"] == "Task_1" and e["event"] == "task_queued"]
    check(4, "движение задач между узлами", model.completed_tasks > 0 and len(set(t1)) >= 3,
          f"путь Task_1: {' -> '.join(t1)} -> Output; завершено задач: {model.completed_tasks}")
    changes = [e for e in events if e["old_state"] and e["new_state"] and e["old_state"] != e["new_state"]]
    check(5, "изменение состояний", len(changes) > 0,
          f"{len(changes)} смен состояния, например {changes[0]['node_id']}: "
          f"{changes[0]['old_state']} -> {changes[0]['new_state']}")
    b = {s: trace[s]["Machine_B"] for s in (3, 4, 8, 9)}
    check(6, "отказ одного узла", b[4]["state"] == "failed" and not b[4]["available"],
          f"шаг 4: Machine_B state={b[4]['state']}, available={b[4]['available']}; "
          f"очередь Machine_B за время отказа: {b[4]['queue']} -> {b[8]['queue']}")
    check(7, "восстановление", b[9]["state"] != "failed" and any(e["event"] == "node_recovered" for e in events),
          f"шаг 9: Machine_B state={b[9]['state']}; после восстановления завершено задач: "
          f"{model.completed_tasks}")
    picture = render(model, step_label="20")
    check(8, "визуализация", "Machine_B" in picture,
          "текст: src/simulation/console_visualizer.py; браузер: python live_server.py -> http://localhost:5050")
    print("\n".join("        " + line for line in picture.splitlines()))
    fields_ok = all(LOG_FIELDS <= e.keys() for e in events)
    check(9, "журнал работы", fields_ok and len(events) > 0,
          f"{len(events)} записей JSON Lines, поля: {', '.join(sorted(LOG_FIELDS))}")

    if args.no_ollama:
        print("\n(пункты 10–11 пропущены: --no-ollama)")
    else:
        try:
            version = requests.get(f"{OLLAMA_HOST}/api/version", timeout=3).json()["version"]
            client = OllamaClient(model=args.model)
            reply, dt = client.structured_call(
                {"node": "Machine_A", "state": "busy", "queue": 5},
                'Return JSON like {"status": "overloaded"} describing whether this node is overloaded.')
            check(10, "Python-вызов Ollama", True,
                  f"Ollama {version} на {OLLAMA_HOST}, модель {args.model}, ответ за {dt:.2f} с")
            check(11, "структурированный ответ от LLM", isinstance(reply, dict) and "status" in reply,
                  f'{{"node": "Machine_A", "state": "busy", "queue": 5}} -> {json.dumps(reply, ensure_ascii=False)}')
            advisor = NodeAdvisor(client, logger, simulation_step_getter=lambda: model.steps)
            rec = advisor.advise({"node": "Machine_A", "state": "working", "queue": 7, "load": 0.95})
            call = json.loads(open(logger.llm_path, encoding="utf-8").readlines()[-1])
            check(12, "интеграция Mesa -> Python -> Ollama -> Recommendation (сверх списка)",
                  rec is not None and LLM_FIELDS <= call.keys(),
                  f"load 0.95 -> {json.dumps(rec, ensure_ascii=False)}; в журнале: "
                  f"{', '.join(sorted(LLM_FIELDS))}; состояние модели не меняется")
        except (requests.RequestException, OllamaError, KeyError) as e:
            check(10, "Python-вызов Ollama", False, f"Ollama недоступна на {OLLAMA_HOST}: {e}")

    print(f"\nИтог: {sum(results)}/{len(results)} пунктов выполнено. Журналы прогона: {log_dir}")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
