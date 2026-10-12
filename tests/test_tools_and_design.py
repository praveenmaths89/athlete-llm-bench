import json
from lcb.config import RESULTS, TEST_TYPE, VARIABLE
from lcb.tools.centile_tool import centile, value_at_centile
from lcb.experiments.counterfactual import design, payload

RC = {"Male": 3.633, "Female": 5.447}   # 95% reliable change of a test mean (results/typical_error.json)


def test_centile_inverse_round_trip():
    for sex in ("Male", "Female"):
        for age in (10.3, 14.7, 20.0):
            for pct in (10, 25, 50, 75, 90):
                v = value_at_centile(TEST_TYPE, sex, VARIABLE, age, pct)
                assert abs(centile(TEST_TYPE, sex, VARIABLE, age, v).centile - pct) < 1e-6


def test_centile_outside_age_grid_has_no_norm():
    assert centile(TEST_TYPE, "Male", VARIABLE, 3.0, 20.0).norm_label == "no_norm"
    assert centile(TEST_TYPE, "Male", VARIABLE, 90.0, 20.0).norm_label == "no_norm"


def test_centile_is_monotone_in_value_at_fixed_age():
    vals = [10, 15, 20, 25, 30, 35, 40]
    cs = [centile(TEST_TYPE, "Male", VARIABLE, 16.0, v) for v in vals]
    pcts = [c.centile for c in cs if c.centile is not None]
    assert pcts == sorted(pcts)


def test_design_is_balanced_and_within_noise():
    d = design()
    assert len(d) == 180 and d.attrs["dropped"] == 0
    assert (d["size"] < d.sex.map(RC)).all()                       # every gold verdict is "within noise"
    assert set(d.groupby(["sex", "age_a", "base", "size"]).sign.nunique()) == {2}   # both directions per cell
    assert (d.base == d.c_a.round(-0).astype(int)).mean() > 0.95 or (d.c_a - d.base).abs().max() <= 1   # baseline centile held fixed (rounding)


def test_twins_differ_only_by_the_centile_line():
    c = design().iloc[0].to_dict()
    a, b = payload(c, 1), payload(c, 0)
    assert "Centile" in a and "Centile" not in b
    assert a.replace([l for l in a.splitlines() if l.startswith("Centile")][0] + "\n", "") == b
