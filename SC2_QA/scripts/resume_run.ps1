param(
    [Parameter(Mandatory = $true)][string]$RunDirectory,
    [switch]$RetryFailed
)

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Arguments = @("-m", "SC2_QA.evaluation.cli", "--resume", $RunDirectory)
if ($RetryFailed) { $Arguments += "--retry-failed" }

Push-Location $RepoRoot
try { & python @Arguments; exit $LASTEXITCODE }
finally { Pop-Location }
