"""Final-grid analysis (pre-registration A6): tables and figure from the cached runs in runs/*.jsonl. No API calls.

Unit of analysis: a question (repeats are averaged first). Intervals: bootstrap over clusters (athlete; each cohort-level question is its own cluster), 2000 resamples, seed 1.
"""
import collections, glob, json
import numpy as np, pandas as pd
from lcb.config import ROOT, RESULTS

OUT = RESULTS / "final_grid"; OUT.mkdir(parents=True, exist_ok=True)
SYS_ORDER = ["A", "A+", "C", "D", "E"]; MODELS = ["haiku", "sonnet", "opus"]


def load():
    qs = {q["qid"]: q for q in (json.loads(l) for l in open(ROOT / "data/benchmark/questions.jsonl"))}
    runs = []
    rer = {}
    rf = ROOT / "runs_sensitivity/capped_reruns.jsonl"
    if rf.exists():
        for l in open(rf):
            o = json.loads(l); rer[(o["qid"], o["system"], o["model"], o["rep"])] = bool(o["score"]["pass"])
    for f in sorted(glob.glob(str(ROOT / "runs/*_*.jsonl"))):
        for l in open(f):
            r = json.loads(l); q = qs[r["qid"]]
            n_tool = sum(1 for e in r["trace"] if e.get("kind") == "tool")
            runs.append(dict(qid=r["qid"], system=r["system"], model=r["model"], rep=r["rep"], family=r["family"], template=r["template"], split=r["split"], ok=bool(r["score"]["pass"]), no_answer=r["answer"] is None, ok_adj=rer.get((r["qid"], r["system"], r["model"], r["rep"]), bool(r["score"]["pass"])),
                             cost=r["cost"], seconds=r["seconds"], turns=r["turns"], tool_calls=n_tool, error=r["error"] is not None, cohort=bool(q["tags"].get("cohort")),
                             steps=q["tags"].get("steps", 1), cluster=q["athlete"] or q["qid"], fields=json.dumps({k: v for k, v in r["score"]["fields"].items() if not v}), unparsed=r["answer"] is None))
    return pd.DataFrame(runs)


def per_question(df):
    return df.groupby(["system", "model", "qid", "family", "template", "split", "cohort", "steps", "cluster"], as_index=False).agg(ok=("ok", "mean"), ok_adj=("ok_adj", "mean"), no_answer=("no_answer", "mean"), cost=("cost", "mean"), seconds=("seconds", "mean"), turns=("turns", "mean"), tool_calls=("tool_calls", "mean"))


def boot(values, clusters, B=2000, seed=1):
    if len(values) and float(np.mean(values)) == 1.0:           # all correct: the bootstrap interval is degenerate, use the exact one-sided bound (n = clusters)
        n = clusters.nunique(); return 1.0, float(0.025 ** (1 / n)), 1.0
    rng = np.random.default_rng(seed); v = pd.Series(values.values, index=clusters.values); g = [x.values for _, x in v.groupby(level=0)]
    m = np.array([np.mean(np.concatenate([g[i] for i in rng.integers(0, len(g), len(g))])) for _ in range(B)]); return float(np.mean(v.values)), float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def fmt(t): return f"{100*t[0]:.0f} [{100*t[1]:.0f}, {100*t[2]:.0f}]"


def main():
    df = load(); pq = per_question(df); final = pq[pq.split == "final"]; lines = []
    # 1 accuracy by system and model (final split) and by cohort / not cohort
    rows = []
    for m in MODELS:
        for s in SYS_ORDER:
            d = final[(final.model == m) & (final.system == s)]
            if d.empty: continue
            row = dict(model=m, system=s, questions=len(d), accuracy=fmt(boot(d.ok, d.cluster)), no_answer_pct=round(100 * d.no_answer.mean(), 1), accuracy_adjusted=fmt(boot(d.ok_adj, d.cluster)), cost_per_q=round(d.cost.mean(), 4), turns=round(d.turns.mean(), 1), tool_calls=round(d.tool_calls.mean(), 1))
            for name, sub in (("cohort", d[d.cohort]), ("per_athlete", d[~d.cohort])):
                row[name + "_n"] = len(sub); row[name + "_acc"] = fmt(boot(sub.ok, sub.cluster)) if len(sub) else "n/a"; row[name + "_acc_adj"] = fmt(boot(sub.ok_adj, sub.cluster)) if len(sub) else "n/a"
            rows.append(row)
    t1 = pd.DataFrame(rows); t1.to_csv(OUT / "accuracy_final_split.csv", index=False); lines += ["## Accuracy, final split", t1.to_string(index=False)]
    # 2 by family
    rows = []
    for m in MODELS:
        for s in SYS_ORDER:
            d = final[(final.model == m) & (final.system == s)]
            if d.empty: continue
            rows.append(dict(model=m, system=s, **{f: f"{100*d[d.family == f].ok.mean():.0f} (n={int((d.family == f).sum())})" for f in sorted(d.family.unique())}))
    t2 = pd.DataFrame(rows); t2.to_csv(OUT / "accuracy_by_family_final.csv", index=False); lines += ["## By family", t2.to_string(index=False)]
    # 3 paired differences (same questions)
    rows = []
    for col, tag in (("ok", "strict"), ("ok_adj", "adjusted")):
      pairs = [("C", "A", None), ("D", "A", None), ("D", "C", None), ("E", "C", "per_athlete"), ("A+", "A", "Q4")]
      for m in MODELS:
        for x, y, scope in pairs:
            a = pq[(pq.model == m) & (pq.system == x)].set_index("qid"); b = pq[(pq.model == m) & (pq.system == y)].set_index("qid")
            for label, sel in (("final", lambda d: d.split == "final"), ("cohort_final", lambda d: (d.split == "final") & d.cohort), ("per_athlete_final", lambda d: (d.split == "final") & ~d.cohort)):
                j = a.join(b, lsuffix="_x", rsuffix="_y", how="inner"); j = j[(j.split_x == "final") if label != "cohort_final" else ((j.split_x == "final") & j.cohort_x)]
                if label == "per_athlete_final": j = j[~j.cohort_x]
                if scope == "per_athlete": j = j[~j.cohort_x]
                if scope == "Q4": j = j[j.family_x == "Q4"]
                if len(j) < 3: continue
                d = (j[col + "_x"] - j[col + "_y"]); rows.append(dict(outcome=tag, model=m, comparison=f"{x} minus {y}", subset=label + ("/" + scope if scope else ""), questions=len(j), diff_pp=fmt(boot(d, j.cluster_x))))
    t3 = pd.DataFrame(rows); t3.to_csv(OUT / "paired_differences.csv", index=False); lines += ["## Paired differences (percentage points)", t3.to_string(index=False)]
    # 4 all splits, Haiku only (3 repeats)
    h = pq[pq.model == "haiku"]; rows = []
    for s in SYS_ORDER:
        d = h[h.system == s]
        if d.empty: continue
        rows.append(dict(system=s, questions=len(d), accuracy=fmt(boot(d.ok, d.cluster)), cohort=fmt(boot(d[d.cohort].ok, d[d.cohort].cluster)) if d.cohort.any() else "n/a", cost_per_q=round(d.cost.mean(), 4)))
    t4 = pd.DataFrame(rows); t4.to_csv(OUT / "haiku_all_splits.csv", index=False); lines += ["## Haiku, all 119 questions", t4.to_string(index=False)]
    # 5 per template (appendix)
    t5 = final.groupby(["family", "template", "system", "model"]).ok.mean().unstack(["model", "system"]).round(2); t5.to_csv(OUT / "accuracy_by_template_final.csv"); 
    # 6 failure fields
    f = df[(~df.ok) & (df.split == "final")]; t6 = f.groupby(["model", "system", "fields"]).size().reset_index(name="n").sort_values("n", ascending=False); t6.to_csv(OUT / "failures_final.csv", index=False)
    lines += ["## Failures (final split), top", t6.head(25).to_string(index=False)]
    # figure: accuracy cohort vs per-athlete and cost
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 2, figsize=(7.2, 2.7))
    for m, mk in zip(MODELS, ("o", "s", "^")):
        for s, col in zip(SYS_ORDER, ("#999999", "#bbbbbb", "#1b6ca8", "#d1782b", "#3a8f5c")):
            d = final[(final.model == m) & (final.system == s)]
            if d.empty: continue
            ax[1].scatter(d.cost.mean(), d.ok.mean(), c=col, marker=mk, s=28)
            if not d[d.cohort].empty: ax[0].scatter(s, d[d.cohort].ok.mean() + {"haiku": -0.02, "sonnet": 0, "opus": 0.02}[m], c=col, marker=mk, s=28)
    ax[0].set_title("cohort-level questions", fontsize=8); ax[0].set_ylabel("share correct", fontsize=8); ax[0].tick_params(labelsize=7)
    ax[1].set_xscale("log"); ax[1].set_xlabel("USD per question (log)", fontsize=8); ax[1].set_title("accuracy against cost, final split", fontsize=8); ax[1].tick_params(labelsize=7)
    plt.tight_layout(); plt.savefig(OUT / "fig_accuracy_cost.pdf"); plt.savefig(OUT / "fig_accuracy_cost.png", dpi=200)
    (OUT / "summary.txt").write_text("\n\n".join(lines)); print("\n\n".join(lines))


if __name__ == "__main__":
    main()
