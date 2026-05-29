from __future__ import annotations

import json
from typing import Protocol

from engine.models import FormatOverride
from engine.structure.models import RecognizedStructure, StructureInput


class LlmClient(Protocol):
    def parse_format_instruction(self, instruction: str) -> FormatOverride:
        ...

    def recognize_structure(self, structure_input: StructureInput) -> RecognizedStructure:
        ...


def parse_format_override_json(raw_text: str) -> FormatOverride:
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError:
        payload = _extract_first_json_object(raw_text)

    return FormatOverride.model_validate(payload)


def parse_recognized_structure_json(raw_text: str) -> RecognizedStructure:
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError:
        payload = _extract_first_json_object(raw_text)

    return RecognizedStructure.model_validate(payload)


def _extract_first_json_object(raw_text: str) -> object:
    decoder = json.JSONDecoder()

    for index, character in enumerate(raw_text):
        if character != "{":
            continue
        try:
            payload, _ = decoder.raw_decode(raw_text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload

    raise ValueError("Model did not return valid JSON")
