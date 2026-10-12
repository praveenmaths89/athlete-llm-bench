"""Answer schema shared by all systems and used by the scorer."""
FIELDS = ["value_cm", "age_years", "days", "count", "share", "text", "centile_band", "yes_no", "change_cm", "verdict", "trend", "abstain"]

ANSWER_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["answer", "note"],
    "properties": {
        "answer": {"type": "object", "additionalProperties": False, "required": FIELDS, "properties": {
            "value_cm": {"type": ["number", "null"]}, "age_years": {"type": ["number", "null"]}, "days": {"type": ["integer", "null"]}, "count": {"type": ["integer", "null"]}, "share": {"type": ["number", "null"], "description": "a fraction between 0 and 1"},
            "text": {"type": ["string", "null"], "description": "an athlete id, a date (YYYY-MM-DD) or a year, when the question asks for one"},
            "centile_band": {"type": ["string", "null"], "description": "one of <P3, P3-P10, P10-P25, P25-P50, P50-P75, P75-P90, P90-P97, >P97"},
            "yes_no": {"anyOf": [{"type": "string", "enum": ["yes", "no"]}, {"type": "null"}]},
            "change_cm": {"type": ["number", "null"]},
            "verdict": {"anyOf": [{"type": "string", "enum": ["real", "within_measurement_noise", "cannot_tell"]}, {"type": "null"}]},
            "trend": {"anyOf": [{"type": "string", "enum": ["better", "worse", "no_reliable_change"]}, {"type": "null"}]},
            "abstain": {"type": "boolean", "description": "true if the question cannot be answered from the data"}}},
        "note": {"type": "string"}}}

ANSWER_INSTRUCTIONS = (
    "Answer the coach's question about the football countermovement-jump data. Return JSON with `answer` and `note`. In `answer` fill only the fields the question asks for and set every other field to null; "
    "set abstain to true (and the other fields to null) when the data cannot answer the question, for example a missing athlete or test, or too little history. "
    "Jump heights are in cm. `note` is at most 40 words."
)
