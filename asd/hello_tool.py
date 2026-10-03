"""Hello tool: exposes one existing asd function (ToyOracle.run) to Omnigent."""
from .oracle import ToyOracle


def toy_oracle_run(x: float, seed: int = 0) -> dict:
    """Run one toy experiment at x in [0,1] and return {x, y, cost}."""
    return ToyOracle(seed).run(x)
