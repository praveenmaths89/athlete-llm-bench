"""Thin Claude client: loads the key from .env, checks the responding model, retries, tracks cost, stops cleanly on empty credit."""
import json, os, threading, time
from dataclasses import dataclass
import anthropic
from lcb.config import ROOT, EFFORT, call_cost


class CreditExhausted(RuntimeError):
    pass


class BudgetExceeded(RuntimeError):
    pass


class Budget:
    """Thread-safe spend guard shared by all calls of one run."""
    def __init__(self, limit_usd: float):
        self.limit, self.spent, self.lock = limit_usd, 0.0, threading.Lock()
    def charge(self, usd: float):
        with self.lock:
            self.spent += usd
            if self.spent > self.limit: raise BudgetExceeded(f"budget {self.limit} USD exceeded")


def load_env():
    f = ROOT / ".env"
    if f.exists():
        for line in f.read_text().splitlines():
            if line.strip() and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1); os.environ.setdefault(k.strip(), v.strip())


@dataclass
class Reply:
    model: str
    stop_reason: str
    text: str
    parsed: dict | None
    in_tok: int
    out_tok: int
    cost: float


class Claude:
    def __init__(self, budget: Budget | None = None):
        load_env(); self.client = anthropic.Anthropic(); self.budget = budget

    def create(self, model, system, messages, tools=None, schema=None, effort=EFFORT, max_tokens=4000):
        """One Messages API call. Returns (response, cost_usd). `system` may be a string or a list of blocks (for prompt caching)."""
        cfg = {"effort": effort}
        if schema: cfg["format"] = {"type": "json_schema", "schema": schema}
        kw = dict(model=model, max_tokens=max_tokens, system=system, messages=messages, output_config=cfg)
        if tools: kw["tools"] = tools
        for attempt in range(4):
            try:
                r = self.client.messages.create(**kw); break
            except anthropic.BadRequestError as e:
                if "credit balance" in str(e).lower(): raise CreditExhausted(str(e)) from e
                raise
            except anthropic.APIStatusError:
                if attempt == 3: raise
                time.sleep(4 * (attempt + 1))
        if r.model != model: raise RuntimeError(f"requested {model} but the API answered with {r.model}")
        cost = call_cost(model, r.usage)
        if self.budget: self.budget.charge(cost)
        return r, cost

    def ask(self, model: str, system, user: str, schema: dict | None = None, effort: str = EFFORT, max_tokens: int = 4000) -> Reply:
        r, cost = self.create(model, system, [{"role": "user", "content": user}], None, schema, effort, max_tokens)
        text = "".join(b.text for b in r.content if b.type == "text")
        try: parsed = json.loads(text)
        except Exception: parsed = None
        return Reply(r.model, r.stop_reason, text, parsed, r.usage.input_tokens, r.usage.output_tokens, cost)
