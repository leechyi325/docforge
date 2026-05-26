import pytest

from engine.llm.base import parse_format_override_json
from engine.llm.client import create_llm_client
from engine.llm.settings import LlmSettings, normalize_provider


def test_normalize_provider_keeps_openai_alias():
    assert normalize_provider("openai") == "openai-responses"
    assert normalize_provider("openai-compatible") == "openai-compatible"


def test_openai_alias_normalizes_to_responses_provider():
    settings = LlmSettings(provider="openai", api_key="test", model="gpt-test")

    assert settings.normalized_provider == "openai-responses"


def test_openai_responses_provider_has_default_model():
    settings = LlmSettings(provider="openai", api_key="test")

    assert settings.model_or_env() == "gpt-4.1-mini"
    settings.validate_for_remote_use()


def test_local_client_factory_parses_instruction():
    client = create_llm_client(LlmSettings(provider="local"))

    override = client.parse_format_instruction("标题用方正小标宋二号居中，正文仿宋三号")

    assert override.title.font == "方正小标宋"
    assert override.body.font == "仿宋"


def test_remote_provider_requires_model_when_instruction_is_parsed():
    settings = LlmSettings(
        provider="openai-compatible",
        api_key="test",
        base_url="https://example.test/v1",
    )

    with pytest.raises(ValueError, match="requires --llm-model"):
        settings.validate_for_remote_use()


def test_normalize_provider_rejects_unknown_provider():
    with pytest.raises(ValueError, match="Unsupported llm provider"):
        normalize_provider("unknown-provider")


def test_anthropic_settings_read_anthropic_api_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-test")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-test")

    settings = LlmSettings(provider="anthropic-messages", model="claude-test")

    assert settings.api_key_or_env() == "anthropic-test"


def test_parse_format_override_json_extracts_embedded_object():
    override = parse_format_override_json(
        'Here is the override: {"body": {"font": "仿宋", "line_spacing": "28pt"}}'
    )

    assert override.body.font == "仿宋"
    assert override.body.line_spacing == "28pt"
