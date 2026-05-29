from __future__ import annotations

import json
from typing import Optional

from engine.llm.base import parse_format_override_json, parse_recognized_structure_json
from engine.llm.prompts import FORMAT_INSTRUCTION_PROMPT, STRUCTURE_RECOGNITION_PROMPT
from engine.llm.schemas import FORMAT_OVERRIDE_SCHEMA, STRUCTURE_RECOGNITION_SCHEMA
from engine.llm.settings import LlmSettings
from engine.models import FormatOverride
from engine.structure.models import RecognizedStructure, StructureInput


class OpenAIResponsesClient:
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
        return parse_format_override_json(response.output_text)

    def recognize_structure(self, structure_input: StructureInput) -> RecognizedStructure:
        response = self.client.responses.create(
            model=self.model,
            input=[
                {"role": "system", "content": STRUCTURE_RECOGNITION_PROMPT},
                {
                    "role": "user",
                    "content": json.dumps(structure_input.model_dump(), ensure_ascii=False),
                },
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "recognized_structure",
                    "schema": STRUCTURE_RECOGNITION_SCHEMA,
                    "strict": True,
                }
            },
        )
        return parse_recognized_structure_json(response.output_text)
