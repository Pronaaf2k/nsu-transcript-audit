Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$venvPython = Join-Path $root 'packages/cli/.venv/Scripts/python.exe'

if (-not (Test-Path $venvPython)) {
  Write-Host "Missing packages/cli/.venv. Run 'pnpm setup:local' first." -ForegroundColor Red
  exit 1
}

Push-Location (Join-Path $root 'packages/cli')
try {
  & "$venvPython" main.py @args
}
finally {
  Pop-Location
}
