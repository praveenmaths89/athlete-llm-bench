import csv, collections
from lcb.config import RELEASE_TESTS, RELEASE_TRIALS

tests = list(csv.DictReader(open(RELEASE_TESTS))); trials = list(csv.DictReader(open(RELEASE_TRIALS)))


def test_no_names_ids_or_birth_dates():
    cols = set(tests[0]) | set(trials[0])
    assert not (cols & {"athlete_name", "given_name", "family_name", "profile_id", "date_of_birth", "club", "sport"})


def test_athlete_ids_are_pseudonyms():
    assert all(r["athlete"].startswith("A") and len(r["athlete"]) == 11 for r in tests)


def test_test_index_is_consecutive_and_dates_ordered():
    by = collections.defaultdict(list)
    for r in tests: by[r["athlete"]].append(r)
    for v in by.values():
        assert [int(r["test_index"]) for r in v] == list(range(1, len(v) + 1)) and [r["test_date"] for r in v] == sorted(r["test_date"] for r in v)


def test_trial_rows_match_test_counts_and_means():
    tr = collections.defaultdict(list)
    for r in trials: tr[(r["athlete"], r["test_index"])].append(float(r["jump_height_cm"]))
    bad = 0
    for r in tests:
        v = tr[(r["athlete"], r["test_index"])]
        assert len(v) == int(r["n_trials"]) and abs(max(v) - float(r["jump_best_cm"])) < 0.011
        bad += abs(sum(v) / len(v) - float(r["jump_mean_cm"])) > 0.05
    assert bad <= 8        # a few same-day tests were averaged in the source
