"""Run one system with one model on a split; resumable, budget-capped, every result cached as JSONL.

usage: python -m lcb.runner --system C --model haiku --split dev --reps 1 [--limit N] [--budget 2.0]
"""
import argparse, json, threading
from concurrent.futures import ThreadPoolExecutor
from lcb.config import ROOT, RUNS_DIR
from lcb import tracing
from lcb.llm.client import Claude, Budget, BudgetExceeded, CreditExhausted
from lcb.tools.registry import Toolbox
from lcb.benchmark.score import score
from lcb.systems import a_context, c_agent, d_multi, e_pipeline

RUNS = RUNS_DIR
SYSTEMS = {"A": a_context, "A+": a_context, "C": c_agent, "D": d_multi, "E": e_pipeline}


def load_questions(split, half=False):
    qs = [json.loads(l) for l in open(ROOT / "data/benchmark/questions.jsonl")]
    qs = [q for q in qs if split == "all" or q["split"] == split]
    if half:    # fixed stratified half: within each family, every second question in id order
        keep = []
        for fam in sorted({q["family"] for q in qs}):
            keep += [q for i, q in enumerate(sorted((q for q in qs if q["family"] == fam), key=lambda q: q["qid"])) if i % 2 == 0]
        qs = keep
    return qs


def run(system, model, split, reps, limit, budget_usd, workers=4, half=False):
    out = RUNS / f"{system}_{model}.jsonl"; RUNS.mkdir(exist_ok=True); done = set()
    if out.exists():
        for l in out.read_text().splitlines():
            d = json.loads(l)
            if d.get("error") is None: done.add((d["qid"], d["rep"]))
    qs = load_questions(split, half)
    if system == "E": qs = [q for q in qs if not q["tags"].get("cohort")]      # E has per-athlete evidence only: cohort questions are not applicable
    jobs = [(q, r) for q in qs for r in range(1, reps + 1) if (q["qid"], r) not in done]
    if limit: jobs = jobs[:limit]
    print(f"{system}/{model}/{split}: {len(jobs)} runs to do"); budget = Budget(budget_usd); llm = Claude(budget); lock = threading.Lock(); stop = threading.Event(); n = [0]
    mod = SYSTEMS[system]

    def work(j):
        q, rep = j
        if stop.is_set(): return
        try:
            tb = Toolbox(); res = mod.run(llm, model, q["text"], with_noise=(system == "A+")) if system in ("A", "A+") else mod.run(llm, model, q["text"], tb)
        except (BudgetExceeded, CreditExhausted) as e:
            stop.set(); print("stopping:", e); return
        except Exception as e:
            from lcb.systems.base import Result
            res = Result(error=f"{type(e).__name__}: {e}")
        sc = score(q, res.answer)
        rec = dict(qid=q["qid"], family=q["family"], template=q["template"], split=q["split"], system=system, model=model, rep=rep, answer=res.answer, note=res.note, score=sc,
                   trace=res.trace, in_tok=res.in_tok, out_tok=res.out_tok, cost=res.cost, seconds=round(res.seconds, 2), turns=res.turns, stop=res.stop, error=res.error)
        with lock:
            with open(out, "a") as fh: fh.write(json.dumps(rec) + "\n")
            n[0] += 1
    with ThreadPoolExecutor(max_workers=workers) as ex: list(ex.map(work, jobs))
    print(f"done {n[0]} runs; spent about USD {budget.spent:.3f}")


def main():
    tracing.setup()
    ap = argparse.ArgumentParser(); ap.add_argument("--system", required=True, choices=list(SYSTEMS)); ap.add_argument("--model", required=True, choices=["haiku", "sonnet", "opus"])
    ap.add_argument("--split", default="dev"); ap.add_argument("--reps", type=int, default=1); ap.add_argument("--limit", type=int); ap.add_argument("--budget", type=float, default=2.0); ap.add_argument("--half", action="store_true")
    a = ap.parse_args(); run(a.system, a.model, a.split, a.reps, a.limit, a.budget, half=a.half)


if __name__ == "__main__":
    main()
