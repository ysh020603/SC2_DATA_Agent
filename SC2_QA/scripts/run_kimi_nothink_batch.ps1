# Kimi non-thinking retest batch (60 cases each): plain, V1, V2, V2.1
param(
    [ValidateRange(1, 32)][int]$AgentWorkers = 4,
    [ValidateRange(1, 32)][int]$PlainWorkers = 8
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$LogFile = Join-Path $RepoRoot "SC2_QA\logs\batch_kimi_nothink_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
New-Item -ItemType Directory -Force -Path (Split-Path $LogFile) | Out-Null

$Jobs = @(
    @{
        Label = "plain Kimi-k2.5 non-thinking"
        Script = "run_plain.ps1"
        Config = "SC2_QA\configs\plain_kimi_60_nothink.example.json"
        Workers = $PlainWorkers
    },
    @{
        Label = "V1 Kimi-k2.5 non-thinking"
        Script = "run_agent.ps1"
        Config = "SC2_QA\configs\v1_kimi_60_nothink.example.json"
        Workers = $AgentWorkers
    },
    @{
        Label = "V2 Kimi-k2.5 non-thinking"
        Script = "run_agent.ps1"
        Config = "SC2_QA\configs\v2_kimi_60_nothink.example.json"
        Workers = $AgentWorkers
    },
    @{
        Label = "V2.1 Kimi-k2.5 non-thinking"
        Script = "run_agent.ps1"
        Config = "SC2_QA\configs\v2_1_kimi_60_nothink.example.json"
        Workers = $AgentWorkers
    }
)

function Write-Log([string]$Message) {
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message"
    Write-Host $line
    Add-Content -Path $LogFile -Value $line
}

Push-Location $RepoRoot
try {
    Write-Log "Nothink batch started. Log: $LogFile"
    $Index = 0
    foreach ($Job in $Jobs) {
        $Index++
        Write-Log "[$Index/$($Jobs.Count)] START $($Job.Label)"
        & (Join-Path $PSScriptRoot $Job.Script) `
            -Config (Join-Path $RepoRoot $Job.Config) `
            -Workers $Job.Workers
        if ($LASTEXITCODE -ne 0) {
            Write-Log "[$Index/$($Jobs.Count)] FAILED exit=$LASTEXITCODE"
            exit $LASTEXITCODE
        }
        Write-Log "[$Index/$($Jobs.Count)] DONE $($Job.Label)"
    }
    Write-Log "Nothink batch completed successfully."
}
finally {
    Pop-Location
}
