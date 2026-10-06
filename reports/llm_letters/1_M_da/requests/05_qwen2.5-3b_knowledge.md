# Запрос 5: qwen2.5:3b, вопрос №1 (знание)

Буквы: **M = да**, **K = нет**. Полный запрос и ответ Ollama — `05_qwen2.5-3b_knowledge.json`.

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
| 1 | `M` | 1.000000 |
| 2 | ` M` | 0.000000 |
| 3 | `K` | 0.000000 |
| 4 | `М` | 0.000000 |
| 5 | `.M` | 0.000000 |
| 6 | `_M` | 0.000000 |
| 7 | `(M` | 0.000000 |
| 8 | `Ｍ` | 0.000000 |
| 9 | `	M` | 0.000000 |
| 10 | `<M` | 0.000000 |

## Как это превращается в решение

- P(M) = 1.0000 (это «да»), P(K) = 0.0000 (это «нет»)
- mass = P(да) + P(нет) = 1.0000
- ответ: **M** = **да**, уверенность = max / mass = 1.000
- правильный ответ: да — верно
