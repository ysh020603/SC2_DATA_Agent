# Resume interrupted agent Kimi-k2.5 run, then start the updated 5-run batch.
$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$LogFile = Join-Path $RepoRoot "SC2_QA\logs\batch_kimi_deepseek_resume_then_remaining.log"
$ResumeDir = Join-Path $RepoRoot "SC2_QA\logs\20260701_105715_agent_Kimi-k2.5_Kimi-k2.5_bbe1c68e"

function Write-Log([string]$Message) {
    $Line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message"
    Write-Host $Line
    Add-Content -Path $LogFile -Value $Line
}

Push-Location $RepoRoot
try {
    Write-Log "Resume agent Kimi-k2.5 from $ResumeDir"
    & python -m SC2_QA.evaluation.cli --resume $ResumeDir
    if ($LASTEXITCODE -ne 0) {
        Write-Log "Resume FAILED exit=$LASTEXITCODE"
        exit $LASTEXITCODE
    }
    Write-Log "Resume done. Starting remaining batch (5 runs)..."
    & (Join-Path $PSScriptRoot "run_kimi_deepseek_batch.ps1") -SkipAgentAnswerModels "Kimi-k2.5"
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
