"""Model-free demo: the budget policy DENYs and the approval policy ASKs, built exactly as Omnigent
builds them from agents/planner.yaml (via omnigent's own shim). Run from repo root:
    python scripts/demo_policies.py
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from omnigent.spec._omnigent_legacy_shim import build  # noqa: E402

from asd import policies as P  # noqa: E402
from asd import tools as T  # noqa: E402

LIMIT = 3
budget = build(target="asd.policies.experiment_budget", factory_kwargs={"limit": LIMIT})
approval = build(target="asd.policies.human_approval", factory_kwargs={"ask_after": 2})
T.reset(seed=0, budget=60, run_dir=tempfile.mkdtemp())
ids = T._st()["oracle"].ids()
state = 0
for i in range(LIMIT + 1):
    ev = {"type": "tool_call", "target": "run_experiment", "data": {"name": "run_experiment"},
          "session_state": {P._KEY: state}}
    v, a = budget(ev), approval(ev)
    print(f"run_experiment #{i + 1}: budget={v['result']} {v.get('reason', '')} | "
          f"approval={a['result']} {a.get('reason', '')}")
    if v["result"] == "ALLOW":
        T.run_experiment(ids[i])
        state += 1
ev = {"type": "tool_call", "target": "recommend_for_validation", "data": {}, "session_state": {}}
r = approval(ev)
print(f"recommend_for_validation: approval={r['result']} ({r['reason']})")
