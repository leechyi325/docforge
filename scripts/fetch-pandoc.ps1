# Download Pandoc sidecar binary for Windows
$ErrorActionPreference = "Stop"

$PANDOC_VERSION = if ($env:PANDOC_VERSION) { $env:PANDOC_VERSION } else { "3.9.0.2" }
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$PROJECT_ROOT = Split-Path -Parent $SCRIPT_DIR
$BINARIES_DIR = "$PROJECT_ROOT\apps\desktop\src-tauri\binaries"
New-Item -ItemType Directory -Force -Path $BINARIES_DIR | Out-Null

$TARGET = "x86_64-pc-windows-msvc"
$ARCHIVE_NAME = "pandoc-$PANDOC_VERSION-windows-x86_64.zip"
$URL = "https://github.com/jgm/pandoc/releases/download/$PANDOC_VERSION/$ARCHIVE_NAME"
$DEST = "$BINARIES_DIR\pandoc-$TARGET.exe"

if (Test-Path $DEST) {
    Write-Host "Pandoc sidecar already exists at $DEST"
    exit 0
}

$TMPDIR = New-Item -ItemType Directory -Path ([System.IO.Path]::GetTempPath() + [System.Guid]::NewGuid().ToString())
try {
    Write-Host "Downloading Pandoc $PANDOC_VERSION for $TARGET..."
    $archivePath = "$TMPDIR\$ARCHIVE_NAME"
    Invoke-WebRequest -Uri $URL -OutFile $archivePath -UseBasicParsing

    Write-Host "Extracting..."
    Expand-Archive -Path $archivePath -DestinationPath $TMPDIR -Force

    # Find pandoc.exe in extracted directory
    $pandocExe = Get-ChildItem -Path $TMPDIR -Recurse -Filter "pandoc.exe" | Select-Object -First 1
    if (-not $pandocExe) {
        throw "pandoc.exe not found in archive"
    }

    Copy-Item $pandocExe.FullName $DEST -Force
    Write-Host "Pandoc sidecar ready: $DEST"
} finally {
    Remove-Item -Recurse -Force $TMPDIR -ErrorAction SilentlyContinue
}
