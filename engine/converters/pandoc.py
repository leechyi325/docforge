from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional


class PandocNotFoundError(RuntimeError):
    pass


def _find_pandoc() -> str:
    custom = os.environ.get("DOCFORGE_PANDOC")
    if custom and Path(custom).exists():
        return custom
    found = shutil.which("pandoc")
    if found:
        return found
    raise PandocNotFoundError("Pandoc is not installed or not available on PATH")


def convert_markdown_to_docx(
    input_path: Path,
    output_path: Path,
    reference_doc: Optional[Path] = None,
) -> Path:
    pandoc = _find_pandoc()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [pandoc, str(input_path), "-o", str(output_path)]
    if reference_doc is not None:
        command.extend(["--reference-doc", str(reference_doc)])

    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Pandoc failed: {result.stderr.strip()}")
    return output_path
