param(
    [string]$ApiKey = $env:OPENAI_API_KEY,
    [string]$Model = "deepseek-chat",
    [string]$BaseUrl = "https://api.deepseek.com/v1",
    [string]$Result = "output/result.json",
    [string]$Dataset = "data/benchmark_dataset.json",
    [string]$OutJson = "output/eval_llm_judge.json",
    [string]$OutMd = "output/eval_llm_judge.md",
    [int]$TimeoutSeconds = 180
)

$ErrorActionPreference = "Stop"

if (-not $ApiKey) {
    throw "OPENAI_API_KEY is empty. Provide -ApiKey or set OPENAI_API_KEY env var."
}

$RepoRoot = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $RepoRoot ".venv/Scripts/python.exe"

if (Test-Path $VenvPython) {
    $PythonCmd = $VenvPython
} else {
    $PythonCmd = "python"
}

$env:OPENAI_API_KEY = $ApiKey
$env:OPENAI_BASE_URL = $BaseUrl
$env:OPENAI_MODEL = $Model
$env:EVAL_JUDGE_TIMEOUT_SECONDS = [string]$TimeoutSeconds

$Evaluator = Join-Path $RepoRoot "src/evaluator.py"

& $PythonCmd $Evaluator --mode llm_judge --result $Result --dataset $Dataset --out-json $OutJson --out-md $OutMd

if ($LASTEXITCODE -ne 0) {
    throw "LLM judge run failed, exit code: $LASTEXITCODE"
}

Write-Host "[deepseek-runner] done"
Write-Host "[deepseek-runner] json report: $OutJson"
Write-Host "[deepseek-runner] md report: $OutMd"
