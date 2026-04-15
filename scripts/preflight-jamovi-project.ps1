param(
    [string]$JamoviHome = "",
    [string]$Locale = "zh"
)

$ErrorActionPreference = "Stop"

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

& $python -Xutf8 $runner --preflight
exit $LASTEXITCODE
