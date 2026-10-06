# Запрос 9: qwen3.5:9b, вопрос №1 (знание)

Буквы: **M = да**, **K = нет**. Полный запрос и ответ Ollama — `09_qwen3.5-9b_knowledge.json`.

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
Is the Sun a star?
```

## Что вернула модель

Сгенерированный токен: `M`

| # | токен | вероятность |
|---|---|---|
| 1 | `M` | 0.999048 |
| 2 | `K` | 0.000754 |
| 3 | ` M` | 0.000151 |
| 4 | `A` | 0.000006 |
| 5 | `Yes` | 0.000005 |
| 6 | `The` | 0.000004 |
| 7 | `<\|im_end\|>` | 0.000002 |
| 8 | `I` | 0.000002 |
| 9 | `m` | 0.000002 |
| 10 | `T` | 0.000002 |

## Как это превращается в решение

- P(M) = 0.9992 (это «да»), P(K) = 0.0008 (это «нет»)
- mass = P(да) + P(нет) = 1.0000
- ответ: **M** = **да**, уверенность = max / mass = 0.999
- правильный ответ: да — верно
