#!/usr/bin/env bash
set -euo pipefail

# Create placeholder sidecar binaries for development.
# These are replaced by real builds via build-desktop.sh.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BINARIES_DIR="$PROJECT_ROOT/apps/desktop/src-tauri/binaries"
mkdir -p "$BINARIES_DIR"

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

ENGINE="$BINARIES_DIR/docforge-engine-${TARGET}"
PANDOC="$BINARIES_DIR/pandoc-${TARGET}"

if [ "$(uname -s)" != "Darwin" ]; then
  ENGINE="${ENGINE}.exe"
  PANDOC="${PANDOC}.exe"
fi

for f in "$ENGINE" "$PANDOC"; do
  if [ ! -f "$f" ]; then
    echo '#!/bin/sh' > "$f"
    chmod +x "$f"
    echo "Created placeholder: $f"
  fi
done

echo "Dev sidecar placeholders ready."
