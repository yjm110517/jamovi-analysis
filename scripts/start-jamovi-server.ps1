param(
    [string]$JamoviHome = "C:\Program Files\jamovi 2.6.19.0",
    [int]$Port = 0,
    [switch]$ExposeAllInterfaces,
    [switch]$Debug,
    [switch]$StartBrowser
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $JamoviHome)) {
    throw "JamoviHome not found: $JamoviHome"
}

$python = Join-Path $JamoviHome "Frameworks\python\python.exe"
$serverRoot = Join-Path $JamoviHome "Resources\server"

if (-not (Test-Path -LiteralPath $python)) {
    throw "Bundled Python not found: $python"
}

if (-not (Test-Path -LiteralPath $serverRoot)) {
    throw "Server root not found: $serverRoot"
}

$env:R_HOME = Join-Path $JamoviHome "Frameworks\R"
$env:R_LIBS = Join-Path $JamoviHome "Resources\modules\base\R"
$env:JAMOVI_HOME = $JamoviHome
$env:JAMOVI_MODULES_PATH = Join-Path $JamoviHome "Resources\modules"
$env:JAMOVI_CLIENT_PATH = Join-Path $JamoviHome "Resources\client"
$env:JAMOVI_I18N_PATH = Join-Path $JamoviHome "Resources\i18n"
$env:JAMOVI_VERSION_PATH = Join-Path $JamoviHome "Resources\version"
$env:JAMOVI_R_VERSION = "4.4.1-x64"

$pathParts = @(
    (Join-Path $JamoviHome "bin"),
    (Join-Path $JamoviHome "Resources\lib"),
    (Join-Path $JamoviHome "Frameworks\R\bin\x64"),
    (Join-Path $JamoviHome "Frameworks\R\library\RInside\lib\x64"),
    $env:PATH
)
$env:PATH = ($pathParts -join ";")

$cmdArgs = @("-u", "-Xutf8", "-m", "jamovi.server", [string]$Port, "--stdin-slave")

if ($ExposeAllInterfaces) {
    $cmdArgs += "--if=*"
}

if ($Debug) {
    $cmdArgs += "--debug"
}

if ($StartBrowser) {
    $cmdArgs += "--start-wb"
}

Push-Location $serverRoot
try {
    & $python @cmdArgs
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}
finally {
    Pop-Location
}
