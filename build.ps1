param(
    [switch]$Console
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$Frontend = Join-Path $Root "frontend"
$Python = Join-Path $Root "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    throw "找不到 backend/.venv，请先创建虚拟环境。"
}

Write-Host "Building frontend..."
Push-Location $Frontend
npm run build
Pop-Location

Write-Host "Installing PyInstaller if needed..."
& $Python -m pip install "pyinstaller==6.16.0"

$Spec = Join-Path $Root "weaveverse.spec"
if ($Console) {
    Write-Host "Console build: temporarily enabling console in spec copy."
    $TempSpec = Join-Path $Root "weaveverse.console.spec"
    (Get-Content $Spec -Raw) -replace "console=False", "console=True" | Set-Content $TempSpec -NoNewline
    $Spec = $TempSpec
}

Write-Host "Running PyInstaller..."
& $Python -m PyInstaller --noconfirm --clean $Spec

if ($Console -and (Test-Path (Join-Path $Root "weaveverse.console.spec"))) {
    Remove-Item (Join-Path $Root "weaveverse.console.spec")
}

$Exe = Join-Path $Root "dist\WeaveverseOS\WeaveverseOS.exe"
if (-not (Test-Path $Exe)) {
    throw "没有生成 $Exe"
}

Write-Host "Done: $Exe"
Write-Host "User data: %APPDATA%\WeaveverseOS\"
Write-Host "This onedir build does not bundle faster-whisper/torch. Local STT stays in the venv workflow."
