# Запрос 6: qwen2.5:3b, вопрос №13 (знание)

Буквы: **K = да**, **M = нет**. Полный запрос и ответ Ollama — `06_qwen2.5-3b_knowledge.json`.

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
| 1 | `M` | 1.000000 |
| 2 | `K` | 0.000000 |
| 3 | `N` | 0.000000 |
| 4 | `М` | 0.000000 |
| 5 | `Ｍ` | 0.000000 |
| 6 | ` M` | 0.000000 |
| 7 | `(M` | 0.000000 |
| 8 | `MX` | 0.000000 |
| 9 | `<M` | 0.000000 |
| 10 | `J` | 0.000000 |

## Как это превращается в решение

- P(K) = 0.0000 (это «да»), P(M) = 1.0000 (это «нет»)
- mass = P(да) + P(нет) = 1.0000
- ответ: **M** = **нет**, уверенность = max / mass = 1.000
- правильный ответ: нет — верно
