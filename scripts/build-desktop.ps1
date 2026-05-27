# Full DocForge desktop build for Windows
$ErrorActionPreference = "Stop"

$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$PROJECT_ROOT = Split-Path -Parent $SCRIPT_DIR

Write-Host "=== DocForge Desktop Build ==="
Write-Host ""

# Step 1: Setup environment
Write-Host "[1/4] Setting up environment..."
$VENV_PYTHON = "$PROJECT_ROOT\.venv\Scripts\python.exe"
if (-not (Test-Path $VENV_PYTHON)) {
    Write-Host "Creating virtual environment..."
    python -m venv "$PROJECT_ROOT\.venv"
    & $VENV_PYTHON -m pip install -e "$PROJECT_ROOT[dev]"
}
Set-Location "$PROJECT_ROOT\apps\desktop"
npm install
Write-Host ""

# Step 2: Fetch Pandoc
Write-Host "[2/4] Fetching Pandoc sidecar..."
& "$SCRIPT_DIR\fetch-pandoc.ps1"
Write-Host ""

# Step 3: Build Python engine
Write-Host "[3/4] Building Python engine..."
& "$SCRIPT_DIR\build-engine.ps1"
Write-Host ""

# Step 4: Build Tauri app
Write-Host "[4/4] Building Tauri desktop app..."
$env:DOCFORGE_PYTHON = $VENV_PYTHON
npm run tauri build
Write-Host ""

Write-Host "=== Build complete ==="
Write-Host "Output: $PROJECT_ROOT\apps\desktop\src-tauri\target\release\bundle\"
