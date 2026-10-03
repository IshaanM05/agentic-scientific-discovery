#!/usr/bin/env bash
# Offline reproduction: no LLM calls. Run from anywhere.
set -u
cd "$(dirname "$0")/.."
export PYTHONUTF8=1 PYTHONIOENCODING=utf-8 PYTHONPATH="$PWD"
PY=${PYTHON:-python}
LOG=$(mktemp)
FAIL=0
step() { echo "== $1"; shift; if "$@" > "$LOG" 2>&1; then echo "   ok"; else echo "   FAILED"; tail -n 8 "$LOG"; FAIL=1; fi; }
step "install" $PY -m pip install -q -r requirements.txt
step "tests" $PY -m pytest -q
step "baselines (seeds 0-19)" $PY scripts/run_baselines.py 20
step "judge calibration" $PY scripts/calibrate_judge.py
step "arena calibration" $PY scripts/calibrate_arena.py
n=$(ls runs/e1/cfnamed/llm_bo_s*.json 2>/dev/null | grep -vc ledger)
m=$(ls runs/e1/blind/llm_bo_s*.json 2>/dev/null | grep -vc ledger)
if [ "$n" -ge 20 ] && [ "$m" -ge 20 ]; then
  step "E1 stats from cache" $PY scripts/e1_counterfactual.py
else
  echo "== E1 stats: SKIPPED (cache missing: $n/20 cfnamed, $m/20 blind)"
fi
step "plot" $PY scripts/plot_headline.py
echo "== summary"
$PY - <<'P'
import json, os
for f in ("results/e1_counterfactual.json", "results/judge_calibration.json", "results/arena_calibration.json"):
    if not os.path.exists(f):
        print(f, "missing"); continue
    d = json.load(open(f))
    if "arms" in d:
        print("E1 mean hits@60:", {a: round(v["mean_hits60"], 2) for a, v in d["arms"].items()}, "rule_met", d.get("rule_met"))
    else:
        print(f, {x: d[x] for x in list(d)[:4]})
print("figure: docs/headline.png", "present" if os.path.exists("docs/headline.png") else "missing")
P
if [ "$FAIL" = 0 ]; then echo "REPRODUCE OK"; else echo "REPRODUCE: some steps failed"; exit 1; fi
