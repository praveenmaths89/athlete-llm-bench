"""Amendment A4 runner. usage: run_final.py c0c1|s3 [limit]"""
import json, sys, time, threading, os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import anthropic
from lcb.legacy.final_cases import all_cases
from lcb.legacy.quick_test2 import SCHEMA, payload, SYSTEM, load_env
from lcb.legacy import quick_test3 as q3

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "data_private/real_pairs/final"; OUT.mkdir(parents=True, exist_ok=True)
PRICE = {"claude-haiku-5-5": (0.10, 0.50), "claude-sonnet-5-5": (2.0, 10.0), "claude-opus-5-5": (4.0, 20.0)}

def single(client, c, cond, m, run, raw, lock):
    r = None
    for attempt in range(4):
        try:
            r = client.messages.create(model=m, max_tokens=4000, system=SYSTEM,
                    output_config={"effort": "medium", "format": {"type": "json_schema", "schema": SCHEMA}},
                    messages=[{"role": "user", "content": payload(c, cond)}]); break
        except anthropic.APIStatusError as e:
            if attempt == 3: raise
            time.sleep(4 * (attempt + 1))
    if r.model != m: raise SystemExit(f"requested {m} got {r.model}")
    text = "".join(b.text for b in r.content if b.type == "text")
    try: parsed = json.loads(text)
    except Exception: parsed = None
    rec = dict(case_id=c["case_id"], cond=cond, model=m, run=run, stop_reason=r.stop_reason, in_tok=r.usage.input_tokens, out_tok=r.usage.output_tokens, parsed=parsed, text=text)
    with lock, open(raw, "a") as fh: fh.write(json.dumps(rec) + "\n")
    return rec["in_tok"], rec["out_tok"]

def main():
    mode = sys.argv[1]; limit = int(sys.argv[2]) if len(sys.argv) > 2 else None
    load_env(); client = anthropic.Anthropic(); cases = all_cases()
    (OUT / "cases.json").write_text(json.dumps(cases, indent=1))
    lock = threading.Lock(); cost = [0.0]
    if mode == "c0c1":
        raw = OUT / "c0c1_raw.jsonl"; key = lambda d: (d["case_id"], d["cond"], d["model"], d["run"])
        jobs = [(c, "C0", m, r) for m in ("claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5") for r in ((1,) if "opus" in m else (1, 2)) for c in cases] + \
               [(c, "C1", m, 1) for m in ("claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5") for c in cases]
        fn = lambda j: single(client, *j, raw, lock)
    else:
        raw = OUT / "s3_raw.jsonl"; key = lambda d: (d["case_id"], d["cond"], d["model"], d["run"])
        jobs = [(c, "N", m, 1) for m in ("claude-haiku-5-5", "claude-sonnet-5-5") for c in cases]
        fn = lambda j: q3.one(client, *j, raw, lock)
    done = set()
    if raw.exists():
        for l in raw.read_text().splitlines(): done.add(key(json.loads(l)))
    jobs = [j for j in jobs if (j[0]["case_id"], j[1], j[2], j[3]) not in done]
    if limit: jobs = jobs[:limit]
    print(mode, len(jobs), "runs to do", flush=True)
    def work(j):
        if cost[0] > (7.5 if mode == 'c0c1' else 3.0): return
        tin, tout = fn(j); p = PRICE[j[2]]
        with lock: cost[0] += tin / 1e6 * p[0] + tout / 1e6 * p[1]
    with ThreadPoolExecutor(max_workers=4) as ex: list(ex.map(work, jobs))
    print(f"done {mode}; approx cost USD {cost[0]:.3f}", flush=True)

if __name__ == "__main__":
    main()
