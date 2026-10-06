# Как LLM отвечает одной буквой: M = да, K = нет

Модуль `src/llm/token_decision.py`: модель отвечает ровно одним токеном — буквой **M** (да) или **K** (нет). Из вероятностей этих двух букв считаются ответ, уверенность = max(P) / (P(да) + P(нет)) и mass = P(да) + P(нет).

Модели: `qwen2.5:1.5b`, `qwen2.5:3b`, `qwen3.5:9b`; Ollama, `temperature 0`, запросы последовательные. Вопросов — 60 на модель, одинаковые для всех моделей и для обоих отчётов:

- **20 вопросов на знания** с известным ответом (10 «да», 10 «нет»), без контекста — проверяют, отвечает ли модель по смыслу;
- **40 вопросов агента**: 20 реальных состояний зон из модели конфликта (по 4 на каждый из 5 механизмов, вода 6 при потребности ~10) × «уступить воду в этот шаг?» и «запросить больше, чем нужно?», с полным контекстом (своё состояние, механизм, соседи, цель сети). Правильного ответа здесь нет — смотрим, что модель выбирает.

## Файлы

- `answers.csv` — большая таблица всех ответов (открывается в Excel/LibreOffice); `answers.md` — она же для просмотра;
- `requests/` — запросы целиком: что отправлено в Ollama и что она вернула (топ-10 токенов с вероятностями):

  - [`01_qwen2.5-1.5b_knowledge.md`](requests/01_qwen2.5-1.5b_knowledge.md) — qwen2.5:1.5b, «Is the Sun a star?»
  - [`02_qwen2.5-1.5b_knowledge.md`](requests/02_qwen2.5-1.5b_knowledge.md) — qwen2.5:1.5b, «Do cats have six legs?»
  - [`03_qwen2.5-1.5b_agent.md`](requests/03_qwen2.5-1.5b_agent.md) — qwen2.5:1.5b, «Should Zone1 skip requesting water this step and leave it to the other»
  - [`04_qwen2.5-1.5b_agent.md`](requests/04_qwen2.5-1.5b_agent.md) — qwen2.5:1.5b, «Should Zone1 request more water than its field actually needs this ste»
  - [`05_qwen2.5-3b_knowledge.md`](requests/05_qwen2.5-3b_knowledge.md) — qwen2.5:3b, «Is the Sun a star?»
  - [`06_qwen2.5-3b_knowledge.md`](requests/06_qwen2.5-3b_knowledge.md) — qwen2.5:3b, «Do cats have six legs?»
  - [`07_qwen2.5-3b_agent.md`](requests/07_qwen2.5-3b_agent.md) — qwen2.5:3b, «Should Zone1 skip requesting water this step and leave it to the other»
  - [`08_qwen2.5-3b_agent.md`](requests/08_qwen2.5-3b_agent.md) — qwen2.5:3b, «Should Zone1 request more water than its field actually needs this ste»
  - [`09_qwen3.5-9b_knowledge.md`](requests/09_qwen3.5-9b_knowledge.md) — qwen3.5:9b, «Is the Sun a star?»
  - [`10_qwen3.5-9b_knowledge.md`](requests/10_qwen3.5-9b_knowledge.md) — qwen3.5:9b, «Do cats have six legs?»
  - [`11_qwen3.5-9b_agent.md`](requests/11_qwen3.5-9b_agent.md) — qwen3.5:9b, «Should Zone1 skip requesting water this step and leave it to the other»
  - [`12_qwen3.5-9b_agent.md`](requests/12_qwen3.5-9b_agent.md) — qwen3.5:9b, «Should Zone1 request more water than its field actually needs this ste»

## Итоги по моделям

| модель | знания: верно | верно, где ответ «да» | верно, где ответ «нет» | агент: ответов «да» | агент: средняя P(да) | средняя уверенность | min mass |
|---|---|---|---|---|---|---|---|
| qwen2.5:1.5b | 20/20 | 10/10 | 10/10 | 0/40 | 0.068 | 0.946 | 0.997 |
| qwen2.5:3b | 18/20 | 8/10 | 10/10 | 0/40 | 0.001 | 0.997 | 1.000 |
| qwen3.5:9b | 20/20 | 10/10 | 10/10 | 15/40 | 0.425 | 0.802 | 0.999 |

## Какие буквы выбирает модель

| модель | выбрана M (да) | выбрана K (нет) | средняя P(M) | средняя P(K) |
|---|---|---|---|---|
| qwen2.5:1.5b | 10 | 50 | 0.210 | 0.789 |
| qwen2.5:3b | 8 | 52 | 0.136 | 0.864 |
| qwen3.5:9b | 25 | 35 | 0.450 | 0.550 |

## Вопросы агента

| модель | вопрос | ответов «да» | средняя P(да) | min / max P(да) |
|---|---|---|---|---|
| qwen2.5:1.5b | уступить воду? | 0/20 | 0.053 | 0.034 / 0.073 |
| qwen2.5:1.5b | завысить запрос? | 0/20 | 0.083 | 0.056 / 0.115 |
| qwen2.5:3b | уступить воду? | 0/20 | 0.002 | 0.000 / 0.015 |
| qwen2.5:3b | завысить запрос? | 0/20 | 0.000 | 0.000 / 0.000 |
| qwen3.5:9b | уступить воду? | 6/20 | 0.429 | 0.226 / 0.687 |
| qwen3.5:9b | завысить запрос? | 9/20 | 0.420 | 0.065 / 0.826 |
