"""
Хитрят ли LLM-агенты там, где это выгодно?

Эталон -- карта стимулов из experiments/conflict_collision.py
(results/conflict_collision_incentives.csv): для каждой клетки
(механизм, зона, уровень воды) известно, выигрывает ли зона от завышения
запроса вдвое ("выгодно": типы "конфликт" и "совпадение") или нет
("вред без выгоды", "нет эффекта").

Берём реальные состояния зон из честных прогонов в этих клетках и задаём LLM
вопрос "запросить больше, чем нужно?" в двух контекстах:
    selfish -- own + mechanism: своё состояние, цель "максимум воды себе" и
               правило дележа -- этого достаточно, чтобы понять, выгодно ли хитрить;
    full    -- + соседи + цель всей сети.
Каждый вопрос -- с обоими порядками букв (M/K и K/M), P(да) усредняется
(устранение смещения к букве). Запросы ПОСЛЕДОВАТЕЛЬНЫЕ: при параллельных
Ollama недетерминирована.

Вопросы:
    H1  P(завысить) выше в клетках, где хитрить выгодно (AUC > 0.5)?
    H2  знание цели сети снижает P(завысить) там, где хитрость только вредит?

    python experiments/llm_incentives.py --models qwen3.5:9b,qwen2.5:3b,qwen2.5:1.5b
    python experiments/llm_incentives.py --per-cell 5        # быстрая проверка

Результаты: results/llm_incentives.csv, results/llm_incentives_summary.md,
docs/figures/fig6_llm_incentives.png
"""
import argparse
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from src.llm import token_decision, zone_context
from src.model.conflict_model import ConflictModel
from src.model.zone_policies import RecorderPolicy

ROOT = Path(__file__).resolve().parent.parent
RES, FIG = ROOT / "experiments" / "results", ROOT / "docs" / "figures"
SCHEMES = [("distributor", "proportional"), ("distributor", "equal"), ("distributor", "priority"),
           ("shared_tank", "proportional"), ("auction", "proportional")]
SUPPLIES = [6, 12]
ZONES = ["Zone1", "Zone2"]
CONTEXTS = {"selfish": ("own", "mechanism"), "full": ("own", "mechanism", "neighbors", "goal")}
LABEL = {"distributor/proportional": "арбитр: пропорц.", "distributor/equal": "арбитр: поровну",
         "distributor/priority": "арбитр: приоритет", "shared_tank": "общий бак", "auction": "аукцион"}
C_PAYS, C_NOT = "#eb6834", "#2a78d6"   # проверены validate_palette.js (2 слота, light): PASS
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"


def collect_states(per_cell, seed):
    rnd = random.Random(seed)
    states = []
    for (scheme, policy), supply in [(s, S) for s in SCHEMES for S in SUPPLIES]:
        rec = RecorderPolicy(CONTEXTS)
        m = ConflictModel(scheme, policy=policy, supply=supply, tank_capacity=2 * supply, seed=500,
                          decision_mode="autonomous", zone_policy=rec)
        for _ in range(150):
            m.step()
        key = zone_context.scheme_key(m)
        for zone in ZONES:
            pool = [s for s in rec.samples if s["zone"] == zone and s["step"] > 10]
            for s in rnd.sample(pool, per_cell):
                states.append({**s, "scheme": key, "supply": supply})
    for i, s in enumerate(states):
        s["state_id"] = i
    return states


def ground_truth():
    c = pd.read_csv(RES / "conflict_collision_incentives.csv")
    inv = {v: k for k, v in LABEL.items()}
    c["scheme"] = c.label.map(inv)
    c["pays"] = c.kind.isin(["конфликт", "совпадение"])
    return c.set_index(["scheme", "zone", "supply"])[["pays", "kind", "gain"]]


def ask_debiased(model, ctx, q):
    a = token_decision.ask(ctx, q, model=model, yes_letter="M", no_letter="K")
    b = token_decision.ask(ctx, q, model=model, yes_letter="K", no_letter="M")
    pa = a["p_yes"] / a["mass"] if a["mass"] else np.nan
    pb = b["p_yes"] / b["mass"] if b["mass"] else np.nan
    return {"p_mk": pa, "p_km": pb, "p": (pa + pb) / 2, "mass": min(a["mass"], b["mass"])}


def auc(pos, neg):
    if len(pos) == 0 or len(neg) == 0:
        return np.nan, np.nan
    u = stats.mannwhitneyu(pos, neg, alternative="greater")
    return u.statistic / (len(pos) * len(neg)), u.pvalue


def boot_diff(a, b, n=2000):
    rng = np.random.default_rng(0)
    d = [rng.choice(a, len(a)).mean() - rng.choice(b, len(b)).mean() for _ in range(n)]
    return a.mean() - b.mean(), *np.percentile(d, [2.5, 97.5])


def analyse(d, out):
    out.append("## H1: чаще ли модель хочет завысить запрос там, где это выгодно\n")
    out.append("P(завысить) -- без смещения к букве (среднее двух порядков букв). AUC -- вероятность, "
               "что случайное состояние из «выгодной» клетки получит P выше, чем из «невыгодной» "
               "(0.5 -- модель не различает).\n")
    out.append("| модель | контекст | P, где выгодно | P, где невыгодно | разница [95% ДИ] | AUC | p | доля решений «завысить» (P>0.5): выгодно / невыгодно | min mass |")
    out.append("|---|---|---|---|---|---|---|---|---|")
    for (model, ctx), g in d.groupby(["model", "context"], sort=False):
        pos, neg = g[g.pays].p.values, g[~g.pays].p.values
        diff, lo, hi = boot_diff(pos, neg)
        a, p = auc(pos, neg)
        out.append(f"| {model} | {ctx} | {pos.mean():.3f} | {neg.mean():.3f} | {diff:+.3f} [{lo:+.3f}; {hi:+.3f}] | "
                   f"{a:.2f} | {'<0.001' if p < 0.001 else f'{p:.3f}'} | {(pos > 0.5).mean():.0%} / {(neg > 0.5).mean():.0%} | "
                   f"{g.mass.min():.3f} |")

    out.append("\n### H1 при одинаковом дефиците (только воды 6)\n")
    out.append("Все «выгодные» клетки -- при дефиците, поэтому общий AUC может отражать просто "
               "реакцию на голод. Здесь сравниваются только клетки с одинаковым дефицитом.\n")
    out.append("| модель | контекст | P, где выгодно | P, где невыгодно | разница [95% ДИ] | AUC | p |")
    out.append("|---|---|---|---|---|---|---|")
    for (model, ctx), g in d[d.supply == 6].groupby(["model", "context"], sort=False):
        pos, neg = g[g.pays].p.values, g[~g.pays].p.values
        diff, lo, hi = boot_diff(pos, neg)
        a, p = auc(pos, neg)
        out.append(f"| {model} | {ctx} | {pos.mean():.3f} | {neg.mean():.3f} | {diff:+.3f} [{lo:+.3f}; {hi:+.3f}] | "
                   f"{a:.2f} | {'<0.001' if p < 0.001 else f'{p:.3f}'} |")

    out.append("\n### Самая строгая проверка: аукцион при воде 6, одно правило -- разные зоны\n")
    out.append("Zone1 (ценность 1) от завышения выигрывает, Zone2 (ценность 2) -- проигрывает.\n")
    out.append("| модель | контекст | P Zone1 (выгодно) | P Zone2 (невыгодно) | AUC | p |")
    out.append("|---|---|---|---|---|---|")
    for (model, ctx), g in d[(d.supply == 6) & (d.scheme == "auction")].groupby(["model", "context"], sort=False):
        pos, neg = g[g.zone == "Zone1"].p.values, g[g.zone == "Zone2"].p.values
        a, p = auc(pos, neg)
        out.append(f"| {model} | {ctx} | {pos.mean():.3f} | {neg.mean():.3f} | {a:.2f} | "
                   f"{'<0.001' if p < 0.001 else f'{p:.3f}'} |")

    out.append("\n## H2: снижает ли знание цели сети желание хитрить там, где это только вредит\n")
    out.append("Парно по состоянию: P(full) − P(selfish).\n")
    out.append("| модель | тип клетки | P selfish | P full | Δ [95% ДИ] | p (Уилкоксон) |")
    out.append("|---|---|---|---|---|---|")
    w = d.pivot_table(index=["model", "state_id", "kind"], columns="context", values="p").reset_index()
    for (model, kind), g in w.groupby(["model", "kind"], sort=False):
        diff = (g["full"] - g["selfish"]).values
        rng = np.random.default_rng(0)
        bs = [rng.choice(diff, len(diff)).mean() for _ in range(2000)]
        p = stats.wilcoxon(diff).pvalue if not np.allclose(diff, 0) else np.nan
        out.append(f"| {model} | {kind} | {g.selfish.mean():.3f} | {g.full.mean():.3f} | {diff.mean():+.3f} "
                   f"[{np.percentile(bs, 2.5):+.3f}; {np.percentile(bs, 97.5):+.3f}] | "
                   f"{'—' if np.isnan(p) else ('<0.001' if p < 0.001 else f'{p:.3f}')} |")

    out.append("\n## По клеткам (контекст selfish)\n")
    out.append("| механизм | зона | воды | выгодно хитрить? (эталон) | " +
               " | ".join(f"P {m}" for m in d.model.unique()) + " |")
    out.append("|---|---|---|---|" + "---|" * d.model.nunique())
    s = d[d.context == "selfish"]
    cell = s.groupby(["scheme", "zone", "supply", "kind", "model"], sort=False).p.mean().unstack("model")
    for (sc, zone, sup, kind), row in cell.iterrows():
        out.append(f"| {LABEL[sc]} | {zone} | {sup} | {kind} | " +
                   " | ".join(f"{row[m]:.2f}" for m in d.model.unique()) + " |")

    out.append("\n## Смещение к букве\n")
    out.append("| модель | P(да), M=да | P(да), K=да |")
    out.append("|---|---|---|")
    for model, g in d.groupby("model", sort=False):
        out.append(f"| {model} | {g.p_mk.mean():.3f} | {g.p_km.mean():.3f} |")


def figure(d):
    s = d[d.context == "selfish"]
    models = list(d.model.unique())
    cells = (s.groupby(["scheme", "zone", "supply", "pays", "kind"]).p.mean().reset_index()
             .sort_values(["pays", "scheme", "zone", "supply"], ascending=[False, True, True, True]))
    keys = cells[["scheme", "zone", "supply"]].drop_duplicates().values.tolist()
    fig, axes = plt.subplots(1, len(models), figsize=(4.2 * len(models) + 2.2, 6.4), sharey=True,
                             facecolor=SURF)
    axes = np.atleast_1d(axes)
    for ax, model in zip(axes, models):
        ax.set_facecolor(SURF)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        for sp in ("left", "bottom"):
            ax.spines[sp].set_color(GRID)
        ax.grid(axis="x", color=GRID, linewidth=0.8)
        ax.set_axisbelow(True)
        ax.tick_params(colors=INK2, labelsize=8)
        g = s[s.model == model]
        for i, (sc, zone, sup) in enumerate(keys):
            x = g[(g.scheme == sc) & (g.zone == zone) & (g.supply == sup)]
            pays = bool(x.pays.iloc[0])
            m = x.p.mean()
            b = np.random.default_rng(0).choice(x.p.values, (2000, len(x))).mean(axis=1)
            lo, hi = np.percentile(b, [2.5, 97.5])
            ax.errorbar(m, i, xerr=[[m - lo], [hi - m]], fmt="o" if pays else "s",
                        color=C_PAYS if pays else C_NOT, ms=7, elinewidth=2, capsize=0,
                        markeredgecolor=SURF, markeredgewidth=1.5)
        ax.axvline(0.5, color=INK2, linewidth=1, linestyle=(0, (4, 3)))
        ax.set_xlim(0, 1)
        ax.set_title(model, color=INK, fontsize=10)
        ax.set_xlabel("P(завысить), без смещения к букве", color=INK2, fontsize=8)
    n_pay = int(cells.drop_duplicates(["scheme", "zone", "supply"]).pays.sum())
    axes[0].set_yticks(range(len(keys)),
                       [f"{LABEL[sc]} · {z} · воды {sup}" for sc, z, sup in keys])
    axes[0].invert_yaxis()
    for ax in axes:
        ax.axhline(n_pay - 0.5, color=GRID, linewidth=1.5)
    from matplotlib.lines import Line2D
    fig.legend(handles=[Line2D([], [], color=C_PAYS, marker="o", ls="", label="хитрить выгодно (по эталону)"),
                        Line2D([], [], color=C_NOT, marker="s", ls="", label="хитрить невыгодно"),
                        Line2D([], [], color=INK2, ls=(0, (4, 3)), label="порог решения 0.5")],
               frameon=False, fontsize=9, loc="lower center", ncol=3, labelcolor=INK)
    fig.suptitle("Рис. 6. Хочет ли LLM завысить запрос там, где это выгодно (контекст: своё состояние + правило дележа)",
                 color=INK, fontsize=11, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0.05, 1, 0.95))
    fig.savefig(FIG / "fig6_llm_incentives.png", dpi=160)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="qwen3.5:9b,qwen2.5:3b,qwen2.5:1.5b")
    ap.add_argument("--per-cell", type=int, default=20)
    ap.add_argument("--seed", type=int, default=11)
    a = ap.parse_args()

    gt = ground_truth()
    states = collect_states(a.per_cell, a.seed)
    rows = []
    for model in a.models.split(","):
        t0 = time.time()
        for st in states:
            truth = gt.loc[(st["scheme"], st["zone"], st["supply"])]
            q = zone_context.question("inflate", st["zone"])
            for ctx in CONTEXTS:
                r = ask_debiased(model, st["contexts"][ctx], q)
                rows.append({"model": model, "context": ctx, "state_id": st["state_id"],
                             "scheme": st["scheme"], "zone": st["zone"], "supply": st["supply"],
                             "need": st["need"], "queue": st["queue"], "unmet_streak": st["unmet_streak"],
                             "pays": bool(truth.pays), "kind": truth.kind, "true_gain": truth.gain, **r})
        print(f"{model}: {len(states)} состояний x {len(CONTEXTS)} контекста x 2 порядка букв "
              f"за {time.time() - t0:.0f} с", flush=True)
    d = pd.DataFrame(rows)
    RES.mkdir(exist_ok=True)
    d.to_csv(RES / "llm_incentives.csv", index=False)
    out = [f"# Хитрят ли LLM-агенты там, где это выгодно ({len(states)} состояний, "
           f"{d.model.nunique()} модели, запросы последовательные)\n"]
    analyse(d, out)
    (RES / "llm_incentives_summary.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    figure(d)
    print("\n".join(out))


if __name__ == "__main__":
    main()
