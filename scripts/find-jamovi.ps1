param(
    [string]$ProvidedPath = ""
)

if (-not [string]::IsNullOrWhiteSpace($ProvidedPath)) {
    if (Test-Path -LiteralPath $ProvidedPath) {
        return $ProvidedPath
    }
    throw "Provided JamoviHome not found: $ProvidedPath"
}

$registryPaths = @(
    "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*",
    "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*",
    "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*"
)

$regInstalls = Get-ItemProperty $registryPaths -ErrorAction SilentlyContinue | Where-Object { $_.DisplayName -match "jamovi" -and -not [string]::IsNullOrWhiteSpace($_.InstallLocation) }

if ($regInstalls) {
    foreach ($regInstall in $regInstalls) {
        $installLoc = $regInstall.InstallLocation.TrimEnd('\')
        $testPython = Join-Path $installLoc "Frameworks\python\python.exe"
        if (Test-Path -LiteralPath $testPython) {
            return $installLoc
        }
    }
}

$potentialDirs = @(
    "C:\Program Files",
    "C:\Program Files (x86)",
    $env:LOCALAPPDATA,
    $env:APPDATA
)

foreach ($baseDir in $potentialDirs) {
    if (-not (Test-Path -LiteralPath $baseDir)) { continue }
    
    $jamoviInstalls = Get-ChildItem -LiteralPath $baseDir -Filter "jamovi*" -Directory -ErrorAction SilentlyContinue | Sort-Object Name -Descending
    foreach ($install in $jamoviInstalls) {
        $testPython = Join-Path $install.FullName "Frameworks\python\python.exe"
        if (Test-Path -LiteralPath $testPython) {
            return $install.FullName
        }
    }
}

throw "Jamovi installation could not be automatically found. Please provide -JamoviHome explicitly."
