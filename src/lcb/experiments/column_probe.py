"""Headroom probe (exploratory): can an LLM pick the right column out of ~830 near-duplicate metric columns?"""
import json, sys, threading
from concurrent.futures import ThreadPoolExecutor
from lcb.config import RESULTS, MODELS
from lcb.llm.client import Claude
from lcb.benchmark.column_questions import EXPLICIT, UNDERSPECIFIED

OUT = RESULTS / "probe_columns"
COLUMNS = (OUT / "schema_columns.txt").read_text().splitlines()
SYSTEM = ("You map a coach's request to one column of a VALD ForceDecks results table. Answer only with the requested JSON.\n"
          "Columns (one per line):\n" + "\n".join(COLUMNS))
SCHEMA = {"type": "object", "additionalProperties": False, "required": ["column", "ambiguous", "alternatives"],
          "properties": {"column": {"type": "string"}, "ambiguous": {"type": "boolean"}, "alternatives": {"type": "array", "items": {"type": "string"}}}}
ASK = ("Request: {q}\nReturn JSON: column (the single best column name, copied exactly), ambiguous (true if the request does not determine one column), "
       "alternatives (other plausible columns, empty if none).")

def main(models=("haiku", "sonnet"), runs=2):
    llm = Claude(); raw = OUT / "raw.jsonl"; lock = threading.Lock()
    items = [("explicit", i, q, g) for i, (q, g) in enumerate(EXPLICIT)] + [("underspecified", i, q, g) for i, (q, g) in enumerate(UNDERSPECIFIED)]
    jobs = [(m, k, i, q, g, r) for m in models for (k, i, q, g) in items for r in range(1, runs + 1)]
    def work(j):
        m, k, i, q, g, r = j; out = llm.ask(MODELS[m], SYSTEM, ASK.format(q=q), SCHEMA)
        with lock, open(raw, "a") as fh: fh.write(json.dumps(dict(model=out.model, kind=k, idx=i, request=q, gold=g, run=r, parsed=out.parsed, cost=out.cost, in_tok=out.in_tok)) + "\n")
    with ThreadPoolExecutor(max_workers=4) as ex: list(ex.map(work, jobs))
    print("columns in schema:", len(COLUMNS), "calls:", len(jobs))

if __name__ == "__main__":
    main()
