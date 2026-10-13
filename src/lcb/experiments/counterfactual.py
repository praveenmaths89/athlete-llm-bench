"""A5: causal test of centile display. Synthetic athletes built from the GAMLSS grid; twin prompts with and without the centile line.

usage: python -m lcb.experiments.counterfactual design | run <haiku|sonnet|opus> [--runs N] [--limit K] | analyze
"""
import argparse, itertools, json, sys, threading
from concurrent.futures import ThreadPoolExecutor
import numpy as np, pandas as pd
from lcb.config import RESULTS, MODELS, TEST_TYPE, VARIABLE
from lcb.llm.schemas import SCHEMA, SYSTEM
from lcb.llm.client import Claude, CreditExhausted
from lcb.tools.centile_tool import centile, value_at_centile
from lcb.analysis.stats import cluster_bootstrap, gee_logit

OUT = RESULTS / "exploratory" / "a5"
SEXES = ("Male", "Female"); AGES = (10, 12, 14, 16, 20); GAP_Y = 0.5; BASES = (25, 50, 75); SIZES = (1.5, 2.5, 3.2); SIGNS = (1, -1)
INSTR = ("\nReturn JSON with: jump_change_is (real | within_measurement_noise | cannot_tell), centile_change_reason "
         "(what mainly caused the centile change: jump_change | age_drift | both | none; none if no centile is given), noise_threshold_cm "
         "(the smallest change in cm you treated as a real change; 0 if you used none), note (at most 60 words, how the athlete is doing).")


def design() -> pd.DataFrame:
    rows, dropped = [], 0
    for sex, age, base, size, sign in itertools.product(SEXES, AGES, BASES, SIZES, SIGNS):
        v_a = round(value_at_centile(TEST_TYPE, sex, VARIABLE, age, base), 1); v_b = round(v_a + sign * size, 1)
        ca = centile(TEST_TYPE, sex, VARIABLE, age, v_a); cb = centile(TEST_TYPE, sex, VARIABLE, age + GAP_Y, v_b)
        if ca.centile is None or cb.centile is None: dropped += 1; continue
        ca_i, cb_i = round(ca.centile), round(cb.centile)
        rows.append(dict(cell_id=f"{sex[0]}{age}_b{base}_{'u' if sign > 0 else 'd'}{size}", sex=sex, age_a=age, age_b=age + GAP_Y, base=base,
                         size=size, sign=sign, v_a=v_a, v_b=v_b, c_a=ca_i, c_b=cb_i, delta=cb_i - ca_i, norm_label=ca.norm_label))
    d = pd.DataFrame(rows); d.attrs["dropped"] = dropped; return d


def payload(c: dict, shown: int) -> str:
    t = (f"Athlete: {c['sex'].lower()}, football player, {c['age_a']:.1f} years at test 1 and {c['age_b']:.1f} years at test 2 (6 months apart).\n"
         f"Countermovement jump height (impulse-momentum): test 1 = {c['v_a']:.1f} cm, test 2 = {c['v_b']:.1f} cm.\n")
    if shown: t += f"Centile in the age- and sex-matched reference group: test 1 = P{c['c_a']:.0f}, test 2 = P{c['c_b']:.0f}.\n"
    return t + "Question: How is this athlete doing?" + INSTR


def run(model_key: str, runs: int, limit: int | None):
    OUT.mkdir(parents=True, exist_ok=True); d = design(); d.to_csv(OUT / "design.csv", index=False)
    print(f"design: {len(d)} cells ({d.attrs['dropped']} dropped outside P3-P97)")
    model = MODELS[model_key]; raw = OUT / "raw.jsonl"; done = set()
    if raw.exists():
        for l in raw.read_text().splitlines(): r = json.loads(l); done.add((r["cell_id"], r["shown"], r["model"], r["run"]))
    jobs = [(c, s, r) for c in d.to_dict("records") for s in (1, 0) for r in range(1, runs + 1) if (c["cell_id"], s, model, r) not in done]
    if limit: jobs = jobs[:limit]
    print(len(jobs), "prompts to send to", model); llm = Claude(); lock = threading.Lock(); cost = [0.0]; stop = threading.Event()

    def work(j):
        c, shown, r = j
        if stop.is_set(): return
        try: out = llm.ask(model, SYSTEM, payload(c, shown), SCHEMA)
        except CreditExhausted: stop.set(); print("credit exhausted: stopping cleanly (run is resumable)"); return
        rec = dict(cell_id=c["cell_id"], shown=shown, model=out.model, run=r, stop_reason=out.stop_reason, in_tok=out.in_tok, out_tok=out.out_tok, parsed=out.parsed, text=out.text)
        with lock:
            with open(raw, "a") as fh: fh.write(json.dumps(rec) + "\n")
            cost[0] += out.cost
    with ThreadPoolExecutor(max_workers=4) as ex: list(ex.map(work, jobs))
    print(f"done; approx cost USD {cost[0]:.3f}")


def load() -> pd.DataFrame:
    d = pd.read_csv(OUT / "design.csv"); r = pd.DataFrame([json.loads(l) for l in (OUT / "raw.jsonl").read_text().splitlines()])
    r["verdict"] = r.parsed.map(lambda x: (x or {}).get("jump_change_is")); r["thr"] = r.parsed.map(lambda x: (x or {}).get("noise_threshold_cm"))
    r["real"] = (r.verdict == "real").astype(int); df = r.merge(d, on="cell_id")
    df["z"] = df.delta.abs() / 10; df["female"] = (df.sex == "Female").astype(int); return df


def analyze():
    df = load(); T = OUT / "tables"; T.mkdir(exist_ok=True); lines, tab = [], []
    for m in sorted(df.model.unique()):
        for label, sub in (("falls", df[(df.model == m) & (df.sign < 0)]), ("rises", df[(df.model == m) & (df.sign > 0)])):
            if sub.empty: continue
            sub = sub.assign(shown_z=sub.shown * sub.z)
            g = gee_logit(sub, "real", ["shown", "z", "shown_z", "size", "female", "age_a", "base"], "cell_id")
            b, ci = g.params["shown_z"], g.conf_int().loc["shown_z"].tolist()
            sub = sub.assign(tert=pd.qcut(sub.z, 3, labels=["low", "mid", "high"], duplicates="drop"))
            for t, s in sub.groupby("tert", observed=True):
                f = lambda x: x[x.shown == 1].real.mean() - x[x.shown == 0].real.mean()
                lo, hi = cluster_bootstrap(s, f, "cell_id")
                tab.append(dict(model=m, direction=label, tertile=t, abs_delta_range=f"{s.delta.abs().min()}-{s.delta.abs().max()}", prompts=len(s), cells=s.cell_id.nunique(),
                                p_real_shown=round(s[s.shown == 1].real.mean(), 3), p_real_not_shown=round(s[s.shown == 0].real.mean(), 3),
                                contrast_pp=round(100 * f(s), 1), ci_lo_pp=round(100 * lo, 1), ci_hi_pp=round(100 * hi, 1)))
            top = [x for x in tab if x["model"] == m and x["direction"] == label][-1]
            lines.append(f"{m} {label}: shown:z coef {b:.2f} (95% CI {ci[0]:.2f}, {ci[1]:.2f}, p={g.pvalues['shown_z']:.3f}); top-tertile contrast {top['contrast_pp']} pp [{top['ci_lo_pp']}, {top['ci_hi_pp']}]")
        mix = df[df.model == m].groupby("shown").verdict.value_counts(normalize=True).unstack(fill_value=0).round(3)
        lines.append(f"{m} verdict mix by shown (0 = no centile):\n{mix.to_string()}")
    pd.DataFrame(tab).to_csv(T / "a5_contrasts.csv", index=False); (T / "a5_summary.txt").write_text("\n".join(lines)); print("\n".join(lines)); print(pd.DataFrame(tab).to_string(index=False))


def explore():
    """EXPLORATORY (not pre-registered): main effect of showing the centile, and verdicts among answers that commit."""
    df = load(); T = OUT / "tables"; T.mkdir(exist_ok=True); rows = []
    for m in sorted(df.model.unique()):
        for label, sub in (("all", df[df.model == m]), ("falls", df[(df.model == m) & (df.sign < 0)]), ("rises", df[(df.model == m) & (df.sign > 0)])):
            f_real = lambda x: x[x.shown == 1].real.mean() - x[x.shown == 0].real.mean()
            f_commit = lambda x: (x[x.shown == 1].verdict != "cannot_tell").mean() - (x[x.shown == 0].verdict != "cannot_tell").mean()
            def f_real_given_commit(x):
                a, b = x[(x.shown == 1) & (x.verdict != "cannot_tell")], x[(x.shown == 0) & (x.verdict != "cannot_tell")]
                return a.real.mean() - b.real.mean() if len(a) and len(b) else float("nan")
            row = dict(model=m, subset=label, prompts=len(sub))
            for name, f in (("real", f_real), ("commits", f_commit), ("real_given_commit", f_real_given_commit)):
                lo, hi = cluster_bootstrap(sub, f, "cell_id"); row[name + "_shown_minus_not_pp"] = f"{100*f(sub):.1f} [{100*lo:.1f}, {100*hi:.1f}]"
            rows.append(row)
    out = pd.DataFrame(rows); out.to_csv(T / "a5_exploratory_main_effect.csv", index=False); print(out.to_string(index=False))
    thr = df[df.thr > 0].groupby(["model", "shown"]).thr.median().round(2); print("median stated threshold (cm):\n" + thr.to_string())


def main(argv=None):
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True); sub.add_parser("design"); sub.add_parser("analyze"); sub.add_parser("explore")
    r = sub.add_parser("run"); r.add_argument("model", choices=list(MODELS)); r.add_argument("--runs", type=int, default=2); r.add_argument("--limit", type=int)
    a = ap.parse_args(argv)
    if a.cmd == "design":
        d = design(); OUT.mkdir(parents=True, exist_ok=True); d.to_csv(OUT / "design.csv", index=False)
        print(len(d), "cells,", d.attrs["dropped"], "dropped"); print(d.groupby(["sex", "sign"]).delta.describe().round(1).to_string())
    elif a.cmd == "run": run(a.model, a.runs, a.limit)
    elif a.cmd == "explore": explore()
    else: analyze()


if __name__ == "__main__":
    main()
