# Offline reproduction: no LLM calls. powershell -ExecutionPolicy Bypass -File scripts/reproduce.ps1
$ErrorActionPreference = "Continue"
Set-Location (Join-Path $PSScriptRoot "..")
$env:PYTHONPATH = (Get-Location).Path; $env:PYTHONUTF8 = "1"; $env:PYTHONIOENCODING = "utf-8"
$script:fail = $false
function Step($name, [scriptblock]$cmd) {
  Write-Host "== $name"
  $out = & $cmd 2>&1 | Out-String
  if ($LASTEXITCODE -eq 0) { Write-Host "   ok" }
  else { Write-Host "   FAILED"; (($out -split "`n") | Select-Object -Last 8) -join "`n" | Write-Host; $script:fail = $true }
}
Step "install" { python -m pip install -q -r requirements.txt }
Step "tests" { python -m pytest -q }
Step "baselines (seeds 0-19)" { python scripts/run_baselines.py 20 }
Step "judge calibration" { python scripts/calibrate_judge.py }
Step "arena calibration" { python scripts/calibrate_arena.py }
$n = @(Get-ChildItem runs/e1/cfnamed -Filter "llm_bo_s*.json" -ErrorAction SilentlyContinue | Where-Object { $_.Name -notlike "*ledger*" }).Count
$m = @(Get-ChildItem runs/e1/blind -Filter "llm_bo_s*.json" -ErrorAction SilentlyContinue | Where-Object { $_.Name -notlike "*ledger*" }).Count
if ($n -ge 20 -and $m -ge 20) { Step "E1 stats from cache" { python scripts/e1_counterfactual.py } }
else { Write-Host "== E1 stats: SKIPPED (cache missing: $n/20 cfnamed, $m/20 blind)" }
Step "plot" { python scripts/plot_headline.py }
Write-Host "== summary"
$code = @'
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
'@
$code | python -
if ($script:fail) { Write-Host "REPRODUCE: some steps failed"; exit 1 } else { Write-Host "REPRODUCE OK" }
