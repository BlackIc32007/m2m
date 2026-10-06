# Запрос 10: qwen3.5:9b, вопрос №13 (знание)

Буквы: **K = да**, **M = нет**. Полный запрос и ответ Ollama — `10_qwen3.5-9b_knowledge.json`.

## Что отправлено (`/api/chat`)

Параметры: `temperature 0`, `num_predict 1` (один токен), `logprobs`, `top_logprobs 10`, `think false`.

**system:**

```
You answer yes/no questions with exactly one letter. K means YES. M means NO. Output only K or M.
```

**user:**

```
Is fire hot?
```

**assistant:**

```
K
```

**user:**

```
Is 1 greater than 3?
```

**assistant:**

```
M
```

**user:**

```
Do cats have six legs?
```

## Что вернула модель

Сгенерированный токен: `M`

| # | токен | вероятность |
|---|---|---|
| 1 | `M` | 0.997166 |
| 2 | `K` | 0.002653 |
| 3 | ` M` | 0.000112 |
| 4 | `No` | 0.000008 |
| 5 | `m` | 0.000006 |
| 6 | `The` | 0.000006 |
| 7 | `A` | 0.000004 |
| 8 | `<think>` | 0.000003 |
| 9 | `М` | 0.000003 |
| 10 | `C` | 0.000002 |

## Как это превращается в решение

- P(K) = 0.0027 (это «да»), P(M) = 0.9973 (это «нет»)
- mass = P(да) + P(нет) = 0.9999
- ответ: **M** = **нет**, уверенность = max / mass = 0.997
- правильный ответ: нет — верно
