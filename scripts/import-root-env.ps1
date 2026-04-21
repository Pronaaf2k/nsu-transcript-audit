Set-StrictMode -Version Latest

function Import-RootEnv {
  param(
    [Parameter(Mandatory = $true)]
    [string]$RootPath
  )

  $envFile = Join-Path $RootPath '.env'
  if (-not (Test-Path $envFile)) {
    Write-Host "Warning: .env not found at $envFile" -ForegroundColor Yellow
    return $false
  }

  foreach ($line in Get-Content $envFile) {
    $trimmed = $line.Trim()
    if (-not $trimmed -or $trimmed.StartsWith('#')) {
      continue
    }

    $match = [regex]::Match($trimmed, '^(?<key>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?<value>.*)$')
    if (-not $match.Success) {
      continue
    }

    $key = $match.Groups['key'].Value
    $value = $match.Groups['value'].Value.Trim()

    if (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'"))) {
      $value = $value.Substring(1, $value.Length - 2)
    }

    Set-Item -Path "Env:$key" -Value $value
  }

  return $true
}
