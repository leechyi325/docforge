from __future__ import annotations

from typing import Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class ParagraphStyle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    font: Optional[str] = None
    size: Optional[str] = None
    bold: Optional[bool] = None
    align: Optional[Literal["left", "center", "right", "justify"]] = None
    first_line_indent: Optional[str] = None
    line_spacing: Optional[str] = None
    space_before: Optional[str] = None
    space_after: Optional[str] = None


class PageSetup(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paper: str = "A4"
    margin_top: str = "3.7cm"
    margin_bottom: str = "3.5cm"
    margin_left: str = "2.8cm"
    margin_right: str = "2.6cm"


class Profile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    required_fields: List[str] = Field(default_factory=list)
    page: PageSetup = Field(default_factory=PageSetup)
    title: ParagraphStyle
    body: ParagraphStyle
    headings: Dict[str, ParagraphStyle] = Field(default_factory=dict)
    special_sections: Dict[str, ParagraphStyle] = Field(default_factory=dict)
    auto_fix_rules: List[str] = Field(default_factory=list)
    template: Optional[str] = None


class FormatOverride(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Optional[ParagraphStyle] = None
    body: Optional[ParagraphStyle] = None
    headings: Dict[str, ParagraphStyle] = Field(default_factory=dict)
    page: Optional[PageSetup] = None
    notes: List[str] = Field(default_factory=list)


class DocumentStructure(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_type: str
    title: Optional[str] = None
    headings: List[str] = Field(default_factory=list)
    required_fields_present: Dict[str, bool] = Field(default_factory=dict)


class Location(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["document", "paragraph", "section"]
    index: Optional[int] = None
    key: Optional[str] = None


class FixAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal[
        "set_paragraph_format",
        "apply_heading_style",
        "set_page_setup",
        "set_section_format",
    ]
    target: Location
    properties: Union[ParagraphStyle, PageSetup]


class Issue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    severity: Literal["info", "warning", "error"]
    message: str
    location: Location
    fix_action: Optional[FixAction] = None
