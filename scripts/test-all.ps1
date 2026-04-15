Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$venvPython = Join-Path $root 'packages/api/.venv/Scripts/python.exe'

if (-not (Test-Path $venvPython)) {
  Write-Host "Missing packages/api/.venv. Run 'pnpm setup:local' first." -ForegroundColor Red
  exit 1
}

Write-Host "==> Running Python tests (API + program knowledge)" -ForegroundColor Cyan
& "$venvPython" -m pytest "$root/tests/test_api_endpoints.py" "$root/tests/test_program_knowledge.py" -q

Write-Host "==> Running web lint" -ForegroundColor Cyan
pnpm --filter web lint

Write-Host "==> Running web typecheck" -ForegroundColor Cyan
pnpm --filter web exec tsc --noEmit

Write-Host "==> Running CLI smoke test" -ForegroundColor Cyan
pnpm run cli -- --help | Out-Null

Write-Host "All checks passed." -ForegroundColor Green
