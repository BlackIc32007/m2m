"""
Этапы 2-3 (+ чувствительность правила из этапа 5): ЗАМКНУТЫЙ ЦИКЛ.
Решения зон (правило или LLM) управляют симуляцией; сравниваем, чего это
стоит системе.

Условия (одинаковые сиды во всех -> парные сравнения):
    passive            -- зоны не решают, просят реальную потребность
    rule               -- RulePolicy (пороги)
    llm_own            -- LLM, контекст только "own"
    llm_full           -- LLM, полный контекст (own+mechanism+neighbors+goal)
    llm_full_sample    -- полный контекст, решение случайно с P(ДА)
    llm_full_db_sample -- то же, но P(ДА) без смещения к букве (debias)
    llm_full_soft      -- запрос = need x (1 + P(завысить)) -- RQ3: уверенность как вес
    llm_full_db_soft   -- то же с debias

Результаты:
    experiments/results/closed_loop_runs.csv       -- метрики каждого прогона
    experiments/results/closed_loop_decisions.csv  -- каждое решение LLM + его последствия
    experiments/results/rule_sensitivity.csv       -- (--sensitivity) сетка порогов правила

    python experiments/llm_closed_loop.py --seeds 10 --steps 80
    python experiments/llm_closed_loop.py --sensitivity
"""
import argparse
import csv
import itertools
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.llm.zone_context import BLOCKS
from src.model.conflict_model import ConflictModel
from src.model.zone_policies import RulePolicy, TokenLLMPolicy

SCHEMES = [("distributor", "proportional"), ("distributor", "equal"), ("distributor", "priority"),
           ("shared_tank", None), ("auction", None)]
RESULTS = Path(__file__).resolve().parent / "results"


def make_policy(cond: str, seed: int):
    rng = random.Random(10_000 + seed)  # своя случайность -> не сдвигает random модели
    return {
        "passive": None,
        "rule": RulePolicy(),
        "llm_own": TokenLLMPolicy(blocks=("own",)),
        "llm_full": TokenLLMPolicy(blocks=BLOCKS),
        "llm_full_sample": TokenLLMPolicy(blocks=BLOCKS, sample=True, rng=rng),
        "llm_full_db_sample": TokenLLMPolicy(blocks=BLOCKS, sample=True, debias=True, rng=rng),
        "llm_full_soft": TokenLLMPolicy(blocks=BLOCKS, soft=True),
        "llm_full_db_soft": TokenLLMPolicy(blocks=BLOCKS, soft=True, debias=True),
    }[cond]


CONDITIONS = ["passive", "rule", "llm_own", "llm_full", "llm_full_sample",
              "llm_full_db_sample", "llm_full_soft", "llm_full_db_soft"]


def run(scheme, policy, cond, seed, steps, zone_policy=None, extra=None):
    if zone_policy is None and cond != "passive":
        zone_policy = make_policy(cond, seed)
    m = ConflictModel(scheme, policy=policy or "proportional", seed=seed,
                      decision_mode="passive" if cond == "passive" else "autonomous",
                      zone_policy=zone_policy)
    t0 = time.time()
    for _ in range(steps):
        m.step()
    counts = {k: sum(z.decision_counts[k] for z in m.zones) for k in ("ACCEPT", "REFUSE", "MODIFY")}
    row = {
        "scheme": f"{scheme}/{policy}" if policy else scheme, "condition": cond, "seed": seed,
        "steps": steps, "efficiency": m.efficiency, "fairness_mean": None,
        "cum_yield": m.cum_yield, "cum_optimal": m.cum_optimal, "wasted": m.cum_wasted,
        "served": m.total_served, **{f"n_{k}": v for k, v in counts.items()},
        "wall_sec": round(time.time() - t0, 1), **(extra or {}),
    }
    fair = m.datacollector.get_model_vars_dataframe()["fairness"]
    row["fairness_mean"] = float(fair.mean())
    recs = []
    if isinstance(zone_policy, TokenLLMPolicy):
        row.update(llm_calls=zone_policy.calls, cache_hits=zone_policy.cache_hits,
                   fallbacks=sum(r["fallback"] for r in zone_policy.records),
                   contested=sum(bool(r.get("contested")) for r in zone_policy.records))
        recs = [{"condition": cond, "seed": seed, **r} for r in zone_policy.records]
    return row, recs


def write_csv(path, rows):
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def main_closed(seeds, steps, workers, conditions):
    jobs = [(sc, po, c, s) for c in conditions for sc, po in SCHEMES for s in range(seeds)]
    print(f"прогонов: {len(jobs)} ({len(conditions)} условий x {len(SCHEMES)} схем x {seeds} сидов, "
          f"{steps} шагов)", flush=True)
    rows, decisions, t0 = [], [], time.time()
    with ThreadPoolExecutor(workers) as ex:
        futs = [ex.submit(run, sc, po, c, s, steps) for sc, po, c, s in jobs]
        for i, f in enumerate(as_completed(futs), 1):
            row, recs = f.result()
            rows.append(row)
            decisions += recs
            if i % 10 == 0 or i == len(futs):
                print(f"  {i}/{len(futs)}  {time.time() - t0:.0f} с", flush=True)
    RESULTS.mkdir(exist_ok=True)
    write_csv(RESULTS / "closed_loop_runs.csv", rows)
    if decisions:
        write_csv(RESULTS / "closed_loop_decisions.csv", decisions)
    print("записано: closed_loop_runs.csv, closed_loop_decisions.csv", flush=True)


def main_sensitivity(seeds, steps):
    grid = list(itertools.product([0.05, 0.15, 0.3], [1, 2, 4], [1.5, 2.0, 3.0]))
    rows = []
    for (sc, po), s in itertools.product(SCHEMES, range(seeds)):
        rows.append(run(sc, po, "passive", s, steps)[0])
        for rt, ia, f in grid:
            pol = RulePolicy(refuse_threshold=rt, inflate_after=ia, inflate_factor=f)
            rows.append(run(sc, po, "rule", s, steps, zone_policy=pol,
                            extra={"refuse_threshold": rt, "inflate_after": ia, "inflate_factor": f})[0])
    RESULTS.mkdir(exist_ok=True)
    write_csv(RESULTS / "rule_sensitivity.csv", rows)
    print(f"записано: rule_sensitivity.csv ({len(rows)} прогонов)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--steps", type=int, default=80)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--conditions", default=",".join(CONDITIONS))
    ap.add_argument("--sensitivity", action="store_true")
    a = ap.parse_args()
    if a.sensitivity:
        main_sensitivity(a.seeds, a.steps)
    else:
        main_closed(a.seeds, a.steps, a.workers, a.conditions.split(","))
