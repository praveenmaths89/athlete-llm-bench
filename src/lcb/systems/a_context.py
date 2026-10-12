"""System A: single call. Everything the other systems can reach is placed in the prompt (data table, centile grid, noise thresholds); no tools."""
import csv, time
from functools import lru_cache
from lcb.config import MODELS, RELEASE_TESTS, RELEASE_TRIALS, GRID_PATH, TEST_TYPE, VARIABLE
from lcb.benchmark.schema import ANSWER_SCHEMA, ANSWER_INSTRUCTIONS
from lcb.tools import noise
from lcb.systems.base import Result, parse_final
from lcb.systems.prompts import BANDS, NOISE_RULE


@lru_cache(maxsize=2)
def context_block(with_noise: bool) -> str:
    table = [open(RELEASE_TESTS).readline().strip()] + [",".join(r.values()) for r in csv.DictReader(open(RELEASE_TESTS))]
    trials = [open(RELEASE_TRIALS).readline().strip()] + [",".join(r.values()) for r in csv.DictReader(open(RELEASE_TRIALS))]
    grid = ["sex,age,P3,P10,P25,P50,P75,P90,P97  (reference centiles of impulse-momentum jump height in cm, football CMJ cohort; interpolate linearly between ages)"]
    for r in csv.DictReader(open(GRID_PATH)):
        if r["test_type"] == TEST_TYPE and r["variable"] == VARIABLE and float(r["age"]) <= 25:
            grid.append(",".join([r["gender"], r["age"]] + [f"{float(r[c]):.2f}" for c in ("P3", "P10", "P25", "P50", "P75", "P90", "P97")]))
    return ("TABLE tests (one row per athlete test; jump_mean_cm = impulse-momentum jump height, mean of the trials):\n" + "\n".join(table) + "\n\nTABLE trials (one row per trial):\n" + "\n".join(trials) + "\n\nCENTILE GRID:\n" + "\n".join(grid) + "\n\n" + BANDS +
            "\nTo find a centile band: interpolate the sex-specific quantiles to the athlete's age, then place the jump height among them.\n" + NOISE_RULE.format(m=noise.reliable_change_cm("Male"), f=noise.reliable_change_cm("Female")))


def run(llm, model_key: str, question: str, with_noise: bool = False, max_tokens: int = 4000) -> Result:
    t0 = time.time(); model = MODELS[model_key]
    system = [{"type": "text", "text": ANSWER_INSTRUCTIONS + "\n\n" + context_block(with_noise), "cache_control": {"type": "ephemeral"}}]
    r, cost = llm.create(model, system, [{"role": "user", "content": question}], schema=ANSWER_SCHEMA, max_tokens=max_tokens)
    text = "".join(b.text for b in r.content if b.type == "text"); ans, note = parse_final(text)
    u = r.usage; tin = u.input_tokens + (u.cache_read_input_tokens or 0) + (u.cache_creation_input_tokens or 0)
    return Result(ans, note, [{"kind": "llm", "agent": "single", "turn": 0, "stop": r.stop_reason, "in": tin, "out": u.output_tokens, "tool_calls": []}], tin, u.output_tokens, cost, time.time() - t0, 1, r.stop_reason)
