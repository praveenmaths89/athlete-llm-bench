"""Sensitivity re-run (declared after the final grid): rerun the answers that ended without a valid answer because of a harness cap
(output budget 4000 tokens for system A, 8 turns for system C) with larger caps (16000 tokens, 16 turns). Results go to runs_sensitivity/ and are reported next to the main grid.

usage: python -m lcb.sensitivity
"""
import json, glob, collections
from concurrent.futures import ThreadPoolExecutor
from lcb.config import ROOT
from lcb.llm.client import Claude, Budget
from lcb.tools.registry import Toolbox
from lcb.benchmark.score import score
from lcb.systems import a_context, c_agent

OUT = ROOT / "runs_sensitivity"


def main():
    OUT.mkdir(exist_ok=True); qs = {q["qid"]: q for q in (json.loads(l) for l in open(ROOT / "data/benchmark/questions.jsonl"))}
    todo = []
    for f in sorted(glob.glob(str(ROOT / "runs/*_*.jsonl"))):
        for l in open(f):
            r = json.loads(l)
            if r["answer"] is None and r["stop"] in ("max_tokens", "max_turns") and r["system"] in ("A", "A+", "C"): todo.append(r)
    print(len(todo), "capped runs to rerun:", dict(collections.Counter((r["system"], r["model"], r["stop"]) for r in todo)))
    llm = Claude(Budget(3.0)); out = []

    def work(r):
        q = qs[r["qid"]]
        if r["system"] in ("A", "A+"): res = a_context.run(llm, r["model"], q["text"], with_noise=(r["system"] == "A+"), max_tokens=16000)
        else: res = c_agent.run(llm, r["model"], q["text"], Toolbox(), max_turns=16)
        sc = score(q, res.answer)
        return dict(qid=r["qid"], family=r["family"], template=r["template"], split=r["split"], system=r["system"], model=r["model"], rep=r["rep"], answer=res.answer, note=res.note, score=sc, in_tok=res.in_tok, out_tok=res.out_tok, cost=res.cost, seconds=round(res.seconds, 2), turns=res.turns, stop=res.stop, error=res.error, original_stop=r["stop"])
    with ThreadPoolExecutor(max_workers=4) as ex: out = list(ex.map(work, todo))
    with open(OUT / "capped_reruns.jsonl", "w") as fh:
        for o in out: fh.write(json.dumps(o) + "\n")
    ok = collections.Counter((o["system"], o["model"], o["score"]["pass"], o["stop"]) for o in out)
    for k, v in sorted(ok.items()): print(k, v)
    print("cost USD %.3f" % sum(o["cost"] for o in out))


if __name__ == "__main__":
    main()
