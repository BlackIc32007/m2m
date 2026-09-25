"""
token_decision -- решение одним токеном (да/нет) с уверенностью модели.

Перенос ядра модуля "решение одним токеном" (ask.py): модель отвечает ровно
одним токеном -- буквой ДА или буквой НЕТ (по умолчанию M/K), а из
распределения вероятностей по кандидатам на этот токен считаются:

    confidence = max(P(yes), P(no)) / (P(yes) + P(no))  -- уверенность в ответе
    mass       = P(yes) + P(no)                          -- здоровье промпта

confidence -- уверенность модели ПРИ ДАННОМ КОНТЕКСТЕ, а не истинность.
Если mass заметно меньше 1, вероятность ушла в посторонние токены, и ответу
верить нельзя (вызывающий код откатывается на правило).

Отличия от исходного ask.py (всё -- ради экспериментов на qwen2.5:1.5b):
  * вызов через HTTP /api/chat (requests уже в зависимостях), а не пакет ollama;
  * system-промпт + два примера (few-shot): без них 1.5b отвечает словом "Yes"
    вместо буквы и mass падает (проверено в experiments/llm_sanity.py);
  * буквы ДА/НЕТ настраиваются (yes_letter/no_letter) -- для проверки
    смещения к конкретной букве; поле yes (bool) не зависит от выбора букв;
  * язык промпта en/ru.
Кэширования здесь нет намеренно (как и в исходном модуле) -- кэш живёт в
политике агента (src/model/zone_policies.py).
"""
import math
import os

import requests

OLLAMA_HOST = os.environ.get("OLLAMA_HOST_URL", "http://localhost:11434")
MODEL = "qwen2.5:1.5b"
TOP_LOGPROBS = 10

_SYSTEM = {
    "en": "You answer yes/no questions with exactly one letter. {y} means YES. {n} means NO. "
          "Output only {y} or {n}.",
    "ru": "Ты отвечаешь на вопросы да/нет ровно одной латинской буквой. {y} означает ДА. "
          "{n} означает НЕТ. Выведи только {y} или {n}.",
}
_FEWSHOT = {
    "en": [("Is fire hot?", True), ("Is 1 greater than 3?", False)],
    "ru": [("Огонь горячий?", True), ("1 больше 3?", False)],
}


def build_messages(context: str, question: str, lang: str = "en",
                   yes_letter: str = "M", no_letter: str = "K") -> list:
    msgs = [{"role": "system", "content": _SYSTEM[lang].format(y=yes_letter, n=no_letter)}]
    for q, ans in _FEWSHOT[lang]:
        msgs.append({"role": "user", "content": q})
        msgs.append({"role": "assistant", "content": yes_letter if ans else no_letter})
    user = f"{context.strip()}\n\n{question.strip()}" if context.strip() else question.strip()
    msgs.append({"role": "user", "content": user})
    return msgs


def ask(context: str, question: str, model: str = MODEL, lang: str = "en",
        yes_letter: str = "M", no_letter: str = "K", timeout: float = 120.0) -> dict:
    """Задать вопрос да/нет. Возвращает dict:
        answer     -- yes_letter / no_letter / None (буквы не найдены в топе)
        yes        -- True / False / None (не зависит от выбора букв)
        confidence -- 0.5..1.0 или None
        mass       -- P(yes)+P(no), здоровье промпта
        p_yes, p_no, raw, prompt
    """
    messages = build_messages(context, question, lang, yes_letter, no_letter)
    resp = requests.post(f"{OLLAMA_HOST}/api/chat", json={
        "model": model, "messages": messages, "stream": False,
        "logprobs": True, "top_logprobs": TOP_LOGPROBS,
        "options": {"temperature": 0, "num_predict": 1},
    }, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    raw = data.get("message", {}).get("content", "")
    top = (data.get("logprobs") or [{}])[0].get("top_logprobs", [])

    # разбираем ВЕСЬ топ: " M" и "M" -- разные токены, их вероятности складываются;
    # кириллические М/К -- другие токены и не засчитываются
    p_yes = sum(math.exp(t["logprob"]) for t in top if t["token"].strip() == yes_letter)
    p_no = sum(math.exp(t["logprob"]) for t in top if t["token"].strip() == no_letter)
    mass = p_yes + p_no
    prompt = "\n".join(f"[{m['role']}] {m['content']}" for m in messages)

    if mass <= 0:
        return {"answer": None, "yes": None, "confidence": None, "mass": 0.0,
                "p_yes": 0.0, "p_no": 0.0, "raw": raw, "prompt": prompt}
    yes = p_yes >= p_no
    return {
        "answer": yes_letter if yes else no_letter,
        "yes": yes,
        "confidence": max(p_yes, p_no) / mass,
        "mass": mass,
        "p_yes": p_yes,
        "p_no": p_no,
        "raw": raw,
        "prompt": prompt,
    }
