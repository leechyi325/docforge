from __future__ import annotations

import json
import os
import re
from typing import Dict, List, Optional

from engine.llm.prompts import FORMAT_INSTRUCTION_PROMPT
from engine.llm.schemas import FORMAT_OVERRIDE_SCHEMA
from engine.models import FormatOverride, ParagraphStyle


class OpenAIClient:
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4.1-mini") -> None:
        from openai import OpenAI

        self.model = model
        self.client = OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))

    def parse_format_instruction(self, instruction: str) -> FormatOverride:
        response = self.client.responses.create(
            model=self.model,
            input=[
                {"role": "system", "content": FORMAT_INSTRUCTION_PROMPT},
                {"role": "user", "content": instruction},
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "format_override",
                    "schema": FORMAT_OVERRIDE_SCHEMA,
                    "strict": True,
                }
            },
        )
        raw_text = response.output_text
        return FormatOverride.model_validate(json.loads(raw_text))


def parse_format_instruction_locally(instruction: str) -> FormatOverride:
    title = ParagraphStyle()
    body = ParagraphStyle()
    headings: Dict[str, ParagraphStyle] = {}

    if "标题" in instruction:
        title.font = _find_font(instruction, ["方正小标宋", "小标宋", "黑体", "宋体"])
        title.size = _find_size_near(instruction, "标题")
        if "居中" in instruction:
            title.align = "center"

    if "正文" in instruction:
        body.font = _find_font_after(instruction, "正文", ["仿宋", "宋体", "黑体", "楷体"])
        body.size = _find_size_near(instruction, "正文")

    spacing_match = re.search(r"行距(?:固定)?\s*(\d+(?:\.\d+)?)\s*磅", instruction)
    if spacing_match:
        body.line_spacing = f"{spacing_match.group(1)}pt"

    if "一级标题" in instruction:
        headings["heading_1"] = ParagraphStyle(
            font=_find_font_after(instruction, "一级标题", ["黑体", "楷体", "仿宋", "宋体"]),
            size=_find_size_near(instruction, "一级标题"),
        )

    return FormatOverride(title=title, body=body, headings=headings)


def _find_font(text: str, fonts: List[str]) -> Optional[str]:
    for font in fonts:
        if font in text:
            return font
    return None


def _find_font_after(text: str, marker: str, fonts: List[str]) -> Optional[str]:
    index = text.find(marker)
    if index == -1:
        return None
    return _find_font(text[index : index + 40], fonts)


def _find_size_near(text: str, marker: str) -> Optional[str]:
    index = text.find(marker)
    if index == -1:
        return None
    window = text[index : index + 50]
    match = re.search(r"(初号|小初|一号|小一|二号|小二|三号|小三|四号|小四|五号|小五)", window)
    return match.group(1) if match else None
