"""Toy oracle: noisy 1-D response with a hidden optimum; deterministic given seed."""
import math
import random

from .replay import BudgetExceeded


class ToyOracle:
    def __init__(self, seed=0, noise=0.02, hit_threshold=0.9, budget=10**9):
        rng = random.Random(seed)
        self.x_star = rng.uniform(0.15, 0.85)
        self.noise, self.hit_threshold = noise, hit_threshold
        self._rng = random.Random(seed + 1)
        self.spent, self.budget = 0, budget

    def true(self, x):
        return math.exp(-((x - self.x_star) ** 2) / 0.02)

    def run(self, x):
        if self.spent >= self.budget:
            raise BudgetExceeded(f"budget {self.budget} exhausted")
        self.spent += 1
        y = self.true(x) + self._rng.gauss(0, self.noise)
        return {"x": float(x), "y": float(y), "cost": 1}

    def is_hit(self, y):
        return y >= self.hit_threshold

    def is_true_hit(self, x):
        """Hit judged on the noise-free value (ADR-001)."""
        return self.true(x) >= self.hit_threshold
