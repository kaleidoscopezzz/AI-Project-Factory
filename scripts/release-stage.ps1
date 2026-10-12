[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$ProjectId,
    [Parameter(Mandatory=$true)][ValidateSet('Goal 0','Goal 1')][string]$Goal,
    [Parameter(Mandatory=$true)][string]$ConfigFile,
    [string]$RuntimeRoot,
    [switch]$Execute
)
$ErrorActionPreference = 'Stop'
$releaseConfig = (Resolve-Path -LiteralPath $ConfigFile).Path
$factoryRoot = Split-Path -Parent $PSScriptRoot
$releaseArgs = @('-B', '-m', 'factory.release_agent', '--project-id', $ProjectId, '--goal', $Goal, '--config', $releaseConfig)
if ($RuntimeRoot) { $releaseArgs += @('--root', (Resolve-Path -LiteralPath $RuntimeRoot).Path) }
if ($Execute) { $releaseArgs += '--execute' }
$env:PYTHONIOENCODING = 'utf-8'
Push-Location $factoryRoot
try { & python @releaseArgs; $releaseExit = $LASTEXITCODE } finally { Pop-Location }
exit $releaseExit
