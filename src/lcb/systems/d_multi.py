"""System D: multi-agent. A coordinator delegates to two specialists (data agent with sql; statistics agent with centile and tracking) and writes the final answer."""
import time
from lcb.config import MODELS
from lcb.benchmark.schema import ANSWER_INSTRUCTIONS
from lcb.tools.registry import TOOL_DEFS
from lcb.systems.base import Result, tool_loop, parse_final
from lcb.systems.prompts import BANDS

DATA_TOOLS = [t for t in TOOL_DEFS if t["name"] == "sql"]
STATS_TOOLS = [t for t in TOOL_DEFS if t["name"] in ("centile", "tracking")]
DATA_SYS = "You are the data specialist. Use the sql tool to fetch exactly the rows requested and report them concisely as plain text (athlete, test_index, age, jump height). If the athlete or test does not exist, say so."
STATS_SYS = "You are the statistics specialist. Use the centile and tracking tools on stored tests (athlete id and test_index) and report the results concisely as plain text: centile band, norm label, change in cm, noise threshold and label. " + BANDS
COORD_SYS = (ANSWER_INSTRUCTIONS + "\n\nYou are the coordinator. You cannot read data yourself. Delegate with ask_data_agent (to look up rows) and ask_stats_agent (centiles and change versus measurement noise for stored tests), then write the final answer from what they report. " + BANDS)
COORD_TOOLS = [
    {"name": "ask_data_agent", "description": "Ask the data specialist to look up rows of the athlete test table.", "input_schema": {"type": "object", "properties": {"request": {"type": "string"}}, "required": ["request"]}},
    {"name": "ask_stats_agent", "description": "Ask the statistics specialist for centiles or change-versus-noise results of stored tests (give athlete id and test indexes).", "input_schema": {"type": "object", "properties": {"request": {"type": "string"}}, "required": ["request"]}},
]


def run(llm, model_key: str, question: str, toolbox) -> Result:
    t0 = time.time(); model = MODELS[model_key]; trace = []; acc = {"in": 0, "out": 0, "cost": 0.0, "turns": 0}

    def delegate(name, args):
        sysmsg, tools, label = (DATA_SYS, DATA_TOOLS, "data_agent") if name == "ask_data_agent" else (STATS_SYS, STATS_TOOLS, "stats_agent")
        trace.append({"kind": "handoff", "to": label, "request": args.get("request", "")})
        text, tin, tout, cost, stop, turns = tool_loop(llm, model, sysmsg, args.get("request", ""), tools, toolbox, schema=None, max_turns=6, trace=trace, label=label)
        acc["in"] += tin; acc["out"] += tout; acc["cost"] += cost; acc["turns"] += turns
        trace.append({"kind": "handoff_return", "from": label, "text": text[:500]})
        return text or "(no result)"

    text, tin, tout, cost, stop, turns = tool_loop(llm, model, COORD_SYS, question, COORD_TOOLS, toolbox, max_turns=8, trace=trace, label="coordinator", handler=delegate)
    ans, note = parse_final(text)
    return Result(ans, note, trace, tin + acc["in"], tout + acc["out"], cost + acc["cost"], time.time() - t0, turns + acc["turns"], stop)
