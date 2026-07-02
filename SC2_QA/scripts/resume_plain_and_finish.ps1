# Resume interrupted plain Kimi-k2.5, then run remaining plain experiments.
$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$LogFile = Join-Path $RepoRoot "SC2_QA\logs\batch_plain_finish_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
$ResumeDir = Join-Path $RepoRoot "SC2_QA\logs\20260701_125340_plain_Kimi-k2.5_Kimi-k2.5_170bb14c"
$JudgeModelKey = "Kimi-k2.5"

$RemainingPlain = @(
    "Kimi-k2.5_think",
    "DeepSeek-V4-flash",
    "DeepSeek-V4-flash_think"
)

function Write-Log([string]$Message) {
    $Line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message"
    Write-Host $Line
    Add-Content -Path $LogFile -Value $Line
}

Push-Location $RepoRoot
try {
    Write-Log "Resume plain Kimi-k2.5 from $ResumeDir"
    & python -m SC2_QA.evaluation.cli --resume $ResumeDir
    if ($LASTEXITCODE -ne 0) {
        Write-Log "Resume FAILED exit=$LASTEXITCODE"
        exit $LASTEXITCODE
    }
    Write-Log "Resume done."

    $Index = 0
    $Total = $RemainingPlain.Count
    foreach ($AnswerModel in $RemainingPlain) {
        $Index++
        Write-Log "[$Index/$Total] START plain answer=$AnswerModel judge=$JudgeModelKey"
        & python -m SC2_QA.evaluation.cli `
            --config "SC2_QA\configs\plain.example.json" `
            --mode plain `
            --answer-model-key $AnswerModel `
            --judge-model-key $JudgeModelKey
        if ($LASTEXITCODE -ne 0) {
            Write-Log "[$Index/$Total] FAILED exit=$LASTEXITCODE plain answer=$AnswerModel"
            exit $LASTEXITCODE
        }
        Write-Log "[$Index/$Total] DONE plain answer=$AnswerModel"
    }
    Write-Log "All remaining plain runs completed."
}
finally {
    Pop-Location
}
