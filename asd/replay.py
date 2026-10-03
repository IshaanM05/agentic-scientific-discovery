"""Replay oracle on steel_strength (ADR-001). Pool = 312 steels, features = 13 composition columns.

Hidden from agents: yield/tensile/elongation until a candidate is run (only yield is ever revealed).
"""
import gzip
import hashlib
import json
import random
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data" / "steel_strength.json.gz"
SHA256 = "e36501d7057cd833223bb8ed9948668b5ac90fd585d29a749f45af51c1d7f6ad"
FEATURES = ["c", "mn", "si", "cr", "ni", "mo", "v", "n", "nb", "co", "w", "al", "ti"]
TARGET = "yield strength"
HIT_THRESHOLD = 2000.0  # MPa


class BudgetExceeded(Exception):
    pass


def load_pool(path=DATA):
    raw = Path(path).read_bytes()
    got = hashlib.sha256(raw).hexdigest()
    if got != SHA256:
        raise ValueError(f"steel_strength sha256 mismatch: {got} != {SHA256}")
    d = json.loads(gzip.decompress(raw))
    cols = d["columns"]
    return [dict(zip(cols, r)) for r in d["data"]]


class ReplayOracle:
    def __init__(self, seed=0, budget=60, ledger_path=None, path=DATA):
        rows = load_pool(path)
        order = list(range(len(rows)))
        random.Random(seed).shuffle(order)
        self._rows = {f"c{i:03d}": rows[j] for i, j in enumerate(order)}
        self.seed, self.budget, self.spent = seed, budget, 0
        self._revealed, self.ledger_path, self.step = {}, ledger_path, 0
        self.hits_by_step = []  # budget_used at each new hit

    def ids(self):
        return list(self._rows)

    def features(self, cid):
        r = self._rows[cid]
        return {k: r[k] for k in FEATURES}

    def is_hit(self, value):
        return value >= HIT_THRESHOLD

    def run(self, cid):
        """Reveal yield strength. 1 experiment on first reveal, free + cached afterwards."""
        if cid not in self._rows:
            raise KeyError(cid)
        if cid in self._revealed:
            return {**self._revealed[cid], "cost": 0}
        if self.spent >= self.budget:
            raise BudgetExceeded(f"budget {self.budget} exhausted")
        self.spent += 1
        v = float(self._rows[cid][TARGET])
        hit = self.is_hit(v)
        res = {"id": cid, "value": v, "is_hit": hit, "cost": 1, "budget_used": self.spent}
        self._revealed[cid] = {k: res[k] for k in ("id", "value", "is_hit", "budget_used")}
        if hit:
            self.hits_by_step.append(self.spent)
        self.step += 1
        if self.ledger_path:
            with open(self.ledger_path, "a") as f:
                f.write(json.dumps({"step": self.step, "id": cid, "value": v, "is_hit": hit,
                                    "budget_used": self.spent}) + "\n")
        return res


def log_llm(path, tokens_in, tokens_out, usd, note=""):
    """LLM spend is logged separately from the experiment budget."""
    with open(path, "a") as f:
        f.write(json.dumps({"tokens_in": tokens_in, "tokens_out": tokens_out, "usd": usd, "note": note}) + "\n")


def experiments_to_k_hits(hits_by_step, k, budget=60):
    """Experiments needed to reach k hits; censored at budget+1."""
    return hits_by_step[k - 1] if len(hits_by_step) >= k else budget + 1


def random_policy(oracle, seed=0):
    order = oracle.ids()
    random.Random(seed).shuffle(order)
    for cid in order:
        try:
            oracle.run(cid)
        except BudgetExceeded:
            break
    return oracle
