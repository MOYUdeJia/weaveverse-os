$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

& (Join-Path $Root "build.ps1")
if ($LASTEXITCODE -ne 0) {
    throw "portable build failed"
}

$pf86 = ${env:ProgramFiles(x86)}
$Candidates = @(
    (Join-Path $pf86 "Inno Setup 6\ISCC.exe"),
    (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe"),
    (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"),
    (Join-Path $pf86 "Inno Setup 7\ISCC.exe"),
    (Join-Path $env:ProgramFiles "Inno Setup 7\ISCC.exe"),
    (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 7\ISCC.exe")
)
$Iscc = $Candidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
if (-not $Iscc) {
    throw "ISCC.exe not found. Install Inno Setup, then rerun. See docs/BUILD.md"
}

& $Iscc (Join-Path $Root "installer.iss")
if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup compile failed"
}

$Setup = Join-Path $Root "dist\WeaveverseOS-Setup.exe"
if (-not (Test-Path $Setup)) {
    throw "missing $Setup"
}
Write-Host "Done: $Setup"
Write-Host "Uninstall keeps %APPDATA%\WeaveverseOS"
