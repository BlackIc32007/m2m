"""
Эксперимент без LLM: коллизия и конфликт в модели распределения воды.

Коллизия (зона против зоны): несколько зон одновременно претендуют на воду,
которой на всех не хватает. Измеряем, насколько неравно механизм делит воду:
    fairness       -- индекс Джайна по доле удовлетворённой потребности (1 = поровну)
    worst_share    -- доля потребности, которую получила самая обделённая зона
    starved_steps  -- доля шагов, когда хоть одна зона с потребностью не получила ничего

Конфликт (зона против системы): зоне выгодно получить больше себе, системе --
максимум sum(приоритет x sqrt(вода)). Конфликт ЕСТЬ, когда одной зоне выгодно
завысить запрос (её вода растёт), а система от этого теряет (эффективность
падает). Измеряем:
    own_gain  -- на сколько % больше воды получает зона, завысившая запрос в 2 раза
                 (остальные честные), против всех честных -- тот же сид
    sys_delta -- изменение эффективности системы при этом
    all_delta -- изменение эффективности, если завышают все ("трагедия общин")

Факторы: 5 механизмов x 5 уровней воды (3..15 за шаг при среднем приходе
потребности 10) x 4 поведения x сиды.

    python experiments/conflict_collision.py            # 20 сидов x 200 шагов, ~1-2 мин
    python experiments/conflict_collision.py --seeds 5  # быстро

Результаты: experiments/results/conflict_collision.csv,
            experiments/results/conflict_collision_summary.md,
            docs/figures/fig4_collision.png, docs/figures/fig5_conflict.png
"""
import argparse
import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from src.model.conflict_model import ConflictModel
from src.model.zone_policies import Decision

ROOT = Path(__file__).resolve().parent.parent
RES, FIG = ROOT / "experiments" / "results", ROOT / "docs" / "figures"

SCHEMES = [("distributor", "proportional", "арбитр: пропорц."), ("distributor", "equal", "арбитр: поровну"),
           ("distributor", "priority", "арбитр: приоритет"), ("shared_tank", "proportional", "общий бак"),
           ("auction", "proportional", "аукцион")]
SUPPLIES = [3, 6, 9, 12, 15]
BEHAVIOURS = {"honest": set(), "zone1_inflates": {"Zone1"}, "zone2_inflates": {"Zone2"},
              "all_inflate": {"Zone1", "Zone2", "Zone3"}}
MEAN_ARRIVAL = 10.0  # 3 + 3 + 4 в среднем за шаг

# палитра проверена validate_palette.js (5 слотов, light): PASS, контраст WARN ->
# прямые подписи линий + разные маркеры + таблица в отчёте
COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
MARKERS = ["o", "s", "^", "D", "v"]
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"


class InflatePolicy:
    """Зоны из множества inflaters всегда просят вдвое больше потребности,
    остальные -- честно. Без порогов и случайности: чистая стратегия."""

    def __init__(self, inflaters):
        self.inflaters = inflaters

    def decide(self, zone):
        if zone.name in self.inflaters:
            return Decision("MODIFY", zone.need * 2.0, "завышает запрос")
        return Decision("ACCEPT", zone.need, "честный запрос")


def run(scheme, policy, supply, behaviour, seed, steps):
    inflaters = BEHAVIOURS[behaviour]
    m = ConflictModel(scheme, policy=policy, supply=supply, tank_capacity=2 * supply, seed=seed,
                      decision_mode="autonomous" if inflaters else "passive",
                      zone_policy=InflatePolicy(inflaters))
    need = {z.name: 0.0 for z in m.zones}
    starved_steps = 0
    for _ in range(steps):
        m.step()
        for z in m.zones:
            need[z.name] += z.need
        if any(z.need > 1e-9 and z.allocated < 1e-9 for z in m.zones):
            starved_steps += 1
    shares = {z.name: z.total_served / need[z.name] if need[z.name] else 1.0 for z in m.zones}
    fair = m.datacollector.get_model_vars_dataframe()["fairness"].mean()
    return {
        "scheme": scheme if scheme != "distributor" else f"distributor/{policy}",
        "supply": supply, "scarcity": supply / MEAN_ARRIVAL, "behaviour": behaviour, "seed": seed,
        "efficiency": m.efficiency, "fairness": fair, "worst_share": min(shares.values()),
        "starved_steps": starved_steps / steps, "wasted": m.cum_wasted,
        **{f"served_{z.name}": z.total_served for z in m.zones},
        **{f"share_{k}": v for k, v in shares.items()},
    }


def ci(x):
    x = np.asarray(x, float)
    b = np.random.default_rng(0).choice(x, (2000, len(x))).mean(axis=1)
    return x.mean(), *np.percentile(b, [2.5, 97.5])


def style(ax):
    ax.set_facecolor(SURF)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=9)
    ax.grid(color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def lines_panel(ax, table, ylabel, fmt_label, hline=None, ylim=None):
    style(ax)
    for (label, col, mk) in zip([s[2] for s in SCHEMES], COLORS, MARKERS):
        sub = table[table.label == label].sort_values("supply")
        ax.plot(sub.supply, sub.value, color=col, linewidth=2, marker=mk, ms=7,
                markeredgecolor=SURF, markeredgewidth=1.5, label=label)
        ax.fill_between(sub.supply, sub.lo, sub.hi, color=col, alpha=0.12, linewidth=0)
    if ylim is not None:
        ax.set_ylim(*ylim)
    if hline is not None:
        ax.axhline(hline, color=INK2, linewidth=1, linestyle=(0, (4, 3)))
    ax.axvline(MEAN_ARRIVAL, color=GRID, linewidth=1.5)
    lo, hi = ax.get_ylim()
    ax.text(MEAN_ARRIVAL, lo + (hi - lo) * 0.03, " воды = средний\n приход потребности",
            color=INK2, fontsize=7, va="bottom")
    ax.set_xticks(SUPPLIES)
    ax.set_xlim(2.5, 15.5)
    ax.set_xlabel("воды за шаг (средний приход потребности -- 10)", color=INK2, fontsize=9)
    ax.set_ylabel(ylabel, color=INK2, fontsize=9)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--steps", type=int, default=200)
    a = ap.parse_args()

    rows = [run(sc, po, sup, beh, seed, a.steps)
            for (sc, po, _), sup, beh, seed in itertools.product(SCHEMES, SUPPLIES, BEHAVIOURS, range(a.seeds))]
    d = pd.DataFrame(rows)
    labels = {("distributor/" + po if sc == "distributor" else sc): lab for sc, po, lab in SCHEMES}
    d["label"] = d.scheme.map(labels)
    RES.mkdir(exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    d.to_csv(RES / "conflict_collision.csv", index=False)

    out = [f"# Коллизия и конфликт без LLM ({len(d)} прогонов: {len(SCHEMES)} механизмов x "
           f"{len(SUPPLIES)} уровней воды x {len(BEHAVIOURS)} поведения x {a.seeds} сидов x {a.steps} шагов)\n"]

    # ---------- коллизия: все честные ----------
    h = d[d.behaviour == "honest"]
    out.append("## Коллизия: как механизм делит воду, когда её не хватает (все зоны честные)\n")
    out.append("| механизм | воды за шаг | эффективность | справедливость (Джайн) | доля потребности у самой обделённой зоны | шагов, где кто-то получил 0 | Zone1 / Zone2 / Zone3: доля потребности |")
    out.append("|---|---|---|---|---|---|---|")
    for (lab, sup), g in h.groupby(["label", "supply"], sort=False):
        out.append(f"| {lab} | {sup} | {g.efficiency.mean():.3f} | {g.fairness.mean():.3f} | "
                   f"{g.worst_share.mean():.2f} | {g.starved_steps.mean():.0%} | "
                   f"{g.share_Zone1.mean():.2f} / {g.share_Zone2.mean():.2f} / {g.share_Zone3.mean():.2f} |")

    # ---------- конфликт: одна зона завышает ----------
    base = h.set_index(["scheme", "supply", "seed"]).sort_index()
    out.append("\n## Конфликт: выгодно ли одной зоне завысить запрос и чего это стоит системе\n")
    out.append("Выигрыш зоны -- изменение воды, которую она использовала, против всех честных "
               "(тот же сид), в % (если в честном варианте зона не получала ничего -- в единицах "
               "воды за прогон). Тип отношения: **конфликт** -- зоне выгодно, системе вредно; "
               "**совпадение** -- выгодно обоим; **вред без выгоды** -- зона ничего не выигрывает, "
               "система теряет; **нет эффекта**.\n")
    out.append("| механизм | воды за шаг | кто завышает | выигрыш зоны [95% ДИ] | Δ эффективности системы | p | тип отношения | все завышают: Δ эффективности |")
    out.append("|---|---|---|---|---|---|---|---|")
    conf_rows = []
    for (lab, sc, sup), _ in h.groupby(["label", "scheme", "supply"], sort=False):
        allinf = d[(d.scheme == sc) & (d.supply == sup) & (d.behaviour == "all_inflate")].set_index("seed")
        b = base.loc[(sc, sup)]
        all_delta = (allinf.efficiency - b.efficiency).mean()
        for beh, zone in (("zone1_inflates", "Zone1"), ("zone2_inflates", "Zone2")):
            dev = d[(d.scheme == sc) & (d.supply == sup) & (d.behaviour == beh)].set_index("seed")
            diff = dev[f"served_{zone}"] - b[f"served_{zone}"]
            pct = b[f"served_{zone}"].mean() > 0
            gain = 100 * diff / b[f"served_{zone}"] if pct else diff
            unit = "%" if pct else " ед."
            sysd = dev.efficiency - b.efficiency
            p = stats.wilcoxon(sysd).pvalue if not np.allclose(sysd, 0) else float("nan")
            m_, lo, hi = ci(gain)
            gains = lo > 0 and m_ > (1 if pct else 0.5)          # зона значимо выигрывает
            sys_sig = not np.isnan(p) and p < 0.05 and abs(sysd.mean()) > 0.001
            kind = ("конфликт" if gains and sys_sig and sysd.mean() < 0 else
                    "совпадение" if gains and sys_sig and sysd.mean() > 0 else
                    "вред без выгоды" if not gains and sys_sig and sysd.mean() < 0 else
                    "нет эффекта" if not gains and not sys_sig else "прочее")
            conflict = kind == "конфликт"
            out.append(f"| {lab} | {sup} | {zone} | {m_:+.1f}{unit} [{lo:+.1f}; {hi:+.1f}] | {sysd.mean():+.3f} | "
                       f"{'—' if np.isnan(p) else ('<0.001' if p < 0.001 else f'{p:.3f}')} | "
                       f"{'**' + kind + '**' if kind in ('конфликт', 'совпадение') else kind} | {all_delta:+.3f} |")
            conf_rows.append({"label": lab, "supply": sup, "zone": zone, "gain": m_, "gain_lo": lo,
                              "gain_hi": hi, "gain_pct": pct, "sys": sysd.mean(), "sys_lo": ci(sysd)[1],
                              "sys_hi": ci(sysd)[2], "kind": kind, "conflict": conflict})
    c = pd.DataFrame(conf_rows)
    c.to_csv(RES / "conflict_collision_incentives.csv", index=False)
    (RES / "conflict_collision_summary.md").write_text("\n".join(out) + "\n", encoding="utf-8")

    # ---------- рисунок 4: коллизия ----------
    def agg(col):
        t = []
        for (lab, sup), g in h.groupby(["label", "supply"]):
            v, lo, hi = ci(g[col])
            t.append({"label": lab, "supply": sup, "value": v, "lo": lo, "hi": hi})
        return pd.DataFrame(t)

    short = lambda s: s.replace("арбитр: ", "")
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), facecolor=SURF)
    lines_panel(axes[0], agg("worst_share"), "доля потребности у самой обделённой зоны", short,
                ylim=(0, 1.05))
    axes[0].set_title("А. Кого обделяет коллизия (линия «пропорц.» совпадает с «поровну»)",
                      color=INK, fontsize=10, loc="left")
    lines_panel(axes[1], agg("efficiency"), "эффективность относительно оптимума", short, hline=1.0)
    axes[1].set_title("Б. Сколько теряет система", color=INK, fontsize=10, loc="left")
    handles, labs = axes[0].get_legend_handles_labels()
    fig.legend(handles, labs, frameon=False, fontsize=9, loc="lower center", ncol=5, labelcolor=INK)
    fig.suptitle("Рис. 4. Коллизия: все зоны честные, воды не хватает на всех слева от линии «10»",
                 color=INK, fontsize=11, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0.07, 1, 0.95))
    fig.savefig(FIG / "fig4_collision.png", dpi=160)
    plt.close(fig)

    # ---------- рисунок 5: конфликт (Zone1 завышает) ----------
    z1 = c[c.zone == "Zone1"].copy()
    z1.loc[~z1.gain_pct, ["gain", "gain_lo", "gain_hi"]] = np.nan  # в % не выражается (база 0)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), facecolor=SURF)
    t = z1.rename(columns={"gain": "value", "gain_lo": "lo", "gain_hi": "hi"})
    lines_panel(axes[0], t, "выигрыш Zone1, % воды", short, hline=0.0)
    axes[0].set_title("А. Выгодно ли зоне завысить запрос", color=INK, fontsize=10, loc="left")
    t = z1.rename(columns={"sys": "value", "sys_lo": "lo", "sys_hi": "hi"})
    lines_panel(axes[1], t, "изменение эффективности системы", short, hline=0.0)
    axes[1].set_title("Б. Чего это стоит системе", color=INK, fontsize=10, loc="left")
    handles, labs = axes[0].get_legend_handles_labels()
    fig.legend(handles, labs, frameon=False, fontsize=9, loc="lower center", ncol=5, labelcolor=INK)
    fig.suptitle("Рис. 5. Конфликт: Zone1 (приоритет 1) завышает запрос вдвое, остальные честные",
                 color=INK, fontsize=11, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0.07, 1, 0.95))
    fig.savefig(FIG / "fig5_conflict.png", dpi=160)
    plt.close(fig)

    print("\n".join(out))


if __name__ == "__main__":
    main()
