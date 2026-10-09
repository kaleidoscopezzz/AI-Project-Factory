[CmdletBinding()]
param(
    [switch]$Prepare,
    [switch]$Execute,
    [switch]$CheckCli,
    [string]$ProjectId,
    [string]$SourceEvidence,
    [string]$RunId,
    [string]$AuthorizationId,
    [switch]$FullAccess,
    [string]$CodexPath
)
$ErrorActionPreference = 'Stop'
$factoryRoot = Split-Path -Parent $PSScriptRoot
$factoryPython = (Get-Command python -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source
$factoryArgs = @('-B', '-m', 'factory.revalidation')
if ($Prepare) { $factoryArgs += '--prepare' }
if ($Execute) { $factoryArgs += '--execute' }
if ($CheckCli) { $factoryArgs += '--check-cli' }
foreach ($factoryBinding in @(@('ProjectId','--project-id'),@('SourceEvidence','--source-evidence'),@('RunId','--run-id'),@('AuthorizationId','--authorization-id'),@('CodexPath','--codex-path'))) {
    if ($PSBoundParameters.ContainsKey($factoryBinding[0])) { $factoryArgs += @($factoryBinding[1], $PSBoundParameters[$factoryBinding[0]]) }
}
if ($FullAccess) { $factoryArgs += '--full-access' }
$env:PYTHONIOENCODING = 'utf-8'
Push-Location -LiteralPath $factoryRoot
try { & $factoryPython @factoryArgs; $factoryExit = $LASTEXITCODE }
finally { Pop-Location }
exit $factoryExit
