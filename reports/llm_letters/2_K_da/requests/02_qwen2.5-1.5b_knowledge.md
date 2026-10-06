# Запрос 2: qwen2.5:1.5b, вопрос №13 (знание)

Буквы: **K = да**, **M = нет**. Полный запрос и ответ Ollama — `02_qwen2.5-1.5b_knowledge.json`.

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
| 1 | `M` | 0.890254 |
| 2 | `K` | 0.109257 |
| 3 | `N` | 0.000197 |
| 4 | `No` | 0.000074 |
| 5 | `L` | 0.000046 |
| 6 | `F` | 0.000019 |
| 7 | `C` | 0.000016 |
| 8 | `I` | 0.000013 |
| 9 | `A` | 0.000011 |
| 10 | `Yes` | 0.000009 |

## Как это превращается в решение

- P(K) = 0.1093 (это «да»), P(M) = 0.8903 (это «нет»)
- mass = P(да) + P(нет) = 0.9995
- ответ: **M** = **нет**, уверенность = max / mass = 0.891
- правильный ответ: нет — верно
