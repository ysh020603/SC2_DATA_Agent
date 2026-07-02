# Sequential batch: non-thinking models in agent+plain; thinking models in plain only.
# Judge defaults to Kimi-k2.5.
param(
    [string]$JudgeModelKey = "Kimi-k2.5",
    [string[]]$SkipAgentAnswerModels = @()
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$LogFile = Join-Path $RepoRoot "SC2_QA\logs\batch_kimi_deepseek_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
New-Item -ItemType Directory -Force -Path (Split-Path $LogFile) | Out-Null

$AnswerModelsNonThink = @(
    "Kimi-k2.5",
    "DeepSeek-V4-flash"
)

$AnswerModelsAll = @(
    "Kimi-k2.5",
    "Kimi-k2.5_think",
    "DeepSeek-V4-flash",
    "DeepSeek-V4-flash_think"
)

$Jobs = @()
foreach ($AnswerModel in $AnswerModelsNonThink) {
    if ($SkipAgentAnswerModels -contains $AnswerModel) { continue }
    $Jobs += @{
        Mode = "agent"
        AnswerModel = $AnswerModel
        Config = "SC2_QA\configs\agent.example.json"
    }
}
foreach ($AnswerModel in $AnswerModelsAll) {
    $Jobs += @{
        Mode = "plain"
        AnswerModel = $AnswerModel
        Config = "SC2_QA\configs\plain.example.json"
    }
}

function Write-Log([string]$Message) {
    $Line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message"
    Write-Host $Line
    Add-Content -Path $LogFile -Value $Line
}

Push-Location $RepoRoot
try {
    Write-Log "Batch started. Log: $LogFile"
    Write-Log "Plan: agent for non-thinking only; plain for all 4 models ($($Jobs.Count) runs)."
    if ($SkipAgentAnswerModels.Count -gt 0) {
        Write-Log "Skipped agent answer models: $($SkipAgentAnswerModels -join ', ')"
    }

    $Index = 0
    $Total = $Jobs.Count
    foreach ($Job in $Jobs) {
        $Index++
        $AnswerModel = $Job.AnswerModel
        $Mode = $Job.Mode
        Write-Log "[$Index/$Total] START mode=$Mode answer=$AnswerModel judge=$JudgeModelKey"
        $Args = @(
            "-m", "SC2_QA.evaluation.cli",
            "--config", $Job.Config,
            "--mode", $Mode,
            "--answer-model-key", $AnswerModel,
            "--judge-model-key", $JudgeModelKey
        )
        & python @Args
        $Code = $LASTEXITCODE
        if ($Code -ne 0) {
            Write-Log "[$Index/$Total] FAILED exit=$Code mode=$Mode answer=$AnswerModel"
            exit $Code
        }
        Write-Log "[$Index/$Total] DONE mode=$Mode answer=$AnswerModel"
    }
    Write-Log "Batch completed successfully ($Total runs)."
}
finally {
    Pop-Location
}
