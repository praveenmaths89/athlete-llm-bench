"""Designed sweep of the output cap for system A on the cohort-level questions (declared after the grid, as a follow-up to the sensitivity re-run).
Caps 2000, 4000, 8000 and 16000 tokens; Haiku 3 repeats, Sonnet 1; all 12 cohort-level questions. Results: runs_sensitivity/capsweep.jsonl and results/final_grid/capsweep.csv

usage: python -m lcb.capsweep
"""
import json, collections
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
from lcb.config import ROOT
from lcb.llm.client import Claude, Budget
from lcb.benchmark.score import score
from lcb.systems import a_context

CAPS = (2000, 4000, 8000, 16000)


def main():
    qs = [q for q in (json.loads(l) for l in open(ROOT / "data/benchmark/questions.jsonl")) if q["tags"].get("cohort")]
    llm = Claude(Budget(3.0)); jobs = [(q, m, r, c) for q in qs for m, reps in (("haiku", 3), ("sonnet", 1)) for r in range(1, reps + 1) for c in CAPS]
    print(len(qs), "cohort questions;", len(jobs), "runs")

    def work(j):
        q, m, r, c = j; res = a_context.run(llm, m, q["text"], with_noise=False, max_tokens=c); sc = score(q, res.answer)
        return dict(qid=q["qid"], model=m, rep=r, cap=c, no_answer=res.answer is None, ok=bool(sc["pass"]), out_tok=res.out_tok, cost=res.cost, stop=res.stop)
    with ThreadPoolExecutor(max_workers=4) as ex: rows = list(ex.map(work, jobs))
    with open(ROOT / "runs_sensitivity/capsweep.jsonl", "w") as fh:
        for r in rows: fh.write(json.dumps(r) + "\n")
    df = pd.DataFrame(rows); t = df.groupby(["model", "cap"]).agg(runs=("ok", "size"), correct=("ok", "mean"), no_answer=("no_answer", "mean"), mean_out_tokens=("out_tok", "mean"), cost_per_q=("cost", "mean")).round(3).reset_index()
    t.to_csv(ROOT / "results/final_grid/capsweep.csv", index=False); print(t.to_string(index=False)); print("total cost USD %.2f" % df.cost.sum())


if __name__ == "__main__":
    main()
