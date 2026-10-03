# Usage: powershell -File scripts/live.ps1 <agent.yaml> "<prompt>" [-Interactive]  (-Interactive omits -p: REPL, policy ASK waits for a human y/n)
# Loads KEY=VALUE lines from the main checkout .env into this process only (never printed or copied),
# starts the managed local omnigent server (the auto-spawn path times out on Windows), then runs the agent.
param([string]$Agent, [string]$Prompt, [switch]$Interactive)
$EnvFile = "C:\Users\Ishaan\Desktop\agentic-scientific-discovery\.env"
Get-Content $EnvFile | ForEach-Object {
  if ($_ -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$') {
    [Environment]::SetEnvironmentVariable($Matches[1], $Matches[2].Trim('"').Trim("'"), 'Process')
  }
}
Set-Location (Join-Path $PSScriptRoot "..")
$env:PYTHONPATH = (Get-Location).Path; $env:PYTHONUTF8 = "1"; $env:PYTHONIOENCODING = "utf-8"
if (-not $env:ASD_RUN_DIR) { $env:ASD_RUN_DIR = "runs/live-" + (Get-Date -Format "yyyyMMdd-HHmmss") }
if (-not $env:ASD_SEED) { $env:ASD_SEED = "0" }
if (-not $env:ASD_RUN_ID) { $env:ASD_RUN_ID = "run-" + (Get-Date -Format "yyyyMMdd-HHmmss") + "-s" + $env:ASD_SEED }
if (-not $env:ASD_BUDGET) { $env:ASD_BUDGET = "60" }
$env:OMNIGENT_RUNNER_ENV_PASSTHROUGH = "ASD_SEED,ASD_BUDGET,ASD_RUN_DIR,ASD_RUN_ID"
# The daemon strips ASD_* (env allowlist) but forwards LC_* to the runner: mirror the config there.
foreach ($n in "SEED","BUDGET","RUN_DIR","RUN_ID") { Set-Item -Path "Env:LC_ASD_$n" -Value (Get-Item "Env:ASD_$n").Value }
omnigent stop 2>&1 | Out-Null   # fresh server so it inherits ASD_* and token env
omnigent server --background 2>&1 | Out-Null
for ($i = 0; $i -lt 30; $i++) {
  try { $r = Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 http://127.0.0.1:6767/health; if ($r.StatusCode -eq 200) { break } } catch { Start-Sleep 2 }
}
if ($Interactive) { omnigent run $Agent --server local } else { omnigent run $Agent -p $Prompt --server local }
