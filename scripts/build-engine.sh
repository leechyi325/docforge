#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BINARIES_DIR="$PROJECT_ROOT/apps/desktop/src-tauri/binaries"
VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"

# Detect target triple
ARCH="$(uname -m)"
case "$(uname -s)" in
  Darwin)
    if [ "$ARCH" = "arm64" ]; then
      TARGET="aarch64-apple-darwin"
    else
      TARGET="x86_64-apple-darwin"
    fi
    ;;
  MINGW*|MSYS*|CYGWIN*|Windows_NT)
    TARGET="x86_64-pc-windows-msvc"
    ;;
  *)
    echo "Unsupported OS" >&2
    exit 1
    ;;
esac

echo "Building DocForge engine for ${TARGET}..."

# Ensure venv exists
if [ ! -f "$VENV_PYTHON" ]; then
  echo "Creating virtual environment..."
  python3 -m venv "$PROJECT_ROOT/.venv"
  "$VENV_PYTHON" -m pip install -e "$PROJECT_ROOT[dev]"
fi

# Install PyInstaller
"$VENV_PYTHON" -m pip install pyinstaller --quiet

# Build with PyInstaller
mkdir -p "$BINARIES_DIR"
"$VENV_PYTHON" -m PyInstaller \
  "$PROJECT_ROOT/engine/engine.spec" \
  --distpath "$BINARIES_DIR" \
  --workpath "$PROJECT_ROOT/build/pyinstaller" \
  --clean \
  --noconfirm

# Rename to Tauri sidecar convention
BINARY_NAME="docforge-engine"
if [ "$(uname -s)" != "Darwin" ]; then
  BINARY_NAME="${BINARY_NAME}.exe"
fi

SRC="$BINARIES_DIR/$BINARY_NAME"
DST="$BINARIES_DIR/docforge-engine-${TARGET}"
[ "$(uname -s)" != "Darwin" ] && DST="${DST}.exe"

mv "$SRC" "$DST"
chmod +x "$DST"

echo "Engine sidecar ready: $DST"
