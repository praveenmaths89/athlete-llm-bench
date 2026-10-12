"""Score amendment A2 deterministically from the JSON fields (no keywords, no judge)."""
import json, collections, statistics as st, random
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
cases = {c["case_id"]: c for c in json.load(open(ROOT / "data_private/real_pairs/quick_test2/cases.json"))}
rows = [json.loads(l) for l in (ROOT / "data_private/real_pairs/quick_test2/raw.jsonl").read_text().splitlines()]
bad = [r for r in rows if r["parsed"] is None]
for r in rows:
    c = cases[r["case_id"]]; p = r["parsed"] or {}
    r["ok_change"] = p.get("jump_change_is") == c["gold_change"]
    r["said_real"] = p.get("jump_change_is") == "real"
    r["ok_reason"] = None if c["gold_reason"] is None else p.get("centile_change_reason") == c["gold_reason"]
    r["thr"] = p.get("noise_threshold_cm"); r["rc"] = c["rc"]
def pct(xs): return "n/a" if not xs else f"{100*sum(xs)/len(xs):3.0f}%"
def ci(xs, B=2000):
    # bootstrap over cases (cluster) for the share of True
    by = collections.defaultdict(list)
    for r, x in xs: by[r["case_id"]].append(x)
    ids = list(by); rng = random.Random(1); vals = []
    for _ in range(B):
        s = [x for i in (rng.choice(ids) for _ in ids) for x in by[i]]; vals.append(sum(s) / len(s))
    vals.sort(); return f"[{100*vals[int(.025*B)]:.0f}, {100*vals[int(.975*B)]:.0f}]"
L = [f"# A2 grounding test. Calls {len(rows)}; unparsed {len(bad)}; stop reasons {dict(collections.Counter(r['stop_reason'] for r in rows))}"]
for m in sorted({r["model"] for r in rows}):
    for grp in ("gray_zone", "reliable_change"):
        for cond in ("C0", "C1"):
            s = [r for r in rows if r["model"] == m and r["group"] == grp and r["cond"] == cond]
            if not s: continue
            thr = [r["thr"] for r in s if r["thr"]]
            L.append(f"{m:17s} {grp:15s} {cond}  n={len(s):2d}  correct verdict {pct([r['ok_change'] for r in s])} CI{ci([(r, r['ok_change']) for r in s])}  said real {pct([r['said_real'] for r in s])}  "
                     f"reason correct {pct([r['ok_reason'] for r in s if r['ok_reason'] is not None])}  median threshold used {st.median(thr) if thr else 'n/a'} cm (cohort RC median {st.median(r['rc'] for r in s):.1f})")
tc = sum(r["in_tok"] / 1e6 * (0.10 if "haiku" in r["model"] else 4.0) + r["out_tok"] / 1e6 * (0.50 if "haiku" in r["model"] else 20.0) for r in rows)
L.append(f"Approx cost USD {tc:.2f}"); (ROOT / "data_private/real_pairs/quick_test2/summary.md").write_text("\n".join(L) + "\n"); print("\n".join(L))
