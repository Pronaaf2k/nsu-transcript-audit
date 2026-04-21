Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
. (Join-Path $PSScriptRoot 'import-root-env.ps1')
[void](Import-RootEnv -RootPath $root)

Set-Location $root
pnpm --filter mobile start
