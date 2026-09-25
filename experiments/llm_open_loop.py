"""
Этапы 1 и 4: эксперимент БЕЗ обратной связи (open loop).

1. Прогоняем ConflictModel в режиме, эквивалентном пассивному (зоны просят
   ровно свою потребность), и на каждом решении сохраняем реальное состояние
   зоны и тексты контекста для разных наборов блоков (RecorderPolicy).
2. Берём стратифицированную выборку состояний (поровну по 5 схемам).
3. Каждому состоянию задаём ОБА вопроса (уступить? / завысить?) при разных
   наборах блоков контекста -- решения LLM на симуляцию НЕ влияют.
   RQ1: какой блок контекста переворачивает решение.
4. На полном контексте -- проверки устойчивости (RQ4): переставленные буквы,
   перефразированные вопросы, русский язык, другая модель.

Результат: experiments/results/open_loop.csv (одна строка = состояние x
условие x вопрос). Анализ -- experiments/llm_analyze.py.

    python experiments/llm_open_loop.py                    # 60 состояний на схему
    python experiments/llm_open_loop.py --per-scheme 20    # быстрый прогон
"""
import argparse
import csv
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.llm import token_decision, zone_context
from src.model.conflict_model import ConflictModel
from src.model.zone_policies import RecorderPolicy

SCHEMES = [("distributor", "proportional"), ("distributor", "equal"), ("distributor", "priority"),
           ("shared_tank", None), ("auction", None)]
BLOCK_SETS = {
    "own": ("own",),
    "own+mechanism": ("own", "mechanism"),
    "own+neighbors": ("own", "neighbors"),
    "own+goal": ("own", "goal"),
    "full": ("own", "mechanism", "neighbors", "goal"),
}
RESULTS = Path(__file__).resolve().parent / "results"


def collect_states(per_scheme: int, seed: int) -> list:
    rnd = random.Random(seed)
    states = []
    for scheme, policy in SCHEMES:
        pool = []
        for s in range(3):
            rec = RecorderPolicy(BLOCK_SETS)
            m = ConflictModel(scheme, policy=policy or "proportional", seed=100 + s,
                              decision_mode="autonomous", zone_policy=rec)
            for _ in range(100):
                m.step()
            pool += rec.samples
        states += rnd.sample(pool, per_scheme)
    for i, st in enumerate(states):
        st["state_id"] = i
    return states


def conditions(st: dict) -> list:
    """(условие, контекст, язык, буквы, вариант вопроса, модель)."""
    base = dict(lang="en", swap=False, variant=0, model=token_decision.MODEL)
    out = []
    # RQ1: наборы блоков контекста
    for k in BLOCK_SETS:
        out.append({"condition": k, "context": st["contexts"][k], **base})
    # якорение на первой цели: те же блоки без "Your own goal: ..."
    out.append({"condition": "own[no-goal]", "context": st["contexts_nogoal"]["own"], **base})
    out.append({"condition": "full[no-goal]", "context": st["contexts_nogoal"]["full"], **base})
    # RQ4: устойчивость на полном контексте
    full = st["contexts"]["full"]
    out.append({"condition": "full|swap", "context": full, **{**base, "swap": True}})
    out.append({"condition": "full|para1", "context": full, **{**base, "variant": 1}})
    out.append({"condition": "full|para2", "context": full, **{**base, "variant": 2}})
    out.append({"condition": "full|ru", "context": st["contexts_ru"]["full"], **{**base, "lang": "ru"}})
    out.append({"condition": "full|3b", "context": full, **{**base, "model": "qwen2.5:3b"}})
    return out


def run_one(job):
    st, c, kind = job
    y, n = ("K", "M") if c["swap"] else ("M", "K")
    q = zone_context.question(kind, st["zone"], c["lang"], c["variant"])
    r = token_decision.ask(c["context"], q, model=c["model"], lang=c["lang"], yes_letter=y, no_letter=n)
    return {
        "state_id": st["state_id"], "scheme": st["scheme"], "zone": st["zone"], "priority": st["priority"],
        "need": round(st["need"], 2), "queue": round(st["queue"], 2), "unmet_streak": st["unmet_streak"],
        "condition": c["condition"], "question": kind, "model": c["model"], "lang": c["lang"],
        "swap": c["swap"], "variant": c["variant"],
        "yes": r["yes"], "p_yes": (r["p_yes"] / r["mass"]) if r["mass"] else None,
        "confidence": r["confidence"], "mass": r["mass"], "raw": r["raw"],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-scheme", type=int, default=60)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()

    states = collect_states(a.per_scheme, a.seed)
    jobs = [(st, c, kind) for st in states for c in conditions(st) for kind in ("yield", "inflate")]
    print(f"состояний: {len(states)}, вызовов LLM: {len(jobs)}")
    t0 = time.time()
    with ThreadPoolExecutor(a.workers) as ex:
        rows = list(ex.map(run_one, jobs))
    print(f"готово за {time.time() - t0:.0f} с")

    RESULTS.mkdir(exist_ok=True)
    out = RESULTS / "open_loop.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"записано: {out}")


if __name__ == "__main__":
    main()
