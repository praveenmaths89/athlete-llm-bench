"""Measurement noise of countermovement-jump height from the released tables.

Within-test trial variance is pooled over tests with two or more trials. For a test mean over k trials (k = median number of trials),
the typical error is SD / sqrt(k), and the 95% reliable change between two test means is 1.96 * sqrt(2) * SD / sqrt(k).
The benchmark uses the values stored in results/typical_error.json, which were computed from the source extract before de-identification;
this script recomputes them from the released tables and prints both, so that the small difference can be inspected. It writes nothing.

    python -m lcb.tools.noise_estimate
"""
import csv, collections, json, math, statistics as st
from lcb.config import RELEASE_TESTS, RELEASE_TRIALS, NOISE_PATH


def estimate():
    sex = {r["athlete"]: r["sex"] for r in csv.DictReader(open(RELEASE_TESTS))}
    trials = collections.defaultdict(list)
    for r in csv.DictReader(open(RELEASE_TRIALS)):
        trials[(r["athlete"], r["test_index"])].append(float(r["jump_height_cm"]))
    res = {}
    for group in ("Male", "Female", "Pooled"):
        var, k = [], []
        for (athlete, _), x in trials.items():
            if len(x) >= 2 and (group == "Pooled" or sex[athlete] == group):
                var.append(st.variance(x)); k.append(len(x))
        sd, kk = math.sqrt(sum(var) / len(var)), st.median(k)
        res[group] = dict(tests=len(var), median_trials=kk, within_sd_cm=round(sd, 3), te_mean_cm=round(sd / math.sqrt(kk), 3),
                          reliable_change_cm=round(1.96 * math.sqrt(2) * sd / math.sqrt(kk), 3))
    return res


if __name__ == "__main__":
    new, stored = estimate(), json.loads(NOISE_PATH.read_text())
    for g in new:
        print(f"{g:7s} tests {new[g]['tests']:4d} (stored {stored[g]['tests']})  within-test SD {new[g]['within_sd_cm']:.2f} cm (stored {stored[g]['within_sd_cm']:.2f})  "
              f"reliable change {new[g]['reliable_change_cm']:.2f} cm (stored {stored[g]['reliable_change_cm']:.2f})")
