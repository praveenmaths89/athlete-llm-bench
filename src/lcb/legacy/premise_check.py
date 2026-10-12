"""Step 1a: how often does a real athlete's jump go up while the centile goes down (or the reverse)?

Local only; no API. Reads data_private/football_cmj.csv. Writes results/premise_check*.
"""
import csv, collections, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from lcb.tools.centile_tool import centile

ROOT = Path(__file__).resolve().parents[3]
VAR = "Jump_Height_Imp-Mom_"
rows = []
for r in csv.DictReader(open(ROOT / "data_private/football_cmj.csv")):
    try:
        rows.append(dict(pid=r["pid"], sex=r["sex"], date=r["test_date"], age=float(r["age"]), v=float(r["jump_height_impmom_cm"])))
    except ValueError:
        pass
by = collections.defaultdict(list)
for r in rows:
    by[(r["pid"], r["sex"])].append(r)

CUT, ART = 5.0, 2.0   # centile points: counted conflict / artefact threshold
pairs = []
for (pid, sex), tests in by.items():
    tests.sort(key=lambda t: t["date"])
    for a, b in zip(tests, tests[1:]):
        ca, cb = centile("CMJ", sex, VAR, a["age"], a["v"]), centile("CMJ", sex, VAR, b["age"], b["v"])
        if ca.centile is None or cb.centile is None:
            kind, dc = "no_centile", None
        else:
            dc = cb.centile - ca.centile
            dv = b["v"] - a["v"]
            if dv > 0 and dc <= -CUT: kind = "value_up_centile_down"
            elif dv < 0 and dc >= CUT: kind = "value_down_centile_up"
            elif dv > 0 and dc >= 0 or dv < 0 and dc <= 0: kind = "agree"
            else: kind = "small_disagreement"
        gap = (__import__("datetime").date.fromisoformat(b["date"]) - __import__("datetime").date.fromisoformat(a["date"])).days
        pairs.append(dict(pid=pid, sex=sex, age_a=a["age"], age_b=b["age"], gap_days=gap, v_a=a["v"], v_b=b["v"],
                          dv=round(b["v"] - a["v"], 2), c_a=None if ca.centile is None else round(ca.centile, 1),
                          c_b=None if cb.centile is None else round(cb.centile, 1), dc=None if dc is None else round(dc, 1),
                          kind=kind, norm_a=ca.norm_label, norm_b=cb.norm_label))
out = ROOT / "data_private/real_pairs"; out.mkdir(parents=True, exist_ok=True)
with open(out / "premise_check.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(pairs[0])); w.writeheader(); w.writerows(pairs)

n = len(pairs); k = collections.Counter(p["kind"] for p in pairs)
conf = [p for p in pairs if p["kind"] in ("value_up_centile_down", "value_down_centile_up")]
lines = [f"# Premise check (Step 1a)", f"Consecutive pairs: {n}; athletes with 2+ tests: {sum(len(t)>=2 for t in by.values())}",
         f"By kind: {dict(k)}", f"Conflict pairs (|centile change| >= {CUT} points): {len(conf)} = {100*len(conf)/n:.1f}% of pairs"]
for sex in ("Male", "Female"):
    ps = [p for p in pairs if p["sex"] == sex]; cs = [p for p in conf if p["sex"] == sex]
    lines.append(f"{sex}: pairs {len(ps)}, conflicts {len(cs)}")
for lo, hi, name in [(0, 120, "<=120 d"), (121, 240, "121-240 d"), (241, 10000, ">240 d")]:
    ps = [p for p in pairs if lo <= p["gap_days"] <= hi]; cs = [p for p in conf if lo <= p["gap_days"] <= hi]
    lines.append(f"Gap {name}: pairs {len(ps)}, conflicts {len(cs)}")
ages = [p["age_a"] for p in conf]
if ages: lines.append(f"Age of conflict pairs: min {min(ages)}, median {sorted(ages)[len(ages)//2]}, max {max(ages)}")
lines.append(f"Conflicts with age <18 at first test: {sum(p['age_a'] < 18 for p in conf)}")
art = [p for p in pairs if p["dc"] is not None and abs(p["dc"]) < ART and ((p["dv"] > 0) != (p["dc"] >= 0))]
lines.append(f"Sign disagreements with |centile change| < {ART} points (rounding-scale, not counted): {len(art)}")
gate = len(conf) >= 15 and len(conf) / n >= 0.05
lines.append(f"GATE (>=15 conflict pairs and >=5% of pairs): {'PASS' if gate else 'FAIL'}")
(out / "premise_check_summary.md").write_text("\n".join(lines) + "\n")
print("\n".join(lines))
