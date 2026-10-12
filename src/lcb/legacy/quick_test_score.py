"""Score the quick test with the pre-registered keyword checks (exploratory; answers are also read by the author)."""
import json, re, collections, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from quick_test import NOISE, CHANGE, AGE
ROOT = Path(__file__).resolve().parents[3]
rows = [json.loads(l) for l in (ROOT / "data_private/real_pairs/quick_test/raw.jsonl").read_text().splitlines()]
for r in rows:
    t = r["text"]; r["noise"] = bool(NOISE.search(t)); r["change"] = bool(CHANGE.search(t)); r["age"] = bool(AGE.search(t))
    r["E"] = r["change"] and not r["noise"]
within = ("within_noise_centile_down", "within_noise_centile_up", "within_noise_centile_flat")
L = [f"# Quick test (Step 1b, amendment A1). Calls: {len(rows)}; stop reasons: {dict(collections.Counter(r['stop_reason'] for r in rows))}"]
for m in sorted({r["model"] for r in rows}):
    for grp, name in ((within, "within-noise cases"), (("reliable_gain_centile_up", "reliable_drop_centile_down"), "reliable-change controls")):
        s = [r for r in rows if r["model"] == m and r["stratum"] in grp]
        if not s: continue
        L.append(f"{m:18s} {name:24s} n={len(s):3d}  states a change: {100*sum(r['change'] for r in s)/len(s):3.0f}%  mentions noise/error: {100*sum(r['noise'] for r in s)/len(s):3.0f}%  mentions age/growth: {100*sum(r['age'] for r in s)/len(s):3.0f}%  E (change, no noise): {100*sum(r['E'] for r in s)/len(s):3.0f}%")
    for st in sorted({r["stratum"] for r in rows}):
        s = [r for r in rows if r["model"] == m and r["stratum"] == st]
        L.append(f"   {st:28s} n={len(s):3d} change {sum(r['change'] for r in s):3d} noise {sum(r['noise'] for r in s):3d} age {sum(r['age'] for r in s):3d} E {sum(r['E'] for r in s):3d}")
tot_c = sum(r["in_tok"] / 1e6 * (0.10 if "haiku" in r["model"] else 4.0) + r["out_tok"] / 1e6 * (0.50 if "haiku" in r["model"] else 20.0) for r in rows)
L.append(f"Approx cost USD {tot_c:.3f}")
(ROOT / "data_private/real_pairs/quick_test/summary.md").write_text("\n".join(L) + "\n"); print("\n".join(L))
