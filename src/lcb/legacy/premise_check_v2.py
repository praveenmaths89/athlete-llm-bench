"""Step 1a, redefined (post hoc, after seeing v1): tracking label from typical error, then conflict types."""
import csv, json, collections
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
te = json.loads((ROOT / "results/typical_error.json").read_text())
P = [p for p in csv.DictReader(open(ROOT / "data_private/real_pairs/premise_check.csv")) if p["dc"] != ""]
CUT = 5.0
def track(p):
    rc = te[p["sex"]]["reliable_change_cm"]; dv = float(p["dv"])
    return "within_noise" if abs(dv) <= rc else ("beyond_up" if dv > 0 else "beyond_down")
out = []
for p in P:
    t = track(p); dc = float(p["dc"])
    cm = "centile_up" if dc >= CUT else "centile_down" if dc <= -CUT else "centile_flat"
    p2 = dict(p, tracking=t, centile_move=cm); out.append(p2)
with open(ROOT / "data_private/real_pairs/premise_check_v2.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
n = len(out); c = collections.Counter((o["tracking"], o["centile_move"]) for o in out)
L = ["# Premise check v2 (post hoc definition)", f"Pairs with a centile at both tests: {n}",
     "Reliable change (cm): " + ", ".join(f"{s} {te[s]['reliable_change_cm']}" for s in ("Male", "Female")),
     "tracking x centile move (cutoff 5 centile points):"]
for k in sorted(c): L.append(f"  {k[0]:13s} {k[1]:13s} {c[k]}")
A = [o for o in out if o["tracking"] == "within_noise" and o["centile_move"] != "centile_flat"]
B = [o for o in out if o["tracking"] == "beyond_up" and o["centile_move"] == "centile_flat"]
Cc = [o for o in out if o["tracking"] == "beyond_up" and o["centile_move"] == "centile_down"]
L += [f"Type A  within noise but centile moves 5+ points: {len(A)} ({100*len(A)/n:.1f}%); down {sum(o['centile_move']=='centile_down' for o in A)}, up {sum(o['centile_move']=='centile_up' for o in A)}",
      f"Type B  real gain beyond noise but centile flat: {len(B)}",
      f"Type C  real gain beyond noise and centile down: {len(Cc)}",
      f"Type A by sex: " + str({s: sum(o['sex'] == s for o in A) for s in ('Male', 'Female')}),
      f"Type A, athletes: {len({o['pid'] for o in A})}; under 18 at first test: {sum(float(o['age_a']) < 18 for o in A)}",
      f"Within-noise pairs overall: {sum(o['tracking']=='within_noise' for o in out)} ({100*sum(o['tracking']=='within_noise' for o in out)/n:.0f}%)"]
(ROOT / "data_private/real_pairs/premise_check_v2_summary.md").write_text("\n".join(L) + "\n"); print("\n".join(L))
