# Resume Kimi non-thinking retest for V1, V2, V2.1 (plain already completed).
# Waits for the Kimi API to be stable before each run to avoid 500-storm pollution.
param(
    [ValidateRange(1, 32)][int]$AgentWorkers = 4,
    [ValidateRange(1, 20)][int]$StableProbes = 6,
    [ValidateRange(1, 60)][int]$ProbeIntervalSeconds = 5
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$LogFile = Join-Path $RepoRoot "SC2_QA\logs\batch_kimi_nothink_resume_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
New-Item -ItemType Directory -Force -Path (Split-Path $LogFile) | Out-Null

$Jobs = @(
    @{ Label = "V1 Kimi-k2.5 non-thinking";   Config = "SC2_QA\configs\v1_kimi_60_nothink.example.json" },
    @{ Label = "V2 Kimi-k2.5 non-thinking";   Config = "SC2_QA\configs\v2_kimi_60_nothink.example.json" },
    @{ Label = "V2.1 Kimi-k2.5 non-thinking"; Config = "SC2_QA\configs\v2_1_kimi_60_nothink.example.json" }
)

function Write-Log([string]$Message) {
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message"
    Write-Host $line
    Add-Content -Path $LogFile -Value $line
}

function Wait-ApiStable {
    $consecutive = 0
    while ($consecutive -lt $StableProbes) {
        $probe = Start-Process -FilePath python -ArgumentList (Join-Path $RepoRoot "SC2_QA\scripts\_api_probe.py") -WorkingDirectory $RepoRoot -NoNewWindow -PassThru -Wait
        if ($probe.ExitCode -eq 0) {
            $consecutive++
            Write-Log "API probe OK ($consecutive/$StableProbes)"
        } else {
            if ($consecutive -gt 0) { Write-Log "API probe FAILED, resetting stability counter" }
            $consecutive = 0
            Start-Sleep -Seconds 15
        }
        Start-Sleep -Seconds $ProbeIntervalSeconds
    }
    Write-Log "API confirmed stable ($StableProbes consecutive successes)"
}

Push-Location $RepoRoot
try {
    Write-Log "Resume batch started (V1, V2, V2.1). Log: $LogFile"
    $Index = 0
    foreach ($Job in $Jobs) {
        $Index++
        Write-Log "[$Index/$($Jobs.Count)] Waiting for stable API before $($Job.Label)"
        Wait-ApiStable
        Write-Log "[$Index/$($Jobs.Count)] START $($Job.Label)"
        & (Join-Path $PSScriptRoot "run_agent.ps1") `
            -Config (Join-Path $RepoRoot $Job.Config) `
            -Workers $AgentWorkers
        if ($LASTEXITCODE -ne 0) {
            Write-Log "[$Index/$($Jobs.Count)] FAILED exit=$LASTEXITCODE"
            exit $LASTEXITCODE
        }
        Write-Log "[$Index/$($Jobs.Count)] DONE $($Job.Label)"
    }
    Write-Log "Resume batch completed successfully."
}
finally {
    Pop-Location
}
