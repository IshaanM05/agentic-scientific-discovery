"""LLM access with cache and deterministic offline stub.

Real path only if use_real=True and ANTHROPIC_API_KEY is set. Otherwise the stub runs.
"""
import json
import os
import random

from .cache import Cache

MODEL = "claude-sonnet-5-5"


class LLM:
    def __init__(self, cache=None, use_real=False, seed=0):
        self.cache, self.seed = cache or Cache(), seed
        self.real = use_real and bool(os.environ.get("ANTHROPIC_API_KEY"))
        self.model = MODEL if self.real else "stub"

    def complete(self, prompt: str) -> dict:
        fn = (lambda: self._real(prompt)) if self.real else (lambda: self._stub(prompt))
        return self.cache.get_or_call(prompt, self.model, self.seed, fn)

    def _stub(self, prompt):
        r = random.Random(f"{prompt}|{self.seed}")
        return {"guesses": [round(r.uniform(0, 1), 3) for _ in range(3)]}

    def _real(self, prompt):
        import anthropic
        c = anthropic.Anthropic()
        m = c.messages.create(model=self.model, max_tokens=300, messages=[{
            "role": "user", "content": prompt + '\nReply only JSON {"guesses":[3 floats in 0..1]}'}])
        return json.loads(m.content[0].text)
