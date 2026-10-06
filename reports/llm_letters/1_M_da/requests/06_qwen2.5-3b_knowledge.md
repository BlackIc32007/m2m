# Запрос 6: qwen2.5:3b, вопрос №13 (знание)

Буквы: **M = да**, **K = нет**. Полный запрос и ответ Ollama — `06_qwen2.5-3b_knowledge.json`.

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
| 1 | `K` | 1.000000 |
| 2 | `Ｋ` | 0.000000 |
| 3 | `К` | 0.000000 |
| 4 | ` K` | 0.000000 |
| 5 | `KHTML` | 0.000000 |
| 6 | `k` | 0.000000 |
| 7 | `	K` | 0.000000 |
| 8 | `Ka` | 0.000000 |
| 9 | `_K` | 0.000000 |
| 10 | `-K` | 0.000000 |

## Как это превращается в решение

- P(M) = 0.0000 (это «да»), P(K) = 1.0000 (это «нет»)
- mass = P(да) + P(нет) = 1.0000
- ответ: **K** = **нет**, уверенность = max / mass = 1.000
- правильный ответ: нет — верно
