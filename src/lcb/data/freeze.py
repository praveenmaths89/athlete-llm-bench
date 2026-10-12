"""Freeze the football CMJ data and build the RELEASE VIEW (two tables: tests and trials).

De-identification rule (author decision, 11 Oct 2026): remove names and any club name, replace the VALD profile id by a pseudonymous athlete id
(salted hash, salt kept private), drop date_of_birth; keep test date, age, height, body mass, age band, sex and every trial value as in the source.

Private (never released): data_private/salt.txt.   Release: data/release/tests.csv, data/release/trials.csv, data/FREEZE.md
Usage: LCB_PIPELINE_DIR=<R_pipeline folder> python -m lcb.data.freeze
"""
import csv, hashlib, json, secrets, collections, statistics as st
from datetime import datetime, timedelta
from lcb.config import ROOT, PRIVATE, pipeline_dir

SPORT, TEST = "football", "CMJ"
VALUE_COL = "Jump_Height_Imp-Mom_"; RESULT = "Jump Height (Imp-Mom)"
REL = ROOT / "data/release"


def salt() -> str:
    f = PRIVATE / "salt.txt"; PRIVATE.mkdir(exist_ok=True)
    if not f.exists(): f.write_text(secrets.token_hex(16))
    return f.read_text().strip()


def num(x):
    try: return float(x)
    except (TypeError, ValueError): return None


def build():
    P = pipeline_dir() / "data"; s = salt()
    clean = [r for r in csv.DictReader(open(P / "processed/tests_clean.csv")) if r["sport"].lower().startswith(SPORT) and r["test_type"] == TEST]
    profiles = {r["profile_id"] for r in clean}
    # link source tests to trials: (profile, local date) -> test ids
    key_tests = collections.defaultdict(list)
    for r in csv.DictReader(open(P / "raw/tests.csv")):
        if r["testType"] == TEST and r["profileId"] in profiles:
            utc = datetime.fromisoformat(r["recordedDateUtc"].replace("Z", "+00:00")).replace(tzinfo=None)
            local = (utc + timedelta(minutes=float(r["recordedDateOffset"] or 0))).date().isoformat()
            key_tests[(r["profileId"], local)].append(r["testId"])
    wanted = {t for v in key_tests.values() for t in v}; trials = collections.defaultdict(dict)   # testId -> trialId -> (utc, value)
    for r in csv.DictReader(open(P / "raw/trials.csv")):
        if r["testId"] in wanted and r["resultName"] == RESULT and r["limb"] == "Trial":
            v = num(r["value"])
            if v is not None: trials[r["testId"]][r["trialId"]] = (r["recordedUTC"], v)
    by = collections.defaultdict(list)
    for r in clean: by[r["profile_id"]].append(r)
    tests_out, trials_out = [], []; mismatch = 0
    for prof, rows in by.items():
        pid = "A" + hashlib.sha256((s + "|" + prof).encode()).hexdigest()[:10]; rows.sort(key=lambda x: x["test_date"]); prev = None
        for i, r in enumerate(rows, 1):
            tv = sorted(v for tid in key_tests.get((prof, r["test_date"]), []) for v in trials.get(tid, {}).values())
            vals = [v for _, v in tv]; mean_src = num(r[VALUE_COL])
            if vals and mean_src is not None and abs(st.mean(vals) - mean_src) > 0.05: mismatch += 1
            gap = None if prev is None else (datetime.fromisoformat(r["test_date"]) - datetime.fromisoformat(prev)).days; prev = r["test_date"]
            tests_out.append(dict(athlete=pid, sex=r["gender"], test_index=i, test_date=r["test_date"], days_since_prev=gap, age_years=num(r["age_at_test"]), age_band=r["age_band"],
                                  height_cm=num(r["height_cm"]), body_mass_kg=num(r["body_mass_kg"]), n_trials=len(vals), jump_mean_cm=None if mean_src is None else round(mean_src, 2),
                                  jump_best_cm=round(max(vals), 2) if vals else None, jump_sd_cm=round(st.stdev(vals), 2) if len(vals) > 1 else None))
            for j, (_, v) in enumerate(tv, 1): trials_out.append(dict(athlete=pid, test_index=i, trial_no=j, jump_height_cm=round(v, 2)))
    REL.mkdir(parents=True, exist_ok=True)
    for name, rows in (("tests", tests_out), ("trials", trials_out)):
        with open(REL / f"{name}.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    info = dict(tests=len(tests_out), athletes=len(by), trial_rows=len(trials_out), tests_without_trials=sum(t["n_trials"] == 0 for t in tests_out), trial_mean_vs_source_mismatch=mismatch,
                sha256_tests=hashlib.sha256((REL / "tests.csv").read_bytes()).hexdigest(), sha256_trials=hashlib.sha256((REL / "trials.csv").read_bytes()).hexdigest())
    (ROOT / "data/FREEZE.md").write_text("# Freeze record (release view)\n\n```json\n" + json.dumps(info, indent=1) + "\n```\n"); print(json.dumps(info, indent=1))


if __name__ == "__main__":
    build()
