"""
Этап 0: проверка здоровья решения одним токеном (аналог sanity.py модуля).

6 вопросов с заведомо известным ответом. Критерий готовности: все ответы
верные и mass >= 0.9. Если нет -- сломан промпт или модель не та, дальше
идти нет смысла.

    python experiments/llm_sanity.py
    python experiments/llm_sanity.py --model qwen2.5:3b --lang ru
    python experiments/llm_sanity.py --swap      # M = НЕТ, K = ДА
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.llm.token_decision import MODEL, ask

QUESTIONS = {
    "en": [("Is water wet?", True), ("Is 2 + 2 = 5?", False), ("Is the sun hot?", True),
           ("Can a fish fly to the moon?", False), ("Is ice cold?", True),
           ("Is a circle a square?", False)],
    "ru": [("Вода мокрая?", True), ("2 + 2 = 5?", False), ("Солнце горячее?", True),
           ("Рыба может долететь до Луны?", False), ("Лёд холодный?", True),
           ("Круг -- это квадрат?", False)],
}


def run(model: str, lang: str, swap: bool) -> bool:
    y, n = ("K", "M") if swap else ("M", "K")
    ok, min_mass = 0, 1.0
    print(f"model={model} lang={lang} ДА={y} НЕТ={n}")
    print(f"{'вопрос':34} {'ждём':5} {'ответ':6} {'conf':>6} {'mass':>7}")
    for q, expected in QUESTIONS[lang]:
        r = ask("", q, model=model, lang=lang, yes_letter=y, no_letter=n)
        good = r["yes"] == expected
        ok += good
        min_mass = min(min_mass, r["mass"])
        conf = f"{r['confidence']:.3f}" if r["confidence"] is not None else "  -  "
        print(f"{q:34} {'да' if expected else 'нет':5} {str(r['answer']):6} {conf:>6} "
              f"{r['mass']:7.4f} {'' if good else '  <-- ОШИБКА'}")
    healthy = ok == len(QUESTIONS[lang]) and min_mass >= 0.9
    print(f"итого: {ok}/{len(QUESTIONS[lang])} верно, min mass {min_mass:.4f} -> "
          f"{'OK' if healthy else 'НЕ ГОТОВО'}")
    return healthy


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--lang", default="en", choices=["en", "ru"])
    ap.add_argument("--swap", action="store_true", help="поменять буквы: M = НЕТ, K = ДА")
    a = ap.parse_args()
    sys.exit(0 if run(a.model, a.lang, a.swap) else 1)
