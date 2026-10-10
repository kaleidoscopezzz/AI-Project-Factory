[CmdletBinding()]
param(
    [switch]$Prepare,
    [switch]$PrepareReview,
    [switch]$Execute,
    [switch]$CheckCli,
    [string]$ProjectId,
    [string]$SourceEvidence,
    [string]$SourceRunId,
    [string]$SourceManifest,
    [string]$ReviewerSourceRunId,
    [string]$RunId,
    [string]$AuthorizationId,
    [switch]$FullAccess,
    [string]$CodexPath,
    [string]$Goal3RuntimeRoot
)
$ErrorActionPreference = 'Stop'
$factoryRoot = Split-Path -Parent $PSScriptRoot
$factoryPython = (Get-Command python -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source
$factoryArgs = @('-B', '-m', 'factory.revalidation')
if ($Prepare) { $factoryArgs += '--prepare' }
if ($PrepareReview) { $factoryArgs += '--prepare-review' }
if ($Execute) { $factoryArgs += '--execute' }
if ($CheckCli) { $factoryArgs += '--check-cli' }
foreach ($factoryBinding in @(@('ProjectId','--project-id'),@('SourceEvidence','--source-evidence'),@('SourceRunId','--source-run-id'),@('SourceManifest','--source-manifest'),@('ReviewerSourceRunId','--reviewer-source-run-id'),@('RunId','--run-id'),@('AuthorizationId','--authorization-id'),@('CodexPath','--codex-path'),@('Goal3RuntimeRoot','--goal3-runtime-root'))) {
    if ($PSBoundParameters.ContainsKey($factoryBinding[0])) { $factoryArgs += @($factoryBinding[1], $PSBoundParameters[$factoryBinding[0]]) }
}
if ($FullAccess) { $factoryArgs += '--full-access' }
$env:PYTHONIOENCODING = 'utf-8'
Push-Location -LiteralPath $factoryRoot
try { & $factoryPython @factoryArgs; $factoryExit = $LASTEXITCODE }
finally { Pop-Location }
exit $factoryExit
