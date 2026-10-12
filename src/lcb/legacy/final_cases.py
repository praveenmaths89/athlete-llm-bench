"""All real pairs with a centile at both tests, with gold labels (analysis plan A4)."""
import csv, json
from pathlib import Path
from lcb.tools.centile_tool import centile
ROOT = Path(__file__).resolve().parents[3]
VAR = "Jump_Height_Imp-Mom_"
TE = json.loads((ROOT / "results/typical_error.json").read_text())

def all_cases():
    out = []
    for i, p in enumerate(csv.DictReader(open(ROOT / "data_private/real_pairs/premise_check_v2.csv"))):
        a, b, va, vb = float(p["age_a"]), float(p["age_b"]), float(p["v_a"]), float(p["v_b"])
        drift = centile("CMJ", p["sex"], VAR, b, va).centile - centile("CMJ", p["sex"], VAR, a, va).centile
        total = float(p["c_b"]) - float(p["c_a"]); rest = total - drift
        gold_reason = None if max(abs(drift), abs(rest)) < 2 else ("age_drift" if abs(drift) > abs(rest) else "jump_change")
        out.append(dict(case_id=f"pair_{i+1:03d}", pid=p["pid"], group=p["tracking"], sex=p["sex"], age_a=a, age_b=b,
                        months=round(int(p["gap_days"]) / 30.4), v_a=va, v_b=vb, c_a=float(p["c_a"]), c_b=float(p["c_b"]), dv=vb - va,
                        age_drift=round(drift, 1), gold_change="within_measurement_noise" if p["tracking"] == "within_noise" else "real",
                        gold_reason=gold_reason, rc=TE[p["sex"]]["reliable_change_cm"], sd=TE[p["sex"]]["within_sd_cm"]))
    return out
