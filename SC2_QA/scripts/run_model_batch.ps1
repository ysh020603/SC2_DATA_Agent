# Batch SC2_QA evaluation: answer models x agent/plain, judge = Kimi-k2.5
# Qwen35-27b variants excluded (16k context too small for Agent mode).
param(
    [string]$JudgeModelKey = "Kimi-k2.5"
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$LogFile = Join-Path $RepoRoot "SC2_QA\logs\batch_run_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
New-Item -ItemType Directory -Force -Path (Split-Path $LogFile) | Out-Null

$Models = @(
    "Kimi-k2.5",
    "Kimi-k2.5_think",
    "DeepSeek-V4-flash",
    "DeepSeek-V4-flash_think"
)

function Write-Log([string]$Message) {
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message"
    Add-Content -Path $LogFile -Value $line
    Write-Host $line
}

Push-Location $RepoRoot
try {
    foreach ($model in $Models) {
        foreach ($mode in @("agent", "plain")) {
            $script = if ($mode -eq "agent") { "run_agent.ps1" } else { "run_plain.ps1" }
            Write-Log "START $mode :: $model (judge=$JudgeModelKey)"
            $exit = & (Join-Path $PSScriptRoot $script) `
                -AnswerModelKey $model `
                -JudgeModelKey $JudgeModelKey `
                -AnswerReasoning auto `
                -JudgeReasoning auto
            if ($LASTEXITCODE -ne 0) {
                Write-Log "FAILED $mode :: $model exit=$LASTEXITCODE"
                exit $LASTEXITCODE
            }
            Write-Log "DONE $mode :: $model"
        }
    }
    Write-Log "BATCH_COMPLETE"
}
finally {
    Pop-Location
}
