[CmdletBinding()]
param(
    [string]$Request,
    [ValidateSet('Plan','Auto')][string]$Mode = 'Auto',
    [string]$ProjectId,
    [switch]$Status,
    [switch]$Retry,
    [switch]$FullAccess,
    [string]$CodexPath,
    [switch]$CheckCli,
    [switch]$QualityGate,
    [switch]$NoAutoRepair,
    [ValidateRange(1,1800)][int]$TimeoutSeconds = 900
)
$ErrorActionPreference = 'Stop'
$factoryRoot = Split-Path -Parent $PSScriptRoot
$factoryPython = (Get-Command python -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source
$factoryArgs = @('-B', '-m', 'factory.controller', '--mode', $Mode, '--timeout-seconds', "$TimeoutSeconds")
if ($PSBoundParameters.ContainsKey('Request')) { $factoryArgs += @('--request', $Request) }
if ($ProjectId) { $factoryArgs += @('--project-id', $ProjectId) }
if ($Status) { $factoryArgs += '--status' }
if ($Retry) { $factoryArgs += '--retry' }
if ($FullAccess) { $factoryArgs += '--full-access' }
if ($PSBoundParameters.ContainsKey('CodexPath')) { $factoryArgs += @('--codex-path', $CodexPath) }
if ($CheckCli) { $factoryArgs += '--check-cli' }
if ($QualityGate) { $factoryArgs += '--quality-gate' }
if ($NoAutoRepair) { $factoryArgs += '--no-auto-repair' }
$env:PYTHONIOENCODING = 'utf-8'
Push-Location -LiteralPath $factoryRoot
try { & $factoryPython @factoryArgs; $factoryExit = $LASTEXITCODE }
finally { Pop-Location }
exit $factoryExit
