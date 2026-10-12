"""The tools offered to the agent systems (C, D) and used by the fixed-code system (E). All deterministic and read-only."""
import json
from lcb.config import TEST_TYPE, VARIABLE
from lcb.tools import noise
from lcb.tools.centile_tool import centile
from lcb.tools.sql_tool import Db, SCHEMA_TEXT

TOOL_DEFS = [
    {"name": "sql", "description": "Run a read-only SQL SELECT on the athlete test table. " + SCHEMA_TEXT,
     "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    {"name": "centile", "description": "Centile of one stored test in the age- and sex-matched reference group (published GAMLSS grid). Returns centile, band and norm label; the label is no_norm when the age is outside the grid, and the band is <P3 or >P97 at the edges.",
     "input_schema": {"type": "object", "properties": {"athlete": {"type": "string"}, "test_index": {"type": "integer"}}, "required": ["athlete", "test_index"]}},
    {"name": "tracking", "description": "Compare two stored tests of one athlete: change in jump height (cm), the cohort 95% reliable-change threshold for that sex, and a label: within_noise, beyond_noise or insufficient_history.",
     "input_schema": {"type": "object", "properties": {"athlete": {"type": "string"}, "from_index": {"type": "integer"}, "to_index": {"type": "integer"}}, "required": ["athlete", "from_index", "to_index"]}},
]


class Toolbox:
    def __init__(self, db: Db | None = None):
        self.db = db or Db(); self.calls: list[dict] = []

    def _row(self, athlete: str, idx: int):
        r = self.db.query(f"SELECT sex, age_years, jump_mean_cm, days_since_prev FROM tests WHERE athlete = '{athlete.replace(chr(39), '')}' AND test_index = {int(idx)}")
        return r["rows"][0] if r.get("rows") else None

    def call(self, name: str, args: dict) -> dict:
        try:
            if name == "sql": out = self.db.query(args["query"])
            elif name == "centile": out = self.centile(args["athlete"], args["test_index"])
            elif name == "tracking": out = self.tracking(args["athlete"], args["from_index"], args["to_index"])
            else: out = {"error": f"unknown tool {name}"}
        except Exception as e:  # tool errors are returned to the model, never raised
            out = {"error": f"{type(e).__name__}: {e}"}
        self.calls.append({"name": name, "args": args, "result": out}); return out

    def centile(self, athlete: str, test_index: int) -> dict:
        r = self._row(athlete, test_index)
        if r is None: return {"error": "no such test", "athlete": athlete, "test_index": test_index}
        sex, age, val, _ = r; c = centile(TEST_TYPE, sex, VARIABLE, age, val)
        return {"athlete": athlete, "test_index": test_index, "sex": sex, "age_years": age, "jump_height_cm": val,
                "centile": None if c.centile is None else round(c.centile, 1), "band": c.band, "norm_label": c.norm_label}

    def tracking(self, athlete: str, from_index: int, to_index: int) -> dict:
        a, b = self._row(athlete, from_index), self._row(athlete, to_index)
        if a is None or b is None: return {"athlete": athlete, "label": "insufficient_history", "reason": "one of the two tests does not exist"}
        if from_index == to_index: return {"athlete": athlete, "label": "insufficient_history", "reason": "same test twice"}
        sex = a[0]; rc = noise.reliable_change_cm(sex); d = round(b[2] - a[2], 2)
        return {"athlete": athlete, "from_index": from_index, "to_index": to_index, "change_cm": d, "reliable_change_threshold_cm": rc,
                "label": "within_noise" if abs(d) <= rc else "beyond_noise", "noise_basis": noise.noise_basis(sex)}


def dumps(x) -> str: return json.dumps(x, separators=(",", ":"))
