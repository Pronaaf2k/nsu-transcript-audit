Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$apiDir = Join-Path $root 'packages/api'
$cliDir = Join-Path $root 'packages/cli'
$apiVenvDir = Join-Path $apiDir '.venv'
$cliVenvDir = Join-Path $cliDir '.venv'
$apiPython = Join-Path $apiVenvDir 'Scripts/python.exe'
$cliPython = Join-Path $cliVenvDir 'Scripts/python.exe'

function Ensure-Venv($venvDir, $pythonExe, $label) {
  if (-not (Test-Path $pythonExe)) {
    Write-Host "==> Creating Python virtual environment at $label" -ForegroundColor Cyan
    $created = $false
    try {
      py -3.11 -m venv "$venvDir"
      if (Test-Path $pythonExe) {
        $created = $true
      }
    }
    catch {
    }

    if (-not $created) {
      Write-Host "Python 3.11 runtime not found, falling back to default 'py'" -ForegroundColor Yellow
      py -m venv "$venvDir"
    }
  }

  if (-not (Test-Path $pythonExe)) {
    Write-Host "Failed to create virtual environment for $label. Ensure Python is installed and available via 'py'." -ForegroundColor Red
    exit 1
  }
}

Write-Host "==> Installing Node workspace dependencies" -ForegroundColor Cyan
pnpm install

Ensure-Venv $apiVenvDir $apiPython 'packages/api/.venv'
Ensure-Venv $cliVenvDir $cliPython 'packages/cli/.venv'

Write-Host "==> Installing API Python dependencies" -ForegroundColor Cyan
& "$apiPython" -m pip install --upgrade pip
& "$apiPython" -m pip install -r (Join-Path $root 'packages/api/requirements.txt')

Write-Host "==> Installing CLI Python dependencies" -ForegroundColor Cyan
& "$cliPython" -m pip install --upgrade pip
& "$cliPython" -m pip install -r (Join-Path $root 'packages/cli/requirements.txt')

Write-Host "" 
Write-Host "Local setup complete." -ForegroundColor Green
Write-Host "Next steps:" -ForegroundColor Green
Write-Host "  1) Copy .env.example to .env and set required keys" -ForegroundColor Green
Write-Host "  2) Run: pnpm dev:local" -ForegroundColor Green
Write-Host "  3) Run CLI: pnpm cli -- --help" -ForegroundColor Green
