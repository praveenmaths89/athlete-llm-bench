"""Read-only SQL over the release view (SQLite, in memory): tables tests and trials."""
import csv, re, sqlite3, threading
from lcb.config import RELEASE_TESTS, RELEASE_TRIALS

SCHEMA_TEXT = (
    "Table tests (one row per athlete test, football countermovement jump; same-day tests are merged):\n"
    "  athlete TEXT (pseudonymous id), sex TEXT ('Male'|'Female'), test_index INTEGER (1 = first test of that athlete, in date order), test_date TEXT (YYYY-MM-DD),\n"
    "  days_since_prev INTEGER (NULL for the first test), age_years REAL, age_band TEXT ('<12','12-14','15-17','18-20','21-24','25+'), height_cm REAL (may be NULL), body_mass_kg REAL,\n"
    "  n_trials INTEGER, jump_mean_cm REAL (impulse-momentum jump height, mean of the trials: this is the test's jump height), jump_best_cm REAL (best trial), jump_sd_cm REAL (SD between trials, NULL if one trial).\n"
    "Table trials (one row per trial): athlete TEXT, test_index INTEGER, trial_no INTEGER, jump_height_cm REAL.\n"
    "Only SELECT statements are allowed; results are limited to 200 rows."
)
_FORBIDDEN = re.compile(r"\b(insert|update|delete|drop|alter|create|attach|detach|pragma|replace|vacuum)\b", re.I)
TEST_COLS = ["athlete", "sex", "test_index", "test_date", "days_since_prev", "age_years", "age_band", "height_cm", "body_mass_kg", "n_trials", "jump_mean_cm", "jump_best_cm", "jump_sd_cm"]


def _v(x, kind):
    if x in ("", None): return None
    return {"i": int, "f": float, "s": str}[kind](x) if kind != "i" else int(float(x))


class Db:
    def __init__(self, tests=RELEASE_TESTS, trials=RELEASE_TRIALS):
        self.con = sqlite3.connect(":memory:", check_same_thread=False); self.lock = threading.Lock()
        self.con.execute("CREATE TABLE tests (athlete TEXT, sex TEXT, test_index INTEGER, test_date TEXT, days_since_prev INTEGER, age_years REAL, age_band TEXT, height_cm REAL, body_mass_kg REAL, n_trials INTEGER, jump_mean_cm REAL, jump_best_cm REAL, jump_sd_cm REAL)")
        kinds = dict(athlete="s", sex="s", test_index="i", test_date="s", days_since_prev="i", age_years="f", age_band="s", height_cm="f", body_mass_kg="f", n_trials="i", jump_mean_cm="f", jump_best_cm="f", jump_sd_cm="f")
        self.con.executemany("INSERT INTO tests VALUES (" + ",".join("?" * 13) + ")", [tuple(_v(r[c], kinds[c]) for c in TEST_COLS) for r in csv.DictReader(open(tests))])
        self.con.execute("CREATE TABLE trials (athlete TEXT, test_index INTEGER, trial_no INTEGER, jump_height_cm REAL)")
        self.con.executemany("INSERT INTO trials VALUES (?,?,?,?)", [(r["athlete"], int(r["test_index"]), int(r["trial_no"]), float(r["jump_height_cm"])) for r in csv.DictReader(open(trials))])
        self.con.commit(); self.con.execute("PRAGMA query_only = ON")

    def query(self, sql: str, limit: int = 200) -> dict:
        q = sql.strip().rstrip(";")
        if ";" in q or not re.match(r"^(select|with)\b", q, re.I) or _FORBIDDEN.search(q):
            return {"error": "only a single read-only SELECT statement is allowed"}
        try:
            with self.lock:
                cur = self.con.execute(q); cols = [c[0] for c in cur.description]; rows = cur.fetchmany(limit + 1)
        except sqlite3.Error as e:
            return {"error": f"sql error: {e}"}
        return {"columns": cols, "rows": [list(r) for r in rows[:limit]], "truncated": len(rows) > limit}
