import random

import pytest

from asd import replay as R


def test_pool_and_hits():
    rows = R.load_pool()
    assert len(rows) == 312
    assert sum(r[R.TARGET] >= R.HIT_THRESHOLD for r in rows) == 15


def test_sha_mismatch_fails(tmp_path):
    p = tmp_path / "x.gz"
    p.write_bytes(b"bad")
    with pytest.raises(ValueError):
        R.load_pool(p)


def test_features_hide_targets():
    o = R.ReplayOracle(0)
    f = o.features(o.ids()[0])
    assert set(f) == set(R.FEATURES) and len(f) == 13


def test_budget_and_cache(tmp_path):
    o = R.ReplayOracle(0, budget=3, ledger_path=tmp_path / "l.jsonl")
    a = o.ids()
    r1 = o.run(a[0])
    r2 = o.run(a[0])
    assert r1["cost"] == 1 and r2["cost"] == 0 and o.spent == 1 and r1["value"] == r2["value"]
    o.run(a[1])
    o.run(a[2])
    with pytest.raises(R.BudgetExceeded):
        o.run(a[3])
    assert o.run(a[0])["cost"] == 0
    assert len((tmp_path / "l.jsonl").read_text().splitlines()) == 3


def test_deterministic_fresh_state():
    def traj(seed):
        o = R.random_policy(R.ReplayOracle(seed), seed)
        return list(o.hits_by_step), o.spent
    assert traj(3) == traj(3)
    f1 = [R.ReplayOracle(1).features(c) for c in R.ReplayOracle(1).ids()[:3]]
    f2 = [R.ReplayOracle(2).features(c) for c in R.ReplayOracle(2).ids()[:3]]
    assert f1 != f2


def test_metric_censoring():
    assert R.experiments_to_k_hits([5, 9], 1) == 5
    assert R.experiments_to_k_hits([5, 9], 3) == 61


def test_random_mean_matches_analytic():
    rng = random.Random(0)
    flags = [1] * 15 + [0] * 297
    for k in (1, 3, 5):
        tot = 0
        for _ in range(2000):
            rng.shuffle(flags)
            c = 0
            for i, f in enumerate(flags, 1):
                c += f
                if c == k:
                    tot += i
                    break
        assert abs(tot / 2000 - k * 313 / 16) / (k * 313 / 16) < 0.10


def test_baselines_matched_and_budgeted():
    from asd.baselines import ARMS, run_arm
    for arm in ARMS:
        r = run_arm(arm, 0, budget=20)
        assert r["spent"] == 20 and r["n_init"] == 5
        assert r == run_arm(arm, 0, budget=20)  # deterministic
