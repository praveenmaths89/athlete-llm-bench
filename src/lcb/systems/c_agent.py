"""System C: one agent with the tools sql, centile and tracking (tool choice automatic)."""
import time
from lcb.config import MODELS
from lcb.benchmark.schema import ANSWER_INSTRUCTIONS
from lcb.tools.registry import TOOL_DEFS
from lcb.systems.base import Result, tool_loop, parse_final
from lcb.systems.prompts import BANDS

SYSTEM = (ANSWER_INSTRUCTIONS + "\n\nYou have three tools: sql (read the test table), centile (centile band of a stored test) and tracking (change between two stored tests against the cohort measurement noise). "
          "Use them to ground your answer in the data. " + BANDS)


def run(llm, model_key: str, question: str, toolbox, max_turns: int = 8) -> Result:
    t0 = time.time(); trace = []
    text, tin, tout, cost, stop, turns = tool_loop(llm, MODELS[model_key], SYSTEM, question, TOOL_DEFS, toolbox, max_turns=max_turns, trace=trace, label="agent")
    ans, note = parse_final(text); return Result(ans, note, trace, tin, tout, cost, time.time() - t0, turns, stop)
