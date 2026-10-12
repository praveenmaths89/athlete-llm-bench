"""Amendment A3: S3 tool-using agent. Does the agent fetch cohort evidence? Real pairs, no ids/dates."""
import json, sys, time, os, threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import anthropic
from lcb.tools.centile_tool import centile
from lcb.legacy.quick_test2 import SCHEMA, INSTR, load_env, payload as payload2

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "data_private/real_pairs/quick_test3"; OUT.mkdir(parents=True, exist_ok=True)
MODELS = ["claude-haiku-5-5", "claude-opus-5-5"]; RUNS = 2; VAR = "Jump_Height_Imp-Mom_"
TE = json.loads((ROOT / "results/typical_error.json").read_text())
SYS_N = ("You are assisting a strength and conditioning coach. You have tools: tracking_check (compares two test results against the cohort's "
         "measurement noise) and centile_lookup (position in the age- and sex-matched reference group). Answer only with the requested JSON.")
SYS_U = SYS_N.replace("Answer only", "Check your claims with the tools before answering. Answer only")
TOOLS = [
    {"name": "tracking_check", "description": "Compare two countermovement jump heights (cm) of one athlete against the football cohort's measurement noise. Returns the change, the cohort 95% reliable-change threshold in cm, and a label: within_noise or beyond_noise.",
     "input_schema": {"type": "object", "properties": {"sex": {"type": "string", "enum": ["Male", "Female"]}, "value_1_cm": {"type": "number"}, "value_2_cm": {"type": "number"}}, "required": ["sex", "value_1_cm", "value_2_cm"]}},
    {"name": "centile_lookup", "description": "Centile of a countermovement jump height (impulse-momentum, cm) in the age- and sex-matched reference group, from the published GAMLSS grid. Returns centile, band and norm label.",
     "input_schema": {"type": "object", "properties": {"sex": {"type": "string", "enum": ["Male", "Female"]}, "age_years": {"type": "number"}, "value_cm": {"type": "number"}}, "required": ["sex", "age_years", "value_cm"]}},
]

def run_tool(name, a):
    if name == "tracking_check":
        rc = TE[a["sex"]]["reliable_change_cm"]; d = a["value_2_cm"] - a["value_1_cm"]
        return {"change_cm": round(d, 2), "reliable_change_threshold_cm": rc, "label": "within_noise" if abs(d) <= rc else "beyond_noise"}
    if name == "centile_lookup":
        r = centile("CMJ", a["sex"], VAR, a["age_years"], a["value_cm"])
        return {"centile": None if r.centile is None else round(r.centile, 1), "band": r.band, "norm_label": r.norm_label}
    return {"error": "unknown tool"}

def base_prompt(c):
    # same facts as A2 C0 (no cohort evidence in the prompt)
    return payload2(c, "C0")

def one(client, c, cond, m, run, raw, lock):
    system = SYS_U if cond == "U" else SYS_N
    msgs = [{"role": "user", "content": base_prompt(c)}]; calls = []; tin = tout = 0; text = ""; stop = None
    for turn in range(6):
        for attempt in range(4):
            try:
                r = client.messages.create(model=m, max_tokens=4000, system=system, tools=TOOLS, messages=msgs,
                                           output_config={"effort": "medium", "format": {"type": "json_schema", "schema": SCHEMA}}); break
            except anthropic.APIStatusError as e:
                if attempt == 3: raise
                time.sleep(4 * (attempt + 1))
        if r.model != m: raise SystemExit(f"requested {m} got {r.model}")
        tin += r.usage.input_tokens; tout += r.usage.output_tokens; stop = r.stop_reason
        msgs.append({"role": "assistant", "content": r.content})
        uses = [b for b in r.content if b.type == "tool_use"]
        if not uses:
            text = "".join(b.text for b in r.content if b.type == "text"); break
        results = []
        for b in uses:
            out = run_tool(b.name, b.input); calls.append({"name": b.name, "args": b.input, "result": out})
            results.append({"type": "tool_result", "tool_use_id": b.id, "content": json.dumps(out)})
        msgs.append({"role": "user", "content": results})
    try: parsed = json.loads(text)
    except Exception: parsed = None
    rec = dict(case_id=c["case_id"], group=c["group"], cond=cond, model=m, run=run, stop_reason=stop, in_tok=tin, out_tok=tout, calls=calls, parsed=parsed, text=text)
    with lock, open(raw, "a") as fh: fh.write(json.dumps(rec) + "\n")
    return tin, tout

def main():
    load_env(); client = anthropic.Anthropic()
    cases = json.load(open(ROOT / "data_private/real_pairs/quick_test2/cases.json"))
    raw = OUT / "raw.jsonl"; done = set()
    if raw.exists():
        for l in raw.read_text().splitlines(): d = json.loads(l); done.add((d["case_id"], d["cond"], d["model"], d["run"]))
    jobs = [(c, cond, m, run) for c in cases for cond in ("N", "U") for m in MODELS for run in range(1, RUNS + 1) if (c["case_id"], cond, m, run) not in done]
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    if limit: jobs = jobs[:limit]
    print(len(jobs), "runs to do"); lock = threading.Lock(); price = {"claude-haiku-5-5": (0.10, 0.50), "claude-opus-5-5": (4.0, 20.0)}
    cost = [0.0]
    def work(j):
        if cost[0] > 5.0: return
        tin, tout = one(client, *j, raw, lock); p = price[j[2]]
        with lock: cost[0] += tin / 1e6 * p[0] + tout / 1e6 * p[1]
    with ThreadPoolExecutor(max_workers=4) as ex: list(ex.map(work, jobs))
    print(f"done; approx cost USD {cost[0]:.3f}")

if __name__ == "__main__":
    main()
