#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=== DocForge Desktop Build ==="
echo ""

# Step 1: Setup environment
echo "[1/4] Setting up environment..."
VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"
if [ ! -f "$VENV_PYTHON" ]; then
  echo "Creating virtual environment..."
  python3 -m venv "$PROJECT_ROOT/.venv"
  "$VENV_PYTHON" -m pip install -e "$PROJECT_ROOT[dev]"
fi
cd "$PROJECT_ROOT/apps/desktop"
npm install
echo ""

# Step 2: Fetch Pandoc
echo "[2/4] Fetching Pandoc sidecar..."
"$SCRIPT_DIR/fetch-pandoc.sh"
echo ""

# Step 3: Build Python engine
echo "[3/4] Building Python engine..."
"$SCRIPT_DIR/build-engine.sh"
echo ""

# Step 4: Build Tauri app
echo "[4/4] Building Tauri desktop app..."
export DOCFORGE_PYTHON="$VENV_PYTHON"
npm run tauri build
echo ""

echo "=== Build complete ==="
echo "Output: $PROJECT_ROOT/apps/desktop/src-tauri/target/release/bundle/"
