"""Step 1b amendment A2: grounding test. C0 bare payload vs C1 payload with cohort evidence. Real pairs, no ids/dates."""
import csv, json, random, sys, time, collections, os, statistics as st
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import anthropic
from lcb.tools.centile_tool import centile

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "data_private/real_pairs/quick_test2"; OUT.mkdir(parents=True, exist_ok=True)
MODELS = ["claude-haiku-5-5", "claude-opus-5-5"]; RUNS = 3; VAR = "Jump_Height_Imp-Mom_"
TE = json.loads((ROOT / "results/typical_error.json").read_text())
SYSTEM = "You are assisting a strength and conditioning coach. Answer only with the requested JSON."
SCHEMA = {"type": "object", "additionalProperties": False,
          "required": ["jump_change_is", "centile_change_reason", "noise_threshold_cm", "note"],
          "properties": {"jump_change_is": {"type": "string", "enum": ["real", "within_measurement_noise", "cannot_tell"]},
                         "centile_change_reason": {"type": "string", "enum": ["jump_change", "age_drift", "both", "none"]},
                         "noise_threshold_cm": {"type": "number"}, "note": {"type": "string"}}}
INSTR = ("\nReturn JSON with: jump_change_is (real | within_measurement_noise | cannot_tell), centile_change_reason "
         "(what mainly caused the centile change: jump_change | age_drift | both | none), noise_threshold_cm (the smallest "
         "change in cm you treated as a real change; 0 if you used none), note (at most 60 words, how the athlete is doing).")

def load_env():
    for line in (ROOT / ".env").read_text().splitlines():
        if line.strip() and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1); os.environ.setdefault(k.strip(), v.strip())

def build_cases():
    P = [p for p in csv.DictReader(open(ROOT / "data_private/real_pairs/premise_check_v2.csv"))]
    gray = [p for p in P if p["tracking"] == "within_noise" and abs(float(p["dv"])) >= 2.0]
    ctrl = [p for p in P if p["tracking"] in ("beyond_up", "beyond_down")]
    rng = random.Random(7); out = []
    for name, pool, n in (("gray_zone", gray, 12), ("reliable_change", ctrl, 6)):
        pool = sorted(pool, key=lambda p: (p["pid"], p["age_a"])); rng.shuffle(pool)
        print(name, "available", len(pool), "using", min(n, len(pool)))
        for i, p in enumerate(pool[:n]):
            a, b, va, vb = float(p["age_a"]), float(p["age_b"]), float(p["v_a"]), float(p["v_b"])
            drift = centile("CMJ", p["sex"], VAR, b, va).centile - centile("CMJ", p["sex"], VAR, a, va).centile
            total = float(p["c_b"]) - float(p["c_a"]); rest = total - drift
            gold_reason = None if max(abs(drift), abs(rest)) < 2 else ("age_drift" if abs(drift) > abs(rest) else "jump_change")
            gold_change = "within_measurement_noise" if p["tracking"] == "within_noise" else "real"
            out.append(dict(case_id=f"{name}_{i+1}", group=name, sex=p["sex"], age_a=a, age_b=b, months=round(int(p["gap_days"]) / 30.4),
                            v_a=va, v_b=vb, c_a=float(p["c_a"]), c_b=float(p["c_b"]), dv=vb - va, age_drift=round(drift, 1),
                            gold_change=gold_change, gold_reason=gold_reason, rc=TE[p["sex"]]["reliable_change_cm"], sd=TE[p["sex"]]["within_sd_cm"]))
    return out

def payload(c, cond):
    t = (f"Athlete: {c['sex'].lower()}, football player, {c['age_a']:.1f} years at test 1 and {c['age_b']:.1f} years at test 2 ({c['months']} months apart).\n"
         f"Countermovement jump height (impulse-momentum): test 1 = {c['v_a']:.1f} cm, test 2 = {c['v_b']:.1f} cm.\n"
         f"Centile in the age- and sex-matched reference group: test 1 = P{c['c_a']:.0f}, test 2 = P{c['c_b']:.0f}.\n")
    if cond == "C1":
        t += (f"Cohort evidence (same test, same {c['sex'].lower()} football cohort): trial-to-trial variation within one test is about {c['sd']:.1f} cm (SD), "
              f"so a change in the average of a test smaller than {c['rc']:.1f} cm is within measurement noise (95% reliable change). "
              f"Holding jump height constant at the test 1 value, the centile would have changed by {c['age_drift']:+.0f} points from the age difference alone.\n")
    return t + "Question: How is this athlete doing?" + INSTR

def main():
    load_env(); client = anthropic.Anthropic(); cases = build_cases()
    (OUT / "cases.json").write_text(json.dumps([dict(c, payload_C0=payload(c, "C0"), payload_C1=payload(c, "C1")) for c in cases], indent=1))
    raw = OUT / "raw.jsonl"; done = set()
    if raw.exists():
        for l in raw.read_text().splitlines(): d = json.loads(l); done.add((d["case_id"], d["cond"], d["model"], d["run"]))
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None; n = 0; cost = 0.0
    price = {"claude-haiku-5-5": (0.10, 0.50), "claude-opus-5-5": (4.0, 20.0)}
    for c in cases:
        for cond in ("C0", "C1"):
            for m in MODELS:
                for run in range(1, RUNS + 1):
                    if (c["case_id"], cond, m, run) in done: continue
                    if limit is not None and n >= limit: print("limit reached"); return
                    r = None
                    for attempt in range(3):
                        try:
                            r = client.messages.create(model=m, max_tokens=4000, system=SYSTEM,
                                    output_config={"effort": "medium", "format": {"type": "json_schema", "schema": SCHEMA}},
                                    messages=[{"role": "user", "content": payload(c, cond)}]); break
                        except anthropic.APIStatusError as e:
                            print("API error", e.status_code, str(e)[:300]); time.sleep(5 * (attempt + 1))
                    if r is None: sys.exit("aborting: repeated API errors")
                    if r.model != m: sys.exit(f"aborting: requested {m} got {r.model}")
                    text = "".join(b.text for b in r.content if b.type == "text"); u = r.usage
                    cost += u.input_tokens / 1e6 * price[m][0] + u.output_tokens / 1e6 * price[m][1]
                    try: parsed = json.loads(text)
                    except Exception: parsed = None
                    with open(raw, "a") as fh:
                        fh.write(json.dumps(dict(case_id=c["case_id"], group=c["group"], cond=cond, model=r.model, run=run, stop_reason=r.stop_reason,
                                                 in_tok=u.input_tokens, out_tok=u.output_tokens, parsed=parsed, text=text)) + "\n")
                    n += 1
                    if cost > 3.0: sys.exit("aborting: spend cap USD 3")
    print(f"done; {n} new calls; approx cost USD {cost:.3f}")

if __name__ == "__main__":
    main()
