from __future__ import annotations

import json
from typing import Optional

from engine.llm.base import parse_format_override_json, parse_recognized_structure_json
from engine.llm.prompts import FORMAT_INSTRUCTION_PROMPT, STRUCTURE_RECOGNITION_PROMPT
from engine.llm.schemas import FORMAT_OVERRIDE_SCHEMA, STRUCTURE_RECOGNITION_SCHEMA
from engine.llm.settings import LlmSettings
from engine.models import FormatOverride
from engine.structure.models import RecognizedStructure, StructureInput


_JSON_ONLY_PROMPT = (
    f"{FORMAT_INSTRUCTION_PROMPT}\n"
    "Return only a JSON object matching the DocForge format_override schema. "
    "Do not include Markdown code fences."
)

_STRUCTURE_JSON_ONLY_PROMPT = (
    f"{STRUCTURE_RECOGNITION_PROMPT}\n"
    "Return only a JSON object matching the DocForge recognized_structure schema. "
    "Do not include Markdown code fences."
)


class OpenAICompatibleClient:
    def __init__(self, settings: LlmSettings, client: Optional[object] = None) -> None:
        settings.validate_for_remote_use()
        self.model = settings.model_or_env()

        if client is not None:
            self.client = client
            return

        from openai import OpenAI

        kwargs = {"api_key": settings.api_key_or_env(), "timeout": 60.0}
        base_url = settings.base_url_or_env()
        if base_url:
            kwargs["base_url"] = base_url
        self.client = OpenAI(**kwargs)

    def parse_format_instruction(self, instruction: str) -> FormatOverride:
        response = self._create_completion(instruction)
        return parse_format_override_json(response.choices[0].message.content)

    def recognize_structure(self, structure_input: StructureInput) -> RecognizedStructure:
        response = self._create_structure_completion(structure_input)
        return parse_recognized_structure_json(response.choices[0].message.content)

    def _create_completion(self, instruction: str) -> object:
        kwargs = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": _JSON_ONLY_PROMPT},
                {"role": "user", "content": instruction},
            ],
        }

        try:
            return self.client.chat.completions.create(
                **kwargs,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "format_override",
                        "schema": FORMAT_OVERRIDE_SCHEMA,
                        "strict": True,
                    },
                },
            )
        except Exception as error:
            if not _is_response_format_unsupported(error):
                raise

        try:
            return self.client.chat.completions.create(
                **kwargs,
                response_format={"type": "json_object"},
            )
        except Exception as error:
            if not _is_response_format_unsupported(error):
                raise

        return self.client.chat.completions.create(**kwargs)

    def _create_structure_completion(self, structure_input: StructureInput) -> object:
        kwargs = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": _STRUCTURE_JSON_ONLY_PROMPT},
                {
                    "role": "user",
                    "content": json.dumps(structure_input.model_dump(), ensure_ascii=False),
                },
            ],
        }

        try:
            return self.client.chat.completions.create(
                **kwargs,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "recognized_structure",
                        "schema": STRUCTURE_RECOGNITION_SCHEMA,
                        "strict": True,
                    },
                },
            )
        except Exception as error:
            if not _is_response_format_unsupported(error):
                raise

        try:
            return self.client.chat.completions.create(
                **kwargs,
                response_format={"type": "json_object"},
            )
        except Exception as error:
            if not _is_response_format_unsupported(error):
                raise

        return self.client.chat.completions.create(**kwargs)


def _is_response_format_unsupported(error: Exception) -> bool:
    message = str(error).lower()
    return "response_format" in message and any(
        marker in message
        for marker in ("json_schema", "json_object", "unsupported")
    )
