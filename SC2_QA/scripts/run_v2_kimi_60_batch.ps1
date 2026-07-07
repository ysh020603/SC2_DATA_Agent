# V2 Agent: full 60-case Kimi non-thinking then Kimi thinking.
# Each run writes its own experiment directory under SC2_QA/logs/<experiment_id>/.
param(
    [ValidateRange(1, 32)][int]$Workers = 4
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$LogFile = Join-Path $RepoRoot "SC2_QA\logs\batch_v2_kimi_60_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
New-Item -ItemType Directory -Force -Path (Split-Path $LogFile) | Out-Null

$Jobs = @(
    @{
        Label = "v2 Kimi-k2.5 non-thinking"
        Config = "SC2_QA\configs\v2_kimi_60_nothink.example.json"
    },
    @{
        Label = "v2 Kimi-k2.5_think thinking"
        Config = "SC2_QA\configs\v2_kimi_60_think.example.json"
    }
)

function Write-Log([string]$Message) {
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message"
    Write-Host $line
    Add-Content -Path $LogFile -Value $line
}

Push-Location $RepoRoot
try {
    Write-Log "Batch started. Console log: $LogFile"
    $Index = 0
    foreach ($Job in $Jobs) {
        $Index++
        Write-Log "[$Index/$($Jobs.Count)] START $($Job.Label)"
        & (Join-Path $PSScriptRoot "run_agent.ps1") `
            -Config (Join-Path $RepoRoot $Job.Config) `
            -Workers $Workers
        if ($LASTEXITCODE -ne 0) {
            Write-Log "[$Index/$($Jobs.Count)] FAILED exit=$LASTEXITCODE"
            exit $LASTEXITCODE
        }
        Write-Log "[$Index/$($Jobs.Count)] DONE $($Job.Label)"
    }
    Write-Log "Batch completed successfully."
}
finally {
    Pop-Location
}
