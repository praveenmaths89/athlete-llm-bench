"""Step 3: typical error of CMJ jump height (Imp-Mom) from within-test trial spread. Local only.

Within-test trial SD is pooled over football CMJ tests. TE of a test mean = pooled SD / sqrt(k) with k = median trials.
Change between two test means is 'beyond noise' when |change| > 1.96 * sqrt(2) * TE_mean (95% reliable change).
"""
import csv, collections, math, statistics as st
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
from lcb.config import pipeline_dir
RAW = pipeline_dir() / "data"
clean = RAW / "processed/tests_clean.csv"
fb = {}
for r in csv.DictReader(open(clean)):
    if r["sport"].lower().startswith("foot") and r["test_type"] == "CMJ":
        fb[r["profile_id"]] = r["gender"]
testtype = {}
for r in csv.DictReader(open(RAW / "raw/tests.csv")):
    if r["testType"] == "CMJ" and r["profileId"] in fb:
        testtype[r["testId"]] = fb[r["profileId"]]
vals = collections.defaultdict(dict)   # testId -> trialId -> value
for r in csv.DictReader(open(RAW / "raw/trials.csv")):
    if r["resultName"] == "Jump Height (Imp-Mom)" and r["limb"] == "Trial" and r["testId"] in testtype:
        try: vals[r["testId"]][r["trialId"]] = float(r["value"]) * 100 if float(r["value"]) < 2 else float(r["value"])
        except ValueError: pass
res = {}
for sex in ("Male", "Female", "Pooled"):
    vs, ks = [], []
    for t, d in vals.items():
        if sex != "Pooled" and testtype[t] != sex: continue
        x = list(d.values())
        if len(x) >= 2:
            vs.append(st.variance(x)); ks.append(len(x))
    sd = math.sqrt(sum(vs) / len(vs)); k = st.median(ks)
    res[sex] = dict(tests=len(vs), median_trials=k, within_sd_cm=round(sd, 3), te_mean_cm=round(sd / math.sqrt(k), 3),
                    reliable_change_cm=round(1.96 * math.sqrt(2) * sd / math.sqrt(k), 3))
    print(sex, res[sex])
import json; (ROOT / "results/typical_error.json").write_text(json.dumps(res, indent=1))
