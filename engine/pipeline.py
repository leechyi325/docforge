from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from engine.converters.pandoc import convert_markdown_to_docx
from engine.diagnostics.diagnose import diagnose_docx
from engine.formatter.docx_formatter import apply_profile_formatting
from engine.llm.base import LlmClient
from engine.models import FormatOverride, Issue, Profile
from engine.structure import (
    StructureSummary,
    extract_structure_input,
    summarize_structure,
    validate_recognized_structure,
)

MARKDOWN_SUFFIXES = {".md", ".markdown"}


def _emit_progress(stage: str, message: str, progress: float | None = None) -> None:
    event = {"stage": stage, "message": message}
    if progress is not None:
        event["progress"] = progress
    print(json.dumps(event, ensure_ascii=False), file=sys.stderr, flush=True)


class UnsupportedInputError(ValueError):
    pass


@dataclass(frozen=True)
class FormatResult:
    output_path: Path
    issues: List[Issue]
    structure_summary: Optional[StructureSummary] = None


def format_document(
    input_path: Path,
    output_path: Path,
    profile: Profile,
    override: Optional[FormatOverride] = None,
    llm_client: Optional[LlmClient] = None,
) -> FormatResult:
    input_path = Path(input_path)
    output_path = Path(output_path)
    _validate_paths(input_path, output_path)

    _emit_progress("preparing", "验证输入路径", 0.1)

    if profile.id == "default" and llm_client is None:
        raise ValueError("AI 智能识别需要配置远程模型。请在 AI 设置中配置 API Key 和模型，或改用“通用格式文档”。")

    source_docx = _prepare_source_docx(input_path, output_path)
    recognized_structure = None
    structure_summary = None

    if profile.id == "default":
        _emit_progress("recognizing", "正在进行 AI 结构识别", 0.25)
        structure_input = extract_structure_input(source_docx)
        recognized_structure = validate_recognized_structure(
            llm_client.recognize_structure(structure_input),
            structure_input,
        )
        structure_summary = summarize_structure(recognized_structure)

    _emit_progress("formatting", "正在应用格式化规则", 0.4)

    apply_profile_formatting(source_docx, output_path, profile, override, structure=recognized_structure)

    _emit_progress("diagnosing", "正在诊断格式问题", 0.7)

    issues = diagnose_docx(output_path, profile)

    _emit_progress("done", "处理完成", 1.0)

    return FormatResult(output_path=output_path, issues=issues, structure_summary=structure_summary)


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
