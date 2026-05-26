from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from engine.converters.pandoc import convert_markdown_to_docx
from engine.diagnostics.diagnose import diagnose_docx
from engine.formatter.docx_formatter import apply_profile_formatting
from engine.models import FormatOverride, Issue, Profile

MARKDOWN_SUFFIXES = {".md", ".markdown"}


class UnsupportedInputError(ValueError):
    pass


@dataclass(frozen=True)
class FormatResult:
    output_path: Path
    issues: List[Issue]


def format_document(
    input_path: Path,
    output_path: Path,
    profile: Profile,
    override: Optional[FormatOverride] = None,
) -> FormatResult:
    input_path = Path(input_path)
    output_path = Path(output_path)
    _validate_paths(input_path, output_path)

    source_docx = _prepare_source_docx(input_path, output_path)
    apply_profile_formatting(source_docx, output_path, profile, override)
    issues = diagnose_docx(output_path, profile)
    return FormatResult(output_path=output_path, issues=issues)


def _validate_paths(input_path: Path, output_path: Path) -> None:
    if not input_path.exists():
        raise FileNotFoundError(f"Input file does not exist: {input_path}")
    if output_path.suffix.lower() != ".docx":
        raise ValueError("Output path must end with .docx")
    if input_path.resolve() == output_path.resolve():
        raise ValueError("Output path must be different from input path")

    suffix = input_path.suffix.lower()
    if suffix == ".doc" or suffix not in MARKDOWN_SUFFIXES | {".docx"}:
        raise UnsupportedInputError("Unsupported input format. DocForge currently supports Markdown and .docx input.")


def _prepare_source_docx(input_path: Path, output_path: Path) -> Path:
    if input_path.suffix.lower() == ".docx":
        return input_path

    temp_docx = output_path.with_suffix(".pandoc.docx")
    return convert_markdown_to_docx(input_path, temp_docx)
