# Запрос 5: qwen2.5:3b, вопрос №1 (знание)

Буквы: **K = да**, **M = нет**. Полный запрос и ответ Ollama — `05_qwen2.5-3b_knowledge.json`.

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
| 1 | `K` | 1.000000 |
| 2 | ` K` | 0.000000 |
| 3 | `M` | 0.000000 |
| 4 | `k` | 0.000000 |
| 5 | `Ｋ` | 0.000000 |
| 6 | `	K` | 0.000000 |
| 7 | `(K` | 0.000000 |
| 8 | `.K` | 0.000000 |
| 9 | `_K` | 0.000000 |
| 10 | `К` | 0.000000 |

## Как это превращается в решение

- P(K) = 1.0000 (это «да»), P(M) = 0.0000 (это «нет»)
- mass = P(да) + P(нет) = 1.0000
- ответ: **K** = **да**, уверенность = max / mass = 1.000
- правильный ответ: да — верно
