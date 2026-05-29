from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, Optional

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.text.paragraph import Paragraph

from engine.structure.models import ParagraphCandidate, StructureInput, TableCandidate

_CHINESE_NUMERALS = ("一", "二", "三", "四", "五", "六", "七", "八", "九")
_NUMBERED_HEADING_RE = re.compile(r"^\d+[\.、]")


def extract_structure_input(source_docx: Path) -> StructureInput:
    document = Document(source_docx)
    paragraphs: list[ParagraphCandidate] = []
    tables: list[TableCandidate] = []
    pending_after_indexes: list[int] = []
    last_paragraph_index: Optional[int] = None

    for block in _iter_body_blocks(document):
        if isinstance(block, Paragraph):
            candidate = _paragraph_candidate(block, len(paragraphs))
            paragraphs.append(candidate)
            last_paragraph_index = candidate.index
            for table_index in pending_after_indexes:
                tables[table_index].after_paragraph_index = candidate.index
            pending_after_indexes.clear()
            continue

        table_index = len(tables)
        caption_index = _caption_index(paragraphs, last_paragraph_index)
        tables.append(
            TableCandidate(
                index=table_index,
                rows=len(block.rows),
                columns=len(block.columns),
                before_paragraph_index=last_paragraph_index,
                caption_paragraph_index=caption_index,
                sample_cells=_sample_cells(block),
            )
        )
        pending_after_indexes.append(table_index)

    return StructureInput(source_path=str(source_docx), paragraphs=paragraphs, tables=tables)


def _iter_body_blocks(document) -> Iterable[Paragraph | Table]:
    for child in document.element.body.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, document)
        elif isinstance(child, CT_Tbl):
            yield Table(child, document)


def _paragraph_candidate(paragraph: Paragraph, index: int) -> ParagraphCandidate:
    text = paragraph.text.strip()
    first_run = _first_non_empty_run(paragraph)
    return ParagraphCandidate(
        index=index,
        text=text,
        char_count=len(text),
        is_empty=not text,
        alignment=_alignment_hint(paragraph),
        is_bold=_has_bold_run(paragraph),
        font_hint=_font_hint(first_run),
        size_hint=_size_hint(first_run),
        numbering_hint=_numbering_hint(text),
    )


def _alignment_hint(paragraph: Paragraph) -> Optional[str]:
    alignment = paragraph.alignment
    if alignment is None:
        return None
    if alignment == WD_ALIGN_PARAGRAPH.LEFT:
        return "left"
    if alignment == WD_ALIGN_PARAGRAPH.CENTER:
        return "center"
    if alignment == WD_ALIGN_PARAGRAPH.RIGHT:
        return "right"
    if alignment == WD_ALIGN_PARAGRAPH.JUSTIFY:
        return "justify"
    return "unknown"


def _has_bold_run(paragraph: Paragraph) -> bool:
    return any(run.text.strip() and run.font.bold is True for run in paragraph.runs)


def _first_non_empty_run(paragraph: Paragraph):
    for run in paragraph.runs:
        if run.text.strip():
            return run
    return None


def _font_hint(run) -> Optional[str]:
    if run is None:
        return None
    return run.font.name


def _size_hint(run) -> Optional[float]:
    if run is None or run.font.size is None:
        return None
    return float(run.font.size.pt)


def _numbering_hint(text: str) -> Optional[str]:
    if text.startswith(tuple(f"{numeral}、" for numeral in _CHINESE_NUMERALS)):
        return "chinese_heading_1"
    if text.startswith(tuple(f"（{numeral}）" for numeral in _CHINESE_NUMERALS)):
        return "chinese_heading_2"
    if _NUMBERED_HEADING_RE.match(text):
        return "numbered_heading_3"
    return None


def _caption_index(paragraphs: list[ParagraphCandidate], index: Optional[int]) -> Optional[int]:
    if index is None:
        return None
    text = paragraphs[index].text
    if text.startswith("表") or text.lower().startswith("table"):
        return index
    return None


def _sample_cells(table: Table) -> list[list[str]]:
    samples: list[list[str]] = []
    for row in table.rows[:3]:
        samples.append([cell.text.strip() for cell in row.cells[:4]])
    return samples
