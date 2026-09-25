"""
Контроль для замкнутого цикла: случайная политика с ТЕМИ ЖЕ частотами
действий, что у LLM-политики (по closed_loop_runs.csv), но без всякой
зависимости от состояния. Если LLM теряет столько же, сколько случайная
политика, -- её решения почти не используют контекст.

Плюс разложение вреда: только REFUSE / только MODIFY / оба.

    python experiments/random_baseline.py      # -> experiments/results/random_baseline.csv
"""
import csv
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from src.model.conflict_model import ConflictModel
from src.model.zone_policies import Decision

RES = Path(__file__).resolve().parent / "results"
SCHEMES = [("distributor", "proportional"), ("distributor", "equal"), ("distributor", "priority"),
           ("shared_tank", None), ("auction", None)]


class RandomPolicy:
    def __init__(self, p_refuse, p_modify, seed, factor=2.0):
        self.pr, self.pm, self.f, self.rng = p_refuse, p_modify, factor, random.Random(seed)

    def decide(self, zone):
        u = self.rng.random()
        if u < self.pr:
            return Decision("REFUSE", 0.0, "случайно")
        if u < self.pr + self.pm:
            return Decision("MODIFY", zone.need * self.f, "случайно")
        return Decision("ACCEPT", zone.need, "случайно")


def eff(scheme, policy, seed, steps, zone_policy=None):
    m = ConflictModel(scheme, policy=policy or "proportional", seed=seed,
                      decision_mode="autonomous" if zone_policy else "passive", zone_policy=zone_policy)
    for _ in range(steps):
        m.step()
    return m.efficiency


def main(seeds=10, steps=80, llm_condition="llm_full_db_sample"):
    runs = pd.read_csv(RES / "closed_loop_runs.csv")
    rows = []
    for sc, po in SCHEMES:
        key = f"{sc}/{po}" if po else sc
        g = runs[(runs.scheme == key) & (runs.condition == llm_condition)]
        n = g[["n_ACCEPT", "n_REFUSE", "n_MODIFY"]].sum()
        pr, pm = n.n_REFUSE / n.sum(), n.n_MODIFY / n.sum()
        llm_eff = g.efficiency.mean()
        for label, a, b in (("random_matched", pr, pm), ("random_refuse_only", pr, 0.0),
                            ("random_modify_only", 0.0, pm)):
            for s in range(seeds):
                base = eff(sc, po, s, steps)
                e = eff(sc, po, s, steps, RandomPolicy(a, b, 10_000 + s))
                rows.append({"scheme": key, "condition": label, "seed": s, "p_refuse": round(a, 3),
                             "p_modify": round(b, 3), "efficiency": e, "delta_vs_passive": e - base,
                             "llm_efficiency_mean": llm_eff})
    with open(RES / "random_baseline.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    d = pd.DataFrame(rows)
    print(d.groupby(["scheme", "condition"])[["p_refuse", "p_modify", "efficiency", "delta_vs_passive",
                                              "llm_efficiency_mean"]].mean().round(3).to_string())


if __name__ == "__main__":
    main()
