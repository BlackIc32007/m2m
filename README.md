# M2M — открытая инфраструктура для экспериментов с агентной системой

Минимальный экспериментальный полигон на Mesa (agent-based modeling) с
опциональной интеграцией локальной LLM через Ollama. Первый этап задания:
инфраструктура, а не интеллектуальная агентная логика.

## Стек

- Python 3.10+
- [Mesa](https://mesa.readthedocs.io/) — agent-based modeling
- [Ollama](https://ollama.com/) — локальный запуск LLM
- Git

## Установка

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Версии, на которых проект проверен:

| Компонент | Версия |
|---|---|
| Python | 3.12.3 |
| Mesa | 3.5.1 |
| Flask | 3.1.3 |
| Solara | 1.62.0 (опционально, для `experiments/gui.py`) |
| Ollama | 0.20.7 (модель `qwen2.5:3b`) |
| Git | 2.43.0 |
| Docker | 29.1.3 |
| ОС | Ubuntu 24.04 |

Проверить версии у себя:

```bash
python3 --version
python3 -c "import mesa; print('Mesa', mesa.__version__)"
git --version
ollama --version
docker --version
```

Ollama должна быть запущена отдельно и иметь загруженную модель:

```bash
ollama serve                 # если не запущена как сервис
ollama pull qwen2.5:3b       # или любая другая модель по вкусу
```

## Структура проекта

```
project/
├── README.md
├── requirements.txt
├── src/
│   ├── model/
│   │   ├── chain_mixin.py       # общий код цепочки: шаг через Mesa AgentSet, отказы, add_node
│   │   └── factory_model.py     # Mesa Model: Input -> A -> Buffer -> B -> Output
│   ├── agents/
│   │   ├── node_agent.py        # Mesa Agent: узел со состоянием
│   │   ├── endpoint_agents.py   # Mesa Agent: Input (источник задач) и Output (сток)
│   │   └── task.py              # класс задачи
│   ├── simulation/
│   │   ├── logger.py            # запись событий и вызовов LLM в logs/*.jsonl
│   │   └── console_visualizer.py# текстовая визуализация состояния
│   └── llm/
│       ├── ollama_client.py     # вызов Ollama, парсинг JSON-ответа
│       └── node_advisor.py      # Mesa Node State -> Ollama -> Recommendation
├── experiments/
│   └── run_demo.py              # запускаемый демо-сценарий
├── logs/                        # сюда пишутся events.jsonl и llm_calls.jsonl
├── docs/
└── docker/
```

## Запуск демо-сценария

Сценарий: поступают Task 1–3, Machine_A начинает обработку, во время работы
Machine_B отказывает, задачи накапливаются в очереди, затем Machine_B
восстанавливается и система продолжает работу.

```bash
# без Ollama — только Mesa
python experiments/run_demo.py --steps 20 --fail-at 4 --fail-duration 5

# с интеграцией Ollama (на каждом шаге запрашивается рекомендация для занятых узлов)
python experiments/run_demo.py --steps 20 --fail-at 4 --fail-duration 5 --with-ollama --model qwen2.5:3b
```

Параметры:
- `--steps` — сколько шагов модели прогнать
- `--fail-at` — на каком шаге Machine_B отказывает
- `--fail-duration` — на сколько шагов
- `--with-ollama` — включить запросы к Ollama
- `--model` — имя модели Ollama
- `--quiet` — не печатать визуализацию на каждом шаге, только итог

## Два режима узлов: «просто труба» и «агент решает»

- `pipe` (по умолчанию) -- узлы ничего не решают: принимают задачу, если в
  очереди есть место, обрабатывают и передают дальше.
- `agent` -- каждый узел сам решает, принимать ли новые задачи, глядя только
  на свою ситуацию: **REFUSE**, если очередь >= 80% или следующий узел в
  отказе; снова **ACCEPT**, когда очередь < 50% и следующий узел работает.
  Клапаны (ValveAgent*) используют своё правило (MODIFY / REFUSE).
  Каждое решение с причиной пишется в `logs/events.jsonl`
  (`event: decision_REFUSE / decision_ACCEPT`, поле `details.reason`).

```bash
python experiments/run_demo.py --mode pipe
python experiments/run_demo.py --mode agent
```

В веб-интерфейсе режим переключается выпадающим списком на ходу.

## Веб-визуализация (живая модель в браузере)

```bash
python live_server.py
# открыть http://localhost:5050
```

Видно узлы, связи, состояние (IDLE / WORKING / BLOCKED / FAILED), текущую
задачу и очередь каждого узла. Кнопками можно делать шаги, вызывать отказ и
восстановление любого узла (включая Input и Output) и добавлять новые узлы
в цепочку на лету. В выпадающем списке -- модели factory, pipeline и
модели конфликта «зона vs система».

Сравнение вариантов клапана (ACCEPT/REFUSE/MODIFY):

```bash
python experiments/compare_valves.py --steps 60
```

## Проверка отдельного вызова Ollama

Без Mesa, просто проверить, что Ollama доступна и возвращает JSON:

```bash
python -m src.llm.ollama_client
```

## Логи

- `logs/events.jsonl` — история модели: timestamp, simulation_step, node_id,
  old_state, new_state, event, task_id (одна JSON-запись на строку)
- `logs/llm_calls.jsonl` — вызовы Ollama: simulation_step, node_id, model_name,
  llm_input, llm_output, response_time_sec, error

Прочитать логи в pandas:

```python
import pandas as pd
events = pd.read_json("logs/events.jsonl", lines=True)
```

## Что уже реализовано (соответствие заданию)

- [x] создание нескольких узлов (5 Mesa-агентов: Input, Machine_A, Buffer,
      Machine_B, Output; шаг модели -- через Mesa AgentSet)
- [x] состояние узла: state, current_task, queue, load, available, priority
- [x] изменение состояния во времени, BUSY(working)/IDLE
- [x] появление задач, передача задачи от узла к узлу, очередь
- [x] отказ узла и восстановление, влияние отказа на движение задач:
      задача, прерванная отказом, продолжается после восстановления; если
      следующий узел не принимает задачу, узел переходит в BLOCKED и держит
      её у себя (затор распространяется назад по цепочке, задачи не теряются)
- [x] журналирование событий (JSON Lines)
- [x] простая текстовая визуализация без чтения кода
- [x] вызов локальной LLM из Python со стабильным JSON-ответом
- [x] интеграция Mesa → Python → Ollama → Recommendation (только лог, без
      автоматического изменения состояния модели)

## Что НЕ реализовано на этом этапе (сознательно, по заданию)

Интеллектуальный выбор действий, право LLM менять состояние модели, сложная
multi-agent архитектура, реальный производственный процесс — всё это
запланировано на следующий этап (Global Goal → Local Context → Agent →
ACCEPT/REFUSE/MODIFY).
