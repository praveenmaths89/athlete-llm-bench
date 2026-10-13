"""Final analysis (plan A4). Writes tables to results/exploratory/final/tables and figures to results/exploratory/final/figures."""
import json, math, random, sys, collections
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parents[3]
F = ROOT / "results/exploratory/final"; FIN = ROOT / "data_private/real_pairs/final"; T = F / "tables"; G = F / "figures"; T.mkdir(exist_ok=True, parents=True); G.mkdir(exist_ok=True, parents=True)
TE = json.loads((ROOT / "results/typical_error.json").read_text())
cases = pd.DataFrame(json.load(open(FIN / "cases.json"))); cases["adv"] = cases["dv"].abs()
Z = {"68%": 1.0, "90%": 1.645, "95%": 1.96}
def thr(sex, crit): return Z[crit] * math.sqrt(2) * TE[sex]["te_mean_cm"]
for crit in Z: cases["thr_" + crit] = cases["sex"].map(lambda s: thr(s, crit))
rng = np.random.default_rng(1)

def cboot(df, fn, B=2000):
    """athlete-clustered bootstrap CI of fn(df)."""
    groups = [g for _, g in df.groupby("pid")]; vals = []
    for _ in range(B):
        idx = rng.integers(0, len(groups), len(groups)); vals.append(fn(pd.concat([groups[i] for i in idx])))
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))
def fmt(x, ci): return f"{100*x:.0f}% [{100*ci[0]:.0f}, {100*ci[1]:.0f}]"

# ---------- Part 1: the phenomenon ----------
rows = []
for crit in Z:
    within = cases["adv"] <= cases["thr_" + crit]
    for cut in (3, 5, 10):
        moved = (cases["c_b"] - cases["c_a"]).abs() >= cut
        both = within & moved
        d = cases.assign(w=within, b=both)
        rows.append(dict(criterion=crit, centile_cut=cut, pairs=len(cases),
                         within_noise=fmt(d.w.mean(), cboot(d, lambda x: x.w.mean())),
                         within_noise_and_centile_moves=fmt(d.b.mean(), cboot(d, lambda x: x.b.mean()))))
pd.DataFrame(rows).to_csv(T / "part1_prevalence.csv", index=False)
cases["dc"] = cases["c_b"] - cases["c_a"]
cases["age_share"] = (cases["age_drift"].abs() >= 5)
p1 = dict(pairs=len(cases), athletes=int(cases.pid.nunique()), age_drift_median=float(cases.age_drift.median()),
          age_drift_p10=float(cases.age_drift.quantile(.1)), age_drift_5plus=fmt(cases.age_share.mean(), cboot(cases, lambda x: x.age_share.mean())),
          change_cm_median=float(cases.dv.median()))
(T / "part1_summary.json").write_text(json.dumps(p1, indent=1)); print(json.dumps(p1, indent=1)); print(pd.DataFrame(rows).to_string(index=False))

# ---------- Parts 2 and 3 ----------
def load(path):
    p = FIN / path
    if not p.exists(): return None
    r = [json.loads(l) for l in p.read_text().splitlines()]
    d = pd.DataFrame(r); d = d.merge(cases, on="case_id", how="left")
    d["said_real"] = d.parsed.map(lambda x: (x or {}).get("jump_change_is") == "real")
    d["verdict"] = d.parsed.map(lambda x: (x or {}).get("jump_change_is"))
    d["thr_used"] = d.parsed.map(lambda x: (x or {}).get("noise_threshold_cm"))
    d["reason"] = d.parsed.map(lambda x: (x or {}).get("centile_change_reason"))
    d["ok95"] = d.verdict == d.gold_change
    return d
c = load("c0c1_raw.jsonl")
if c is not None and len(c):
    import statsmodels.api as sm
    out = []
    for m in sorted(c.model.unique()):
        for cond in ("C0", "C1"):
            s = c[(c.model == m) & (c.cond == cond)]
            if s.empty: continue
            wn = s[s.gold_change == "within_measurement_noise"]; re_ = s[s.gold_change == "real"]
            row = dict(model=m, cond=cond, calls=len(s), pairs=int(s.case_id.nunique()), unparsed=int(s.parsed.isna().sum()),
                       agree95_all=fmt(s.ok95.mean(), cboot(s, lambda x: x.ok95.mean())))
            if len(wn): row["agree95_within_noise"] = fmt(wn.ok95.mean(), cboot(wn, lambda x: x.ok95.mean()))
            if len(re_): row["agree95_real"] = fmt(re_.ok95.mean(), cboot(re_, lambda x: x.ok95.mean()))
            for crit in Z:
                row["agree_" + crit] = fmt(((s.said_real) == (s.adv > s["thr_" + crit])).mean(), cboot(s, lambda x, cr=crit: ((x.said_real) == (x.adv > x["thr_" + cr])).mean()))
            if cond == "C0":
                try:
                    X = sm.add_constant(s.adv.values); y = s.said_real.astype(int).values
                    g = sm.GEE(y, X, groups=s.pid.values, family=sm.families.Binomial()).fit()
                    b0, b1 = g.params; row["implied_threshold_cm_p50"] = round(-b0 / b1, 2) if b1 > 0 else None
                except Exception as e: row["implied_threshold_cm_p50"] = f"fit failed: {e}"
                tu = s.thr_used.dropna(); tu = tu[tu > 0]
                row["stated_threshold_cm_median"] = float(tu.median()) if len(tu) else None
            out.append(row)
    df = pd.DataFrame(out); df.to_csv(T / "part2_models.csv", index=False); print(df.T.to_string())

    # by sex (cohort noise differs by sex; models use one threshold for both)
    so = []
    for m in sorted(c.model.unique()):
        for sx in ("Male", "Female"):
            s_ = c[(c.model == m) & (c.cond == "C0") & (c.sex == sx)]
            if s_.empty: continue
            row = dict(model=m, sex=sx, calls=len(s_), pairs=int(s_.case_id.nunique()), cohort_rc_cm=TE[sx]["reliable_change_cm"],
                       agree95_all=fmt(s_.ok95.mean(), cboot(s_, lambda x: x.ok95.mean())),
                       says_real_when_within_noise=fmt(s_[s_.gold_change == "within_measurement_noise"].said_real.mean(), cboot(s_[s_.gold_change == "within_measurement_noise"], lambda x: x.said_real.mean())) if (s_.gold_change == "within_measurement_noise").any() else "n/a")
            try:
                g = sm.GEE(s_.said_real.astype(int).values, sm.add_constant(s_.adv.values), groups=s_.pid.values, family=sm.families.Binomial()).fit()
                row["implied_threshold_cm_p50"] = round(-g.params[0] / g.params[1], 2) if g.params[1] > 0 else None
            except Exception: row["implied_threshold_cm_p50"] = None
            so.append(row)
    pd.DataFrame(so).to_csv(T / "part2_by_sex.csv", index=False); print(pd.DataFrame(so).to_string(index=False))
    # band table
    bands = pd.cut(c.adv, [0, 2, 3.63, 100], labels=["<2 cm", "2-3.6 cm", ">3.6 cm"]); c["band"] = bands
    bt = c.groupby(["model", "cond", "band"], observed=True).agg(calls=("said_real", "size"), said_real=("said_real", "mean")).reset_index()
    bt.to_csv(T / "part2_by_band.csv", index=False)
    # paired C1 - C0 on said_real->agreement, run 1 only
    pr = []
    for m in sorted(c.model.unique()):
        a = c[(c.model == m) & (c.cond == "C0") & (c.run == 1)].set_index("case_id"); b = c[(c.model == m) & (c.cond == "C1")].set_index("case_id")
        j = a[["ok95", "pid"]].join(b[["ok95"]], rsuffix="_c1", how="inner").reset_index()
        if len(j):
            d = j.assign(diff=j.ok95_c1.astype(int) - j.ok95.astype(int))
            pr.append(dict(model=m, pairs=len(d), c1_minus_c0_agreement_pp=f"{100*d['diff'].mean():.0f} [{100*cboot(d, lambda x: x['diff'].mean())[0]:.0f}, {100*cboot(d, lambda x: x['diff'].mean())[1]:.0f}]"))
    pd.DataFrame(pr).to_csv(T / "part2_paired.csv", index=False); print(pd.DataFrame(pr).to_string(index=False))
    # figure 1: decision curves
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 2, figsize=(7.2, 2.7), sharey=True)
    for k, cond in enumerate(("C0", "C1")):
        for m, col in zip(sorted(c.model.unique()), ("#4C72B0", "#DD8452", "#55A868")):
            s = c[(c.model == m) & (c.cond == cond)]
            if s.empty: continue
            bins = np.array([0, 0.75, 1.5, 2.25, 3, 3.75, 4.5, 5.5, 8, 20]); idx = np.digitize(s.adv, bins) - 1
            xs = [s.adv[idx == i].mean() for i in range(len(bins) - 1) if (idx == i).sum() >= 3]
            ys = [s.said_real[idx == i].mean() for i in range(len(bins) - 1) if (idx == i).sum() >= 3]
            ax[k].plot(xs, ys, marker="o", ms=3, lw=1.2, color=col, label=m.replace("claude-", ""))
        for sx, ls in (("Male", "--"), ("Female", ":")): ax[k].axvline(TE[sx]["reliable_change_cm"], color="k", ls=ls, lw=0.8)
        ax[k].set_title("bare prompt (C0)" if cond == "C0" else "with cohort evidence (C1)", fontsize=8); ax[k].set_xlabel("|change in jump height| (cm)", fontsize=8)
        ax[k].tick_params(labelsize=7)
    ax[0].set_ylabel("share of answers: 'real change'", fontsize=8); ax[0].legend(fontsize=6, frameon=False, loc="lower right")
    ax[1].text(3.7, 0.05, "95% criterion:\nmale 3.6, female 5.4", fontsize=6)
    plt.tight_layout(); plt.savefig(G / "fig1_decision_curves.pdf"); plt.savefig(G / "fig1_decision_curves.png", dpi=200)
s3 = load("s3_raw.jsonl")
if s3 is not None and len(s3):
    def stage(r):
        tc = [x for x in r["calls"] if x["name"] == "tracking_check"]
        if not tc: return "no_tracking_call"
        ok = any(x["args"].get("sex") == r["sex"] and abs(x["args"].get("value_1_cm", -9) - r["v_a"]) <= 0.05 and abs(x["args"].get("value_2_cm", -9) - r["v_b"]) <= 0.05 for x in tc)
        if not ok: return "wrong_args"
        lab = [x["result"]["label"] for x in tc][-1]; tool = "within_measurement_noise" if lab == "within_noise" else "real"
        return "pass" if r["verdict"] == tool else "misread_tool"
    s3["stage"] = s3.apply(stage, axis=1); s3["ncalls"] = s3.calls.map(len)
    o = []
    for m in sorted(s3.model.unique()):
        s = s3[s3.model == m]
        o.append(dict(model=m, runs=len(s), unparsed=int(s.parsed.isna().sum()), called_tracking=fmt((s.stage != "no_tracking_call").mean(), cboot(s, lambda x: (x.stage != "no_tracking_call").mean())),
                      agree95=fmt(s.ok95.mean(), cboot(s, lambda x: x.ok95.mean())), mean_tool_calls=round(s.ncalls.mean(), 1), stages=json.dumps(s.stage.value_counts().to_dict())))
    pd.DataFrame(o).to_csv(T / "part3_agent.csv", index=False); print(pd.DataFrame(o).T.to_string())

# ---------- extra: verdict mix, practical error on the 'within noise but centile moved' pairs ----------
if c is not None and len(c):
    ex = []
    for m in sorted(c.model.unique()):
        for cond in ("C0", "C1"):
            s = c[(c.model == m) & (c.cond == cond)]
            vm = s.verdict.value_counts(normalize=True).to_dict()
            tgt = s[(s.gold_change == "within_measurement_noise") & ((s.c_b - s.c_a).abs() >= 5)]
            ex.append(dict(model=m, cond=cond, verdict_real=round(vm.get("real", 0), 3), verdict_within_noise=round(vm.get("within_measurement_noise", 0), 3),
                           verdict_cannot_tell=round(vm.get("cannot_tell", 0), 3), target_pairs=int(tgt.case_id.nunique()),
                           says_real_on_target=fmt(tgt.said_real.mean(), cboot(tgt, lambda x: x.said_real.mean())),
                           says_within_noise_on_target=fmt((tgt.verdict == "within_measurement_noise").mean(), cboot(tgt, lambda x: (x.verdict == "within_measurement_noise").mean()))))
    pd.DataFrame(ex).to_csv(T / "part2_target_pairs.csv", index=False); print(pd.DataFrame(ex).to_string(index=False))
    # run-to-run agreement of C0 verdicts (Haiku and Sonnet have 2 runs)
    ra = []
    for m in ("claude-haiku-5-5", "claude-sonnet-5-5"):
        a = c[(c.model == m) & (c.cond == "C0")].pivot_table(index="case_id", columns="run", values="verdict", aggfunc="first")
        ra.append(dict(model=m, run_agreement=f"{100*(a[1] == a[2]).mean():.0f}%"))
    pd.DataFrame(ra).to_csv(T / "part2_run_agreement.csv", index=False); print(pd.DataFrame(ra).to_string(index=False))
