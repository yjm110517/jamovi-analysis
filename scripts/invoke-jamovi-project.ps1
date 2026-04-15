param(
    [string]$JamoviHome = "",
    [string]$DataPath,
    [string]$SpecJson,
    [string]$SpecFile,
    [string]$Request,
    [string]$RequestFile,
    [string]$JobFile,
    [string]$OutputDir,
    [string]$OutputBasename,
    [string]$Locale = "zh",
    [double]$AnalysisTimeoutSeconds = 120,
    [int]$PollIntervalMs = 250
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($DataPath) -and [string]::IsNullOrWhiteSpace($JobFile)) {
    throw "Provide either -DataPath (legacy) or -JobFile."
}

$structured = -not [string]::IsNullOrWhiteSpace($SpecJson) -or -not [string]::IsNullOrWhiteSpace($SpecFile)
$naturalLanguage = -not [string]::IsNullOrWhiteSpace($Request) -or -not [string]::IsNullOrWhiteSpace($RequestFile)
$hasJob = -not [string]::IsNullOrWhiteSpace($JobFile)

if ($hasJob -and ($structured -or $naturalLanguage)) {
    throw "Use either -JobFile OR legacy parameters (-SpecJson/-SpecFile/-Request), not both."
}

if (-not $hasJob -and $structured -and $naturalLanguage) {
    throw "Use either structured mode (-SpecJson/-SpecFile) or NL mode (-Request), not both."
}

if (-not $hasJob -and -not $structured -and -not $naturalLanguage) {
    throw "Provide -JobFile as the canonical config, or legacy -SpecJson/-SpecFile for structured mode, or -Request for NL mode."
}

$findJamoviHelper = Join-Path $PSScriptRoot "find-jamovi.ps1"
$JamoviHome = & $findJamoviHelper -ProvidedPath $JamoviHome

$python = Join-Path $JamoviHome "Frameworks\python\python.exe"
$runner = Join-Path $PSScriptRoot "run-jamovi-project.py"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$vendorRoot = Join-Path $projectRoot "vendor\jamovi-python"

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
$env:LANGUAGE = $Locale
if (Test-Path -LiteralPath $vendorRoot) {
    $env:JAMOVI_PROJECT_VENDOR_PATH = $vendorRoot
}
else {
    Remove-Item -LiteralPath "Env:JAMOVI_PROJECT_VENDOR_PATH" -ErrorAction SilentlyContinue
}

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
    "--analysis-timeout-seconds", [string]$AnalysisTimeoutSeconds,
    "--poll-interval-ms", [string]$PollIntervalMs
)

if (-not [string]::IsNullOrWhiteSpace($DataPath)) {
    $cmdArgs += @("--data-path", $DataPath)
}

if (-not [string]::IsNullOrWhiteSpace($JobFile)) {
    $cmdArgs += @("--job-file", $JobFile)
}

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

$tempRequestFilePath = $null
$exitCode = 0

try {
    if (-not [string]::IsNullOrWhiteSpace($Request)) {
        $tempRequestFilePath = Join-Path ([System.IO.Path]::GetTempPath()) ("jamovi-project-request-" + [System.Guid]::NewGuid().ToString("N") + ".txt")
        $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
        [System.IO.File]::WriteAllText($tempRequestFilePath, $Request, $utf8NoBom)
        $cmdArgs += @("--request-file", $tempRequestFilePath)
    }
    elseif (-not [string]::IsNullOrWhiteSpace($RequestFile)) {
        $cmdArgs += @("--request-file", $RequestFile)
    }

    & $python @cmdArgs
    $exitCode = $LASTEXITCODE
}
finally {
    if ($tempRequestFilePath -and (Test-Path -LiteralPath $tempRequestFilePath)) {
        Remove-Item -LiteralPath $tempRequestFilePath -Force -ErrorAction SilentlyContinue
    }
}

if ($exitCode -ne 0) {
    exit $exitCode
}
