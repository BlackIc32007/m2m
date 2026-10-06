# Запрос 10: qwen3.5:9b, вопрос №13 (знание)

Буквы: **M = да**, **K = нет**. Полный запрос и ответ Ollama — `10_qwen3.5-9b_knowledge.json`.

## Что отправлено (`/api/chat`)

Параметры: `temperature 0`, `num_predict 1` (один токен), `logprobs`, `top_logprobs 10`, `think false`.

**system:**

```
You answer yes/no questions with exactly one letter. M means YES. K means NO. Output only M or K.
```

**user:**

```
Is fire hot?
```

**assistant:**

```
M
```

**user:**

```
Is 1 greater than 3?
```

**assistant:**

```
K
```

**user:**

```
Do cats have six legs?
```

## Что вернула модель

Сгенерированный токен: `K`

| # | токен | вероятность |
|---|---|---|
| 1 | `K` | 0.995692 |
| 2 | `M` | 0.004131 |
| 3 | ` K` | 0.000138 |
| 4 | `k` | 0.000008 |
| 5 | `A` | 0.000004 |
| 6 | `No` | 0.000003 |
| 7 | `C` | 0.000002 |
| 8 | `B` | 0.000002 |
| 9 | `F` | 0.000002 |
| 10 | `N` | 0.000001 |

## Как это превращается в решение

- P(M) = 0.0041 (это «да»), P(K) = 0.9958 (это «нет»)
- mass = P(да) + P(нет) = 1.0000
- ответ: **K** = **нет**, уверенность = max / mass = 0.996
- правильный ответ: нет — верно
