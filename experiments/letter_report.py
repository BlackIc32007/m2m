"""
Отчёт «как LLM отвечает одной буквой»: одни и те же вопросы, заданные
моделям через модуль решения одним токеном (src/llm/token_decision.py).

Буквы ответа -- параметры: --yes M --no K (как в проекте) или наоборот.
Код проекта при этом не меняется -- буквы передаются в вызов ask().

Вопросы (одинаковые и в одном порядке при любых буквах):
  * 20 вопросов на знания с известным ответом (10 «да», 10 «нет»);
  * 40 вопросов агента: 20 реальных состояний зон из модели конфликта
    x {«уступить воду?», «завысить запрос?»}, полный контекст.

В папку --out пишутся:
  report.md          -- отчёт
  answers.csv / .md  -- большая таблица всех ответов
  requests/          -- несколько запросов к LLM целиком: что отправлено и
                        что вернула Ollama (топ-10 токенов с вероятностями)

    python experiments/letter_report.py --yes M --no K --out reports/llm_letters/1_M_da
    python experiments/letter_report.py --yes K --no M --out reports/llm_letters/2_K_da \\
        --compare reports/llm_letters/1_M_da/answers.csv
"""
import argparse
import csv
import json
import math
import random
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests

from src.llm import token_decision, zone_context
from src.model.conflict_model import ConflictModel
from src.model.zone_policies import RecorderPolicy

ROOT = Path(__file__).resolve().parent.parent
MODELS = ["qwen2.5:1.5b", "qwen2.5:3b", "qwen3.5:9b"]
FULL = ("own", "mechanism", "neighbors", "goal")
SCHEMES = [("distributor", "proportional"), ("distributor", "equal"), ("distributor", "priority"),
           ("shared_tank", "proportional"), ("auction", "proportional")]

# вопросы с известным ответом; не повторяют примеры из промпта
# («Is fire hot?», «Is 1 greater than 3?»)
KNOWLEDGE = [
    ("Is the Sun a star?", True), ("Is Paris the capital of France?", True),
    ("Do fish live in water?", True), ("Is 10 greater than 3?", True),
    ("Is ice cold?", True), ("Does a week have seven days?", True),
    ("Is 2 + 2 equal to 4?", True), ("Do birds have feathers?", True),
    ("Is water made of hydrogen and oxygen?", True), ("Is a square a shape with four sides?", True),
    ("Is 1 greater than 5?", False), ("Is the Moon made of cheese?", False),
    ("Do cats have six legs?", False), ("Is snow hot?", False),
    ("Is Berlin the capital of Spain?", False), ("Is 3 an even number?", False),
    ("Can a human breathe underwater without equipment?", False), ("Is the ocean dry?", False),
    ("Does a triangle have four sides?", False), ("Is 7 less than 2?", False),
]
QUESTION_RU = {"yield": "уступить воду?", "inflate": "завысить запрос?"}
SCHEME_RU = {"distributor/proportional": "арбитр: пропорц.", "distributor/equal": "арбитр: поровну",
             "distributor/priority": "арбитр: приоритет", "shared_tank": "общий бак",
             "auction": "аукцион"}


def zone_states(per_scheme=4, seed=7):
    """20 реальных состояний зон (по 4 на механизм) при нехватке воды."""
    rnd = random.Random(seed)
    out = []
    for scheme, policy in SCHEMES:
        rec = RecorderPolicy({"full": FULL})
        m = ConflictModel(scheme, policy=policy, supply=6, tank_capacity=12, seed=500,
                          decision_mode="autonomous", zone_policy=rec)
        for _ in range(100):
            m.step()
        pool = [s for s in rec.samples if s["step"] > 10]
        for s in rnd.sample(pool, per_scheme):
            out.append({"scheme": zone_context.scheme_key(m), "zone": s["zone"],
                        "context": s["contexts"]["full"]})
    return out


def build_questions():
    qs = [{"kind": "знание", "question": q, "context": "", "truth": t, "scheme": "", "zone": ""}
          for q, t in KNOWLEDGE]
    for st in zone_states():
        for kind in ("yield", "inflate"):
            qs.append({"kind": f"агент: {QUESTION_RU[kind]}",
                       "question": zone_context.question(kind, st["zone"]),
                       "context": st["context"], "truth": None,
                       "scheme": st["scheme"], "zone": st["zone"]})
    for i, q in enumerate(qs, 1):
        q["id"] = i
    return qs


def raw_call(model, q, yes, no):
    """Тот же запрос, что делает token_decision.ask, но с полным ответом Ollama
    -- для примеров в папке requests/."""
    body = {"model": model, "messages": token_decision.build_messages(q["context"], q["question"],
                                                                      "en", yes, no),
            "stream": False, "logprobs": True, "top_logprobs": token_decision.TOP_LOGPROBS,
            "think": False, "options": {"temperature": 0, "num_predict": 1}}
    r = requests.post(f"{token_decision.OLLAMA_HOST}/api/chat", json=body, timeout=120)
    r.raise_for_status()
    return body, r.json()


def write_example(folder, n, model, q, yes, no, row):
    body, resp = raw_call(model, q, yes, no)
    top = (resp.get("logprobs") or [{}])[0].get("top_logprobs", [])
    slug = f"{n:02d}_{model.replace(':', '-')}_{'knowledge' if q['kind'] == 'знание' else 'agent'}"
    (folder / f"{slug}.json").write_text(json.dumps(
        {"request": body, "response": resp}, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [f"# Запрос {n}: {model}, вопрос №{q['id']} ({q['kind']})", "",
             f"Буквы: **{yes} = да**, **{no} = нет**. Полный запрос и ответ Ollama — `{slug}.json`.", "",
             "## Что отправлено (`/api/chat`)", "",
             f"Параметры: `temperature 0`, `num_predict 1` (один токен), `logprobs`, "
             f"`top_logprobs {token_decision.TOP_LOGPROBS}`, `think false`.", ""]
    for msg in body["messages"]:
        lines += [f"**{msg['role']}:**", "", "```", msg["content"], "```", ""]
    lines += ["## Что вернула модель", "",
              f"Сгенерированный токен: `{resp.get('message', {}).get('content', '')}`", "",
              "| # | токен | вероятность |", "|---|---|---|"]
    for i, t in enumerate(top, 1):
        tok = t["token"].replace("|", "\\|").replace("\n", "\\n")
        lines.append(f"| {i} | `{tok}` | {math.exp(t['logprob']):.6f} |")
    lines += ["", "## Как это превращается в решение", "",
              f"- P({yes}) = {row[f'P({yes})']:.4f} (это «да»), P({no}) = {row[f'P({no})']:.4f} (это «нет»)",
              f"- mass = P(да) + P(нет) = {row['mass']:.4f}",
              f"- ответ: **{row['буква']}** = **{row['ответ']}**, уверенность = "
              f"max / mass = {row['уверенность']:.3f}"]
    if q["truth"] is not None:
        lines.append(f"- правильный ответ: {'да' if q['truth'] else 'нет'} — "
                     f"{'верно' if row['верно'] == 'да' else 'ошибка'}")
    (folder / f"{slug}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return slug


def fmt_table(rows, cols):
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in rows:
        out.append("| " + " | ".join(str(r[c]).replace("|", "\\|") for c in cols) + " |")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--yes", default="M")
    ap.add_argument("--no", default="K")
    ap.add_argument("--out", required=True)
    ap.add_argument("--compare", help="answers.csv другого отчёта для сравнения")
    ap.add_argument("--models", default=",".join(MODELS))
    a = ap.parse_args()
    yes, no = a.yes, a.no
    out = ROOT / a.out
    (out / "requests").mkdir(parents=True, exist_ok=True)
    models = a.models.split(",")

    qs = build_questions()
    rows = []
    for model in models:
        t0 = time.time()
        for q in qs:   # последовательно: параллельные запросы Ollama недетерминированы
            r = token_decision.ask(q["context"], q["question"], model=model, yes_letter=yes, no_letter=no)
            p = {yes: r["p_yes"], no: r["p_no"]}
            rows.append({
                "№": q["id"], "модель": model, "тип": q["kind"],
                "механизм": SCHEME_RU.get(q["scheme"], ""), "зона": q["zone"],
                "вопрос": q["question"],
                "правильно": "" if q["truth"] is None else ("да" if q["truth"] else "нет"),
                "буква": r["answer"] or "?", "ответ": {True: "да", False: "нет"}.get(r["yes"], "?"),
                "P(M)": p["M"], "P(K)": p["K"], "P(да)": r["p_yes"] / r["mass"] if r["mass"] else 0.0,
                "уверенность": r["confidence"] or 0.0, "mass": r["mass"],
                "верно": "" if q["truth"] is None else ("да" if r["yes"] == q["truth"] else "нет"),
            })
        print(f"{model}: {len(qs)} вопросов за {time.time() - t0:.0f} с", flush=True)

    cols = list(rows[0])
    with open(out / "answers.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows({**r, **{k: round(r[k], 6) for k in ("P(M)", "P(K)", "P(да)", "уверенность", "mass")}}
                    for r in rows)
    view = [{**r, **{k: f"{r[k]:.4f}" for k in ("P(M)", "P(K)", "P(да)", "уверенность", "mass")},
             "вопрос": r["вопрос"] if r["тип"] == "знание" else r["вопрос"][:60]} for r in rows]
    (out / "answers.md").write_text("\n".join(
        [f"# Все ответы ({yes} = да, {no} = нет)", "",
         f"{len(rows)} ответов: {len(qs)} вопросов × {len(models)} модели. "
         "Контекст вопросов агента — в `answers.csv` не входит, он одинаков для всех моделей "
         "и показан в примерах в `requests/`. Числа — вероятности токенов-букв.", ""]
        + fmt_table(view, cols)) + "\n", encoding="utf-8")

    # примеры запросов: по одному вопросу на знание и одному вопросу агента на модель
    examples = []
    pick = [qs[0], qs[12], qs[20], qs[21]]
    n = 0
    for model in models:
        for q in pick:
            n += 1
            row = next(r for r in rows if r["модель"] == model and r["№"] == q["id"])
            examples.append((write_example(out / "requests", n, model, q, yes, no, row), model, q))

    # сводка
    summ = []
    for model in models:
        g = [r for r in rows if r["модель"] == model]
        kn = [r for r in g if r["тип"] == "знание"]
        kn_yes = [r for r in kn if r["правильно"] == "да"]
        kn_no = [r for r in kn if r["правильно"] == "нет"]
        ag = [r for r in g if r["тип"] != "знание"]
        summ.append({
            "модель": model,
            "знания: верно": f"{sum(r['верно'] == 'да' for r in kn)}/{len(kn)}",
            "верно, где ответ «да»": f"{sum(r['верно'] == 'да' for r in kn_yes)}/{len(kn_yes)}",
            "верно, где ответ «нет»": f"{sum(r['верно'] == 'да' for r in kn_no)}/{len(kn_no)}",
            "агент: ответов «да»": f"{sum(r['ответ'] == 'да' for r in ag)}/{len(ag)}",
            "агент: средняя P(да)": f"{statistics.mean(r['P(да)'] for r in ag):.3f}",
            "средняя уверенность": f"{statistics.mean(r['уверенность'] for r in g):.3f}",
            "min mass": f"{min(r['mass'] for r in g):.3f}",
        })
    letter_rows = []
    for model in models:
        g = [r for r in rows if r["модель"] == model]
        letter_rows.append({
            "модель": model,
            f"выбрана {yes} (да)": sum(r["буква"] == yes for r in g),
            f"выбрана {no} (нет)": sum(r["буква"] == no for r in g),
            "средняя P(M)": f"{statistics.mean(r['P(M)'] for r in g):.3f}",
            "средняя P(K)": f"{statistics.mean(r['P(K)'] for r in g):.3f}",
        })
    per_kind = []
    for model in models:
        for kind in ("агент: уступить воду?", "агент: завысить запрос?"):
            g = [r for r in rows if r["модель"] == model and r["тип"] == kind]
            per_kind.append({"модель": model, "вопрос": kind.replace("агент: ", ""),
                             "ответов «да»": f"{sum(r['ответ'] == 'да' for r in g)}/{len(g)}",
                             "средняя P(да)": f"{statistics.mean(r['P(да)'] for r in g):.3f}",
                             "min / max P(да)": f"{min(r['P(да)'] for r in g):.3f} / "
                                                f"{max(r['P(да)'] for r in g):.3f}"})

    rep = [f"# Как LLM отвечает одной буквой: {yes} = да, {no} = нет", "",
           f"Модуль `src/llm/token_decision.py`: модель отвечает ровно одним токеном — буквой "
           f"**{yes}** (да) или **{no}** (нет). Из вероятностей этих двух букв считаются ответ, "
           "уверенность = max(P) / (P(да) + P(нет)) и mass = P(да) + P(нет).", "",
           f"Модели: {', '.join(f'`{m}`' for m in models)}; Ollama, `temperature 0`, запросы "
           "последовательные. Вопросов — "
           f"{len(qs)} на модель, одинаковые для всех моделей и для обоих отчётов:", "",
           "- **20 вопросов на знания** с известным ответом (10 «да», 10 «нет»), без контекста — "
           "проверяют, отвечает ли модель по смыслу;",
           "- **40 вопросов агента**: 20 реальных состояний зон из модели конфликта (по 4 на каждый "
           "из 5 механизмов, вода 6 при потребности ~10) × «уступить воду в этот шаг?» и "
           "«запросить больше, чем нужно?», с полным контекстом (своё состояние, механизм, соседи, "
           "цель сети). Правильного ответа здесь нет — смотрим, что модель выбирает.", "",
           "## Файлы", "",
           "- `answers.csv` — большая таблица всех ответов (открывается в Excel/LibreOffice); "
           "`answers.md` — она же для просмотра;",
           "- `requests/` — запросы целиком: что отправлено в Ollama и что она вернула "
           "(топ-10 токенов с вероятностями):", ""]
    for slug, model, q in examples:
        rep.append(f"  - [`{slug}.md`](requests/{slug}.md) — {model}, «{q['question'][:70]}»")
    rep += ["", "## Итоги по моделям", ""] + fmt_table(summ, list(summ[0]))
    rep += ["", "## Какие буквы выбирает модель", ""] + fmt_table(letter_rows, list(letter_rows[0]))
    rep += ["", "## Вопросы агента", ""] + fmt_table(per_kind, list(per_kind[0]))

    if a.compare:
        prev = {(r["модель"], int(r["№"])): r for r in csv.DictReader(open(ROOT / a.compare, encoding="utf-8"))}
        cmp_rows = []
        for model in models:
            g = [r for r in rows if r["модель"] == model]
            pairs = [(r, prev[(model, r["№"])]) for r in g if (model, r["№"]) in prev]
            same = sum(r["ответ"] == p["ответ"] for r, p in pairs)
            kn = [(r, p) for r, p in pairs if r["тип"] == "знание"]
            ag = [(r, p) for r, p in pairs if r["тип"] != "знание"]
            cmp_rows.append({
                "модель": model,
                "тот же ответ (да/нет)": f"{same}/{len(pairs)}",
                "знания: верно было → стало": f"{sum(p['верно'] == 'да' for _, p in kn)} → "
                                              f"{sum(r['верно'] == 'да' for r, _ in kn)} из {len(kn)}",
                "агент: «да» было → стало": f"{sum(p['ответ'] == 'да' for _, p in ag)} → "
                                            f"{sum(r['ответ'] == 'да' for r, _ in ag)} из {len(ag)}",
                "агент: P(да) было → стало": f"{statistics.mean(float(p['P(да)']) for _, p in ag):.3f} → "
                                             f"{statistics.mean(r['P(да)'] for r, _ in ag):.3f}",
                "средняя разница P(да)": f"{statistics.mean(abs(r['P(да)'] - float(p['P(да)'])) for r, p in pairs):.3f}",
            })
        rep += ["", f"## Сравнение с отчётом, где буквы наоборот (`{a.compare}`)", "",
                "Те же вопросы в том же порядке; поменялось только то, какая буква значит «да». "
                "Если бы модель отвечала по смыслу, ответы да/нет совпали бы полностью.", ""]
        rep += fmt_table(cmp_rows, list(cmp_rows[0]))
    (out / "report.md").write_text("\n".join(rep) + "\n", encoding="utf-8")
    print(f"Готово: {out}")


if __name__ == "__main__":
    main()
