# Все ответы (M = да, K = нет)

180 ответов: 60 вопросов × 3 модели. Контекст вопросов агента — в `answers.csv` не входит, он одинаков для всех моделей и показан в примерах в `requests/`. Числа — вероятности токенов-букв.

| № | модель | тип | механизм | зона | вопрос | правильно | буква | ответ | P(M) | P(K) | P(да) | уверенность | mass | верно |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | qwen2.5:1.5b | знание |  |  | Is the Sun a star? | да | M | да | 0.9506 | 0.0490 | 0.9510 | 0.9510 | 0.9996 | да |
| 2 | qwen2.5:1.5b | знание |  |  | Is Paris the capital of France? | да | M | да | 0.9821 | 0.0177 | 0.9823 | 0.9823 | 0.9997 | да |
| 3 | qwen2.5:1.5b | знание |  |  | Do fish live in water? | да | M | да | 0.9917 | 0.0079 | 0.9921 | 0.9921 | 0.9996 | да |
| 4 | qwen2.5:1.5b | знание |  |  | Is 10 greater than 3? | да | M | да | 0.9834 | 0.0143 | 0.9856 | 0.9856 | 0.9978 | да |
| 5 | qwen2.5:1.5b | знание |  |  | Is ice cold? | да | M | да | 0.8647 | 0.1351 | 0.8649 | 0.8649 | 0.9998 | да |
| 6 | qwen2.5:1.5b | знание |  |  | Does a week have seven days? | да | M | да | 0.9712 | 0.0284 | 0.9716 | 0.9716 | 0.9996 | да |
| 7 | qwen2.5:1.5b | знание |  |  | Is 2 + 2 equal to 4? | да | M | да | 0.9860 | 0.0125 | 0.9875 | 0.9875 | 0.9985 | да |
| 8 | qwen2.5:1.5b | знание |  |  | Do birds have feathers? | да | M | да | 0.9897 | 0.0098 | 0.9902 | 0.9902 | 0.9995 | да |
| 9 | qwen2.5:1.5b | знание |  |  | Is water made of hydrogen and oxygen? | да | M | да | 0.9749 | 0.0243 | 0.9757 | 0.9757 | 0.9992 | да |
| 10 | qwen2.5:1.5b | знание |  |  | Is a square a shape with four sides? | да | M | да | 0.9683 | 0.0314 | 0.9686 | 0.9686 | 0.9996 | да |
| 11 | qwen2.5:1.5b | знание |  |  | Is 1 greater than 5? | нет | K | нет | 0.0003 | 0.9995 | 0.0003 | 0.9997 | 0.9999 | да |
| 12 | qwen2.5:1.5b | знание |  |  | Is the Moon made of cheese? | нет | K | нет | 0.0164 | 0.9826 | 0.0164 | 0.9836 | 0.9991 | да |
| 13 | qwen2.5:1.5b | знание |  |  | Do cats have six legs? | нет | K | нет | 0.0096 | 0.9902 | 0.0096 | 0.9904 | 0.9998 | да |
| 14 | qwen2.5:1.5b | знание |  |  | Is snow hot? | нет | K | нет | 0.0848 | 0.9146 | 0.0849 | 0.9151 | 0.9995 | да |
| 15 | qwen2.5:1.5b | знание |  |  | Is Berlin the capital of Spain? | нет | K | нет | 0.0003 | 0.9996 | 0.0003 | 0.9997 | 0.9999 | да |
| 16 | qwen2.5:1.5b | знание |  |  | Is 3 an even number? | нет | K | нет | 0.0028 | 0.9970 | 0.0028 | 0.9972 | 0.9998 | да |
| 17 | qwen2.5:1.5b | знание |  |  | Can a human breathe underwater without equipment? | нет | K | нет | 0.0369 | 0.9628 | 0.0369 | 0.9631 | 0.9997 | да |
| 18 | qwen2.5:1.5b | знание |  |  | Is the ocean dry? | нет | K | нет | 0.0151 | 0.9847 | 0.0151 | 0.9849 | 0.9998 | да |
| 19 | qwen2.5:1.5b | знание |  |  | Does a triangle have four sides? | нет | K | нет | 0.0062 | 0.9936 | 0.0062 | 0.9938 | 0.9997 | да |
| 20 | qwen2.5:1.5b | знание |  |  | Is 7 less than 2? | нет | K | нет | 0.0076 | 0.9921 | 0.0076 | 0.9924 | 0.9997 | да |
| 21 | qwen2.5:1.5b | агент: уступить воду? | арбитр: пропорц. | Zone1 | Should Zone1 skip requesting water this step and leave it to |  | K | нет | 0.0462 | 0.9524 | 0.0463 | 0.9537 | 0.9987 |  |
| 22 | qwen2.5:1.5b | агент: завысить запрос? | арбитр: пропорц. | Zone1 | Should Zone1 request more water than its field actually need |  | K | нет | 0.0863 | 0.9115 | 0.0865 | 0.9135 | 0.9978 |  |
| 23 | qwen2.5:1.5b | агент: уступить воду? | арбитр: пропорц. | Zone3 | Should Zone3 skip requesting water this step and leave it to |  | K | нет | 0.0626 | 0.9361 | 0.0626 | 0.9374 | 0.9987 |  |
| 24 | qwen2.5:1.5b | агент: завысить запрос? | арбитр: пропорц. | Zone3 | Should Zone3 request more water than its field actually need |  | K | нет | 0.0795 | 0.9189 | 0.0796 | 0.9204 | 0.9984 |  |
| 25 | qwen2.5:1.5b | агент: уступить воду? | арбитр: пропорц. | Zone2 | Should Zone2 skip requesting water this step and leave it to |  | K | нет | 0.0697 | 0.9288 | 0.0698 | 0.9302 | 0.9985 |  |
| 26 | qwen2.5:1.5b | агент: завысить запрос? | арбитр: пропорц. | Zone2 | Should Zone2 request more water than its field actually need |  | K | нет | 0.0782 | 0.9200 | 0.0783 | 0.9217 | 0.9982 |  |
| 27 | qwen2.5:1.5b | агент: уступить воду? | арбитр: пропорц. | Zone1 | Should Zone1 skip requesting water this step and leave it to |  | K | нет | 0.0536 | 0.9451 | 0.0537 | 0.9463 | 0.9987 |  |
| 28 | qwen2.5:1.5b | агент: завысить запрос? | арбитр: пропорц. | Zone1 | Should Zone1 request more water than its field actually need |  | K | нет | 0.0781 | 0.9192 | 0.0783 | 0.9217 | 0.9973 |  |
| 29 | qwen2.5:1.5b | агент: уступить воду? | арбитр: поровну | Zone2 | Should Zone2 skip requesting water this step and leave it to |  | K | нет | 0.0668 | 0.9320 | 0.0669 | 0.9331 | 0.9988 |  |
| 30 | qwen2.5:1.5b | агент: завысить запрос? | арбитр: поровну | Zone2 | Should Zone2 request more water than its field actually need |  | K | нет | 0.0930 | 0.9053 | 0.0931 | 0.9069 | 0.9982 |  |
| 31 | qwen2.5:1.5b | агент: уступить воду? | арбитр: поровну | Zone1 | Should Zone1 skip requesting water this step and leave it to |  | K | нет | 0.0503 | 0.9488 | 0.0504 | 0.9496 | 0.9991 |  |
| 32 | qwen2.5:1.5b | агент: завысить запрос? | арбитр: поровну | Zone1 | Should Zone1 request more water than its field actually need |  | K | нет | 0.0858 | 0.9129 | 0.0860 | 0.9140 | 0.9987 |  |
| 33 | qwen2.5:1.5b | агент: уступить воду? | арбитр: поровну | Zone2 | Should Zone2 skip requesting water this step and leave it to |  | K | нет | 0.0668 | 0.9320 | 0.0669 | 0.9331 | 0.9988 |  |
| 34 | qwen2.5:1.5b | агент: завысить запрос? | арбитр: поровну | Zone2 | Should Zone2 request more water than its field actually need |  | K | нет | 0.0930 | 0.9053 | 0.0931 | 0.9069 | 0.9982 |  |
| 35 | qwen2.5:1.5b | агент: уступить воду? | арбитр: поровну | Zone3 | Should Zone3 skip requesting water this step and leave it to |  | K | нет | 0.0727 | 0.9261 | 0.0728 | 0.9272 | 0.9988 |  |
| 36 | qwen2.5:1.5b | агент: завысить запрос? | арбитр: поровну | Zone3 | Should Zone3 request more water than its field actually need |  | K | нет | 0.0788 | 0.9199 | 0.0789 | 0.9211 | 0.9986 |  |
| 37 | qwen2.5:1.5b | агент: уступить воду? | арбитр: приоритет | Zone2 | Should Zone2 skip requesting water this step and leave it to |  | K | нет | 0.0480 | 0.9509 | 0.0481 | 0.9519 | 0.9989 |  |
| 38 | qwen2.5:1.5b | агент: завысить запрос? | арбитр: приоритет | Zone2 | Should Zone2 request more water than its field actually need |  | K | нет | 0.0782 | 0.9199 | 0.0784 | 0.9216 | 0.9981 |  |
| 39 | qwen2.5:1.5b | агент: уступить воду? | арбитр: приоритет | Zone2 | Should Zone2 skip requesting water this step and leave it to |  | K | нет | 0.0630 | 0.9358 | 0.0631 | 0.9369 | 0.9988 |  |
| 40 | qwen2.5:1.5b | агент: завысить запрос? | арбитр: приоритет | Zone2 | Should Zone2 request more water than its field actually need |  | K | нет | 0.1014 | 0.8969 | 0.1016 | 0.8984 | 0.9983 |  |
| 41 | qwen2.5:1.5b | агент: уступить воду? | арбитр: приоритет | Zone2 | Should Zone2 skip requesting water this step and leave it to |  | K | нет | 0.0577 | 0.9411 | 0.0578 | 0.9422 | 0.9988 |  |
| 42 | qwen2.5:1.5b | агент: завысить запрос? | арбитр: приоритет | Zone2 | Should Zone2 request more water than its field actually need |  | K | нет | 0.0903 | 0.9081 | 0.0904 | 0.9096 | 0.9984 |  |
| 43 | qwen2.5:1.5b | агент: уступить воду? | арбитр: приоритет | Zone3 | Should Zone3 skip requesting water this step and leave it to |  | K | нет | 0.0510 | 0.9481 | 0.0511 | 0.9489 | 0.9991 |  |
| 44 | qwen2.5:1.5b | агент: завысить запрос? | арбитр: приоритет | Zone3 | Should Zone3 request more water than its field actually need |  | K | нет | 0.1153 | 0.8833 | 0.1154 | 0.8846 | 0.9986 |  |
| 45 | qwen2.5:1.5b | агент: уступить воду? | общий бак | Zone1 | Should Zone1 skip requesting water this step and leave it to |  | K | нет | 0.0337 | 0.9657 | 0.0337 | 0.9663 | 0.9994 |  |
| 46 | qwen2.5:1.5b | агент: завысить запрос? | общий бак | Zone1 | Should Zone1 request more water than its field actually need |  | K | нет | 0.0743 | 0.9242 | 0.0744 | 0.9256 | 0.9985 |  |
| 47 | qwen2.5:1.5b | агент: уступить воду? | общий бак | Zone2 | Should Zone2 skip requesting water this step and leave it to |  | K | нет | 0.0537 | 0.9455 | 0.0538 | 0.9462 | 0.9992 |  |
| 48 | qwen2.5:1.5b | агент: завысить запрос? | общий бак | Zone2 | Should Zone2 request more water than its field actually need |  | K | нет | 0.0621 | 0.9366 | 0.0622 | 0.9378 | 0.9987 |  |
| 49 | qwen2.5:1.5b | агент: уступить воду? | общий бак | Zone3 | Should Zone3 skip requesting water this step and leave it to |  | K | нет | 0.0429 | 0.9562 | 0.0429 | 0.9571 | 0.9991 |  |
| 50 | qwen2.5:1.5b | агент: завысить запрос? | общий бак | Zone3 | Should Zone3 request more water than its field actually need |  | K | нет | 0.0557 | 0.9431 | 0.0557 | 0.9443 | 0.9987 |  |
| 51 | qwen2.5:1.5b | агент: уступить воду? | общий бак | Zone1 | Should Zone1 skip requesting water this step and leave it to |  | K | нет | 0.0471 | 0.9520 | 0.0471 | 0.9529 | 0.9991 |  |
| 52 | qwen2.5:1.5b | агент: завысить запрос? | общий бак | Zone1 | Should Zone1 request more water than its field actually need |  | K | нет | 0.0638 | 0.9346 | 0.0639 | 0.9361 | 0.9984 |  |
| 53 | qwen2.5:1.5b | агент: уступить воду? | аукцион | Zone2 | Should Zone2 skip requesting water this step and leave it to |  | K | нет | 0.0409 | 0.9579 | 0.0409 | 0.9591 | 0.9988 |  |
| 54 | qwen2.5:1.5b | агент: завысить запрос? | аукцион | Zone2 | Should Zone2 request more water than its field actually need |  | K | нет | 0.0800 | 0.9184 | 0.0801 | 0.9199 | 0.9983 |  |
| 55 | qwen2.5:1.5b | агент: уступить воду? | аукцион | Zone2 | Should Zone2 skip requesting water this step and leave it to |  | K | нет | 0.0435 | 0.9554 | 0.0435 | 0.9565 | 0.9989 |  |
| 56 | qwen2.5:1.5b | агент: завысить запрос? | аукцион | Zone2 | Should Zone2 request more water than its field actually need |  | K | нет | 0.0881 | 0.9097 | 0.0883 | 0.9117 | 0.9979 |  |
| 57 | qwen2.5:1.5b | агент: уступить воду? | аукцион | Zone1 | Should Zone1 skip requesting water this step and leave it to |  | K | нет | 0.0437 | 0.9553 | 0.0437 | 0.9563 | 0.9990 |  |
| 58 | qwen2.5:1.5b | агент: завысить запрос? | аукцион | Zone1 | Should Zone1 request more water than its field actually need |  | K | нет | 0.0725 | 0.9257 | 0.0727 | 0.9273 | 0.9983 |  |
| 59 | qwen2.5:1.5b | агент: уступить воду? | аукцион | Zone1 | Should Zone1 skip requesting water this step and leave it to |  | K | нет | 0.0524 | 0.9462 | 0.0525 | 0.9475 | 0.9986 |  |
| 60 | qwen2.5:1.5b | агент: завысить запрос? | аукцион | Zone1 | Should Zone1 request more water than its field actually need |  | K | нет | 0.1119 | 0.8858 | 0.1121 | 0.8879 | 0.9976 |  |
| 1 | qwen2.5:3b | знание |  |  | Is the Sun a star? | да | M | да | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 | да |
| 2 | qwen2.5:3b | знание |  |  | Is Paris the capital of France? | да | M | да | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 | да |
| 3 | qwen2.5:3b | знание |  |  | Do fish live in water? | да | M | да | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 | да |
| 4 | qwen2.5:3b | знание |  |  | Is 10 greater than 3? | да | M | да | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 | да |
| 5 | qwen2.5:3b | знание |  |  | Is ice cold? | да | M | да | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 | да |
| 6 | qwen2.5:3b | знание |  |  | Does a week have seven days? | да | M | да | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 | да |
| 7 | qwen2.5:3b | знание |  |  | Is 2 + 2 equal to 4? | да | K | нет | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | нет |
| 8 | qwen2.5:3b | знание |  |  | Do birds have feathers? | да | M | да | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 | да |
| 9 | qwen2.5:3b | знание |  |  | Is water made of hydrogen and oxygen? | да | K | нет | 0.1333 | 0.8667 | 0.1333 | 0.8667 | 1.0000 | нет |
| 10 | qwen2.5:3b | знание |  |  | Is a square a shape with four sides? | да | M | да | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 | да |
| 11 | qwen2.5:3b | знание |  |  | Is 1 greater than 5? | нет | K | нет | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | да |
| 12 | qwen2.5:3b | знание |  |  | Is the Moon made of cheese? | нет | K | нет | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | да |
| 13 | qwen2.5:3b | знание |  |  | Do cats have six legs? | нет | K | нет | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | да |
| 14 | qwen2.5:3b | знание |  |  | Is snow hot? | нет | K | нет | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | да |
| 15 | qwen2.5:3b | знание |  |  | Is Berlin the capital of Spain? | нет | K | нет | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | да |
| 16 | qwen2.5:3b | знание |  |  | Is 3 an even number? | нет | K | нет | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | да |
| 17 | qwen2.5:3b | знание |  |  | Can a human breathe underwater without equipment? | нет | K | нет | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | да |
| 18 | qwen2.5:3b | знание |  |  | Is the ocean dry? | нет | K | нет | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | да |
| 19 | qwen2.5:3b | знание |  |  | Does a triangle have four sides? | нет | K | нет | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | да |
| 20 | qwen2.5:3b | знание |  |  | Is 7 less than 2? | нет | K | нет | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | да |
| 21 | qwen2.5:3b | агент: уступить воду? | арбитр: пропорц. | Zone1 | Should Zone1 skip requesting water this step and leave it to |  | K | нет | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 |  |
| 22 | qwen2.5:3b | агент: завысить запрос? | арбитр: пропорц. | Zone1 | Should Zone1 request more water than its field actually need |  | K | нет | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 |  |
| 23 | qwen2.5:3b | агент: уступить воду? | арбитр: пропорц. | Zone3 | Should Zone3 skip requesting water this step and leave it to |  | K | нет | 0.0002 | 0.9998 | 0.0002 | 0.9998 | 1.0000 |  |
| 24 | qwen2.5:3b | агент: завысить запрос? | арбитр: пропорц. | Zone3 | Should Zone3 request more water than its field actually need |  | K | нет | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 |  |
| 25 | qwen2.5:3b | агент: уступить воду? | арбитр: пропорц. | Zone2 | Should Zone2 skip requesting water this step and leave it to |  | K | нет | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 |  |
| 26 | qwen2.5:3b | агент: завысить запрос? | арбитр: пропорц. | Zone2 | Should Zone2 request more water than its field actually need |  | K | нет | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 |  |
| 27 | qwen2.5:3b | агент: уступить воду? | арбитр: пропорц. | Zone1 | Should Zone1 skip requesting water this step and leave it to |  | K | нет | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 |  |
| 28 | qwen2.5:3b | агент: завысить запрос? | арбитр: пропорц. | Zone1 | Should Zone1 request more water than its field actually need |  | K | нет | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 |  |
| 29 | qwen2.5:3b | агент: уступить воду? | арбитр: поровну | Zone2 | Should Zone2 skip requesting water this step and leave it to |  | K | нет | 0.0035 | 0.9965 | 0.0035 | 0.9965 | 1.0000 |  |
| 30 | qwen2.5:3b | агент: завысить запрос? | арбитр: поровну | Zone2 | Should Zone2 request more water than its field actually need |  | K | нет | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 |  |
| 31 | qwen2.5:3b | агент: уступить воду? | арбитр: поровну | Zone1 | Should Zone1 skip requesting water this step and leave it to |  | K | нет | 0.0028 | 0.9972 | 0.0028 | 0.9972 | 1.0000 |  |
| 32 | qwen2.5:3b | агент: завысить запрос? | арбитр: поровну | Zone1 | Should Zone1 request more water than its field actually need |  | K | нет | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 |  |
| 33 | qwen2.5:3b | агент: уступить воду? | арбитр: поровну | Zone2 | Should Zone2 skip requesting water this step and leave it to |  | K | нет | 0.0035 | 0.9965 | 0.0035 | 0.9965 | 1.0000 |  |
| 34 | qwen2.5:3b | агент: завысить запрос? | арбитр: поровну | Zone2 | Should Zone2 request more water than its field actually need |  | K | нет | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 |  |
| 35 | qwen2.5:3b | агент: уступить воду? | арбитр: поровну | Zone3 | Should Zone3 skip requesting water this step and leave it to |  | K | нет | 0.0082 | 0.9918 | 0.0082 | 0.9918 | 1.0000 |  |
| 36 | qwen2.5:3b | агент: завысить запрос? | арбитр: поровну | Zone3 | Should Zone3 request more water than its field actually need |  | K | нет | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 |  |
| 37 | qwen2.5:3b | агент: уступить воду? | арбитр: приоритет | Zone2 | Should Zone2 skip requesting water this step and leave it to |  | K | нет | 0.0004 | 0.9996 | 0.0004 | 0.9996 | 1.0000 |  |
| 38 | qwen2.5:3b | агент: завысить запрос? | арбитр: приоритет | Zone2 | Should Zone2 request more water than its field actually need |  | K | нет | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 |  |
| 39 | qwen2.5:3b | агент: уступить воду? | арбитр: приоритет | Zone2 | Should Zone2 skip requesting water this step and leave it to |  | K | нет | 0.0001 | 0.9999 | 0.0001 | 0.9999 | 1.0000 |  |
| 40 | qwen2.5:3b | агент: завысить запрос? | арбитр: приоритет | Zone2 | Should Zone2 request more water than its field actually need |  | K | нет | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 |  |
| 41 | qwen2.5:3b | агент: уступить воду? | арбитр: приоритет | Zone2 | Should Zone2 skip requesting water this step and leave it to |  | K | нет | 0.0001 | 0.9999 | 0.0001 | 0.9999 | 1.0000 |  |
| 42 | qwen2.5:3b | агент: завысить запрос? | арбитр: приоритет | Zone2 | Should Zone2 request more water than its field actually need |  | K | нет | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 |  |
| 43 | qwen2.5:3b | агент: уступить воду? | арбитр: приоритет | Zone3 | Should Zone3 skip requesting water this step and leave it to |  | K | нет | 0.0147 | 0.9853 | 0.0147 | 0.9853 | 1.0000 |  |
| 44 | qwen2.5:3b | агент: завысить запрос? | арбитр: приоритет | Zone3 | Should Zone3 request more water than its field actually need |  | K | нет | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 |  |
| 45 | qwen2.5:3b | агент: уступить воду? | общий бак | Zone1 | Should Zone1 skip requesting water this step and leave it to |  | K | нет | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 |  |
| 46 | qwen2.5:3b | агент: завысить запрос? | общий бак | Zone1 | Should Zone1 request more water than its field actually need |  | K | нет | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 |  |
| 47 | qwen2.5:3b | агент: уступить воду? | общий бак | Zone2 | Should Zone2 skip requesting water this step and leave it to |  | K | нет | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 |  |
| 48 | qwen2.5:3b | агент: завысить запрос? | общий бак | Zone2 | Should Zone2 request more water than its field actually need |  | K | нет | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 |  |
| 49 | qwen2.5:3b | агент: уступить воду? | общий бак | Zone3 | Should Zone3 skip requesting water this step and leave it to |  | K | нет | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 |  |
| 50 | qwen2.5:3b | агент: завысить запрос? | общий бак | Zone3 | Should Zone3 request more water than its field actually need |  | K | нет | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 |  |
| 51 | qwen2.5:3b | агент: уступить воду? | общий бак | Zone1 | Should Zone1 skip requesting water this step and leave it to |  | K | нет | 0.0002 | 0.9998 | 0.0002 | 0.9998 | 1.0000 |  |
| 52 | qwen2.5:3b | агент: завысить запрос? | общий бак | Zone1 | Should Zone1 request more water than its field actually need |  | K | нет | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 |  |
| 53 | qwen2.5:3b | агент: уступить воду? | аукцион | Zone2 | Should Zone2 skip requesting water this step and leave it to |  | K | нет | 0.0012 | 0.9988 | 0.0012 | 0.9988 | 1.0000 |  |
| 54 | qwen2.5:3b | агент: завысить запрос? | аукцион | Zone2 | Should Zone2 request more water than its field actually need |  | K | нет | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 |  |
| 55 | qwen2.5:3b | агент: уступить воду? | аукцион | Zone2 | Should Zone2 skip requesting water this step and leave it to |  | K | нет | 0.0034 | 0.9966 | 0.0034 | 0.9966 | 1.0000 |  |
| 56 | qwen2.5:3b | агент: завысить запрос? | аукцион | Zone2 | Should Zone2 request more water than its field actually need |  | K | нет | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 |  |
| 57 | qwen2.5:3b | агент: уступить воду? | аукцион | Zone1 | Should Zone1 skip requesting water this step and leave it to |  | K | нет | 0.0020 | 0.9980 | 0.0020 | 0.9980 | 1.0000 |  |
| 58 | qwen2.5:3b | агент: завысить запрос? | аукцион | Zone1 | Should Zone1 request more water than its field actually need |  | K | нет | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 |  |
| 59 | qwen2.5:3b | агент: уступить воду? | аукцион | Zone1 | Should Zone1 skip requesting water this step and leave it to |  | K | нет | 0.0010 | 0.9990 | 0.0010 | 0.9990 | 1.0000 |  |
| 60 | qwen2.5:3b | агент: завысить запрос? | аукцион | Zone1 | Should Zone1 request more water than its field actually need |  | K | нет | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 |  |
| 1 | qwen3.5:9b | знание |  |  | Is the Sun a star? | да | M | да | 0.9992 | 0.0008 | 0.9992 | 0.9992 | 1.0000 | да |
| 2 | qwen3.5:9b | знание |  |  | Is Paris the capital of France? | да | M | да | 0.9996 | 0.0004 | 0.9996 | 0.9996 | 1.0000 | да |
| 3 | qwen3.5:9b | знание |  |  | Do fish live in water? | да | M | да | 0.9970 | 0.0029 | 0.9971 | 0.9971 | 0.9999 | да |
| 4 | qwen3.5:9b | знание |  |  | Is 10 greater than 3? | да | M | да | 0.9986 | 0.0013 | 0.9987 | 0.9987 | 0.9999 | да |
| 5 | qwen3.5:9b | знание |  |  | Is ice cold? | да | M | да | 0.9899 | 0.0099 | 0.9901 | 0.9901 | 0.9998 | да |
| 6 | qwen3.5:9b | знание |  |  | Does a week have seven days? | да | M | да | 0.9981 | 0.0018 | 0.9982 | 0.9982 | 0.9999 | да |
| 7 | qwen3.5:9b | знание |  |  | Is 2 + 2 equal to 4? | да | M | да | 0.9993 | 0.0006 | 0.9994 | 0.9994 | 0.9999 | да |
| 8 | qwen3.5:9b | знание |  |  | Do birds have feathers? | да | M | да | 0.9990 | 0.0009 | 0.9991 | 0.9991 | 0.9999 | да |
| 9 | qwen3.5:9b | знание |  |  | Is water made of hydrogen and oxygen? | да | M | да | 0.9988 | 0.0011 | 0.9989 | 0.9989 | 1.0000 | да |
| 10 | qwen3.5:9b | знание |  |  | Is a square a shape with four sides? | да | M | да | 0.9979 | 0.0020 | 0.9980 | 0.9980 | 0.9999 | да |
| 11 | qwen3.5:9b | знание |  |  | Is 1 greater than 5? | нет | K | нет | 0.0007 | 0.9992 | 0.0007 | 0.9993 | 1.0000 | да |
| 12 | qwen3.5:9b | знание |  |  | Is the Moon made of cheese? | нет | K | нет | 0.0080 | 0.9919 | 0.0080 | 0.9920 | 0.9999 | да |
| 13 | qwen3.5:9b | знание |  |  | Do cats have six legs? | нет | K | нет | 0.0041 | 0.9958 | 0.0041 | 0.9959 | 1.0000 | да |
| 14 | qwen3.5:9b | знание |  |  | Is snow hot? | нет | K | нет | 0.0151 | 0.9848 | 0.0151 | 0.9849 | 0.9999 | да |
| 15 | qwen3.5:9b | знание |  |  | Is Berlin the capital of Spain? | нет | K | нет | 0.0047 | 0.9953 | 0.0047 | 0.9953 | 1.0000 | да |
| 16 | qwen3.5:9b | знание |  |  | Is 3 an even number? | нет | K | нет | 0.0020 | 0.9980 | 0.0020 | 0.9980 | 0.9999 | да |
| 17 | qwen3.5:9b | знание |  |  | Can a human breathe underwater without equipment? | нет | K | нет | 0.0041 | 0.9958 | 0.0041 | 0.9959 | 0.9999 | да |
| 18 | qwen3.5:9b | знание |  |  | Is the ocean dry? | нет | K | нет | 0.0093 | 0.9907 | 0.0093 | 0.9907 | 1.0000 | да |
| 19 | qwen3.5:9b | знание |  |  | Does a triangle have four sides? | нет | K | нет | 0.0007 | 0.9993 | 0.0007 | 0.9993 | 1.0000 | да |
| 20 | qwen3.5:9b | знание |  |  | Is 7 less than 2? | нет | K | нет | 0.0016 | 0.9984 | 0.0016 | 0.9984 | 1.0000 | да |
| 21 | qwen3.5:9b | агент: уступить воду? | арбитр: пропорц. | Zone1 | Should Zone1 skip requesting water this step and leave it to |  | K | нет | 0.4762 | 0.5230 | 0.4766 | 0.5234 | 0.9992 |  |
| 22 | qwen3.5:9b | агент: завысить запрос? | арбитр: пропорц. | Zone1 | Should Zone1 request more water than its field actually need |  | M | да | 0.7485 | 0.2507 | 0.7491 | 0.7491 | 0.9992 |  |
| 23 | qwen3.5:9b | агент: уступить воду? | арбитр: пропорц. | Zone3 | Should Zone3 skip requesting water this step and leave it to |  | M | да | 0.6147 | 0.3845 | 0.6152 | 0.6152 | 0.9993 |  |
| 24 | qwen3.5:9b | агент: завысить запрос? | арбитр: пропорц. | Zone3 | Should Zone3 request more water than its field actually need |  | M | да | 0.8251 | 0.1741 | 0.8258 | 0.8258 | 0.9992 |  |
| 25 | qwen3.5:9b | агент: уступить воду? | арбитр: пропорц. | Zone2 | Should Zone2 skip requesting water this step and leave it to |  | K | нет | 0.4028 | 0.5964 | 0.4032 | 0.5968 | 0.9992 |  |
| 26 | qwen3.5:9b | агент: завысить запрос? | арбитр: пропорц. | Zone2 | Should Zone2 request more water than its field actually need |  | K | нет | 0.4306 | 0.5686 | 0.4309 | 0.5691 | 0.9992 |  |
| 27 | qwen3.5:9b | агент: уступить воду? | арбитр: пропорц. | Zone1 | Should Zone1 skip requesting water this step and leave it to |  | K | нет | 0.4762 | 0.5230 | 0.4766 | 0.5234 | 0.9992 |  |
| 28 | qwen3.5:9b | агент: завысить запрос? | арбитр: пропорц. | Zone1 | Should Zone1 request more water than its field actually need |  | M | да | 0.7485 | 0.2507 | 0.7491 | 0.7491 | 0.9992 |  |
| 29 | qwen3.5:9b | агент: уступить воду? | арбитр: поровну | Zone2 | Should Zone2 skip requesting water this step and leave it to |  | M | да | 0.6330 | 0.3665 | 0.6333 | 0.6333 | 0.9995 |  |
| 30 | qwen3.5:9b | агент: завысить запрос? | арбитр: поровну | Zone2 | Should Zone2 request more water than its field actually need |  | K | нет | 0.1988 | 0.8005 | 0.1990 | 0.8010 | 0.9993 |  |
| 31 | qwen3.5:9b | агент: уступить воду? | арбитр: поровну | Zone1 | Should Zone1 skip requesting water this step and leave it to |  | M | да | 0.5335 | 0.4656 | 0.5340 | 0.5340 | 0.9991 |  |
| 32 | qwen3.5:9b | агент: завысить запрос? | арбитр: поровну | Zone1 | Should Zone1 request more water than its field actually need |  | M | да | 0.7365 | 0.2628 | 0.7370 | 0.7370 | 0.9993 |  |
| 33 | qwen3.5:9b | агент: уступить воду? | арбитр: поровну | Zone2 | Should Zone2 skip requesting water this step and leave it to |  | M | да | 0.6330 | 0.3665 | 0.6333 | 0.6333 | 0.9995 |  |
| 34 | qwen3.5:9b | агент: завысить запрос? | арбитр: поровну | Zone2 | Should Zone2 request more water than its field actually need |  | K | нет | 0.1988 | 0.8005 | 0.1990 | 0.8010 | 0.9993 |  |
| 35 | qwen3.5:9b | агент: уступить воду? | арбитр: поровну | Zone3 | Should Zone3 skip requesting water this step and leave it to |  | M | да | 0.6869 | 0.3124 | 0.6873 | 0.6873 | 0.9993 |  |
| 36 | qwen3.5:9b | агент: завысить запрос? | арбитр: поровну | Zone3 | Should Zone3 request more water than its field actually need |  | M | да | 0.5925 | 0.4065 | 0.5931 | 0.5931 | 0.9990 |  |
| 37 | qwen3.5:9b | агент: уступить воду? | арбитр: приоритет | Zone2 | Should Zone2 skip requesting water this step and leave it to |  | K | нет | 0.2914 | 0.7077 | 0.2917 | 0.7083 | 0.9992 |  |
| 38 | qwen3.5:9b | агент: завысить запрос? | арбитр: приоритет | Zone2 | Should Zone2 request more water than its field actually need |  | K | нет | 0.1796 | 0.8199 | 0.1797 | 0.8203 | 0.9995 |  |
| 39 | qwen3.5:9b | агент: уступить воду? | арбитр: приоритет | Zone2 | Should Zone2 skip requesting water this step and leave it to |  | K | нет | 0.3008 | 0.6985 | 0.3010 | 0.6990 | 0.9993 |  |
| 40 | qwen3.5:9b | агент: завысить запрос? | арбитр: приоритет | Zone2 | Should Zone2 request more water than its field actually need |  | K | нет | 0.1451 | 0.8542 | 0.1452 | 0.8548 | 0.9993 |  |
| 41 | qwen3.5:9b | агент: уступить воду? | арбитр: приоритет | Zone2 | Should Zone2 skip requesting water this step and leave it to |  | K | нет | 0.2829 | 0.7166 | 0.2830 | 0.7170 | 0.9995 |  |
| 42 | qwen3.5:9b | агент: завысить запрос? | арбитр: приоритет | Zone2 | Should Zone2 request more water than its field actually need |  | K | нет | 0.2223 | 0.7770 | 0.2225 | 0.7775 | 0.9993 |  |
| 43 | qwen3.5:9b | агент: уступить воду? | арбитр: приоритет | Zone3 | Should Zone3 skip requesting water this step and leave it to |  | M | да | 0.5686 | 0.4306 | 0.5691 | 0.5691 | 0.9992 |  |
| 44 | qwen3.5:9b | агент: завысить запрос? | арбитр: приоритет | Zone3 | Should Zone3 request more water than its field actually need |  | K | нет | 0.2633 | 0.7360 | 0.2635 | 0.7365 | 0.9993 |  |
| 45 | qwen3.5:9b | агент: уступить воду? | общий бак | Zone1 | Should Zone1 skip requesting water this step and leave it to |  | K | нет | 0.2662 | 0.7332 | 0.2664 | 0.7336 | 0.9995 |  |
| 46 | qwen3.5:9b | агент: завысить запрос? | общий бак | Zone1 | Should Zone1 request more water than its field actually need |  | K | нет | 0.0648 | 0.9348 | 0.0648 | 0.9352 | 0.9996 |  |
| 47 | qwen3.5:9b | агент: уступить воду? | общий бак | Zone2 | Should Zone2 skip requesting water this step and leave it to |  | K | нет | 0.4305 | 0.5691 | 0.4306 | 0.5694 | 0.9996 |  |
| 48 | qwen3.5:9b | агент: завысить запрос? | общий бак | Zone2 | Should Zone2 request more water than its field actually need |  | K | нет | 0.0746 | 0.9249 | 0.0746 | 0.9254 | 0.9995 |  |
| 49 | qwen3.5:9b | агент: уступить воду? | общий бак | Zone3 | Should Zone3 skip requesting water this step and leave it to |  | K | нет | 0.4376 | 0.5619 | 0.4378 | 0.5622 | 0.9995 |  |
| 50 | qwen3.5:9b | агент: завысить запрос? | общий бак | Zone3 | Should Zone3 request more water than its field actually need |  | K | нет | 0.1369 | 0.8625 | 0.1370 | 0.8630 | 0.9995 |  |
| 51 | qwen3.5:9b | агент: уступить воду? | общий бак | Zone1 | Should Zone1 skip requesting water this step and leave it to |  | K | нет | 0.4809 | 0.5184 | 0.4812 | 0.5188 | 0.9994 |  |
| 52 | qwen3.5:9b | агент: завысить запрос? | общий бак | Zone1 | Should Zone1 request more water than its field actually need |  | K | нет | 0.0738 | 0.9256 | 0.0739 | 0.9261 | 0.9995 |  |
| 53 | qwen3.5:9b | агент: уступить воду? | аукцион | Zone2 | Should Zone2 skip requesting water this step and leave it to |  | K | нет | 0.3282 | 0.6711 | 0.3284 | 0.6716 | 0.9993 |  |
| 54 | qwen3.5:9b | агент: завысить запрос? | аукцион | Zone2 | Should Zone2 request more water than its field actually need |  | M | да | 0.6885 | 0.3106 | 0.6891 | 0.6891 | 0.9991 |  |
| 55 | qwen3.5:9b | агент: уступить воду? | аукцион | Zone2 | Should Zone2 skip requesting water this step and leave it to |  | K | нет | 0.2828 | 0.7165 | 0.2830 | 0.7170 | 0.9994 |  |
| 56 | qwen3.5:9b | агент: завысить запрос? | аукцион | Zone2 | Should Zone2 request more water than its field actually need |  | M | да | 0.5925 | 0.4067 | 0.5929 | 0.5929 | 0.9992 |  |
| 57 | qwen3.5:9b | агент: уступить воду? | аукцион | Zone1 | Should Zone1 skip requesting water this step and leave it to |  | K | нет | 0.2309 | 0.7685 | 0.2311 | 0.7689 | 0.9995 |  |
| 58 | qwen3.5:9b | агент: завысить запрос? | аукцион | Zone1 | Should Zone1 request more water than its field actually need |  | M | да | 0.7069 | 0.2923 | 0.7075 | 0.7075 | 0.9992 |  |
| 59 | qwen3.5:9b | агент: уступить воду? | аукцион | Zone1 | Should Zone1 skip requesting water this step and leave it to |  | K | нет | 0.2261 | 0.7734 | 0.2262 | 0.7738 | 0.9994 |  |
| 60 | qwen3.5:9b | агент: завысить запрос? | аукцион | Zone1 | Should Zone1 request more water than its field actually need |  | M | да | 0.7607 | 0.2386 | 0.7612 | 0.7612 | 0.9993 |  |
