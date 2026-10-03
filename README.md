# M2M — открытая инфраструктура для экспериментов с агентной системой

Минимальный экспериментальный полигон на Mesa (agent-based modeling) с
опциональной интеграцией локальной LLM через Ollama. Первый этап задания:
инфраструктура, а не интеллектуальная агентная логика.

**Общий отчёт (часть 1 — LLM «одна буква», часть 2 — проект m2m) —
[`docs/report.md`](docs/report.md).**

**Отчёт по первому заданию (разделы 1–6, проблемы, предложения, заделы
второго этапа) — [`docs/report_stage1.md`](docs/report_stage1.md).**

Быстрая проверка всех 11 пунктов демонстрации из задания:

```bash
python experiments/check_all.py      # ✔/✘ по каждому пункту + версии компонентов
```

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
| networkx, pandas, numpy, scipy, matplotlib | см. `requirements.txt` (версии закреплены) |
| Ollama | 0.20.7 (модели `qwen2.5:1.5b`, `qwen2.5:3b`, `qwen3.5:9b`) |
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
│   │   ├── pipeline_model.py    # Mesa Model: Pump -> Valve -> Tank (варианты клапана)
│   │   ├── conflict_model.py    # Mesa Model: источник, зоны, 5 механизмов распределения
│   │   └── zone_policies.py     # как решает зона: правило / LLM
│   └── llm/
│       ├── ollama_client.py     # вызов Ollama, парсинг JSON-ответа
│       ├── node_advisor.py      # Mesa Node State -> Ollama -> Recommendation
│       ├── token_decision.py    # решение одним токеном с уверенностью
│       └── zone_context.py      # текст контекста зоны для LLM
├── experiments/
│   ├── check_all.py             # проверка 11 пунктов демонстрации
│   ├── run_demo.py              # демо-сценарий из задания
│   ├── json_stability.py        # насколько стабильно LLM возвращает JSON
│   ├── conflict_collision.py, llm_*.py   # эксперименты второго этапа
│   └── results/                 # таблицы результатов
├── tests/                       # unittest, 28 тестов
├── logs/                        # сюда пишутся events.jsonl и llm_calls.jsonl
├── docs/                        # отчёты, domains.md, figures/
├── docker/                      # Dockerfile, docker-compose.yml
├── live_server.py, live_viewer.html   # веб-визуализация
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

## Режимы работы узлов: пассивный и автономный

Режим задаётся параметром `decision_mode` и переключается на ходу (в коде,
через `--mode` в `run_demo.py` и выпадающим списком в веб-интерфейсе).
Работает во всех моделях -- и в цепочках, и в моделях конфликта.

**Пассивный** (`passive`, по умолчанию) -- узлы не принимают решений:
- в цепочке узел принимает задачу, если в очереди есть место, обрабатывает
  и передаёт дальше;
- в модели конфликта зона запрашивает ровно свою реальную потребность.

**Автономный** (`autonomous`) -- каждый узел решает сам, глядя только на
свою ситуацию:
- в цепочке: **REFUSE** новых задач, если очередь >= 80% или следующий узел
  в отказе; снова **ACCEPT**, когда очередь < 50% и следующий узел работает.
  Клапаны (ValveAgent*) используют своё правило (MODIFY / REFUSE);
- в модели конфликта зона выбирает: **ACCEPT** -- запросить потребность,
  **REFUSE** -- уступить ресурс, если запас мал (не срочно), **MODIFY** --
  завысить запрос в 2 раза, если недополучает 2+ шага подряд. Больше
  потребности зона использовать не может, излишек теряется.

Решения узлов цепочки с причиной пишутся в `logs/events.jsonl`
(`event: decision_REFUSE / decision_ACCEPT`, поле `details.reason`); решения
зон видны в панели метрик конфликта и в `state_dict()` зоны.

```bash
python experiments/run_demo.py --mode passive
python experiments/run_demo.py --mode autonomous
```

**Автономный (LLM)** -- третий пункт в веб-интерфейсе, только у моделей
конфликта: решение каждой зоны принимает локальная `qwen2.5:1.5b` одним
токеном (с устранением смещения к букве и случайным выбором с вероятностью
P(да)). В причине решения видны вероятности ответов LLM, в инспекторе зоны --
поля `llm_p_yield`, `llm_p_inflate`, `llm_mass`. Один шаг занимает ~1–2 с.
Если Ollama недоступна, пункт не включится, а если она пропадёт во время
работы -- зоны решают по правилу (это видно в причине решения).

## Тесты

```bash
python -m unittest discover -s tests -v
```

`tests/test_conflict.py` -- модель конфликта: корректность распределения,
коллизии (кто получает воду при нехватке, в том числе зоны с равным
приоритетом), конфликт целей (эффективность не выше оптимума, где вредит
завышение запросов), учёт воды (произведено = использовано + потеряно +
осталось в баке), отказы. `tests/test_chain.py` -- цепочки: задачи не
теряются, отказы и восстановление, решения узлов в двух режимах, ветвление.

## Эксперимент: коллизия и конфликт без LLM

```bash
python experiments/conflict_collision.py    # ~20 с
```

5 механизмов распределения × 5 уровней воды × 4 поведения зон (честно /
одна зона завышает запрос / все завышают). Измеряет, кого обделяет
коллизия, и где конфликт «зоне выгодно -- системе вредно» существует на
самом деле. Отчёт -- `docs/conflict_collision_report.md`.

## Эксперименты: решение зоны локальной LLM одним токеном

В модели конфликта решение зоны (автономный режим) может принимать локальная
LLM: она отвечает ровно одним токеном (M = да / K = нет), а из вероятностей
токенов считаются уверенность (`confidence`) и здоровье промпта (`mass`).
Ядро -- `src/llm/token_decision.py`, текст контекста зоны --
`src/llm/zone_context.py`, политики (правило / LLM) -- `src/model/zone_policies.py`.

Нужна Ollama с поддержкой `logprobs` (проверено на 0.20.7) и модель
`qwen2.5:1.5b` (контрольная -- `qwen2.5:3b`).

```bash
python experiments/llm_sanity.py            # этап 0: 6/6 и mass >= 0.9
python experiments/llm_open_loop.py         # этап 1 и 4: без обратной связи, ~7 мин
python experiments/llm_closed_loop.py       # этапы 2-3: замкнутый цикл
python experiments/llm_closed_loop.py --sensitivity   # чувствительность правила
python experiments/llm_analyze.py           # таблицы (experiments/results/summary.md) и рисунки (docs/figures)
```

Отчёт с результатами -- `docs/llm_experiment_report.md`.

Хитрят ли LLM там, где это выгодно (эталон -- карта стимулов из
`conflict_collision.py`; модели qwen3.5:9b / qwen2.5:3b / qwen2.5:1.5b):

```bash
python experiments/llm_incentives.py        # ~25 мин, запросы последовательные
```

Отчёт -- `docs/llm_incentives_report.md`.

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

### Доступ с других устройств (ngrok)

Чтобы открыть визуализацию с телефона или другого компьютера:

```bash
ngrok config add-authtoken <токен>        # один раз; токен — на dashboard.ngrok.com
python live_server.py --ngrok --password <пароль от 8 символов>
```

Сервер напечатает ссылку `https://….ngrok-free.dev`; вход — логин `m2m` и
этот пароль. Пароль можно задать переменной `LIVE_PASSWORD`, токен —
переменной `NGROK_AUTHTOKEN` (вместо `ngrok config`). Без `--password`
модель сможет переключать любой, у кого есть ссылка. Через ngrok отладчик
Flask выключен, туннель закрывается вместе с сервером (Ctrl+C). При первом
открытии бесплатный ngrok показывает страницу-предупреждение — нажать
«Visit Site».

Сравнение вариантов клапана (ACCEPT/REFUSE/MODIFY):

```bash
python experiments/compare_valves.py --steps 60
```

## Проверка отдельного вызова Ollama

Без Mesa, просто проверить, что Ollama доступна и возвращает JSON:

```bash
python -m src.llm.ollama_client
python experiments/json_stability.py   # 27 состояний × 3 модели: формат и смысл ответа, ~3 мин
```

Адрес сервера берётся из переменной `OLLAMA_HOST` (по умолчанию
`localhost:11434`).

## Docker

```bash
cd docker
docker compose up --build     # ollama + скачивание qwen2.5:1.5b + демо-сценарий с LLM
```

Журналы появятся в `logs/` на хосте. Веб-визуализация из контейнера:
`docker compose run --service-ports app python live_server.py` →
http://localhost:5050. Если Ollama уже запущена на хосте, достаточно
одного образа:

```bash
docker build -f docker/Dockerfile -t m2m-app .
docker run --rm --network host m2m-app python experiments/check_all.py
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

## Что сделано сверх первого этапа

В основном стенде (цепочка Input → … → Output) LLM, как требует задание,
только советует. Как задел для второго этапа (Global Goal → Local Context →
Agent → ACCEPT/REFUSE/MODIFY) сделаны: автономный режим узлов (правила
ACCEPT/REFUSE), модель конфликта «зона против системы» и три эксперимента,
в том числе с LLM, принимающей решения за зону. Режим, где решает LLM, есть
только в модели конфликта и по умолчанию выключен. Подробно — раздел 7
отчёта `docs/report_stage1.md`.

Не делалось: собственный семантический язык, реальный производственный
процесс, Arduino, физический цифровой двойник.
