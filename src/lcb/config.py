"""Paths, constants and prices in one place. No absolute paths: set LCB_PIPELINE_DIR for the private R pipeline output."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNS_DIR = ROOT / os.environ.get("LCB_RUNS_DIR", "runs")      # cached responses (LCB_RUNS_DIR lets a trace-viewing replay write elsewhere)
RESULTS = ROOT / "results"                  # aggregate, shareable outputs
PRIVATE = ROOT / "data_private"            # real athlete-derived files; git-ignored, never released
RELEASE_TESTS = ROOT / "data/release/tests.csv"
RELEASE_TRIALS = ROOT / "data/release/trials.csv"
NOISE_PATH = RESULTS / "typical_error.json"      # aggregate noise estimate from within-test trial spread
GRID_PATH = ROOT / "data/norm_grid/cmj_jump_height_centile_grid.csv"

TEST_TYPE = "CMJ"
VARIABLE = "Jump_Height_Imp-Mom_"            # impulse-momentum jump height, cm
MODELS = {"haiku": "claude-haiku-5-5", "sonnet": "claude-sonnet-5-5", "opus": "claude-opus-5-5"}
PRICE_PER_MTOK = {"claude-haiku-5-5": (0.10, 0.50), "claude-sonnet-5-5": (2.0, 10.0), "claude-opus-5-5": (4.0, 20.0)}  # (input, output), cached table 2026-10-06
EFFORT = "medium"

def pipeline_dir() -> Path:
    """Private output folder of the R centile pipeline (needed only to rebuild real-data tables)."""
    p = os.environ.get("LCB_PIPELINE_DIR")
    if not p:
        raise SystemExit("Set LCB_PIPELINE_DIR to the R_pipeline folder (private data) to rebuild real-data tables.")
    return Path(p)


def call_cost(model: str, usage) -> float:
    """USD of one API call. Cache reads are billed at 10 percent and cache writes at 125 percent of the input price (approximation of the published rule)."""
    pin, pout = PRICE_PER_MTOK[model]
    cr = getattr(usage, "cache_read_input_tokens", 0) or 0; cw = getattr(usage, "cache_creation_input_tokens", 0) or 0
    return (usage.input_tokens * pin + cr * pin * 0.10 + cw * pin * 1.25 + usage.output_tokens * pout) / 1e6
