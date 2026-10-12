"""Shared pieces of the four systems: result record and the tool loop."""
import json, time
from dataclasses import dataclass, field
from lcb.benchmark.schema import ANSWER_SCHEMA
from lcb.tools.registry import Toolbox, dumps


@dataclass
class Result:
    answer: dict | None = None
    note: str = ""
    trace: list = field(default_factory=list)       # events: {"kind": "llm"|"tool"|"handoff", ...}
    in_tok: int = 0
    out_tok: int = 0
    cost: float = 0.0
    seconds: float = 0.0
    turns: int = 0
    stop: str = ""
    error: str | None = None


def parse_final(text: str):
    try:
        d = json.loads(text); return d.get("answer"), d.get("note", "")
    except Exception:
        return None, text[:200]


def tool_loop(llm, model, system, user, tools, toolbox: Toolbox, schema=ANSWER_SCHEMA, max_turns=8, trace=None, label="agent", handler=None):
    """Run an agent until it stops calling tools. `handler(name, args)` can replace the default toolbox dispatch (used for agent-as-tool)."""
    msgs = [{"role": "user", "content": user}]; tin = tout = 0; cost = 0.0; text = ""; stop = ""; trace = trace if trace is not None else []
    for turn in range(max_turns):
        r, c = llm.create(model, system, msgs, tools=tools, schema=schema)
        tin += r.usage.input_tokens + (getattr(r.usage, "cache_read_input_tokens", 0) or 0); tout += r.usage.output_tokens; cost += c; stop = r.stop_reason
        msgs.append({"role": "assistant", "content": r.content})
        uses = [b for b in r.content if b.type == "tool_use"]
        trace.append({"kind": "llm", "agent": label, "turn": turn, "stop": r.stop_reason, "in": r.usage.input_tokens, "out": r.usage.output_tokens, "tool_calls": [u.name for u in uses]})
        if not uses:
            text = "".join(b.text for b in r.content if b.type == "text"); break
        results = []
        for u in uses:
            out = handler(u.name, u.input) if handler else toolbox.call(u.name, u.input)
            trace.append({"kind": "tool", "agent": label, "name": u.name, "args": u.input, "result": out})
            results.append({"type": "tool_result", "tool_use_id": u.id, "content": dumps(out) if not isinstance(out, str) else out})
        msgs.append({"role": "user", "content": results})
    else:
        stop = "max_turns"
    return text, tin, tout, cost, stop, turn + 1
