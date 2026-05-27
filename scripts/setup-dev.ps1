# Create placeholder sidecar binaries for development (Windows)
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$PROJECT_ROOT = Split-Path -Parent $SCRIPT_DIR
$BINARIES_DIR = "$PROJECT_ROOT\apps\desktop\src-tauri\binaries"
New-Item -ItemType Directory -Force -Path $BINARIES_DIR | Out-Null

$TARGET = "x86_64-pc-windows-msvc"

foreach ($name in @("docforge-engine", "pandoc")) {
    $path = "$BINARIES_DIR\$name-$TARGET.exe"
    if (-not (Test-Path $path)) {
        Set-Content -Path $path -Value "@echo off"
        Write-Host "Created placeholder: $path"
    }
}

Write-Host "Dev sidecar placeholders ready."
