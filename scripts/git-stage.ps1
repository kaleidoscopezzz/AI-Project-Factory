[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$ProjectId,
    [string]$RuntimeRoot,
    [string]$PolicyFile,
    [ValidateSet('Goal 0','Goal 1')][string]$CommitGoal
)
$ErrorActionPreference = 'Stop'
if ($PolicyFile -and $CommitGoal) { throw 'Configure policy and commit are separate explicit operations.' }
$factoryRoot = Split-Path -Parent $PSScriptRoot
$factoryArgs = @('-B', '-m', 'factory.git_agent', '--project-id', $ProjectId)
if ($RuntimeRoot) { $factoryArgs += @('--root', $RuntimeRoot) }
if ($PolicyFile) { $factoryArgs += @('--configure', $PolicyFile) }
if ($CommitGoal) { $factoryArgs += @('--commit', $CommitGoal) }
$env:PYTHONIOENCODING = 'utf-8'
Push-Location $factoryRoot
try {
    & python @factoryArgs
    $factoryExitCode = $LASTEXITCODE
} finally { Pop-Location }
exit $factoryExitCode
