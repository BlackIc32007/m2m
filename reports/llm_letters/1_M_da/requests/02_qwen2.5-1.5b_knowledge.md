# Запрос 2: qwen2.5:1.5b, вопрос №13 (знание)

Буквы: **M = да**, **K = нет**. Полный запрос и ответ Ollama — `02_qwen2.5-1.5b_knowledge.json`.

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
| 1 | `K` | 0.990180 |
| 2 | `M` | 0.009603 |
| 3 | `k` | 0.000057 |
| 4 | `N` | 0.000041 |
| 5 | `No` | 0.000014 |
| 6 | `F` | 0.000012 |
| 7 | `I` | 0.000009 |
| 8 | `L` | 0.000008 |
| 9 | `C` | 0.000007 |
| 10 | `A` | 0.000006 |

## Как это превращается в решение

- P(M) = 0.0096 (это «да»), P(K) = 0.9902 (это «нет»)
- mass = P(да) + P(нет) = 0.9998
- ответ: **K** = **нет**, уверенность = max / mass = 0.990
- правильный ответ: нет — верно
