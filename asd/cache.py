"""On-disk JSON cache for LLM/oracle calls keyed by (prompt, model, seed)."""
import hashlib
import json
import os


def key(prompt: str, model: str, seed: int) -> str:
    return hashlib.sha256(json.dumps([prompt, model, seed]).encode()).hexdigest()


class Cache:
    def __init__(self, path=".cache/calls"):
        self.path = path
        os.makedirs(path, exist_ok=True)

    def get_or_call(self, prompt, model, seed, fn):
        f = os.path.join(self.path, key(prompt, model, seed) + ".json")
        if os.path.exists(f):
            with open(f) as fh:
                return json.load(fh)
        out = fn()
        with open(f, "w") as fh:
            json.dump(out, fh)
        return out
