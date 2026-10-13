"""Plots from the cached runs: output-cap sweep, cost per question and latency per question. Writes results/figures/*.pdf and *.png."""
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from lcb.config import ROOT
from lcb.analysis import final_tables as ft

SC = {"A": "#7f7f7f", "A+": "#bdbdbd", "C": "#1f77b4", "D": "#e69f00", "E": "#2ca02c"}
MARK = {"haiku": "o", "sonnet": "s", "opus": "^"}
NAME = {"haiku": "Haiku 5.5", "sonnet": "Sonnet 5.5", "opus": "Opus 5.5"}
plt.rcParams.update({"pdf.fonttype": 42, "font.size": 8, "axes.labelsize": 8, "xtick.labelsize": 7.5, "ytick.labelsize": 7.5, "legend.fontsize": 7,
                     "axes.spines.top": False, "axes.spines.right": False, "font.family": "serif"})
LAB = {"A": "A", "A+": "A+", "C": "B", "D": "C", "E": "D"}
FIG = ROOT / "results/figures"; FIG.mkdir(parents=True, exist_ok=True)


def sweep():
    cs = pd.read_csv(ROOT / "results/final_grid/capsweep.csv"); caps = sorted(cs.cap.unique())
    fig, ax = plt.subplots(figsize=(2.2, 2.2))
    for m, c in (("haiku", "#1f77b4"), ("sonnet", "#d55e00")):
        d = cs[cs.model == m].sort_values("cap")
        ax.plot(range(len(caps)), 100 * d.correct, "-o", color=c, ms=3.5, lw=1.2, label=f"{NAME[m]}, correct")
        ax.plot(range(len(caps)), 100 * d.no_answer, "--s", color=c, ms=3.5, lw=1.1, label=f"{NAME[m]}, no answer")
    ha = pd.read_csv(ROOT / "results/final_grid/haiku_all_splits.csv"); ref = float(ha[ha.system == "C"].cohort.iloc[0].split()[0])
    ax.axhline(ref, color="#1f77b4", lw=0.8, ls=":"); ax.text(len(caps) - 1, ref - 2, "agent B, Haiku", ha="right", va="top", fontsize=6.5, color="#1f77b4")
    ax.set_xticks(range(len(caps))); ax.set_xticklabels([f"{c // 1000}k" for c in caps])
    ax.set_xlabel("output cap (tokens per call)"); ax.set_ylabel("% of runs"); ax.set_ylim(-3, 108)
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.27), ncol=1, handlelength=1.6)
    fig.savefig(FIG / "fig_sweep.pdf", bbox_inches="tight"); fig.savefig(FIG / "fig_sweep.png", dpi=200, bbox_inches="tight"); plt.close(fig)


def cost():
    df = ft.load(); pq = ft.per_question(df); fin = pq[(pq.split == "final") & (~pq.cohort)]
    fig, ax = plt.subplots(figsize=(2.2, 2.2)); syss = [x for x in ft.SYS_ORDER if x != "A+"]; w = 0.16
    for i, s in enumerate(syss):
        vals = [fin[(fin.model == m) & (fin.system == s)].cost.mean() for m in ("haiku", "sonnet", "opus")]
        xs = [k + (i - (len(syss) - 1) / 2) * w for k in range(3)]
        ax.bar(xs, vals, w * 0.9, color=SC[s], label=LAB[s])
    ax.set_yscale("log"); ax.set_xticks(range(3)); ax.set_xticklabels([NAME[m].split()[0] for m in ("haiku", "sonnet", "opus")])
    ax.set_ylabel("USD per question (log)"); ax.set_ylim(1.5e-4, 0.3)
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=5, handlelength=0.9, columnspacing=1.0, handletextpad=0.4)
    fig.savefig(FIG / "fig_cost.pdf", bbox_inches="tight"); fig.savefig(FIG / "fig_cost.png", dpi=200, bbox_inches="tight"); plt.close(fig)


def latency():
    df = ft.load(); pq = ft.per_question(df); fin = pq[(pq.split == "final") & (~pq.cohort)]
    fig, ax = plt.subplots(figsize=(2.2, 2.2)); syss = [x for x in ft.SYS_ORDER if x != "A+"]; w = 0.16
    for i, s in enumerate(syss):
        vals = [fin[(fin.model == m) & (fin.system == s)].seconds.mean() for m in ("haiku", "sonnet", "opus")]
        xs = [k + (i - (len(syss) - 1) / 2) * w for k in range(3)]
        ax.bar(xs, vals, w * 0.9, color=SC[s], label=LAB[s])
    ax.set_xticks(range(3)); ax.set_xticklabels([NAME[m].split()[0] for m in ("haiku", "sonnet", "opus")])
    ax.set_ylabel("seconds per question")
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=5, handlelength=0.9, columnspacing=1.0, handletextpad=0.4)
    fig.savefig(FIG / "fig_latency.pdf", bbox_inches="tight"); fig.savefig(FIG / "fig_latency.png", dpi=200, bbox_inches="tight"); plt.close(fig)


def main():
    sweep(); cost(); latency(); print("figures written")


if __name__ == "__main__":
    main()
