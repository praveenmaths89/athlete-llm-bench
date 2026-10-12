"""Score A3: tool-call behaviour, failure stages, verdict accuracy."""
import json, collections, statistics as st
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
cases = {c["case_id"]: c for c in json.load(open(ROOT / "data_private/real_pairs/quick_test2/cases.json"))}
rows = [json.loads(l) for l in (ROOT / "data_private/real_pairs/quick_test3/raw.jsonl").read_text().splitlines()]
def stage(r):
    c = cases[r["case_id"]]; p = r["parsed"] or {}
    tc = [x for x in r["calls"] if x["name"] == "tracking_check"]
    if not tc: return "no_tracking_call"
    ok_args = any(x["args"].get("sex") == c["sex"] and abs(x["args"].get("value_1_cm", -9) - c["v_a"]) <= 0.05 and abs(x["args"].get("value_2_cm", -9) - c["v_b"]) <= 0.05 for x in tc)
    if not ok_args: return "wrong_args"
    label = [x["result"]["label"] for x in tc if x["args"].get("value_1_cm") is not None][-1]
    tool_says = "within_measurement_noise" if label == "within_noise" else "real"
    return "pass" if p.get("jump_change_is") == tool_says else "misread_tool"
for r in rows:
    c = cases[r["case_id"]]; p = r["parsed"] or {}
    r["stage"] = stage(r); r["ok"] = p.get("jump_change_is") == c["gold_change"]; r["n_calls"] = len(r["calls"])
    r["centile_calls"] = sum(x["name"] == "centile_lookup" for x in r["calls"])
L = [f"# A3 S3 agent. Runs {len(rows)}; unparsed {sum(r['parsed'] is None for r in rows)}; stop reasons {dict(collections.Counter(r['stop_reason'] for r in rows))}"]
for m in sorted({r["model"] for r in rows}):
    for cond in ("N", "U"):
        s = [r for r in rows if r["model"] == m and r["cond"] == cond]
        if not s: continue
        stg = collections.Counter(r["stage"] for r in s)
        L.append(f"{m:17s} {cond}  n={len(s):2d}  called tracking_check {100*sum(r['stage']!='no_tracking_call' for r in s)/len(s):3.0f}%  verdict correct {100*sum(r['ok'] for r in s)/len(s):3.0f}%  mean tool calls {st.mean(r['n_calls'] for r in s):.1f}  used centile tool {100*sum(r['centile_calls']>0 for r in s)/len(s):3.0f}%  stages {dict(stg)}")
        for g in ("gray_zone", "reliable_change"):
            t = [r for r in s if r["group"] == g]
            L.append(f"     {g:15s} n={len(t):2d} verdict correct {100*sum(r['ok'] for r in t)/len(t):3.0f}%")
tc = sum(r["in_tok"] / 1e6 * (0.10 if "haiku" in r["model"] else 4.0) + r["out_tok"] / 1e6 * (0.50 if "haiku" in r["model"] else 20.0) for r in rows)
L.append(f"Approx cost USD {tc:.2f}"); (ROOT / "data_private/real_pairs/quick_test3/summary.md").write_text("\n".join(L) + "\n"); print("\n".join(L))
