import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from ll_big_benchmark import run_grid, wboot  # noqa: E402

ARMS = ["Random", "Grad-student OFAT", "LLM-style (no BO)"]


def test_grid_deterministic_across_process_counts():
    a, ta = run_grid([3000], 2, ARMS, budget=12, procs=1)
    b, tb = run_grid([3000], 2, ARMS, budget=12, procs=2)
    c, _ = run_grid([3000], 2, ARMS, budget=12, procs=1)
    assert (ta == tb).all()
    for n in ARMS:
        assert a[n].shape == (1, 2, 13)
        assert np.array_equal(a[n], b[n]) and np.array_equal(a[n], c[n])


def test_wboot_resamples_worlds_not_seeds():
    # 2 worlds, 5 identical seeds each: only world draws vary, so the CI spans the two world means.
    x = np.array([[0.0] * 5, [10.0] * 5])
    lo, hi = wboot(x, n=2000)
    assert (lo, hi) == (0.0, 10.0)
    # seed-level resampling would give a much tighter interval; pooled seeds of one world never mix with the other
    assert wboot(x, np.median, n=2000)[0] in (0.0, 5.0)


def test_wboot_synthetic_effect_and_null():
    rng = np.random.default_rng(1)
    W, S = 60, 20
    world_eff = rng.normal(0, 3, (W, 1))
    pos = 1.5 + world_eff + rng.normal(0, 1, (W, S))
    lo, hi = wboot(pos, n=4000)
    assert lo < pos.mean() < hi and lo > 0                      # clear effect excluded zero
    null = world_eff + rng.normal(0, 1, (W, S))
    lo0, hi0 = wboot(null, n=4000)
    assert lo0 < 0 < hi0 or abs(null.mean()) > 0.5              # interval width reflects world variance
    assert hi0 - lo0 > 1.0                                      # ~ 4*3/sqrt(60) = 1.5, not seed-level 0.1
    assert wboot(pos, n=4000) == (lo, hi)                       # reproducible


def test_wboot_handles_inf():
    x = np.array([[np.inf, 1.0], [2.0, 3.0], [np.inf, np.inf]])
    lo, hi = wboot(x, np.median, n=500)
    assert not np.isnan(lo) and not np.isnan(hi)
