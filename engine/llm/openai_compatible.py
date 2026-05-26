from __future__ import annotations

from typing import Optional

from engine.llm.base import parse_format_override_json
from engine.llm.prompts import FORMAT_INSTRUCTION_PROMPT
from engine.llm.schemas import FORMAT_OVERRIDE_SCHEMA
from engine.llm.settings import LlmSettings
from engine.models import FormatOverride


_JSON_ONLY_PROMPT = (
    f"{FORMAT_INSTRUCTION_PROMPT}\n"
    "Return only a JSON object matching the DocForge format_override schema. "
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


def _is_response_format_unsupported(error: Exception) -> bool:
    message = str(error).lower()
    return "response_format" in message and any(
        marker in message
        for marker in ("json_schema", "json_object", "unsupported")
    )
