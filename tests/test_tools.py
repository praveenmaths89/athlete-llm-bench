import pytest
from lcb.tools.registry import Toolbox
from lcb.tools.sql_tool import Db

tb = Toolbox()


def first_athlete_with(n):
    r = tb.db.query(f"SELECT athlete FROM tests GROUP BY athlete HAVING COUNT(*) >= {n} LIMIT 1")
    return r["rows"][0][0]


def test_sql_is_read_only():
    for bad in ["DROP TABLE tests", "SELECT 1; DELETE FROM tests", "UPDATE tests SET sex='x'", "PRAGMA writable_schema=1", "ATTACH 'x' AS y"]:
        assert "error" in tb.db.query(bad)
    assert tb.db.query("SELECT COUNT(*) FROM tests")["rows"][0][0] > 300


def test_sql_row_limit():
    r = tb.db.query("SELECT * FROM tests", limit=5)
    assert len(r["rows"]) == 5 and r["truncated"]


def test_centile_tool_returns_band_and_label():
    a = first_athlete_with(1); out = tb.call("centile", {"athlete": a, "test_index": 1})
    assert out["norm_label"] in ("firm", "indicative", "no_norm") and "band" in out


def test_centile_unknown_test_is_an_error_not_a_crash():
    assert "error" in tb.call("centile", {"athlete": "nobody", "test_index": 1})


def test_tracking_matches_manual_computation_and_label():
    a = first_athlete_with(2)
    rows = tb.db.query(f"SELECT sex, jump_mean_cm FROM tests WHERE athlete='{a}' ORDER BY test_index LIMIT 2")["rows"]
    out = tb.call("tracking", {"athlete": a, "from_index": 1, "to_index": 2})
    assert abs(out["change_cm"] - (rows[1][1] - rows[0][1])) < 0.011
    assert out["label"] == ("within_noise" if abs(out["change_cm"]) <= out["reliable_change_threshold_cm"] else "beyond_noise")


def test_tracking_single_test_is_insufficient_history():
    a = tb.db.query("SELECT athlete FROM tests GROUP BY athlete HAVING COUNT(*) = 1 LIMIT 1")["rows"][0][0]
    assert tb.call("tracking", {"athlete": a, "from_index": 1, "to_index": 2})["label"] == "insufficient_history"
