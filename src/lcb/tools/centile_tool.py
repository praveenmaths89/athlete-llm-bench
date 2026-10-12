"""Centile lookup on the published GAMLSS grid (Table_S5). Pure function, no model refit.

Age is interpolated linearly between the two bracketing grid ages (no snapping).
The value is placed among P3..P97 by piecewise-linear interpolation on the normal-score scale.
Outside the grid age range the tool returns no_norm; outside P3..P97 it returns '<3' / '>97'.
"""
from __future__ import annotations
import csv
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from statistics import NormalDist

from lcb.config import GRID_PATH
PCOLS = ["P3", "P10", "P25", "P50", "P75", "P90", "P97"]
PROBS = [0.03, 0.10, 0.25, 0.50, 0.75, 0.90, 0.97]
Z = [NormalDist().inv_cdf(p) for p in PROBS]
BANDS = [(3, "<P3"), (10, "P3-P10"), (25, "P10-P25"), (50, "P25-P50"), (75, "P50-P75"), (90, "P75-P90"), (97, "P90-P97"), (101, ">P97")]


@dataclass(frozen=True)
class CentileResult:
    centile: float | None      # 0-100, None when outside P3..P97 or no norm
    band: str                  # band label, or 'no_norm'
    norm_label: str            # 'firm' | 'indicative' | 'no_norm'
    age_lo: float | None = None
    age_hi: float | None = None
    edge: str | None = None    # '<3' or '>97' when outside the fitted centiles


@lru_cache(maxsize=None)
def _grid(test_type: str, sex: str, variable: str):
    rows = {}
    with open(GRID_PATH, newline="") as fh:
        for r in csv.DictReader(fh):
            if r["test_type"] == test_type and r["gender"] == sex and r["variable"] == variable:
                rows[float(r["age"])] = ([float(r[c]) for c in PCOLS], r["sample_label"])
    return dict(sorted(rows.items()))


def _band(pct: float) -> str:
    for upper, name in BANDS:
        if pct < upper:
            return name
    return BANDS[-1][1]


def centile(test_type: str, sex: str, variable: str, age: float, value: float) -> CentileResult:
    g = _grid(test_type, sex, variable)
    if not g or age < min(g) or age > max(g):
        return CentileResult(None, "no_norm", "no_norm")
    ages = list(g)
    lo = max(a for a in ages if a <= age)
    hi = min(a for a in ages if a >= age)
    w = 0.0 if hi == lo else (age - lo) / (hi - lo)
    q = [(1 - w) * a + w * b for a, b in zip(g[lo][0], g[hi][0])]
    label = "indicative" if "indicative" in (g[lo][1] + g[hi][1]) else "firm"
    if value < q[0]:
        return CentileResult(None, "<P3", label, lo, hi, "<3")
    if value > q[-1]:
        return CentileResult(None, ">P97", label, lo, hi, ">97")
    for i in range(len(q) - 1):
        if q[i] <= value <= q[i + 1]:
            t = 0.0 if q[i + 1] == q[i] else (value - q[i]) / (q[i + 1] - q[i])
            z = Z[i] + t * (Z[i + 1] - Z[i])
            pct = 100 * NormalDist().cdf(z)
            return CentileResult(pct, _band(pct), label, lo, hi)
    return CentileResult(None, "no_norm", "no_norm")


def value_at_centile(test_type: str, sex: str, variable: str, age: float, pct: float) -> float | None:
    """Inverse of centile(): the value at a given centile (3..97) for an age, same interpolation rules."""
    g = _grid(test_type, sex, variable)
    if not g or age < min(g) or age > max(g) or not 3 <= pct <= 97:
        return None
    ages = list(g)
    lo = max(a for a in ages if a <= age); hi = min(a for a in ages if a >= age)
    w = 0.0 if hi == lo else (age - lo) / (hi - lo)
    q = [(1 - w) * a + w * b for a, b in zip(g[lo][0], g[hi][0])]
    z = NormalDist().inv_cdf(pct / 100)
    for i in range(len(Z) - 1):
        if Z[i] <= z <= Z[i + 1]:
            t = (z - Z[i]) / (Z[i + 1] - Z[i])
            return q[i] + t * (q[i + 1] - q[i])
    return None
