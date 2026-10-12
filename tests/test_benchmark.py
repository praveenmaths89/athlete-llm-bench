import json, collections
from lcb.config import ROOT
from lcb.tools.registry import Toolbox

Q = [json.loads(l) for l in open(ROOT / "data/benchmark/questions.jsonl")]
tb = Toolbox()


def test_basic_integrity():
    assert len({q["qid"] for q in Q}) == len(Q) and len(Q) >= 90
    assert {q["split"] for q in Q} == {"dev", "selection", "final"}
    by = collections.defaultdict(set)
    for q in Q:
        if q["athlete"]: by[q["athlete"]].add(q["split"])
    assert all(len(v) == 1 for v in by.values())                     # no athlete in two splits
    assert all(("abstain" in q["gold"]) == (q["family"] == "Q7" and q["template"] != "outside_reference_range") for q in Q)
    assert {q["family"] for q in Q} == {"Q1", "Q2", "Q3", "Q4", "Q7"}


def test_gold_is_reachable_with_the_tools():
    """A perfect tool user reproduces the gold for the answerable question templates."""
    for q in Q:
        a, g, t = q["athlete"], q["gold"], q["template"]
        if not a: continue                       # cohort-level questions are checked in test_cohort_gold
        n = tb.db.query(f"SELECT COUNT(*) FROM tests WHERE athlete='{a}'")["rows"][0][0]
        if t == "latest_value": assert tb.db.query(f"SELECT jump_mean_cm FROM tests WHERE athlete='{a}' ORDER BY test_index DESC LIMIT 1")["rows"][0][0] == g["value_cm"]
        if t == "best_value": assert tb.db.query(f"SELECT MAX(jump_mean_cm) FROM tests WHERE athlete='{a}'")["rows"][0][0] == g["value_cm"]
        if t == "band_latest": assert tb.call("centile", {"athlete": a, "test_index": n})["band"] == g["centile_band"]
        if t == "change_first_latest": assert abs(tb.call("tracking", {"athlete": a, "from_index": 1, "to_index": n})["change_cm"] - g["change_cm"]) < 0.011
        if t == "span_days": assert tb.db.query(f"SELECT COALESCE(SUM(days_since_prev),0) FROM tests WHERE athlete='{a}'")["rows"][0][0] == g["days"]
        if t == "unknown_athlete": assert n == 0 and g["abstain"]
        if t == "single_test_change": assert n == 1 and g["abstain"]
        if t == "missing_test": assert g["abstain"]


def test_q4_counts_and_labels():
    q4 = [q for q in Q if q["family"] == "Q4"]
    assert len(q4) == 30
    for q in q4:
        g = q["gold"]
        assert g.get("verdict") in (None, "real", "within_measurement_noise") and g.get("trend") in (None, "better", "worse", "no_reliable_change")


def test_cohort_gold_matches_sql():
    for q in Q:
        t, g = q["template"], q["gold"]
        if t == "cohort_count_multi" and "two" in q["text"]:
            assert tb.db.query("SELECT COUNT(*) FROM (SELECT athlete FROM tests GROUP BY athlete HAVING COUNT(*) >= 2)")["rows"][0][0] == g["count"]
        if t == "cohort_busiest_year":
            assert tb.db.query("SELECT substr(test_date,1,4) y FROM tests GROUP BY y ORDER BY COUNT(*) DESC LIMIT 1")["rows"][0][0] == g["text"]
        if t == "cohort_share_single":
            n1 = tb.db.query("SELECT COUNT(*) FROM (SELECT athlete FROM tests GROUP BY athlete HAVING COUNT(*) = 1)")["rows"][0][0]; n = tb.db.query("SELECT COUNT(DISTINCT athlete) FROM tests")["rows"][0][0]
            assert abs(n1 / n - g["share"]) < 0.0051
