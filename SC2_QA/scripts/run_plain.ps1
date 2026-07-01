param(
    [string]$Config = "",
    [string]$AnswerModelKey = "",
    [string]$JudgeModelKey = "",
    [ValidateSet("", "auto", "on", "off")][string]$AnswerReasoning = "",
    [ValidateSet("", "auto", "on", "off")][string]$JudgeReasoning = "",
    [int]$Limit = 0,
    [switch]$ValidateOnly
)

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
if (-not $Config) { $Config = Join-Path $RepoRoot "SC2_QA\configs\plain.example.json" }
$Arguments = @("-m", "SC2_QA.evaluation.cli", "--config", $Config, "--mode", "plain")
if ($AnswerModelKey) { $Arguments += @("--answer-model-key", $AnswerModelKey) }
if ($JudgeModelKey) { $Arguments += @("--judge-model-key", $JudgeModelKey) }
if ($AnswerReasoning) { $Arguments += @("--answer-reasoning", $AnswerReasoning) }
if ($JudgeReasoning) { $Arguments += @("--judge-reasoning", $JudgeReasoning) }
if ($Limit -gt 0) { $Arguments += @("--limit", $Limit) }
if ($ValidateOnly) { $Arguments += "--validate-only" }

Push-Location $RepoRoot
try { & python @Arguments; exit $LASTEXITCODE }
finally { Pop-Location }
