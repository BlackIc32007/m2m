# Запрос 1: qwen2.5:1.5b, вопрос №1 (знание)

Буквы: **M = да**, **K = нет**. Полный запрос и ответ Ollama — `01_qwen2.5-1.5b_knowledge.json`.

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
| 1 | `M` | 0.950580 |
| 2 | `K` | 0.049028 |
| 3 | `Y` | 0.000100 |
| 4 | `N` | 0.000087 |
| 5 | `Yes` | 0.000082 |
| 6 | `S` | 0.000018 |
| 7 | `m` | 0.000012 |
| 8 | `A` | 0.000012 |
| 9 | `T` | 0.000011 |
| 10 | `L` | 0.000008 |

## Как это превращается в решение

- P(M) = 0.9506 (это «да»), P(K) = 0.0490 (это «нет»)
- mass = P(да) + P(нет) = 0.9996
- ответ: **M** = **да**, уверенность = max / mass = 0.951
- правильный ответ: да — верно
