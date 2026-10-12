"""Cohort measurement noise of the jump-height metric, from within-test trial spread (aggregate numbers, no athlete data)."""
import json
from functools import lru_cache
from lcb.config import NOISE_PATH


@lru_cache(maxsize=1)
def table() -> dict:
    return json.loads(NOISE_PATH.read_text())


def reliable_change_cm(sex: str) -> float:
    """95% reliable change of a test mean: 1.96 * sqrt(2) * (trial SD / sqrt(trials))."""
    return float(table()[sex]["reliable_change_cm"])


def noise_basis(sex: str) -> dict:
    t = table()[sex]
    return {"within_test_sd_cm": t["within_sd_cm"], "median_trials_per_test": t["median_trials"], "tests_used": t["tests"]}
