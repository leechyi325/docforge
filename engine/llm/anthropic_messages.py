from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Callable, Dict, Optional, cast

from engine.llm.base import parse_format_override_json, parse_recognized_structure_json
from engine.llm.prompts import FORMAT_INSTRUCTION_PROMPT, STRUCTURE_RECOGNITION_PROMPT
from engine.llm.settings import LlmSettings
from engine.models import FormatOverride
from engine.structure.models import RecognizedStructure, StructureInput


Transport = Callable[[str, Dict[str, str], Dict[str, object]], Dict[str, object]]

DEFAULT_ANTHROPIC_BASE_URL = "https://api.anthropic.com"
ANTHROPIC_VERSION = "2023-06-01"

_JSON_ONLY_PROMPT = (
    f"{FORMAT_INSTRUCTION_PROMPT}\n"
    "Return only a JSON object matching the DocForge format_override schema. "
    "Do not include Markdown or explanation."
)


class AnthropicMessagesClient:
    def __init__(
        self, settings: LlmSettings, transport: Optional[Transport] = None
    ) -> None:
        settings.validate_for_remote_use()
        self.model = cast(str, settings.model_or_env())
        self.api_key = cast(str, settings.api_key_or_env())
        self.base_url = (
            settings.base_url_or_env() or DEFAULT_ANTHROPIC_BASE_URL
        ).rstrip("/")
        self.transport = transport or _post_json

    def parse_format_instruction(self, instruction: str) -> FormatOverride:
        response = self.transport(
            f"{self.base_url}/v1/messages",
            {
                "content-type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": ANTHROPIC_VERSION,
            },
            {
                "model": self.model,
                "max_tokens": 1200,
                "system": _JSON_ONLY_PROMPT,
                "messages": [{"role": "user", "content": instruction}],
            },
        )
        raw_text = _extract_text_content(response)
        return parse_format_override_json(raw_text)

    def recognize_structure(self, structure_input: StructureInput) -> RecognizedStructure:
        response = self.transport(
            f"{self.base_url}/v1/messages",
            {
                "content-type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": ANTHROPIC_VERSION,
            },
            {
                "model": self.model,
                "max_tokens": 3000,
                "system": STRUCTURE_RECOGNITION_PROMPT,
                "messages": [
                    {
                        "role": "user",
                        "content": json.dumps(structure_input.model_dump(), ensure_ascii=False),
                    }
                ],
            },
        )
        raw_text = _extract_text_content(response)
        return parse_recognized_structure_json(raw_text)


def _extract_text_content(response: Dict[str, object]) -> str:
    content = response.get("content")
    if not isinstance(content, list):
        raise ValueError("Anthropic Messages response did not include text content")

    text_blocks = [
        item["text"]
        for item in content
        if isinstance(item, dict)
        and item.get("type") == "text"
        and isinstance(item.get("text"), str)
    ]
    if not text_blocks:
        raise ValueError("Anthropic Messages response did not include text content")

    return "\n".join(text_blocks)


def _post_json(
    url: str, headers: Dict[str, str], payload: Dict[str, object]
) -> Dict[str, object]:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            parsed = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Anthropic Messages API failed: {_error_message(body)}") from error

    if not isinstance(parsed, dict):
        raise ValueError("Anthropic Messages API returned non-object JSON")
    return parsed


def _error_message(body: str) -> str:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return body

    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict) and isinstance(error.get("message"), str):
            return error["message"]
        if isinstance(payload.get("message"), str):
            return payload["message"]

    return body
