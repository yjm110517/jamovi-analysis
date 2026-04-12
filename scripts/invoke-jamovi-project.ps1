param(
    [string]$JamoviHome = "C:\Program Files\jamovi 2.6.19.0",
    [string]$DataPath,
    [string]$SpecJson,
    [string]$SpecFile,
    [string]$Request,
    [string]$OutputDir,
    [string]$OutputBasename,
    [double]$AnalysisTimeoutSeconds = 120,
    [int]$PollIntervalMs = 250
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($DataPath)) {
    throw "Provide -DataPath."
}

$structured = -not [string]::IsNullOrWhiteSpace($SpecJson) -or -not [string]::IsNullOrWhiteSpace($SpecFile)
$naturalLanguage = -not [string]::IsNullOrWhiteSpace($Request)

if ($structured -and $naturalLanguage) {
    throw "Use either structured mode (-SpecJson/-SpecFile) or NL mode (-Request), not both."
}

if (-not $structured -and -not $naturalLanguage) {
    throw "Provide -SpecJson/-SpecFile for structured mode, or -Request for NL mode."
}

if (-not (Test-Path -LiteralPath $JamoviHome)) {
    throw "JamoviHome not found: $JamoviHome"
}

$python = Join-Path $JamoviHome "Frameworks\python\python.exe"
$runner = Join-Path $PSScriptRoot "run-jamovi-project.py"

if (-not (Test-Path -LiteralPath $python)) {
    throw "Bundled Python not found: $python"
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner script not found: $runner"
}

foreach ($entry in Get-ChildItem Env:) {
    if ($entry.Name -in @("PYTHONHOME", "PYTHONPATH", "VIRTUAL_ENV")) {
        Remove-Item -LiteralPath ("Env:\" + $entry.Name) -ErrorAction SilentlyContinue
        continue
    }

    if ($entry.Name -like "CONDA_*") {
        Remove-Item -LiteralPath ("Env:\" + $entry.Name) -ErrorAction SilentlyContinue
    }
}

$env:PYTHONNOUSERSITE = "1"
$env:PYTHONUTF8 = "1"
$env:JAMOVI_PROJECT_RUNNER = "1"
$env:JAMOVI_HOME = $JamoviHome
$env:JAMOVI_MODULES_PATH = Join-Path $JamoviHome "Resources\modules"
$env:JAMOVI_CLIENT_PATH = Join-Path $JamoviHome "Resources\client"
$env:JAMOVI_I18N_PATH = Join-Path $JamoviHome "Resources\i18n"
$env:JAMOVI_VERSION_PATH = Join-Path $JamoviHome "Resources\version"
$env:R_HOME = Join-Path $JamoviHome "Frameworks\R"
$env:R_LIBS = Join-Path $JamoviHome "Resources\modules\base\R"
$env:JAMOVI_R_VERSION = "4.4.1-x64"

$pathParts = @(
    (Join-Path $JamoviHome "Frameworks\python"),
    (Join-Path $JamoviHome "bin"),
    (Join-Path $JamoviHome "Resources\lib"),
    (Join-Path $JamoviHome "Frameworks\R\bin\x64"),
    (Join-Path $JamoviHome "Frameworks\R\library\RInside\lib\x64"),
    $env:PATH
)
$env:PATH = ($pathParts -join ";")

$cmdArgs = @(
    "-Xutf8",
    $runner,
    "--data-path", $DataPath,
    "--analysis-timeout-seconds", [string]$AnalysisTimeoutSeconds,
    "--poll-interval-ms", [string]$PollIntervalMs
)

if (-not [string]::IsNullOrWhiteSpace($SpecJson)) {
    $cmdArgs += @("--spec-json", $SpecJson)
}

if (-not [string]::IsNullOrWhiteSpace($SpecFile)) {
    $cmdArgs += @("--spec-file", $SpecFile)
}

if (-not [string]::IsNullOrWhiteSpace($OutputDir)) {
    $cmdArgs += @("--output-dir", $OutputDir)
}

if (-not [string]::IsNullOrWhiteSpace($OutputBasename)) {
    $cmdArgs += @("--output-basename", $OutputBasename)
}

$requestFilePath = $null
$exitCode = 0

try {
    if (-not [string]::IsNullOrWhiteSpace($Request)) {
        $requestFilePath = Join-Path ([System.IO.Path]::GetTempPath()) ("jamovi-project-request-" + [System.Guid]::NewGuid().ToString("N") + ".txt")
        $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
        [System.IO.File]::WriteAllText($requestFilePath, $Request, $utf8NoBom)
        $cmdArgs += @("--request-file", $requestFilePath)
    }

    & $python @cmdArgs
    $exitCode = $LASTEXITCODE
}
finally {
    if ($requestFilePath -and (Test-Path -LiteralPath $requestFilePath)) {
        Remove-Item -LiteralPath $requestFilePath -Force -ErrorAction SilentlyContinue
    }
}

if ($exitCode -ne 0) {
    exit $exitCode
}
