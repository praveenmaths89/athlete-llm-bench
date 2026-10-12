"""Quick accuracy summary of cached runs: by system x model and by family."""
import json, glob, collections, sys
from lcb.config import ROOT

def load(pattern="*.jsonl", split=None):
    rows = []
    for f in sorted(glob.glob(str(ROOT / "runs" / pattern))):
        for l in open(f):
            d = json.loads(l)
            if split is None or d["split"] == split: rows.append(d)
    return rows

def table(rows):
    g = collections.defaultdict(list)
    for r in rows: g[(r["system"], r["model"])].append(r)
    fam = sorted({r["family"] for r in rows})
    print(f"{'system/model':16s} {'n':>4s} {'acc':>5s} " + " ".join(f"{f:>5s}" for f in fam) + "   $/q   turns  err")
    for (s, m), v in sorted(g.items()):
        a = sum(r["score"]["pass"] for r in v) / len(v)
        by = [sum(r["score"]["pass"] for r in v if r["family"] == f) / max(1, sum(r["family"] == f for r in v)) for f in fam]
        print(f"{s+'/'+m:16s} {len(v):4d} {100*a:4.0f}% " + " ".join(f"{100*x:4.0f}%" for x in by) + f"  {sum(r['cost'] for r in v)/len(v):.4f} {sum(r['turns'] for r in v)/len(v):5.1f}  {sum(r['error'] is not None for r in v)}")

if __name__ == "__main__":
    table(load(split=sys.argv[1] if len(sys.argv) > 1 else None))
