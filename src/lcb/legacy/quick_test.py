"""Step 1b (amendment A1): do Claude models read a within-noise centile move as a real change? Real pairs, no ids/dates."""
import csv, json, random, re, sys, time, collections
from pathlib import Path
import anthropic

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "data_private/real_pairs/quick_test"; OUT.mkdir(parents=True, exist_ok=True)
MODELS = ["claude-haiku-5-5", "claude-opus-5-5"]
RUNS = 3
SYSTEM = "You are assisting a strength and conditioning coach. Answer in 3 to 5 sentences."

def load_env():
    for line in (ROOT / ".env").read_text().splitlines():
        if line.strip() and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1); import os; os.environ.setdefault(k.strip(), v.strip())

def select_cases():
    P = list(csv.DictReader(open(ROOT / "data_private/real_pairs/premise_check_v2.csv")))
    pools = {
        "within_noise_centile_down": [p for p in P if p["tracking"] == "within_noise" and p["centile_move"] == "centile_down"],
        "within_noise_centile_up":   [p for p in P if p["tracking"] == "within_noise" and p["centile_move"] == "centile_up"],
        "reliable_gain_centile_up":  [p for p in P if p["tracking"] == "beyond_up" and p["centile_move"] == "centile_up"],
        "reliable_drop_centile_down":[p for p in P if p["tracking"] == "beyond_down" and p["centile_move"] == "centile_down"],
        "within_noise_centile_flat": [p for p in P if p["tracking"] == "within_noise" and p["centile_move"] == "centile_flat"],
    }
    want = {"within_noise_centile_down": 8, "within_noise_centile_up": 4, "reliable_gain_centile_up": 4,
            "reliable_drop_centile_down": 2, "within_noise_centile_flat": 2}
    rng = random.Random(7); cases = []
    for k, n in want.items():
        pool = sorted(pools[k], key=lambda p: (p["pid"], p["age_a"])); rng.shuffle(pool)
        for i, p in enumerate(pool[:n]):
            cases.append(dict(case_id=f"{k}_{i+1}", stratum=k, sex=p["sex"], age_a=p["age_a"], age_b=p["age_b"],
                              months=round(int(p["gap_days"]) / 30.4), v_a=float(p["v_a"]), v_b=float(p["v_b"]),
                              c_a=float(p["c_a"]), c_b=float(p["c_b"])))
    return cases

def payload(c):
    return (f"Athlete: {c['sex'].lower()}, football player, {float(c['age_a']):.1f} years at test 1 and {float(c['age_b']):.1f} years at test 2 "
            f"({c['months']} months apart).\nCountermovement jump height (impulse-momentum): test 1 = {c['v_a']:.1f} cm, test 2 = {c['v_b']:.1f} cm.\n"
            f"Centile in the age- and sex-matched reference group: test 1 = P{c['c_a']:.0f}, test 2 = P{c['c_b']:.0f}.\nQuestion: How is this athlete doing?")

NOISE = re.compile(r"noise|measurement error|typical error|test-to-test|test to test|variab|reliab|within (the )?(normal|typical|expected)|not (a )?(meaningful|significant|real|reliable)|negligible|essentially (unchanged|stable|the same)|margin of error|natural fluctuation|day-to-day", re.I)
CHANGE = re.compile(r"declin|deteriorat|worsen|regress|dropped|decreas|fell|falling|improv|progress|gain|better|worse|slipp|decline", re.I)
AGE = re.compile(r"\bage\b|aging|ageing|grow|matur|peer|puberty|pubertal|older|development|growth", re.I)

def main():
    load_env(); client = anthropic.Anthropic()
    cases = select_cases()
    (OUT / "cases.json").write_text(json.dumps([dict(c, payload=payload(c)) for c in cases], indent=1))
    print(len(cases), "cases:", collections.Counter(c["stratum"] for c in cases), collections.Counter(c["sex"] for c in cases))
    raw = OUT / "raw.jsonl"; done = set()
    if raw.exists():
        for l in raw.read_text().splitlines(): d = json.loads(l); done.add((d["case_id"], d["model"], d["run"]))
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None; n = 0; cost = 0.0
    price = {"claude-haiku-5-5": (0.10, 0.50), "claude-opus-5-5": (4.0, 20.0)}
    for c in cases:
        for m in MODELS:
            for run in range(1, RUNS + 1):
                if (c["case_id"], m, run) in done: continue
                if limit is not None and n >= limit: return
                for attempt in range(3):
                    try:
                        r = client.messages.create(model=m, max_tokens=4000, system=SYSTEM,
                                                   output_config={"effort": "medium"},
                                                   messages=[{"role": "user", "content": payload(c)}]); break
                    except anthropic.APIStatusError as e:
                        print("API error", e.status_code, str(e)[:200]); time.sleep(5 * (attempt + 1)); r = None
                if r is None: sys.exit("aborting: repeated API errors")
                if r.model != m: sys.exit(f"aborting: requested {m} but got {r.model}")
                text = "".join(b.text for b in r.content if b.type == "text")
                u = r.usage; cost += u.input_tokens / 1e6 * price[m][0] + u.output_tokens / 1e6 * price[m][1]
                rec = dict(case_id=c["case_id"], stratum=c["stratum"], model=r.model, run=run, stop_reason=r.stop_reason,
                           in_tok=u.input_tokens, out_tok=u.output_tokens, text=text)
                with open(raw, "a") as fh: fh.write(json.dumps(rec) + "\n")
                n += 1
                if cost > 2.0: sys.exit("aborting: spend cap USD 2 reached")
    print(f"done; {n} new calls; approx cost this run USD {cost:.3f}")

if __name__ == "__main__":
    main()
