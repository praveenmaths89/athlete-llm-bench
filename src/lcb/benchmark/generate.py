"""Question generator (benchmark v0.2): families Q1 to Q4 and Q7 on the real release view, gold by plain Python.
Cohort-level questions (Q3c) use all athletes; their split is assigned by a hash of the question id.

usage: python -m lcb.benchmark.generate
"""
import collections, json, random, hashlib, statistics as st
from lcb.config import ROOT
from lcb.benchmark import gold as G
from lcb.tools import noise

OUT = ROOT / "data/benchmark"; SEED = 11
SPLIT_P = (("dev", 0.20), ("selection", 0.20), ("final", 0.60)); CAP = 4


def split_of(key: str) -> str:
    u = int(hashlib.sha256(f"split-{SEED}-{key}".encode()).hexdigest()[:8], 16) / 0xFFFFFFFF; acc = 0
    for name, p in SPLIT_P:
        acc += p
        if u < acc: return name
    return "final"


def build():
    data = G.load(); rng = random.Random(SEED); qs = []; used = collections.Counter(); ids = sorted(data)

    def add(family, template, text, athlete, gold, tags, split_key=None):
        if athlete and used[athlete] >= CAP: return False
        if athlete: used[athlete] += 1
        qid = f"{family}{len(qs)+1:03d}"
        qs.append(dict(qid=qid, family=family, template=template, text=text, athlete=athlete, split=split_of(athlete or qid), gold=gold, tags=tags)); return True

    def pick(pool, n): pool = list(pool); rng.shuffle(pool); return pool[:n]
    def run(target, fn, pool):
        c = 0
        for a in pool:
            if c >= target: break
            if fn(a): c += 1
    n_of = lambda a: len(data[a]); multi = [a for a in ids if n_of(a) >= 2]; three = [a for a in ids if n_of(a) >= 3]; single = [a for a in ids if n_of(a) == 1]
    rc = noise.reliable_change_cm
    last = lambda a: data[a][-1]; first = lambda a: data[a][0]

    # ---------- Q1 numerical ----------
    def q1_idx(a):
        k = rng.randint(1, n_of(a)); return add("Q1", "value_at_index", rng.choice([f"What was athlete {a}'s jump height at test number {k}?", f"For athlete {a}, how high did they jump (average of the trials) in test {k}?"]), a, {"value_cm": data[a][k-1]["v"]}, {"steps": 1, "n_tests": n_of(a)})
    def q1_latest(a): return add("Q1", "latest_value", rng.choice([f"What was {a}'s most recent jump height?", f"What is the latest countermovement jump height recorded for athlete {a}?"]), a, {"value_cm": last(a)["v"]}, {"steps": 1, "n_tests": n_of(a)})
    def q1_age(a): return add("Q1", "age_first", rng.choice([f"How old was athlete {a} at their first test?", f"At what age did {a} first test?"]), a, {"age_years": first(a)["age"]}, {"steps": 1, "n_tests": n_of(a)})
    def q1_best_trial(a):
        k = rng.randint(1, n_of(a)); return add("Q1", "best_trial_at_test", f"What was the best single trial in athlete {a}'s test number {k}?", a, {"value_cm": data[a][k-1]["best"]}, {"steps": 1, "n_tests": n_of(a), "uses": "trials"})
    def q1_ntrials(a):
        k = rng.randint(1, n_of(a)); return add("Q1", "n_trials_at_test", f"How many trials were recorded in athlete {a}'s test number {k}?", a, {"count": data[a][k-1]["n_trials"]}, {"steps": 1, "n_tests": n_of(a), "uses": "trials"})
    run(4, q1_idx, pick(ids, 12)); run(3, q1_latest, pick(ids, 12)); run(2, q1_age, pick(ids, 12)); run(3, q1_best_trial, pick(ids, 12)); run(2, q1_ntrials, pick(ids, 12))

    # ---------- Q2 centile ----------
    def q2_band(a):
        t = last(a); c, band, lab = G.cent(t["sex"], t)
        return add("Q2", "band_latest", rng.choice([f"Which centile band was athlete {a} in at their latest test?", f"Where did {a}'s latest jump sit in the age- and sex-matched reference group? Give the centile band."]), a, {"centile_band": band}, {"steps": 1, "norm_label": lab, "edge": band in ("<P3", ">P97")})
    def q2_above(a):
        t = last(a); c, band, lab = G.cent(t["sex"], t)
        return add("Q2", "above_median", rng.choice([f"Was {a}'s latest jump above the median for their age and sex?", f"Is athlete {a} above the 50th centile at their latest test?"]), a, {"yes_no": G.yes(band in (">P97", "P90-P97", "P75-P90", "P50-P75"))}, {"steps": 1, "norm_label": lab})
    edge = [a for a in ids if G.cent(last(a)["sex"], last(a))[1] in ("<P3", ">P97")]
    run(5, q2_band, pick(edge, 3) + pick(ids, 12)); run(5, q2_above, pick(ids, 12))

    # ---------- Q3 longitudinal (per athlete) ----------
    def q3_change(a): return add("Q3", "change_first_latest", rng.choice([f"By how much did athlete {a}'s jump height change from their first test to their latest test?", f"What is the change in {a}'s jump height between the first and the most recent test?"]), a, {"change_cm": G.change(first(a), last(a))}, {"steps": 2, "n_tests": n_of(a)})
    def q3_best(a): return add("Q3", "best_value", f"What is the highest test-average jump height (mean of the trials of one test) across all of athlete {a}'s tests?", a, {"value_cm": max(t["v"] for t in data[a])}, {"steps": 2, "n_tests": n_of(a)})
    def q3_mean3(a): return add("Q3", "mean_first3", f"What was the average of athlete {a}'s first three jump heights?", a, {"value_cm": round(sum(t["v"] for t in data[a][:3]) / 3, 2)}, {"steps": 2, "n_tests": n_of(a)})
    def q3_moved(a):
        b1 = G.cent(data[a][-2]["sex"], data[a][-2])[1]; b2 = G.cent(last(a)["sex"], last(a))[1]
        return add("Q3", "band_moved", f"Did athlete {a}'s centile band change between their last two tests?", a, {"yes_no": G.yes(b1 != b2)}, {"steps": 3, "n_tests": n_of(a), "from": b1, "to": b2})
    def q3_above_personal(a):
        prev = sum(t["v"] for t in data[a][:-1]) / (n_of(a) - 1)
        return add("Q3", "above_personal_mean", f"Is athlete {a}'s latest jump higher than the average of their earlier tests?", a, {"yes_no": G.yes(last(a)["v"] > prev)}, {"steps": 3, "n_tests": n_of(a)})
    def q3_span(a): return add("Q3", "span_days", f"Over how many days were athlete {a}'s tests spread, from the first to the latest?", a, {"days": sum(t["gap"] for t in data[a][1:])}, {"steps": 2, "n_tests": n_of(a), "uses": "dates"})
    def q3_window(a):
        cum = 0; tgt = None
        for t in data[a][1:]:
            cum += t["gap"]
            if cum >= 150: tgt = t; break
        if tgt is None: return False
        return add("Q3", "change_over_window", f"By how much did athlete {a}'s jump height change between their first test and their first test that took place at least 150 days later?", a, {"change_cm": G.change(first(a), tgt)}, {"steps": 3, "n_tests": n_of(a), "uses": "dates"})
    def q3_year(a):
        y = rng.choice(sorted({t["date"][:4] for t in data[a]})); return add("Q3", "tests_in_year", f"How many tests did athlete {a} have in {y}?", a, {"count": sum(t["date"][:4] == y for t in data[a])}, {"steps": 2, "n_tests": n_of(a), "uses": "dates"})
    def q3_date_best(a):
        b = max(data[a], key=lambda t: t["v"]); ties = [t for t in data[a] if t["v"] == b["v"]]
        if len(ties) > 1: return False
        return add("Q3", "date_of_best", f"On which date did athlete {a} reach their best jump height (test average)? Answer as YYYY-MM-DD.", a, {"text": b["date"]}, {"steps": 2, "n_tests": n_of(a), "uses": "dates"})
    run(5, q3_change, pick(multi, 12)); run(3, q3_best, pick(multi, 12)); run(3, q3_mean3, pick(three, 12)); run(4, q3_moved, pick(multi, 12)); run(4, q3_above_personal, pick(multi, 12))
    run(3, q3_span, pick(multi, 12)); run(4, q3_window, pick(multi, 40)); run(3, q3_year, pick(multi, 12)); run(3, q3_date_best, pick(multi, 12))

    # ---------- Q3c cohort level ----------
    ch = {a: G.change(first(a), last(a)) for a in multi}
    def beyond(a): return abs(ch[a]) > rc(first(a)["sex"])
    def cadd(template, text, gold, tags): return add("Q3", template, text, None, gold, dict(tags, cohort=True, steps=3))
    cadd("cohort_count_multi", "How many athletes have at least two tests?", {"count": len(multi)}, {})
    cadd("cohort_count_multi", "How many athletes have at least three tests?", {"count": len(three)}, {})
    cadd("cohort_share_single", "What share of all athletes have only one test? Answer as a fraction between 0 and 1.", {"share": round(len(single) / len(ids), 2)}, {})
    for sex_name in ("Male", "Female"):
        pool = [a for a in multi if first(a)["sex"] == sex_name]
        cadd("cohort_changed_beyond_noise", f"Among {sex_name.lower()} athletes with at least two tests, how many changed beyond measurement noise between their first and their latest test?", {"count": sum(beyond(a) for a in pool)}, {"noise": True})
    cadd("cohort_changed_beyond_noise", "Among all athletes with at least two tests, how many changed beyond measurement noise between their first and their latest test?", {"count": sum(beyond(a) for a in multi)}, {"noise": True})
    up = max(multi, key=lambda a: ch[a]); dn = min(multi, key=lambda a: ch[a])
    if sorted(ch.values())[-1] != sorted(ch.values())[-2]: cadd("cohort_largest_increase", "Which athlete had the largest increase in jump height from their first test to their latest test? Give the athlete id.", {"text": up}, {})
    if sorted(ch.values())[0] != sorted(ch.values())[1]: cadd("cohort_largest_decrease", "Which athlete had the largest decrease in jump height from their first test to their latest test? Give the athlete id.", {"text": dn}, {})
    for band in ("12-14", "15-17"):
        vals = [last(a)["v"] for a in ids if last(a)["band"] == band]
        cadd("cohort_mean_latest_by_band", f"What is the mean latest jump height (test average) of athletes whose age band at their latest test is {band}?", {"value_cm": round(st.mean(vals), 2)}, {})
    ty = collections.Counter(t["date"][:4] for a in ids for t in data[a]); top = ty.most_common(2)
    if top[0][1] != top[1][1]: cadd("cohort_busiest_year", "In which calendar year were the most tests carried out? Answer with the year.", {"text": top[0][0]}, {})
    cadd("cohort_median_trials", "What is the median number of trials per test across all tests?", {"count": int(st.median(t["n_trials"] for a in ids for t in data[a]))}, {})

    # ---------- Q4 noise interpretation ----------
    pairs = []
    for a in multi:
        for x, y in zip(data[a], data[a][1:]):
            d = G.change(x, y); c1, _, _ = G.cent(x["sex"], x); c2, _, _ = G.cent(y["sex"], y)
            if c1 is None or c2 is None: continue
            pairs.append(dict(a=a, x=x, y=y, d=d, rc=rc(x["sex"]), ratio=abs(d) / rc(x["sex"]), dc=c2 - c1, c1=c1, c2=c2))
    def stratum(p): return ("inside" if p["ratio"] < 0.5 else "borderline" if p["ratio"] <= 1 else "outside", "moved" if abs(p["dc"]) >= 5 else "flat")
    by_s = collections.defaultdict(list)
    for p in pairs: by_s[stratum(p)].append(p)
    for v in by_s.values(): rng.shuffle(v)
    def q4_noise(p): return add("Q4", "change_vs_noise", rng.choice([f"Between tests {p['x']['idx']} and {p['y']['idx']}, did athlete {p['a']}'s jump height change by more than normal test-to-test measurement noise?", f"Is the difference in {p['a']}'s jump height between test {p['x']['idx']} and test {p['y']['idx']} a real change or within measurement noise?"]), p["a"], {"verdict": G.noisy(p["x"]["sex"], p["d"])}, {"steps": 2, "stratum": "/".join(stratum(p)), "n_tests": n_of(p["a"])})
    def q4_centile(p): return add("Q4", "centile_move_vs_change", f"Athlete {p['a']}'s centile went from P{round(p['c1'])} at test {p['x']['idx']} to P{round(p['c2'])} at test {p['y']['idx']}. Did their jump performance really change between those two tests, taking measurement noise into account?", p["a"], {"verdict": G.noisy(p["x"]["sex"], p["d"])}, {"steps": 3, "stratum": "/".join(stratum(p)), "n_tests": n_of(p["a"])})
    def q4_trend(p): return add("Q4", "trend_with_noise", f"Taking measurement noise into account, did athlete {p['a']} get better, get worse, or show no reliable change between test {p['x']['idx']} and test {p['y']['idx']}?", p["a"], {"trend": "no_reliable_change" if abs(p["d"]) <= p["rc"] else ("better" if p["d"] > 0 else "worse")}, {"steps": 3, "stratum": "/".join(stratum(p)), "n_tests": n_of(p["a"])})
    order = sorted(by_s)
    for k, (tmpl, target) in enumerate(((q4_noise, 10), (q4_centile, 10), (q4_trend, 10))):
        got = rr = 0
        while got < target and rr < 300:
            s = order[(k + rr) % len(order)]; rr += 1
            if by_s[s] and tmpl(by_s[s].pop()): got += 1

    # ---------- Q7 edge cases ----------
    def q7_single(a): return add("Q7", "single_test_change", f"By how much did athlete {a}'s jump height change since their previous test?", a, {"abstain": True}, {"steps": 1, "edge": "single_test", "n_tests": 1})
    def q7_missing(a): n = n_of(a) + rng.randint(1, 2); return add("Q7", "missing_test", f"What was athlete {a}'s jump height at test number {n}?", a, {"abstain": True}, {"steps": 1, "edge": "missing_test", "n_tests": n_of(a)})
    def q7_outside(a): band = G.cent(last(a)["sex"], last(a))[1]; return add("Q7", "outside_reference_range", f"Is athlete {a}'s latest jump within the P3 to P97 range of the age- and sex-matched reference group?", a, {"yes_no": G.yes(band not in ("<P3", ">P97"))}, {"steps": 1, "edge": "outside_range", "band": band})
    def q7_trial(a):
        ks = [t for t in data[a] if t["n_trials"] < 3]
        if not ks: return False
        t = rng.choice(ks); return add("Q7", "missing_trial", f"What was the jump height of the third trial in athlete {a}'s test number {t['idx']}?", a, {"abstain": True}, {"steps": 1, "edge": "missing_trial", "n_tests": n_of(a), "uses": "trials"})
    run(5, q7_single, pick(single, 12)); run(4, q7_missing, pick(ids, 12)); run(4, q7_outside, pick(edge, 8)); run(5, q7_trial, pick(ids, 20))
    for i in range(3):
        fake = "A" + hashlib.sha256(f"fake-{i}".encode()).hexdigest()[:10]; qid = f"Q7{len(qs)+1:03d}"
        qs.append(dict(qid=qid, family="Q7", template="unknown_athlete", text=f"What was athlete {fake}'s latest jump height?", athlete=fake, split=split_of(fake), gold={"abstain": True}, tags={"steps": 1, "edge": "unknown_athlete"}))

    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "questions.jsonl", "w") as fh:
        for q in qs: fh.write(json.dumps(q) + "\n")
    inv = collections.Counter((q["family"], q["template"], q["split"]) for q in qs)
    with open(OUT / "inventory.csv", "w") as fh:
        fh.write("family,template,split,n\n"); [fh.write(f"{f},{t},{s},{n}\n") for (f, t, s), n in sorted(inv.items())]
    print(len(qs), "questions;", dict(collections.Counter(q["family"] for q in qs)), dict(collections.Counter(q["split"] for q in qs)))
    return qs


if __name__ == "__main__":
    build()
