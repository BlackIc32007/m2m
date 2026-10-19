"""
Меняет ли решения LLM знание топологии сети (блок topology контекста зоны)?

Одни и те же состояния зон спрашиваются с контекстом
    full  -- own + mechanism + neighbors + goal (как в прежних экспериментах)
    topo  -- то же + topology (узлы, роли, куда течёт вода, кто в отказе)
в двух ситуациях:
    normal -- все узлы работают;
    failed -- распределитель (хаб) в отказе: воды до зон в этот шаг не дойдёт.

Вопросы: «уступить воду в этот шаг?» (yield) и «запросить больше, чем нужно?»
(inflate). P(да) без смещения к букве (среднее двух порядков букв).
Решения на модель не влияют (разомкнутый цикл, RecorderPolicy).

    python experiments/llm_topology.py              # 3 модели, ~5 мин
Результат: experiments/results/llm_topology.csv, llm_topology_summary.md
"""
import argparse
import random
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.llm import token_decision, zone_context
from src.model.conflict_model import ConflictModel
from src.model.zone_policies import RecorderPolicy

RES = Path(__file__).resolve().parent / "results"
SCHEMES = [("distributor", "proportional"), ("distributor", "equal"), ("distributor", "priority"),
           ("shared_tank", "proportional"), ("auction", "proportional")]
CONTEXTS = {"full": zone_context.BLOCKS, "topo": zone_context.TOPOLOGY_BLOCKS}


def collect(per_cell, seed):
    """По per_cell состояний на механизм в каждой ситуации (normal / failed)."""
    rnd = random.Random(seed)
    states = []
    for scheme, policy in SCHEMES:
        for situation in ("normal", "failed"):
            rec = RecorderPolicy(CONTEXTS)
            m = ConflictModel(scheme, policy=policy, supply=6, tank_capacity=12, seed=500,
                              decision_mode="autonomous", zone_policy=rec)
            for step in range(1, 61):
                if situation == "failed" and step == 30:
                    m.trigger_failure(m.hub.name, 30)
                m.step()
            # отказ длится шаги 31-60: берём состояния только оттуда
            lo = 31 if situation == "failed" else 11
            pool = [s for s in rec.samples if lo <= s["step"] <= 60]
            for s in rnd.sample(pool, per_cell):
                states.append({**s, "situation": situation})
    return states


def p_yes(model, ctx, q):
    a = token_decision.ask(ctx, q, model=model, yes_letter="M", no_letter="K")
    b = token_decision.ask(ctx, q, model=model, yes_letter="K", no_letter="M")
    norm = [r["p_yes"] / r["mass"] for r in (a, b) if r["mass"] > 0]
    return statistics.mean(norm), min(a["mass"], b["mass"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="qwen2.5:1.5b,qwen2.5:3b,qwen3.5:9b")
    ap.add_argument("--per-cell", type=int, default=4)
    ap.add_argument("--seed", type=int, default=3)
    a = ap.parse_args()
    models = a.models.split(",")
    states = collect(a.per_cell, a.seed)

    rows = []
    for model in models:
        t0 = time.time()
        for i, st in enumerate(states):
            for kind in ("yield", "inflate"):
                q = zone_context.question(kind, st["zone"])
                for ctx in CONTEXTS:   # последовательно: параллельно Ollama недетерминирована
                    p, mass = p_yes(model, st["contexts"][ctx], q)
                    rows.append({"model": model, "state": i, "scheme": st["scheme"], "zone": st["zone"],
                                 "situation": st["situation"], "question": kind, "context": ctx,
                                 "p_yes": p, "mass": mass})
        print(f"{model}: {len(states)} состояний за {time.time() - t0:.0f} с", flush=True)

    RES.mkdir(exist_ok=True)
    import csv
    with open(RES / "llm_topology.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    def get(model, sit, q, ctx):
        return {r["state"]: r["p_yes"] for r in rows
                if r["model"] == model and r["situation"] == sit and r["question"] == q and r["context"] == ctx}

    sit_ru = {"normal": "все узлы работают", "failed": "хаб в отказе"}
    q_ru = {"yield": "уступить воду?", "inflate": "завысить запрос?"}
    lines = ["# Топология в контексте LLM: меняет ли она решения", "",
             f"{len(states)} состояний ({a.per_cell} на механизм × 5 механизмов × 2 ситуации), "
             "P(да) без смещения к букве. full — прежний контекст, topo — тот же плюс устройство сети.", "",
             "| модель | ситуация | вопрос | P(да) full | P(да) topo | разница | решений «да» full → topo |",
             "|---|---|---|---|---|---|---|"]
    for model in models:
        for sit in ("normal", "failed"):
            for q in ("yield", "inflate"):
                f_, t_ = get(model, sit, q, "full"), get(model, sit, q, "topo")
                d = [t_[k] - f_[k] for k in f_]
                lines.append(f"| {model} | {sit_ru[sit]} | {q_ru[q]} | {statistics.mean(f_.values()):.3f} | "
                             f"{statistics.mean(t_.values()):.3f} | {statistics.mean(d):+.3f} | "
                             f"{sum(v > 0.5 for v in f_.values())} → {sum(v > 0.5 for v in t_.values())} "
                             f"из {len(f_)} |")
    lines += ["", f"min mass: {min(r['mass'] for r in rows):.3f}"]
    (RES / "llm_topology_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
