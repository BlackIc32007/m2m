# Запрос 9: qwen3.5:9b, вопрос №1 (знание)

Буквы: **K = да**, **M = нет**. Полный запрос и ответ Ollama — `09_qwen3.5-9b_knowledge.json`.

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
Is the Sun a star?
```

## Что вернула модель

Сгенерированный токен: `K`

| # | токен | вероятность |
|---|---|---|
| 1 | `K` | 0.997783 |
| 2 | `M` | 0.002020 |
| 3 | ` K` | 0.000140 |
| 4 | `A` | 0.000007 |
| 5 | `Yes` | 0.000005 |
| 6 | `The` | 0.000005 |
| 7 | `k` | 0.000005 |
| 8 | `C` | 0.000003 |
| 9 | `I` | 0.000002 |
| 10 | `B` | 0.000002 |

## Как это превращается в решение

- P(K) = 0.9979 (это «да»), P(M) = 0.0020 (это «нет»)
- mass = P(да) + P(нет) = 0.9999
- ответ: **K** = **да**, уверенность = max / mass = 0.998
- правильный ответ: да — верно
