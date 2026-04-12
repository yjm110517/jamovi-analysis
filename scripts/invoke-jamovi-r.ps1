param(
    [string]$JamoviHome = "C:\Program Files\jamovi 2.6.19.0",
    [string]$Code,
    [string]$File,
    [string[]]$Args
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($Code) -and [string]::IsNullOrWhiteSpace($File)) {
    throw "Provide -Code or -File."
}

if (-not [string]::IsNullOrWhiteSpace($Code) -and -not [string]::IsNullOrWhiteSpace($File)) {
    throw "Use either -Code or -File, not both."
}

if (-not (Test-Path -LiteralPath $JamoviHome)) {
    throw "JamoviHome not found: $JamoviHome"
}

$rscript = Join-Path $JamoviHome "Frameworks\R\bin\x64\Rscript.exe"
$jmvLib = Join-Path $JamoviHome "Resources\modules\jmv\R"
$baseLib = Join-Path $JamoviHome "Resources\modules\base\R"

if (-not (Test-Path -LiteralPath $rscript)) {
    throw "Bundled Rscript not found: $rscript"
}

$jmvLibForR = $jmvLib.Replace("\", "/")
$baseLibForR = $baseLib.Replace("\", "/")

$bootstrap = @"
.libPaths(c(
    normalizePath("$jmvLibForR", winslash = "/"),
    normalizePath("$baseLibForR", winslash = "/"),
    .libPaths()
))
"@

$tempPath = Join-Path ([System.IO.Path]::GetTempPath()) ("jamovi-r-" + [guid]::NewGuid().ToString() + ".R")

try {
    if (-not [string]::IsNullOrWhiteSpace($Code)) {
        $body = $bootstrap + "`r`n" + $Code + "`r`n"
    }
    else {
        if (-not (Test-Path -LiteralPath $File)) {
            throw "R script not found: $File"
        }

        $scriptText = Get-Content -Raw -LiteralPath $File
        $body = $bootstrap + "`r`n" + $scriptText + "`r`n"
    }

    [System.IO.File]::WriteAllText($tempPath, $body, (New-Object System.Text.UTF8Encoding $false))
    & $rscript $tempPath @Args
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}
finally {
    if (Test-Path -LiteralPath $tempPath) {
        Remove-Item -LiteralPath $tempPath -Force -ErrorAction SilentlyContinue
    }
}
