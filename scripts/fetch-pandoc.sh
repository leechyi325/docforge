#!/usr/bin/env bash
set -euo pipefail

PANDOC_VERSION="${PANDOC_VERSION:-3.9.0.2}"
BINARIES_DIR="$(cd "$(dirname "$0")/.." && pwd)/apps/desktop/src-tauri/binaries"
mkdir -p "$BINARIES_DIR"

ARCH="$(uname -m)"
OS="$(uname -s)"

case "$OS" in
  Darwin)
    if [ "$ARCH" = "arm64" ]; then
      TARGET="aarch64-apple-darwin"
      ARCHIVE_NAME="pandoc-${PANDOC_VERSION}-arm64-macOS.zip"
    else
      TARGET="x86_64-apple-darwin"
      ARCHIVE_NAME="pandoc-${PANDOC_VERSION}-x64-macOS.zip"
    fi
    ;;
  MINGW*|MSYS*|CYGWIN*|Windows_NT)
    TARGET="x86_64-pc-windows-msvc"
    ARCHIVE_NAME="pandoc-${PANDOC_VERSION}-windows-x86_64.zip"
    ;;
  *)
    echo "Unsupported OS: $OS" >&2
    exit 1
    ;;
esac

URL="https://github.com/jgm/pandoc/releases/download/${PANDOC_VERSION}/${ARCHIVE_NAME}"
DEST="${BINARIES_DIR}/pandoc-${TARGET}"
[ "$OS" != "Darwin" ] && DEST="${DEST}.exe"

if [ -f "$DEST" ]; then
  echo "Pandoc sidecar already exists at $DEST"
  exit 0
fi

TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

echo "Downloading Pandoc ${PANDOC_VERSION} for ${TARGET}..."
curl -fsSL "$URL" -o "${TMPDIR}/${ARCHIVE_NAME}"

unzip -q "${TMPDIR}/${ARCHIVE_NAME}" -d "$TMPDIR"

# Pandoc zip contains pandoc-VERSION/bin/pandoc (or pandoc.exe)
if [ "$OS" = "Darwin" ]; then
  find "$TMPDIR" -name "pandoc" -type f | head -1 | xargs -I{} cp {} "$DEST"
else
  find "$TMPDIR" -name "pandoc.exe" -type f | head -1 | xargs -I{} cp {} "$DEST"
fi

chmod +x "$DEST"
echo "Pandoc sidecar ready: $DEST"
