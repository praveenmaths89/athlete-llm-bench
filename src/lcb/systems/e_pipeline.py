"""System E: fixed code computes an evidence bundle for the athlete named in the question; one LLM call writes the answer (no tools, no agent loop)."""
import re, time
from lcb.config import MODELS
from lcb.benchmark.schema import ANSWER_SCHEMA, ANSWER_INSTRUCTIONS
from lcb.tools import noise
from lcb.systems.base import Result, parse_final
from lcb.systems.prompts import BANDS, NOISE_RULE

ATHLETE = re.compile(r"\bA[0-9a-f]{10}\b")


def bundle(toolbox, question: str) -> str:
    m = ATHLETE.search(question)
    if not m: return "No athlete id was found in the question."
    a = m.group(0)
    rows = toolbox.db.query(f"SELECT test_index, test_date, age_years, jump_mean_cm, jump_best_cm, n_trials, days_since_prev FROM tests WHERE athlete='{a}' ORDER BY test_index")["rows"]
    if not rows: return f"Athlete {a} is not in the database (no tests)."
    lines = [f"Athlete {a}: {len(rows)} test(s)."]
    for idx, date, age, mean, best, ntr, gap in rows:
        c = toolbox.centile(a, idx); tr = [r[0] for r in toolbox.db.query(f"SELECT jump_height_cm FROM trials WHERE athlete='{a}' AND test_index={idx} ORDER BY trial_no")["rows"]]
        lines.append(f"test {idx}: date {date}, age {age}, mean jump {mean} cm, best trial {best} cm, {ntr} trial(s) {tr}, days since previous {gap}, centile {c['centile']} band {c['band']} norm {c['norm_label']}")
    for (i, *_), (j, *_) in zip(rows, rows[1:]):
        t = toolbox.tracking(a, i, j); lines.append(f"change test {i}->{j}: {t['change_cm']} cm, threshold {t['reliable_change_threshold_cm']} cm, label {t['label']}")
    if len(rows) > 2:
        t = toolbox.tracking(a, rows[0][0], rows[-1][0]); lines.append(f"change first->latest: {t['change_cm']} cm, label {t['label']}")
    return "\n".join(lines)


def run(llm, model_key: str, question: str, toolbox) -> Result:
    t0 = time.time(); ev = bundle(toolbox, question)
    system = ANSWER_INSTRUCTIONS + "\n\n" + BANDS + "\n" + NOISE_RULE.format(m=noise.reliable_change_cm("Male"), f=noise.reliable_change_cm("Female")) + "\nEvidence computed by code is given with the question; use only it."
    r, cost = llm.create(MODELS[model_key], system, [{"role": "user", "content": f"EVIDENCE:\n{ev}\n\nQUESTION: {question}"}], schema=ANSWER_SCHEMA)
    text = "".join(b.text for b in r.content if b.type == "text"); ans, note = parse_final(text)
    return Result(ans, note, [{"kind": "code", "name": "bundle", "result": ev}, {"kind": "llm", "agent": "single", "turn": 0, "stop": r.stop_reason, "in": r.usage.input_tokens, "out": r.usage.output_tokens, "tool_calls": []}],
                  r.usage.input_tokens, r.usage.output_tokens, cost, time.time() - t0, 1, r.stop_reason)
