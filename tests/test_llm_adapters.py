import pytest
import openai

from engine.llm.anthropic_messages import AnthropicMessagesClient
from engine.llm.openai_responses import OpenAIResponsesClient
from engine.llm.openai_compatible import OpenAICompatibleClient
from engine.llm.settings import LlmSettings


class FakeResponses:
    def __init__(self):
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return type(
            "FakeResponse",
            (),
            {
                "output_text": '{"title":{"font":"方正小标宋","size":"二号","align":"center"},"body":{"font":"仿宋","size":"三号"},"headings":{},"notes":[]}'
            },
        )()


class FakeOpenAIClient:
    def __init__(self):
        self.responses = FakeResponses()


def test_openai_responses_adapter_uses_json_schema():
    fake_client = FakeOpenAIClient()
    client = OpenAIResponsesClient(
        LlmSettings(provider="openai-responses", api_key="test", model="gpt-test"),
        client=fake_client,
    )

    override = client.parse_format_instruction("标题小标宋二号，正文仿宋三号")

    assert override.title.font == "方正小标宋"
    assert fake_client.responses.kwargs["model"] == "gpt-test"
    assert fake_client.responses.kwargs["text"]["format"]["type"] == "json_schema"


def test_openai_responses_adapter_sets_client_timeout(monkeypatch):
    calls = []

    class FakeOpenAI:
        def __init__(self, **kwargs):
            calls.append(kwargs)
            self.responses = FakeResponses()

    monkeypatch.setattr(openai, "OpenAI", FakeOpenAI)

    OpenAIResponsesClient(LlmSettings(provider="openai-responses", api_key="test", model="gpt-test"))

    assert calls[0]["timeout"] == 60.0


class FakeChatCompletions:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        message = type(
            "FakeMessage",
            (),
            {
                "content": '{"title":{"font":"方正小标宋"},"body":{"font":"仿宋","line_spacing":"28pt"},"headings":{},"notes":[]}'
            },
        )()
        choice = type("FakeChoice", (), {"message": message})()
        return type("FakeCompletion", (), {"choices": [choice]})()


class FakeChat:
    def __init__(self):
        self.completions = FakeChatCompletions()


class FakeChatClient:
    def __init__(self):
        self.chat = FakeChat()


def test_openai_compatible_adapter_uses_chat_completions():
    fake_client = FakeChatClient()
    client = OpenAICompatibleClient(
        LlmSettings(
            provider="openai-compatible",
            api_key="test",
            model="deepseek-chat",
            base_url="https://api.example.test/v1",
        ),
        client=fake_client,
    )

    override = client.parse_format_instruction("正文仿宋，行距固定28磅")

    assert override.body.font == "仿宋"
    assert fake_client.chat.completions.calls[0]["model"] == "deepseek-chat"
    assert fake_client.chat.completions.calls[0]["response_format"]["type"] == "json_schema"


def test_openai_compatible_adapter_sets_client_timeout(monkeypatch):
    calls = []

    class FakeOpenAI:
        def __init__(self, **kwargs):
            calls.append(kwargs)
            self.chat = FakeChat()

    monkeypatch.setattr(openai, "OpenAI", FakeOpenAI)

    OpenAICompatibleClient(LlmSettings(provider="openai-compatible", api_key="test", model="deepseek-chat"))

    assert calls[0]["timeout"] == 60.0


class FakeRejectingChatCompletions:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if kwargs.get("response_format", {}).get("type") == "json_schema":
            raise RuntimeError("unsupported response_format json_schema")
        message = type(
            "FakeMessage",
            (),
            {"content": '{"body":{"font":"仿宋"},"headings":{},"notes":[]}'},
        )()
        choice = type("FakeChoice", (), {"message": message})()
        return type("FakeCompletion", (), {"choices": [choice]})()


class FakeRejectingChat:
    def __init__(self):
        self.completions = FakeRejectingChatCompletions()


class FakeRejectingClient:
    def __init__(self):
        self.chat = FakeRejectingChat()


def test_openai_compatible_adapter_retries_json_object_when_schema_is_unsupported():
    fake_client = FakeRejectingClient()
    client = OpenAICompatibleClient(
        LlmSettings(provider="openai-compatible", api_key="test", model="deepseek-chat"),
        client=fake_client,
    )

    override = client.parse_format_instruction("正文仿宋")

    assert override.body.font == "仿宋"
    assert fake_client.chat.completions.calls[1]["response_format"]["type"] == "json_object"


class FakeDoubleRejectingChatCompletions:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if "response_format" in kwargs:
            raise RuntimeError("unsupported response_format")
        message = type(
            "FakeMessage",
            (),
            {"content": '{"body":{"font":"仿宋"},"headings":{},"notes":[]}'},
        )()
        choice = type("FakeChoice", (), {"message": message})()
        return type("FakeCompletion", (), {"choices": [choice]})()


class FakeDoubleRejectingChat:
    def __init__(self):
        self.completions = FakeDoubleRejectingChatCompletions()


class FakeDoubleRejectingClient:
    def __init__(self):
        self.chat = FakeDoubleRejectingChat()


def test_openai_compatible_adapter_retries_without_response_format_when_needed():
    fake_client = FakeDoubleRejectingClient()
    client = OpenAICompatibleClient(
        LlmSettings(provider="openai-compatible", api_key="test", model="deepseek-chat"),
        client=fake_client,
    )

    override = client.parse_format_instruction("正文仿宋")

    assert override.body.font == "仿宋"
    assert "response_format" not in fake_client.chat.completions.calls[2]


def test_anthropic_messages_adapter_posts_messages_payload():
    calls = []

    def fake_transport(url, headers, payload):
        calls.append((url, headers, payload))
        return {
            "content": [
                {
                    "type": "text",
                    "text": '{"title":{"align":"center"},"body":{"font":"仿宋"},"headings":{},"notes":[]}',
                }
            ]
        }

    client = AnthropicMessagesClient(
        LlmSettings(provider="anthropic-messages", api_key="test-key", model="claude-test"),
        transport=fake_transport,
    )

    override = client.parse_format_instruction("标题居中，正文仿宋")

    assert override.title.align == "center"
    assert override.body.font == "仿宋"
    assert calls[0][0] == "https://api.anthropic.com/v1/messages"
    assert calls[0][1]["x-api-key"] == "test-key"
    assert calls[0][1]["anthropic-version"] == "2023-06-01"
    assert calls[0][2]["model"] == "claude-test"
    assert calls[0][2]["messages"][0]["role"] == "user"
    assert calls[0][2]["messages"][0]["content"] == "标题居中，正文仿宋"


def test_anthropic_messages_adapter_rejects_missing_text_content():
    def fake_transport(url, headers, payload):
        return {"content": [{"type": "tool_use", "name": "ignored"}]}

    client = AnthropicMessagesClient(
        LlmSettings(provider="anthropic-messages", api_key="test-key", model="claude-test"),
        transport=fake_transport,
    )

    with pytest.raises(ValueError, match="text content"):
        client.parse_format_instruction("标题居中")
