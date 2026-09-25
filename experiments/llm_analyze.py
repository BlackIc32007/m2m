"""
Этап 5: статистика и графики по результатам llm_open_loop.py,
llm_closed_loop.py и --sensitivity.

    python experiments/llm_analyze.py

Пишет:
    experiments/results/summary.md   -- все таблицы (markdown)
    docs/figures/fig1_letter_bias.png
    docs/figures/fig2_streak.png
    docs/figures/fig3_closed_loop.png

Доверительные интервалы -- 95% бутстреп (2000 повторов); сравнения --
парный критерий Уилкоксона (пары: одно и то же состояние в open loop,
один и тот же сид в closed loop).
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "experiments" / "results"
FIG = ROOT / "docs" / "figures"
RNG = np.random.default_rng(0)

# палитра: проверена validate_palette.js (light, 2 слота) -- PASS
C1, C2 = "#2a78d6", "#eb6834"
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"

out = []


def md(line=""):
    out.append(line)


def ci(x, n=2000):
    x = np.asarray(pd.Series(x).dropna(), dtype=float)
    if len(x) == 0:
        return np.nan, np.nan, np.nan
    if len(x) == 1 or np.all(x == x[0]):
        return x.mean(), x.mean(), x.mean()
    b = RNG.choice(x, (n, len(x))).mean(axis=1)
    return x.mean(), *np.percentile(b, [2.5, 97.5])


def fmt_ci(x, d=3):
    m, lo, hi = ci(x)
    return f"{m:.{d}f} [{lo:.{d}f}; {hi:.{d}f}]"


def wilcoxon_p(diff):
    diff = np.asarray(pd.Series(diff).dropna(), dtype=float)
    if len(diff) < 5 or np.allclose(diff, 0):
        return float("nan")
    return stats.wilcoxon(diff).pvalue


def fmt_p(p):
    return "—" if np.isnan(p) else ("<0.001" if p < 0.001 else f"{p:.3f}")


def style(ax):
    ax.set_facecolor(SURF)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=9)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


# ------------------------------------------------------------------ #
# 1. Open loop (RQ1, RQ4)
# ------------------------------------------------------------------ #
def open_loop():
    d = pd.read_csv(RES / "open_loop.csv")
    n_states = d.state_id.nunique()
    md(f"## Этап 1. Без обратной связи ({n_states} состояний, {len(d)} вызовов LLM)\n")

    md("### 1.1 Ответы по условиям\n")
    md("| условие | вопрос | доля ДА | P(ДА) среднее [95% ДИ] | уверенность | min mass |")
    md("|---|---|---|---|---|---|")
    for (cond, q), g in d.groupby(["condition", "question"], sort=False):
        md(f"| {cond} | {q} | {g.yes.mean():.3f} | {fmt_ci(g.p_yes)} | {g.confidence.mean():.3f} "
           f"| {g.mass.min():.3f} |")

    piv = d.pivot_table(index=["state_id", "question"], columns="condition", values="p_yes")
    yes = d.pivot_table(index=["state_id", "question"], columns="condition", values="yes")

    md("\n### 1.2 Влияние блоков контекста (RQ1): сдвиг P(ДА) относительно базы, парно по состоянию\n")
    md("| вопрос | условие | база | ΔP(ДА) [95% ДИ] | p (Уилкоксон) | доля переворотов решения |")
    md("|---|---|---|---|---|---|")
    pairs = [("own+mechanism", "own"), ("own+neighbors", "own"), ("own+goal", "own"),
             ("full", "own"), ("own[no-goal]", "own"), ("full[no-goal]", "full")]
    for q in ("yield", "inflate"):
        for cond, base in pairs:
            diff = piv.xs(q, level=1)[cond] - piv.xs(q, level=1)[base]
            flips = (yes.xs(q, level=1)[cond] != yes.xs(q, level=1)[base]).mean()
            md(f"| {q} | {cond} | {base} | {fmt_ci(diff)} | {fmt_p(wilcoxon_p(diff))} | {flips:.3f} |")

    md("\n### 1.3 Устойчивость (RQ4): полный контекст, варианты против базового\n")
    md("| вопрос | вариант | P(ДА) среднее | совпадение решения с базой | корреляция Спирмена P(ДА) с базой |")
    md("|---|---|---|---|---|")
    for q in ("yield", "inflate"):
        base = piv.xs(q, level=1)["full"]
        for v in ("full|swap", "full|para1", "full|para2", "full|ru", "full|3b"):
            pv = piv.xs(q, level=1)[v]
            agree = (yes.xs(q, level=1)[v] == yes.xs(q, level=1)["full"]).mean()
            rho = stats.spearmanr(base, pv).statistic if pv.std() > 0 else float("nan")
            md(f"| {q} | {v} | {pv.mean():.3f} | {agree:.3f} | {rho:.3f} |")

    md("\n### 1.4 Смещение к букве и его устранение\n")
    md("| вопрос | P(ДА), M=да | P(ДА), K=да | P(ДА) без смещения (среднее) | доля решений ДА без смещения |")
    md("|---|---|---|---|---|")
    deb = {}
    for q in ("yield", "inflate"):
        a, b = piv.xs(q, level=1)["full"], piv.xs(q, level=1)["full|swap"]
        deb[q] = (a + b) / 2
        md(f"| {q} | {fmt_ci(a)} | {fmt_ci(b)} | {fmt_ci(deb[q])} | {(deb[q] > 0.5).mean():.3f} |")

    md("\n### 1.5 Реакция на состояние: корреляция Спирмена P(ДА) с числом шагов нехватки\n")
    md("| вопрос | условие | ρ | p |")
    md("|---|---|---|---|")
    st = d.drop_duplicates("state_id").set_index("state_id")
    for q in ("yield", "inflate"):
        for cond in ("own", "full", "full|swap"):
            x = piv.xs(q, level=1)[cond]
            r = stats.spearmanr(st.loc[x.index, "unmet_streak"], x)
            md(f"| {q} | {cond} | {r.statistic:.3f} | {fmt_p(r.pvalue)} |")
        r = stats.spearmanr(st.loc[deb[q].index, "unmet_streak"], deb[q])
        md(f"| {q} | без смещения | {r.statistic:.3f} | {fmt_p(r.pvalue)} |")

    # --- рисунок 1: P(ДА) по условиям, два вопроса ---
    conds = ["own", "own+mechanism", "own+neighbors", "own+goal", "full", "own[no-goal]",
             "full[no-goal]", "full|para1", "full|para2", "full|ru", "full|3b", "full|swap"]
    fig, ax = plt.subplots(figsize=(7.2, 5.2), facecolor=SURF)
    style(ax)
    y = np.arange(len(conds))
    for off, q, col, lab in ((-0.16, "yield", C1, "Q1: уступить?"), (0.16, "inflate", C2, "Q2: завысить запрос?")):
        vals = [ci(piv.xs(q, level=1)[c]) for c in conds]
        m = np.array([v[0] for v in vals])
        err = np.array([[v[0] - v[1] for v in vals], [v[2] - v[0] for v in vals]])
        ax.errorbar(m, y + off, xerr=err, fmt="o", color=col, ms=6, elinewidth=2, capsize=0,
                    markeredgecolor=SURF, markeredgewidth=1.5, label=lab)
    ax.axvline(0.5, color=INK2, linewidth=1, linestyle=(0, (4, 3)))
    ax.text(0.495, -0.7, "порог решения 0.5", color=INK2, fontsize=8, ha="right", va="center")
    ax.set_yticks(y, conds)
    ax.invert_yaxis()
    ax.set_xlim(0, 0.6)
    ax.set_xlabel("P(ДА), среднее по 300 состояниям, 95% ДИ", color=INK2, fontsize=9)
    ax.set_title("Рис. 1. P(ДА) при разных контекстах: только перестановка букв\n"
                 "(M/K → K/M) заметно сдвигает ответ", color=INK, fontsize=11, loc="left")
    ax.set_ylim(len(conds) - 0.5, -1.2)
    ax.legend(frameon=False, fontsize=9, loc="upper right", bbox_to_anchor=(1.0, 0.93), labelcolor=INK)
    fig.tight_layout()
    fig.savefig(FIG / "fig1_letter_bias.png", dpi=160)
    plt.close(fig)

    # --- рисунок 2: P(завысить) vs шаги нехватки ---
    fig, ax = plt.subplots(figsize=(7.2, 4.2), facecolor=SURF)
    style(ax)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    streak = st["unmet_streak"].clip(upper=6)
    for series, col, lab in ((piv.xs("inflate", level=1)["full"], C1, "M = ДА (как в модуле)"),
                             (deb["inflate"], C2, "без смещения к букве")):
        g = pd.DataFrame({"s": streak.loc[series.index], "p": series}).groupby("s").p
        xs = sorted(g.groups)
        vals = [ci(g.get_group(k)) for k in xs]
        m = np.array([v[0] for v in vals])
        ax.plot(xs, m, color=col, linewidth=2, marker="o", ms=7, markeredgecolor=SURF,
                markeredgewidth=1.5, label=lab)
        ax.fill_between(xs, [v[1] for v in vals], [v[2] for v in vals], color=col, alpha=0.12,
                        linewidth=0)
        ax.annotate(lab, (xs[-1], m[-1]), xytext=(6, 0), textcoords="offset points",
                    color=INK2, fontsize=8, va="center")
    ax.axhline(0.5, color=INK2, linewidth=1, linestyle=(0, (4, 3)))
    ax.set_xticks(range(0, 7), ["0", "1", "2", "3", "4", "5", "6+"])
    ax.set_xlim(-0.2, 7.6)
    ax.set_ylim(0, 0.6)
    ax.set_xlabel("шагов подряд с нехваткой воды", color=INK2, fontsize=9)
    ax.set_ylabel("P(ДА) на «завысить запрос?»", color=INK2, fontsize=9)
    counts = streak.value_counts().sort_index()
    for k, n in counts.items():
        ax.text(k, 0.015, f"n={n}", color=INK2, fontsize=7, ha="center")
    ax.set_title("Рис. 2. Склонность завысить запрос слабо зависит от нехватки воды\n"
                 "и ни при каком её уровне не доходит до порога решения", color=INK, fontsize=11, loc="left")
    ax.legend(frameon=False, fontsize=9, loc="upper left", labelcolor=INK)
    fig.tight_layout()
    fig.savefig(FIG / "fig2_streak.png", dpi=160)
    plt.close(fig)


# ------------------------------------------------------------------ #
# 2. Closed loop (RQ2, RQ3)
# ------------------------------------------------------------------ #
COND_ORDER = ["passive", "rule", "llm_own", "llm_full", "llm_full_sample", "llm_full_db_sample",
              "llm_full_soft", "llm_full_db_soft"]


def closed_loop():
    r = pd.read_csv(RES / "closed_loop_runs.csv")
    seeds, steps = r.seed.nunique(), int(r.steps.iloc[0])
    md(f"\n## Этапы 2–3. Замкнутый цикл ({len(r)} прогонов: {r.condition.nunique()} условий × "
       f"{r.scheme.nunique()} схем × {seeds} сидов × {steps} шагов)\n")
    r["n_dec"] = r[["n_ACCEPT", "n_REFUSE", "n_MODIFY"]].sum(axis=1)

    md("### 2.1 Эффективность относительно оптимума (RQ2), парно по сиду против passive\n")
    md("| схема | условие | эффективность [95% ДИ] | Δ к passive | p (Уилкоксон) | справедливость | потери воды | REFUSE | MODIFY |")
    md("|---|---|---|---|---|---|---|---|---|")
    for sc, g in r.groupby("scheme"):
        base = g[g.condition == "passive"].set_index("seed").efficiency
        for c in COND_ORDER:
            x = g[g.condition == c].set_index("seed")
            if x.empty:
                continue
            diff = x.efficiency - base.loc[x.index]
            share = lambda k: (x[f"n_{k}"].sum() / x.n_dec.sum()) if x.n_dec.sum() else 0.0
            md(f"| {sc} | {c} | {fmt_ci(x.efficiency)} | {diff.mean():+.3f} | {fmt_p(wilcoxon_p(diff))} "
               f"| {x.fairness_mean.mean():.3f} | {x.wasted.mean():.1f} | {share('REFUSE'):.2f} "
               f"| {share('MODIFY'):.2f} |")

    llm = r[r.condition.str.startswith("llm")]
    if not llm.empty:
        md("\n### 2.2 Работа LLM\n")
        md("| условие | вызовов LLM | попаданий в кэш | откатов на правило | спорных решений (conf < 0.6) |")
        md("|---|---|---|---|---|")
        for c, g in llm.groupby("condition"):
            tot = g.llm_calls.sum() + g.cache_hits.sum()
            md(f"| {c} | {int(g.llm_calls.sum())} | {g.cache_hits.sum() / tot:.2f} | "
               f"{int(g.fallbacks.sum())} | {g.contested.sum() / g.n_dec.sum():.3f} |")

    dp = RES / "closed_loop_decisions.csv"
    if dp.exists():
        dec = pd.read_csv(dp)
        md("\n### 2.3 Уверенность как сигнал (RQ3)\n")
        md("| условие | решение | n | уверенность | потеряно сверх потребности (среднее) |")
        md("|---|---|---|---|---|")
        for (c, k), g in dec.groupby(["condition", "decision"]):
            md(f"| {c} | {k} | {len(g)} | {g.confidence.mean():.3f} | {g.overdraw.mean():.3f} |")
        md("\n| условие | ρ Спирмена: P(завысить) ~ потери | p | ρ: уверенность ~ потери | p |")
        md("|---|---|---|---|---|")
        for c, g in dec.dropna(subset=["q2_p_yes", "overdraw"]).groupby("condition"):
            if g.q2_p_yes.std() == 0 or g.overdraw.std() == 0:
                md(f"| {c} | — | — | — | — |")
                continue
            a = stats.spearmanr(g.q2_p_yes, g.overdraw)
            b = stats.spearmanr(g.confidence, g.overdraw)
            md(f"| {c} | {a.statistic:.3f} | {fmt_p(a.pvalue)} | {b.statistic:.3f} | {fmt_p(b.pvalue)} |")

    # --- рисунок 3: эффективность по схемам (малые множители) ---
    schemes = sorted(r.scheme.unique())
    conds = [c for c in COND_ORDER if c in set(r.condition)]
    fig, axes = plt.subplots(1, len(schemes), figsize=(12, 4.4), sharey=True, facecolor=SURF)
    for ax, sc in zip(axes, schemes):
        style(ax)
        g = r[r.scheme == sc]
        base = g[g.condition == "passive"].efficiency.mean()
        for i, c in enumerate(conds):
            m, lo, hi = ci(g[g.condition == c].efficiency)
            col = C2 if c.startswith("llm") else C1
            ax.errorbar(m, i, xerr=[[m - lo], [hi - m]], fmt="o", color=col, ms=6, elinewidth=2,
                        capsize=0, markeredgecolor=SURF, markeredgewidth=1.5)
        ax.axvline(base, color=INK2, linewidth=1, linestyle=(0, (4, 3)))
        ax.set_title(sc.replace("distributor/", "арбитр: "), color=INK, fontsize=9)
        ax.tick_params(axis="x", labelsize=8)
    axes[0].set_yticks(range(len(conds)), conds)
    axes[0].invert_yaxis()
    from matplotlib.lines import Line2D
    fig.legend(handles=[Line2D([], [], color=C1, marker="o", ls="", label="без LLM"),
                        Line2D([], [], color=C2, marker="o", ls="", label="LLM-политика"),
                        Line2D([], [], color=INK2, ls=(0, (4, 3)), label="уровень passive")],
               frameon=False, fontsize=9, loc="lower center", ncol=3, labelcolor=INK)
    fig.suptitle("Рис. 3. Эффективность относительно оптимума (95% ДИ по сидам)", color=INK,
                 fontsize=11, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0.07, 1, 0.95))
    fig.savefig(FIG / "fig3_closed_loop.png", dpi=160)
    plt.close(fig)


# ------------------------------------------------------------------ #
# 3. Чувствительность правила
# ------------------------------------------------------------------ #
def sensitivity():
    p = RES / "rule_sensitivity.csv"
    if not p.exists():
        return
    d = pd.read_csv(p)
    rule = d[d.condition == "rule"]
    md(f"\n## Этап 5. Чувствительность правила ({rule[['refuse_threshold', 'inflate_after', 'inflate_factor']].drop_duplicates().shape[0]} "
       f"комбинаций порогов × {d.scheme.nunique()} схем × {d.seed.nunique()} сидов)\n")
    md("| схема | passive | правило: min | правило: max | по inflate_after = 1 / 2 / 4 | по refuse_threshold = 0.05 / 0.15 / 0.3 | по inflate_factor = 1.5 / 2 / 3 |")
    md("|---|---|---|---|---|---|---|")
    for sc, g in rule.groupby("scheme"):
        pas = d[(d.condition == "passive") & (d.scheme == sc)].efficiency.mean()
        by = lambda col: " / ".join(f"{v:.3f}" for v in g.groupby(col).efficiency.mean())
        cell = g.groupby(["refuse_threshold", "inflate_after", "inflate_factor"]).efficiency.mean()
        md(f"| {sc} | {pas:.3f} | {cell.min():.3f} | {cell.max():.3f} | {by('inflate_after')} | "
           f"{by('refuse_threshold')} | {by('inflate_factor')} |")


if __name__ == "__main__":
    FIG.mkdir(parents=True, exist_ok=True)
    md("# Сводка экспериментов: LLM-решение одним токеном в ConflictModel\n")
    open_loop()
    if (RES / "closed_loop_runs.csv").exists():
        closed_loop()
    sensitivity()
    (RES / "summary.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"записано: {RES / 'summary.md'} и рисунки в {FIG}", file=sys.stderr)
