# Weaveverse OS · 一键启动（自动重建前端）
# 用法：.\start.ps1  或双击 start.bat

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

Write-Host "===== Weaveverse OS 启动中 =====" -ForegroundColor Cyan

# 1. 检查 venv
$venv = Join-Path $root "backend\.venv\Scripts\Activate.ps1"
if (-not (Test-Path $venv)) {
    Write-Host "未找到 backend\.venv，请先手动创建：" -ForegroundColor Red
    Write-Host "  cd backend" -ForegroundColor Red
    Write-Host "  python -m venv .venv" -ForegroundColor Red
    Write-Host "  .venv\Scripts\activate" -ForegroundColor Red
    Write-Host "  pip install -r requirements.txt" -ForegroundColor Red
    exit 1
}

# 2. 构建前端
Write-Host "[1/3] 构建前端..." -ForegroundColor Yellow
Push-Location (Join-Path $root "frontend")
npm run build
Pop-Location

# 3. 激活 venv
Write-Host "[2/3] 激活虚拟环境..." -ForegroundColor Green
. $venv

# 4. 启动后端 + 桌面窗口
Write-Host "[3/3] 启动后端 + 桌面窗口..." -ForegroundColor Green
Push-Location (Join-Path $root "backend")
python main.py
Pop-Location

Write-Host "===== 已退出 =====" -ForegroundColor Cyan