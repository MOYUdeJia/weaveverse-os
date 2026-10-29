# Check the built frontend, the API, and the database revision, then write docs/REPORT.md.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Python = Join-Path $Root "backend\.venv\Scripts\python.exe"
$Script = Join-Path $Root "scripts\check_env.py"
if (-not (Test-Path $Python)) {
    throw "backend/.venv is missing"
}
& $Python $Script
exit $LASTEXITCODE
