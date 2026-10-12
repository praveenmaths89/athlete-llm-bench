"""Gold answers computed by plain Python on the release view (independent of the agent tools)."""
import csv, collections
from lcb.config import RELEASE_TESTS, RELEASE_TRIALS, TEST_TYPE, VARIABLE
from lcb.tools import noise
from lcb.tools.centile_tool import centile


def load():
    by = collections.defaultdict(list)
    trials = collections.defaultdict(list)
    for r in csv.DictReader(open(RELEASE_TRIALS)): trials[(r["athlete"], int(r["test_index"]))].append(float(r["jump_height_cm"]))
    for r in csv.DictReader(open(RELEASE_TESTS)):
        k = (r["athlete"], int(r["test_index"]))
        by[r["athlete"]].append(dict(idx=int(r["test_index"]), sex=r["sex"], date=r["test_date"], gap=int(r["days_since_prev"] or 0), age=float(r["age_years"]), band=r["age_band"],
                                     v=float(r["jump_mean_cm"]), best=float(r["jump_best_cm"]), n_trials=int(r["n_trials"]), trials=trials.get(k, [])))
    for v in by.values(): v.sort(key=lambda t: t["idx"])
    return dict(by)


def cent(sex, t):
    c = centile(TEST_TYPE, sex, VARIABLE, t["age"], t["v"])
    return c.centile, c.band, c.norm_label


def change(a, b): return round(b["v"] - a["v"], 2)
def noisy(sex, d): return "within_measurement_noise" if abs(d) <= noise.reliable_change_cm(sex) else "real"
def yes(b): return "yes" if b else "no"
