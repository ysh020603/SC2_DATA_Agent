param(
    [Parameter(Mandatory = $true)][string]$RunDirectory
)

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Push-Location $RepoRoot
try { & python -m SC2_QA.evaluation.cli --summarize $RunDirectory; exit $LASTEXITCODE }
finally { Pop-Location }
