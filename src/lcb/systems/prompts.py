from lcb.benchmark.schema import ANSWER_INSTRUCTIONS
from lcb.tools.sql_tool import SCHEMA_TEXT

BANDS = "Centile bands: <P3, P3-P10, P10-P25, P25-P50, P50-P75, P75-P90, P90-P97, >P97 (centile below 3, 3 to 10, 10 to 25, 25 to 50, 50 to 75, 75 to 90, 90 to 97, above 97)."
NOISE_RULE = "Measurement noise: a change in a test's jump height counts as a real change only if its absolute size exceeds the cohort 95% reliable change (males {m} cm, females {f} cm); otherwise it is within measurement noise."
