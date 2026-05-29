from __future__ import annotations

import re
from typing import Dict, List, Optional

from engine.llm.base import LlmClient
from engine.llm.settings import LlmSettings
from engine.models import FormatOverride, ParagraphStyle
from engine.structure.models import RecognizedStructure, StructureInput


class OpenAIClient:
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4.1-mini") -> None:
        from engine.llm.openai_responses import OpenAIResponsesClient

        self._client = OpenAIResponsesClient(
            LlmSettings(provider="openai-responses", api_key=api_key, model=model)
        )

    def parse_format_instruction(self, instruction: str) -> FormatOverride:
        return self._client.parse_format_instruction(instruction)

    def recognize_structure(self, structure_input: StructureInput) -> RecognizedStructure:
        return self._client.recognize_structure(structure_input)


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

    if "二级标题" in instruction:
        headings["heading_2"] = ParagraphStyle(
            font=_find_font_after(instruction, "二级标题", ["楷体", "黑体", "仿宋", "宋体"]),
            size=_find_size_near(instruction, "二级标题"),
        )

    if "三级标题" in instruction:
        headings["heading_3"] = ParagraphStyle(
            font=_find_font_after(instruction, "三级标题", ["仿宋", "楷体", "黑体", "宋体"]),
            size=_find_size_near(instruction, "三级标题"),
        )
        h3_start = instruction.find("三级标题")
        if "加粗" in instruction[h3_start:h3_start + 30]:
            headings["heading_3"].bold = True

    return FormatOverride(title=title, body=body, headings=headings)


class LocalLlmClient:
    def parse_format_instruction(self, instruction: str) -> FormatOverride:
        return parse_format_instruction_locally(instruction)

    def recognize_structure(self, structure_input: StructureInput) -> RecognizedStructure:
        raise ValueError(
            "AI 智能识别需要配置远程模型。请在 AI 设置中配置 API Key 和模型，或改用“通用格式文档”。"
        )


def create_llm_client(settings: LlmSettings) -> LlmClient:
    provider = settings.normalized_provider
    if provider == "local":
        return LocalLlmClient()
    if provider == "openai-responses":
        from engine.llm.openai_responses import OpenAIResponsesClient

        return OpenAIResponsesClient(settings)
    if provider == "openai-compatible":
        from engine.llm.openai_compatible import OpenAICompatibleClient

        return OpenAICompatibleClient(settings)
    if provider == "anthropic-messages":
        from engine.llm.anthropic_messages import AnthropicMessagesClient

        return AnthropicMessagesClient(settings)
    raise ValueError(f"Unsupported llm provider: {settings.provider}")


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
