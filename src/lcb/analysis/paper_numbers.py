"""Write paper/numbers.tex: LaTeX macros for every number in the paper that describes the data, the benchmark and the noise estimate."""
import csv, json, collections, statistics as st
from lcb.config import ROOT, RELEASE_TESTS, RELEASE_TRIALS, NOISE_PATH


def main():
    tests = list(csv.DictReader(open(RELEASE_TESTS))); trials = list(csv.DictReader(open(RELEASE_TRIALS)))
    qs = [json.loads(l) for l in open(ROOT / "data/benchmark/questions.jsonl")]; te = json.loads(NOISE_PATH.read_text())
    ath = {r["athlete"]: r["sex"] for r in tests}; n_by = collections.Counter(r["athlete"] for r in tests)
    ages = [float(r["age_years"]) for r in tests]; dates = sorted(r["test_date"] for r in tests); ntr = collections.Counter(int(r["n_trials"]) for r in tests)
    fam = collections.Counter(q["family"] for q in qs); split = collections.Counter(q["split"] for q in qs); coh = [q for q in qs if q["tags"].get("cohort")]
    M = {
        "nTests": len(tests), "nAthletes": len(ath), "nTrials": len(trials),
        "nMaleAthletes": sum(s == "Male" for s in ath.values()), "nFemaleAthletes": sum(s == "Female" for s in ath.values()),
        "nMaleTests": sum(r["sex"] == "Male" for r in tests), "nFemaleTests": sum(r["sex"] == "Female" for r in tests),
        "nMulti": sum(v >= 2 for v in n_by.values()), "nThree": sum(v >= 3 for v in n_by.values()),
        "ageMin": f"{min(ages):.1f}", "ageMax": f"{max(ages):.1f}", "yearFirst": dates[0][:4], "yearLast": dates[-1][:4],
        "trialsTwoThree": ntr[2] + ntr[3], "trialsOne": ntr[1], "trialsMore": sum(v for k, v in ntr.items() if k > 3),
        "nQuestions": len(qs), "nQa": fam["Q1"], "nQb": fam["Q2"], "nQc": fam["Q3"], "nQd": fam["Q4"], "nQe": fam["Q7"],
        "nCohort": len(coh), "nDev": split["dev"], "nSel": split["selection"], "nFinal": split["final"],
        "nCohortFinal": sum(q["split"] == "final" for q in coh),
        "rcMale": f"{te['Male']['reliable_change_cm']:.1f}", "rcFemale": f"{te['Female']['reliable_change_cm']:.1f}",
        "dbTests": 767, "dbAthletes": 530,   # all-sport CMJ fit sample (576 male and 191 female tests; 410 and 120 athletes), from the centile pipeline
        "sdMale": f"{te['Male']['within_sd_cm']:.1f}", "sdFemale": f"{te['Female']['within_sd_cm']:.1f}",
    }
    def fmt(v):
        return f"{v:,}".replace(",", "{,}") if isinstance(v, int) and v >= 1000 else v
    out = "\n".join(f"\\newcommand{{\\{k}}}{{{fmt(v)}}}" for k, v in M.items()) + "\n"
    (ROOT / "paper/numbers.tex").write_text(out); print(out)


if __name__ == "__main__":
    main()
