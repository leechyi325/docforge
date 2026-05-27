# Build DocForge engine sidecar for Windows
$ErrorActionPreference = "Stop"

$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$PROJECT_ROOT = Split-Path -Parent $SCRIPT_DIR
$BINARIES_DIR = "$PROJECT_ROOT\apps\desktop\src-tauri\binaries"
$VENV_PYTHON = "$PROJECT_ROOT\.venv\Scripts\python.exe"

$TARGET = "x86_64-pc-windows-msvc"

Write-Host "Building DocForge engine for $TARGET..."

# Ensure venv exists
if (-not (Test-Path $VENV_PYTHON)) {
    Write-Host "Creating virtual environment..."
    python -m venv "$PROJECT_ROOT\.venv"
    & $VENV_PYTHON -m pip install -e "$PROJECT_ROOT[dev]"
}

# Install PyInstaller
& $VENV_PYTHON -m pip install pyinstaller --quiet

# Build
New-Item -ItemType Directory -Force -Path $BINARIES_DIR | Out-Null
& $VENV_PYTHON -m PyInstaller `
    "$PROJECT_ROOT\engine\engine.spec" `
    --distpath $BINARIES_DIR `
    --workpath "$PROJECT_ROOT\build\pyinstaller" `
    --clean `
    --noconfirm

# Rename
$SRC = "$BINARIES_DIR\docforge-engine.exe"
$DST = "$BINARIES_DIR\docforge-engine-$TARGET.exe"
Move-Item -Force $SRC $DST

Write-Host "Engine sidecar ready: $DST"
