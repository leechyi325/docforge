from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


ParagraphRole = Literal[
    "title",
    "date",
    "department",
    "heading_1",
    "heading_2",
    "heading_3",
    "body",
    "table_caption",
    "table_note",
    "attachment",
    "signature",
    "unknown",
]

TableRole = Literal[
    "data_table",
    "schedule_table",
    "signature_table",
    "appendix_table",
    "unknown",
]


class ParagraphCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    index: int
    text: str
    char_count: int
    is_empty: bool = False
    alignment: Optional[Literal["left", "center", "right", "justify", "unknown"]] = None
    is_bold: Optional[bool] = None
    font_hint: Optional[str] = None
    size_hint: Optional[float] = None
    numbering_hint: Optional[str] = None


class TableCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    index: int
    rows: int
    columns: int
    before_paragraph_index: Optional[int] = None
    after_paragraph_index: Optional[int] = None
    caption_paragraph_index: Optional[int] = None
    sample_cells: List[List[str]]


class StructureInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_path: str
    paragraphs: List[ParagraphCandidate]
    tables: List[TableCandidate]


class RecognizedParagraph(BaseModel):
    model_config = ConfigDict(extra="forbid")

    index: int
    role: ParagraphRole
    confidence: float = Field(ge=0, le=1)
    reason: str = ""


class RecognizedTable(BaseModel):
    model_config = ConfigDict(extra="forbid")

    index: int
    role: TableRole
    confidence: float = Field(ge=0, le=1)
    reason: str = ""


class RecognizedStructure(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paragraphs: List[RecognizedParagraph]
    tables: List[RecognizedTable]
    notes: List[str] = Field(default_factory=list)


class StructureSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    counts: Dict[str, int]
