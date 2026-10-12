"""Deterministic scoring against the gold answers. A question passes when every gold field matches (abstain included)."""
TOL = {"value_cm": 0.06, "change_cm": 0.06, "age_years": 0.01, "share": 0.011}
EXACT = {"days", "count", "text", "centile_band", "yes_no", "verdict", "trend"}


def field_ok(name, gold, got) -> bool:
    if got is None: return False
    if name in TOL:
        try: return abs(float(got) - float(gold)) <= TOL[name]
        except (TypeError, ValueError): return False
    if name == "abstain": return bool(got) == bool(gold)
    return str(got).strip() == str(gold).strip()


def score(q: dict, answer: dict | None) -> dict:
    if not answer: return {"pass": False, "fields": {}, "reason": "unparsed"}
    gold = q["gold"]; fields = {}
    for k, v in gold.items(): fields[k] = field_ok(k, v, answer.get(k))
    if "abstain" not in gold: fields["no_abstain"] = not answer.get("abstain", False)
    return {"pass": all(fields.values()), "fields": fields, "reason": "ok"}
