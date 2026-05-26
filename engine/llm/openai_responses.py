from __future__ import annotations

from typing import Optional

from engine.llm.base import parse_format_override_json
from engine.llm.prompts import FORMAT_INSTRUCTION_PROMPT
from engine.llm.schemas import FORMAT_OVERRIDE_SCHEMA
from engine.llm.settings import LlmSettings
from engine.models import FormatOverride


class OpenAIResponsesClient:
    def __init__(self, settings: LlmSettings, client: Optional[object] = None) -> None:
        settings.validate_for_remote_use()
        self.model = settings.model_or_env()

        if client is not None:
            self.client = client
            return

        from openai import OpenAI

        kwargs = {"api_key": settings.api_key_or_env()}
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
