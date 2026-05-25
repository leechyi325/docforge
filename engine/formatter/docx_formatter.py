from __future__ import annotations

from pathlib import Path
from typing import Optional

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt

from engine.models import FormatOverride, PageSetup, ParagraphStyle, Profile
from engine.style_utils import chinese_size_to_pt, merge_style, parse_length_to_pt

ALIGNMENT = {
    "left": WD_ALIGN_PARAGRAPH.LEFT,
    "center": WD_ALIGN_PARAGRAPH.CENTER,
    "right": WD_ALIGN_PARAGRAPH.RIGHT,
    "justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
}


def apply_profile_formatting(
    input_docx: Path,
    output_docx: Path,
    profile: Profile,
    override: Optional[FormatOverride] = None,
) -> Path:
    document = Document(input_docx)
    _apply_page_setup(document, override.page if override and override.page else profile.page)

    title_style = merge_style(profile.title, override.title if override else None)
    body_style = merge_style(profile.body, override.body if override else None)
    heading_overrides = override.headings if override else {}

    for index, paragraph in enumerate(document.paragraphs):
        if index == 0:
            _apply_paragraph_style(paragraph, title_style)
        elif _looks_like_heading(paragraph.text):
            style_key = "heading_1" if paragraph.text.strip().startswith(("一、", "二、", "三、")) else "heading_2"
            base = profile.headings.get(style_key, body_style)
            _apply_paragraph_style(paragraph, merge_style(base, heading_overrides.get(style_key)))
        else:
            _apply_paragraph_style(paragraph, body_style)

    output_docx.parent.mkdir(parents=True, exist_ok=True)
    document.save(output_docx)
    return output_docx


def _apply_page_setup(document: Document, page: PageSetup) -> None:
    for section in document.sections:
        section.top_margin = Cm(parse_length_to_pt(page.margin_top) / 28.3464567)
        section.bottom_margin = Cm(parse_length_to_pt(page.margin_bottom) / 28.3464567)
        section.left_margin = Cm(parse_length_to_pt(page.margin_left) / 28.3464567)
        section.right_margin = Cm(parse_length_to_pt(page.margin_right) / 28.3464567)


def _apply_paragraph_style(paragraph, style: ParagraphStyle) -> None:
    if style.align:
        paragraph.alignment = ALIGNMENT[style.align]
    if style.first_line_indent:
        paragraph.paragraph_format.first_line_indent = Pt(parse_length_to_pt(style.first_line_indent))
    if style.line_spacing:
        paragraph.paragraph_format.line_spacing = Pt(parse_length_to_pt(style.line_spacing))
    if style.space_before:
        paragraph.paragraph_format.space_before = Pt(parse_length_to_pt(style.space_before))
    if style.space_after:
        paragraph.paragraph_format.space_after = Pt(parse_length_to_pt(style.space_after))

    runs = paragraph.runs or [paragraph.add_run("")]
    for run in runs:
        if style.font:
            run.font.name = style.font
            run._element.rPr.rFonts.set("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}eastAsia", style.font)
        if style.size:
            run.font.size = Pt(chinese_size_to_pt(style.size))
        if style.bold is not None:
            run.font.bold = style.bold


def _looks_like_heading(text: str) -> bool:
    stripped = text.strip()
    return stripped.startswith(("一、", "二、", "三、", "四、", "五、", "（一）", "（二）", "（三）"))
