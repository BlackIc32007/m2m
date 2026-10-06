# Запрос 1: qwen2.5:1.5b, вопрос №1 (знание)

Буквы: **K = да**, **M = нет**. Полный запрос и ответ Ollama — `01_qwen2.5-1.5b_knowledge.json`.

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
| 1 | `K` | 0.998171 |
| 2 | `M` | 0.001648 |
| 3 | `Yes` | 0.000043 |
| 4 | `Y` | 0.000042 |
| 5 | `k` | 0.000024 |
| 6 | `N` | 0.000023 |
| 7 | `T` | 0.000006 |
| 8 | `S` | 0.000004 |
| 9 | `No` | 0.000003 |
| 10 | `C` | 0.000003 |

## Как это превращается в решение

- P(K) = 0.9982 (это «да»), P(M) = 0.0016 (это «нет»)
- mass = P(да) + P(нет) = 0.9998
- ответ: **K** = **да**, уверенность = max / mass = 0.998
- правильный ответ: да — верно
