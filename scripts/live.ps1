# Usage: powershell -File scripts/live.ps1 <agent.yaml> "<prompt>"
# Loads KEY=VALUE lines from the main checkout .env into this process only (never printed or copied),
# starts the managed local omnigent server (the auto-spawn path times out on Windows), then runs the agent.
param([string]$Agent, [string]$Prompt)
$EnvFile = "C:\Users\Ishaan\Desktop\agentic-scientific-discovery\.env"
Get-Content $EnvFile | ForEach-Object {
  if ($_ -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$') {
    [Environment]::SetEnvironmentVariable($Matches[1], $Matches[2].Trim('"').Trim("'"), 'Process')
  }
}
Set-Location (Join-Path $PSScriptRoot "..")
$env:PYTHONPATH = (Get-Location).Path; $env:PYTHONUTF8 = "1"; $env:PYTHONIOENCODING = "utf-8"
if (-not $env:ASD_RUN_DIR) { $env:ASD_RUN_DIR = "runs/live-" + (Get-Date -Format "yyyyMMdd-HHmmss") }
if (-not $env:ASD_BUDGET) { $env:ASD_BUDGET = "60" }
omnigent stop 2>&1 | Out-Null   # fresh server so it inherits ASD_* and token env
omnigent server --background 2>&1 | Out-Null
for ($i = 0; $i -lt 30; $i++) {
  try { $r = Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 http://127.0.0.1:6767/health; if ($r.StatusCode -eq 200) { break } } catch { Start-Sleep 2 }
}
omnigent run $Agent -p $Prompt --server local
