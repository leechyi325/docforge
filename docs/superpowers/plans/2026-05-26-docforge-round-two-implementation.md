# DocForge Round Two Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add direct `.docx` formatting and support `local`, OpenAI Responses, OpenAI-compatible Chat Completions, and Anthropic Messages model providers while keeping formatting execution local and deterministic.

**Architecture:** Introduce a Python pipeline that normalizes Markdown and `.docx` inputs into a source `.docx`, applies profile formatting, and runs diagnosis. Add a narrow LLM adapter interface with provider-specific protocol modules, then keep CLI and desktop layers as thin parameter pass-throughs. All model output is parsed as JSON and validated into existing Pydantic models before the formatter or fixer sees it.

**Tech Stack:** Python 3.11+, pytest, pydantic, python-docx, OpenAI Python SDK, stdlib `urllib.request` for Anthropic HTTP, Pandoc CLI, Tauri, React, TypeScript, Vite.

**User Preference:** Do not create git commits unless the user explicitly asks. Use `git status --short` and `git diff` checkpoints instead of commit steps.

---

## File Structure

- Create `engine/pipeline.py`: shared document formatting pipeline for Markdown and `.docx` inputs.
- Create `engine/llm/base.py`: `LlmClient` protocol and shared JSON extraction helpers.
- Create `engine/llm/settings.py`: provider names, aliases, defaults, and validation.
- Create `engine/llm/openai_responses.py`: OpenAI Responses API adapter.
- Create `engine/llm/openai_compatible.py`: OpenAI-compatible Chat Completions adapter.
- Create `engine/llm/anthropic_messages.py`: Anthropic Messages API adapter using stdlib HTTP.
- Modify `engine/llm/client.py`: preserve compatibility imports and expose `create_llm_client`.
- Modify `engine/llm/__init__.py`: export new public LLM entry points.
- Modify `engine/cli.py`: add `format`, provider parameters, and shared error handling.
- Modify `apps/desktop/src/types.ts`: extend request/provider types.
- Modify `apps/desktop/src/App.tsx`: update file input copy and model settings UI.
- Modify `apps/desktop/src-tauri/src/main.rs`: pass new model fields and call `engine.cli format`.
- Modify `README.md`: document `.docx` direct formatting and provider options.
- Modify `AGENTS.md`: update second-round scope and verification notes after implementation.
- Create or modify `tests/test_pipeline.py`: direct `.docx` formatting and extension validation.
- Modify `tests/test_cli.py`: `format` command behavior and error cases.
- Create `tests/test_llm_settings.py`: provider alias and validation behavior.
- Create `tests/test_llm_adapters.py`: fake-client tests for all remote adapters.
- Modify `tests/test_format_instruction.py`: compatibility checks for local parsing through the new factory.
- Modify `tests/test_e2e_cli.py`: keep `generate` compatibility and add Markdown through `format`.

## Task 1: Shared Document Pipeline And `.docx` Direct Formatting

**Files:**
- Create: `engine/pipeline.py`
- Modify: `engine/cli.py`
- Create: `tests/test_pipeline.py`
- Modify: `tests/test_cli.py`
- Modify: `tests/test_e2e_cli.py`

- [ ] **Step 1: Write failing pipeline tests**

Create `tests/test_pipeline.py`:

```python
import shutil

import pytest
from docx import Document

from engine.pipeline import UnsupportedInputError, format_document
from engine.profiles.loader import load_profile


def test_format_document_accepts_docx_input(tmp_path):
    source = tmp_path / "source.docx"
    output = tmp_path / "formatted.docx"
    doc = Document()
    doc.add_paragraph("测试标题")
    doc.add_paragraph("正文段落")
    doc.save(source)

    result = format_document(source, output, load_profile("general"))

    assert result.output_path == output
    assert output.exists()
    formatted = Document(output)
    assert formatted.paragraphs[0].runs[0].font.name == "方正小标宋"
    assert formatted.paragraphs[1].runs[0].font.name == "仿宋"
    assert isinstance(result.issues, list)


def test_format_document_rejects_doc_input(tmp_path):
    source = tmp_path / "legacy.doc"
    output = tmp_path / "formatted.docx"
    source.write_bytes(b"not a real doc file")

    with pytest.raises(UnsupportedInputError, match="Markdown and .docx"):
        format_document(source, output, load_profile("general"))


def test_format_document_requires_docx_output(tmp_path):
    source = tmp_path / "source.docx"
    output = tmp_path / "formatted.pdf"
    doc = Document()
    doc.add_paragraph("测试标题")
    doc.save(source)

    with pytest.raises(ValueError, match="Output path must end with .docx"):
        format_document(source, output, load_profile("general"))


@pytest.mark.skipif(shutil.which("pandoc") is None, reason="pandoc is required for markdown conversion")
def test_format_document_accepts_markdown_input(tmp_path):
    source = tmp_path / "source.md"
    output = tmp_path / "formatted.docx"
    source.write_text("# 测试标题\n\n正文段落\n", encoding="utf-8")

    result = format_document(source, output, load_profile("general"))

    assert result.output_path == output
    assert output.exists()
    assert Document(output).paragraphs[0].text.strip() == "测试标题"
```

- [ ] **Step 2: Write failing CLI tests for `format`**

Append to `tests/test_cli.py`:

```python
from docx import Document

from engine.cli import main


def test_cli_format_docx_outputs_json(tmp_path, capsys):
    input_docx = tmp_path / "input.docx"
    output_docx = tmp_path / "output.docx"
    doc = Document()
    doc.add_paragraph("标题")
    doc.add_paragraph("正文")
    doc.save(input_docx)

    exit_code = main(
        [
            "format",
            "--input",
            str(input_docx),
            "--profile",
            "general",
            "--llm-provider",
            "local",
            "--output",
            str(output_docx),
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["output"] == str(output_docx)
    assert "issues" in payload
    assert output_docx.exists()


def test_cli_format_rejects_doc_extension(tmp_path, capsys):
    input_doc = tmp_path / "input.doc"
    output_docx = tmp_path / "output.docx"
    input_doc.write_bytes(b"legacy")

    exit_code = main(["format", "--input", str(input_doc), "--output", str(output_docx)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Markdown and .docx" in captured.err
```

- [ ] **Step 3: Run tests to verify failure**

Run:

```bash
.venv/bin/python -m pytest tests/test_pipeline.py tests/test_cli.py -v
```

Expected: FAIL because `engine.pipeline` and the `format` subcommand do not exist.

- [ ] **Step 4: Implement `engine/pipeline.py`**

Create `engine/pipeline.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from engine.converters.pandoc import convert_markdown_to_docx
from engine.diagnostics.diagnose import diagnose_docx
from engine.formatter.docx_formatter import apply_profile_formatting
from engine.models import FormatOverride, Issue, Profile

MARKDOWN_SUFFIXES = {".md", ".markdown"}


class UnsupportedInputError(ValueError):
    pass


@dataclass(frozen=True)
class FormatResult:
    output_path: Path
    issues: List[Issue]


def format_document(
    input_path: Path,
    output_path: Path,
    profile: Profile,
    override: Optional[FormatOverride] = None,
) -> FormatResult:
    input_path = input_path.expanduser()
    output_path = output_path.expanduser()
    _validate_paths(input_path, output_path)

    source_docx = _prepare_source_docx(input_path, output_path)
    apply_profile_formatting(source_docx, output_path, profile, override)
    issues = diagnose_docx(output_path, profile)
    return FormatResult(output_path=output_path, issues=issues)


def _validate_paths(input_path: Path, output_path: Path) -> None:
    if not input_path.exists():
        raise FileNotFoundError(f"Input file does not exist: {input_path}")
    if output_path.suffix.lower() != ".docx":
        raise ValueError("Output path must end with .docx")


def _prepare_source_docx(input_path: Path, output_path: Path) -> Path:
    suffix = input_path.suffix.lower()
    if suffix == ".docx":
        return input_path
    if suffix in MARKDOWN_SUFFIXES:
        temp_docx = output_path.with_suffix(".pandoc.docx")
        return convert_markdown_to_docx(input_path, temp_docx)
    raise UnsupportedInputError("Unsupported input file. This release supports Markdown and .docx only.")
```

- [ ] **Step 5: Update CLI with shared error handling and `format`**

Modify `engine/cli.py` so it has a shared argument helper and both `generate` and `format` call the pipeline:

```python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

from pydantic import TypeAdapter

from engine.fixer.apply_fixes import apply_fixes
from engine.llm.client import OpenAIClient, parse_format_instruction_locally
from engine.models import Issue
from engine.pipeline import format_document
from engine.profiles.loader import load_profile


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="docforge")
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate")
    _add_formatting_args(generate)

    format_cmd = subparsers.add_parser("format")
    _add_formatting_args(format_cmd)

    diagnose = subparsers.add_parser("diagnose")
    diagnose.add_argument("--input", required=True)
    diagnose.add_argument("--profile", default="general")

    fix = subparsers.add_parser("fix")
    fix.add_argument("--input", required=True)
    fix.add_argument("--issues", required=True)
    fix.add_argument("--output", required=True)

    args = parser.parse_args(argv)

    try:
        if args.command in {"generate", "format"}:
            profile = load_profile(args.profile)
            override = _parse_override(args.format_instruction, args.llm_provider, args.api_key)
            result = format_document(Path(args.input), Path(args.output), profile, override)
            print(json.dumps({"output": str(result.output_path), "issues": [issue.model_dump() for issue in result.issues]}, ensure_ascii=False))
            return 0

        if args.command == "diagnose":
            from engine.diagnostics.diagnose import diagnose_docx

            issues = diagnose_docx(Path(args.input), load_profile(args.profile))
            print(json.dumps({"issues": [issue.model_dump() for issue in issues]}, ensure_ascii=False))
            return 0

        if args.command == "fix":
            payload = json.loads(Path(args.issues).read_text(encoding="utf-8"))
            issues = TypeAdapter(List[Issue]).validate_python(payload["issues"])
            apply_fixes(Path(args.input), Path(args.output), issues)
            print(json.dumps({"output": args.output}, ensure_ascii=False))
            return 0
    except Exception as error:
        print(str(error), file=sys.stderr)
        return 1

    return 2


def _add_formatting_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--input", required=True)
    parser.add_argument("--profile", default="general")
    parser.add_argument("--format-instruction", default="")
    parser.add_argument("--llm-provider", choices=["local", "openai"], default="local")
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--output", required=True)


def _parse_override(format_instruction: str, llm_provider: str, api_key: Optional[str]):
    if not format_instruction:
        return None
    if llm_provider == "openai":
        return OpenAIClient(api_key=api_key).parse_format_instruction(format_instruction)
    return parse_format_instruction_locally(format_instruction)
```

This is intentionally temporary; Task 6 replaces `_parse_override` with the provider factory.

- [ ] **Step 6: Keep `generate` Markdown compatibility explicit**

Append to `tests/test_e2e_cli.py`:

```python
@pytest.mark.skipif(shutil.which("pandoc") is None, reason="pandoc is required for e2e conversion")
def test_format_general_docx_from_markdown(tmp_path):
    input_md = tmp_path / "input.md"
    output_docx = tmp_path / "output.docx"
    input_md.write_text("# 测试标题\n\n正文段落。\n", encoding="utf-8")

    exit_code = main(
        [
            "format",
            "--input",
            str(input_md),
            "--profile",
            "general",
            "--format-instruction",
            "标题用方正小标宋二号居中，正文仿宋三号",
            "--llm-provider",
            "local",
            "--output",
            str(output_docx),
        ]
    )

    assert exit_code == 0
    assert output_docx.exists()
    assert Document(output_docx).paragraphs[0].text.strip() == "测试标题"
```

- [ ] **Step 7: Run task tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_pipeline.py tests/test_cli.py tests/test_e2e_cli.py -v
```

Expected: PASS, with Pandoc-marked tests skipped if Pandoc is unavailable.

- [ ] **Step 8: Workspace checkpoint**

Run:

```bash
git status --short
git diff -- engine/pipeline.py engine/cli.py tests/test_pipeline.py tests/test_cli.py tests/test_e2e_cli.py
```

Expected: only intended files are modified. Do not commit.

## Task 2: LLM Settings, Base Interface, And Local Provider

**Files:**
- Create: `engine/llm/base.py`
- Create: `engine/llm/settings.py`
- Modify: `engine/llm/client.py`
- Modify: `engine/llm/__init__.py`
- Create: `tests/test_llm_settings.py`
- Modify: `tests/test_format_instruction.py`

- [ ] **Step 1: Write failing settings and local factory tests**

Create `tests/test_llm_settings.py`:

```python
import pytest

from engine.llm.client import create_llm_client
from engine.llm.settings import LlmSettings, normalize_provider


def test_normalize_provider_keeps_openai_alias():
    assert normalize_provider("openai") == "openai-responses"
    assert normalize_provider("openai-compatible") == "openai-compatible"


def test_local_client_factory_parses_instruction():
    client = create_llm_client(LlmSettings(provider="local"))

    override = client.parse_format_instruction("标题用方正小标宋二号居中，正文仿宋三号")

    assert override.title.font == "方正小标宋"
    assert override.body.font == "仿宋"


def test_remote_provider_requires_model_when_instruction_is_parsed():
    settings = LlmSettings(provider="openai-compatible", api_key="test", base_url="https://example.test/v1")

    with pytest.raises(ValueError, match="requires --llm-model"):
        settings.validate_for_remote_use()
```

Append to `tests/test_format_instruction.py`:

```python
from engine.llm.client import create_llm_client
from engine.llm.settings import LlmSettings


def test_local_parser_is_available_through_client_factory():
    client = create_llm_client(LlmSettings(provider="local"))

    override = client.parse_format_instruction("正文仿宋三号，行距固定28磅")

    assert override.body.font == "仿宋"
    assert override.body.line_spacing == "28pt"
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
.venv/bin/python -m pytest tests/test_llm_settings.py tests/test_format_instruction.py -v
```

Expected: FAIL because `settings.py`, `base.py`, and `create_llm_client` do not exist.

- [ ] **Step 3: Implement `engine/llm/base.py`**

Create `engine/llm/base.py`:

```python
from __future__ import annotations

import json
import re
from typing import Protocol

from engine.models import FormatOverride


class LlmClient(Protocol):
    def parse_format_instruction(self, instruction: str) -> FormatOverride:
        ...


def parse_format_override_json(raw_text: str) -> FormatOverride:
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError:
        payload = json.loads(_extract_json_object(raw_text))
    return FormatOverride.model_validate(payload)


def _extract_json_object(raw_text: str) -> str:
    match = re.search(r"\{.*\}", raw_text, flags=re.DOTALL)
    if match is None:
        raise ValueError("Model did not return valid JSON")
    return match.group(0)
```

- [ ] **Step 4: Implement `engine/llm/settings.py`**

Create `engine/llm/settings.py`:

```python
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal, Optional

ProviderName = Literal["local", "openai-responses", "openai-compatible", "anthropic-messages"]

PROVIDER_ALIASES = {
    "openai": "openai-responses",
}


def normalize_provider(provider: str) -> ProviderName:
    normalized = PROVIDER_ALIASES.get(provider, provider)
    if normalized not in {"local", "openai-responses", "openai-compatible", "anthropic-messages"}:
        raise ValueError(f"Unsupported llm provider: {provider}")
    return normalized  # type: ignore[return-value]


@dataclass(frozen=True)
class LlmSettings:
    provider: str = "local"
    api_key: Optional[str] = None
    model: Optional[str] = None
    base_url: Optional[str] = None

    @property
    def normalized_provider(self) -> ProviderName:
        return normalize_provider(self.provider)

    def api_key_or_env(self) -> Optional[str]:
        if self.api_key:
            return self.api_key
        if self.normalized_provider == "anthropic-messages":
            return os.environ.get("ANTHROPIC_API_KEY")
        return os.environ.get("OPENAI_API_KEY")

    def model_or_env(self) -> Optional[str]:
        return self.model or os.environ.get("DOCFORGE_LLM_MODEL")

    def base_url_or_env(self) -> Optional[str]:
        return self.base_url or os.environ.get("DOCFORGE_LLM_BASE_URL")

    def validate_for_remote_use(self) -> None:
        if self.normalized_provider == "local":
            return
        if not self.model_or_env():
            raise ValueError(f"{self.normalized_provider} requires --llm-model")
        if not self.api_key_or_env():
            raise ValueError(f"{self.normalized_provider} requires --api-key or provider API key environment variable")
```

- [ ] **Step 5: Refactor `engine/llm/client.py` with a local client and factory**

Modify the top of `engine/llm/client.py` to keep the existing parser and add:

```python
from engine.llm.base import LlmClient
from engine.llm.settings import LlmSettings


class LocalLlmClient:
    def parse_format_instruction(self, instruction: str) -> FormatOverride:
        return parse_format_instruction_locally(instruction)


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
```

Leave `OpenAIClient` in place until Task 3 moves it behind the new adapter. This preserves first-round imports while the factory lands.

- [ ] **Step 6: Update `engine/llm/__init__.py` exports**

Replace `engine/llm/__init__.py` with:

```python
from engine.llm.client import LocalLlmClient, OpenAIClient, create_llm_client, parse_format_instruction_locally
from engine.llm.settings import LlmSettings

__all__ = [
    "LocalLlmClient",
    "LlmSettings",
    "OpenAIClient",
    "create_llm_client",
    "parse_format_instruction_locally",
]
```

- [ ] **Step 7: Run task tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_llm_settings.py tests/test_format_instruction.py -v
```

Expected: PASS.

- [ ] **Step 8: Workspace checkpoint**

Run:

```bash
git status --short
git diff -- engine/llm/base.py engine/llm/settings.py engine/llm/client.py engine/llm/__init__.py tests/test_llm_settings.py tests/test_format_instruction.py
```

Expected: LLM settings and local factory changes only. Do not commit.

## Task 3: OpenAI Responses Adapter

**Files:**
- Create: `engine/llm/openai_responses.py`
- Modify: `engine/llm/client.py`
- Modify: `engine/llm/__init__.py`
- Create or modify: `tests/test_llm_adapters.py`

- [ ] **Step 1: Write failing fake-client tests for OpenAI Responses**

Create `tests/test_llm_adapters.py`:

```python
from engine.llm.openai_responses import OpenAIResponsesClient
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
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
.venv/bin/python -m pytest tests/test_llm_adapters.py::test_openai_responses_adapter_uses_json_schema -v
```

Expected: FAIL because `engine.llm.openai_responses` does not exist.

- [ ] **Step 3: Implement `engine/llm/openai_responses.py`**

Create `engine/llm/openai_responses.py`:

```python
from __future__ import annotations

import json
from typing import Optional

from engine.llm.prompts import FORMAT_INSTRUCTION_PROMPT
from engine.llm.schemas import FORMAT_OVERRIDE_SCHEMA
from engine.llm.settings import LlmSettings
from engine.models import FormatOverride


class OpenAIResponsesClient:
    def __init__(self, settings: LlmSettings, client: Optional[object] = None) -> None:
        settings.validate_for_remote_use()
        self.settings = settings
        self.model = settings.model_or_env()
        if client is not None:
            self.client = client
        else:
            from openai import OpenAI

            kwargs = {"api_key": settings.api_key_or_env()}
            if settings.base_url_or_env():
                kwargs["base_url"] = settings.base_url_or_env()
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
        return FormatOverride.model_validate(json.loads(response.output_text))
```

- [ ] **Step 4: Make `OpenAIClient` a compatibility wrapper**

Modify `engine/llm/client.py` so `OpenAIClient` delegates to `OpenAIResponsesClient`:

```python
class OpenAIClient:
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4.1-mini") -> None:
        from engine.llm.openai_responses import OpenAIResponsesClient

        self._delegate = OpenAIResponsesClient(
            LlmSettings(provider="openai-responses", api_key=api_key, model=model)
        )

    def parse_format_instruction(self, instruction: str) -> FormatOverride:
        return self._delegate.parse_format_instruction(instruction)
```

Keep `parse_format_instruction_locally`, `LocalLlmClient`, and `create_llm_client` in the same file.

- [ ] **Step 5: Export the adapter**

Update `engine/llm/__init__.py`:

```python
from engine.llm.client import LocalLlmClient, OpenAIClient, create_llm_client, parse_format_instruction_locally
from engine.llm.openai_responses import OpenAIResponsesClient
from engine.llm.settings import LlmSettings

__all__ = [
    "LocalLlmClient",
    "LlmSettings",
    "OpenAIClient",
    "OpenAIResponsesClient",
    "create_llm_client",
    "parse_format_instruction_locally",
]
```

- [ ] **Step 6: Run task tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_llm_adapters.py tests/test_llm_settings.py tests/test_format_instruction.py -v
```

Expected: PASS.

- [ ] **Step 7: Workspace checkpoint**

Run:

```bash
git status --short
git diff -- engine/llm/openai_responses.py engine/llm/client.py engine/llm/__init__.py tests/test_llm_adapters.py
```

Expected: OpenAI Responses adapter changes only. Do not commit.

## Task 4: OpenAI-Compatible Chat Completions Adapter

**Files:**
- Create: `engine/llm/openai_compatible.py`
- Modify: `tests/test_llm_adapters.py`

- [ ] **Step 1: Write failing Chat Completions adapter tests**

Append to `tests/test_llm_adapters.py`:

```python
from engine.llm.openai_compatible import OpenAICompatibleClient


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
        LlmSettings(provider="openai-compatible", api_key="test", model="qwen-test", base_url="https://api.example.test/v1"),
        client=fake_client,
    )

    override = client.parse_format_instruction("正文仿宋")

    assert override.body.font == "仿宋"
    assert fake_client.chat.completions.calls[1]["response_format"]["type"] == "json_object"
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
.venv/bin/python -m pytest tests/test_llm_adapters.py::test_openai_compatible_adapter_uses_chat_completions tests/test_llm_adapters.py::test_openai_compatible_adapter_retries_json_object_when_schema_is_unsupported -v
```

Expected: FAIL because `engine.llm.openai_compatible` does not exist.

- [ ] **Step 3: Implement `engine/llm/openai_compatible.py`**

Create `engine/llm/openai_compatible.py`:

```python
from __future__ import annotations

from typing import Optional

from engine.llm.base import parse_format_override_json
from engine.llm.prompts import FORMAT_INSTRUCTION_PROMPT
from engine.llm.schemas import FORMAT_OVERRIDE_SCHEMA
from engine.llm.settings import LlmSettings
from engine.models import FormatOverride


class OpenAICompatibleClient:
    def __init__(self, settings: LlmSettings, client: Optional[object] = None) -> None:
        settings.validate_for_remote_use()
        self.settings = settings
        self.model = settings.model_or_env()
        if client is not None:
            self.client = client
        else:
            from openai import OpenAI

            kwargs = {"api_key": settings.api_key_or_env()}
            if settings.base_url_or_env():
                kwargs["base_url"] = settings.base_url_or_env()
            self.client = OpenAI(**kwargs)

    def parse_format_instruction(self, instruction: str) -> FormatOverride:
        response = self._create_with_fallbacks(instruction)
        content = response.choices[0].message.content
        return parse_format_override_json(content)

    def _create_with_fallbacks(self, instruction: str):
        messages = [
            {"role": "system", "content": _chat_system_prompt()},
            {"role": "user", "content": instruction},
        ]
        try:
            return self.client.chat.completions.create(
                model=self.model,
                messages=messages,
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
            if not _looks_like_response_format_error(error):
                raise
        try:
            return self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"},
            )
        except Exception as error:
            if not _looks_like_response_format_error(error):
                raise
        return self.client.chat.completions.create(model=self.model, messages=messages)


def _chat_system_prompt() -> str:
    return (
        FORMAT_INSTRUCTION_PROMPT
        + "\n只返回一个 JSON object，字段必须符合 DocForge format_override schema。不要返回 Markdown 代码块。"
    )


def _looks_like_response_format_error(error: Exception) -> bool:
    text = str(error).lower()
    return "response_format" in text or "json_schema" in text or "json_object" in text or "unsupported" in text
```

- [ ] **Step 4: Run task tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_llm_adapters.py -v
```

Expected: PASS.

- [ ] **Step 5: Workspace checkpoint**

Run:

```bash
git status --short
git diff -- engine/llm/openai_compatible.py tests/test_llm_adapters.py
```

Expected: OpenAI-compatible adapter changes only. Do not commit.

## Task 5: Anthropic Messages Adapter

**Files:**
- Create: `engine/llm/anthropic_messages.py`
- Modify: `tests/test_llm_adapters.py`

- [ ] **Step 1: Write failing Anthropic adapter tests**

Append to `tests/test_llm_adapters.py`:

```python
from engine.llm.anthropic_messages import AnthropicMessagesClient


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
    assert calls[0][2]["model"] == "claude-test"
    assert calls[0][2]["messages"][0]["role"] == "user"
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
.venv/bin/python -m pytest tests/test_llm_adapters.py::test_anthropic_messages_adapter_posts_messages_payload -v
```

Expected: FAIL because `engine.llm.anthropic_messages` does not exist.

- [ ] **Step 3: Implement `engine/llm/anthropic_messages.py`**

Create `engine/llm/anthropic_messages.py`:

```python
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Callable, Dict, Optional

from engine.llm.base import parse_format_override_json
from engine.llm.prompts import FORMAT_INSTRUCTION_PROMPT
from engine.llm.settings import LlmSettings
from engine.models import FormatOverride

Transport = Callable[[str, Dict[str, str], Dict[str, object]], Dict[str, object]]

DEFAULT_ANTHROPIC_BASE_URL = "https://api.anthropic.com"
ANTHROPIC_VERSION = "2023-06-01"


class AnthropicMessagesClient:
    def __init__(self, settings: LlmSettings, transport: Optional[Transport] = None) -> None:
        settings.validate_for_remote_use()
        self.settings = settings
        self.model = settings.model_or_env()
        self.base_url = (settings.base_url_or_env() or DEFAULT_ANTHROPIC_BASE_URL).rstrip("/")
        self.api_key = settings.api_key_or_env()
        self.transport = transport or _post_json

    def parse_format_instruction(self, instruction: str) -> FormatOverride:
        payload = {
            "model": self.model,
            "max_tokens": 1200,
            "system": _anthropic_system_prompt(),
            "messages": [{"role": "user", "content": instruction}],
        }
        headers = {
            "content-type": "application/json",
            "x-api-key": self.api_key or "",
            "anthropic-version": ANTHROPIC_VERSION,
        }
        data = self.transport(f"{self.base_url}/v1/messages", headers, payload)
        return parse_format_override_json(_extract_text(data))


def _anthropic_system_prompt() -> str:
    return (
        FORMAT_INSTRUCTION_PROMPT
        + "\n只返回一个 JSON object，字段必须符合 DocForge format_override schema。不要返回 Markdown 代码块或解释。"
    )


def _extract_text(data: Dict[str, object]) -> str:
    content = data.get("content")
    if not isinstance(content, list):
        raise ValueError("Anthropic response did not include content")
    texts = []
    for item in content:
        if isinstance(item, dict) and item.get("type") == "text" and isinstance(item.get("text"), str):
            texts.append(item["text"])
    if not texts:
        raise ValueError("Anthropic response did not include text content")
    return "\n".join(texts)


def _post_json(url: str, headers: Dict[str, str], payload: Dict[str, object]) -> Dict[str, object]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        message = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Anthropic Messages API failed: {message}") from error
```

- [ ] **Step 4: Run task tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_llm_adapters.py -v
```

Expected: PASS.

- [ ] **Step 5: Workspace checkpoint**

Run:

```bash
git status --short
git diff -- engine/llm/anthropic_messages.py tests/test_llm_adapters.py
```

Expected: Anthropic adapter changes only. Do not commit.

## Task 6: CLI Provider Integration

**Files:**
- Modify: `engine/cli.py`
- Modify: `tests/test_cli.py`
- Modify: `tests/test_llm_settings.py`

- [ ] **Step 1: Write failing CLI provider tests**

Append to `tests/test_cli.py`:

```python
def test_cli_format_accepts_openai_responses_provider_without_call_when_no_instruction(tmp_path):
    input_docx = tmp_path / "input.docx"
    output_docx = tmp_path / "output.docx"
    doc = Document()
    doc.add_paragraph("标题")
    doc.save(input_docx)

    exit_code = main(
        [
            "format",
            "--input",
            str(input_docx),
            "--profile",
            "general",
            "--llm-provider",
            "openai-responses",
            "--output",
            str(output_docx),
        ]
    )

    assert exit_code == 0


def test_cli_format_remote_provider_requires_model_when_instruction_is_present(tmp_path, capsys):
    input_docx = tmp_path / "input.docx"
    output_docx = tmp_path / "output.docx"
    doc = Document()
    doc.add_paragraph("标题")
    doc.save(input_docx)

    exit_code = main(
        [
            "format",
            "--input",
            str(input_docx),
            "--profile",
            "general",
            "--format-instruction",
            "正文仿宋三号",
            "--llm-provider",
            "openai-compatible",
            "--api-key",
            "test",
            "--llm-base-url",
            "https://api.example.test/v1",
            "--output",
            str(output_docx),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "requires --llm-model" in captured.err
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
.venv/bin/python -m pytest tests/test_cli.py -v
```

Expected: FAIL because CLI choices do not include the new provider names and model/base URL args.

- [ ] **Step 3: Update CLI argument parsing**

Modify `_add_formatting_args` in `engine/cli.py`:

```python
def _add_formatting_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--input", required=True)
    parser.add_argument("--profile", default="general")
    parser.add_argument("--format-instruction", default="")
    parser.add_argument(
        "--llm-provider",
        choices=["local", "openai", "openai-responses", "openai-compatible", "anthropic-messages"],
        default="local",
    )
    parser.add_argument("--llm-model", default=None)
    parser.add_argument("--llm-base-url", default=None)
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--output", required=True)
```

Modify imports:

```python
from engine.llm.client import create_llm_client
from engine.llm.settings import LlmSettings
```

Remove direct imports of `OpenAIClient` and `parse_format_instruction_locally`.

- [ ] **Step 4: Replace `_parse_override` with provider factory logic**

Replace `_parse_override` in `engine/cli.py`:

```python
def _parse_override(args):
    if not args.format_instruction:
        return None
    settings = LlmSettings(
        provider=args.llm_provider,
        api_key=args.api_key,
        model=args.llm_model,
        base_url=args.llm_base_url,
    )
    return create_llm_client(settings).parse_format_instruction(args.format_instruction)
```

Update the call site:

```python
override = _parse_override(args)
```

- [ ] **Step 5: Add provider alias assertion**

Append to `tests/test_llm_settings.py`:

```python
def test_openai_alias_normalizes_to_responses_provider():
    settings = LlmSettings(provider="openai", api_key="test", model="gpt-test")

    assert settings.normalized_provider == "openai-responses"
```

- [ ] **Step 6: Run task tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_cli.py tests/test_llm_settings.py tests/test_llm_adapters.py -v
```

Expected: PASS.

- [ ] **Step 7: Workspace checkpoint**

Run:

```bash
git status --short
git diff -- engine/cli.py tests/test_cli.py tests/test_llm_settings.py
```

Expected: CLI integration changes only. Do not commit.

## Task 7: Desktop Request And UI Updates

**Files:**
- Modify: `apps/desktop/src/types.ts`
- Modify: `apps/desktop/src/App.tsx`
- Modify: `apps/desktop/src-tauri/src/main.rs`

- [ ] **Step 1: Update TypeScript request types**

Modify `apps/desktop/src/types.ts`:

```ts
export type LlmProvider = "local" | "openai-responses" | "openai-compatible" | "anthropic-messages";

export type GenerateRequest = {
  inputPath: string;
  outputPath: string;
  profile: ProfileId;
  formatInstruction: string;
  llmProvider: LlmProvider;
  llmModel: string;
  llmBaseUrl: string;
  apiKey: string;
};
```

Keep `ProfileId`, `Issue`, and `GenerateResponse` unchanged.

- [ ] **Step 2: Update React UI state and provider selector**

Modify imports in `apps/desktop/src/App.tsx`:

```ts
import type { GenerateResponse, Issue, LlmProvider, ProfileId } from "./types";
```

Replace provider state:

```ts
const [llmProvider, setLlmProvider] = useState<LlmProvider>("local");
const [llmModel, setLlmModel] = useState("");
const [llmBaseUrl, setLlmBaseUrl] = useState("");
```

Update invoke payload:

```ts
request: { inputPath, outputPath, profile, formatInstruction, llmProvider, llmModel, llmBaseUrl, apiKey },
```

Change status text in `handleGenerate`:

```ts
setStatus(inputPath.endsWith(".docx") ? "正在整理 docx 格式" : "正在转换并整理 docx");
```

Update labels and options:

```tsx
<label>
  API Key
  <input value={apiKey} onChange={(event) => setApiKey(event.target.value)} placeholder="OpenAI / Anthropic / 网关 API Key" />
</label>
<label>
  模型协议
  <select value={llmProvider} onChange={(event) => setLlmProvider(event.target.value as LlmProvider)}>
    <option value="local">本地规则解析</option>
    <option value="openai-responses">OpenAI Responses API</option>
    <option value="openai-compatible">OpenAI-compatible Chat Completions</option>
    <option value="anthropic-messages">Anthropic Messages API</option>
  </select>
</label>
<label>
  模型名
  <input value={llmModel} onChange={(event) => setLlmModel(event.target.value)} placeholder="gpt-4.1-mini / deepseek-chat / claude-..." />
</label>
<label>
  Base URL
  <input value={llmBaseUrl} onChange={(event) => setLlmBaseUrl(event.target.value)} placeholder="可选，例如 https://api.example.com/v1" />
</label>
<label>
  输入文件
  <input value={inputPath} onChange={(event) => setInputPath(event.target.value)} placeholder="/path/to/input.md 或 /path/to/input.docx" />
</label>
```

Change button text:

```tsx
整理并导出 docx
```

- [ ] **Step 3: Update Rust request struct and CLI args**

Modify `apps/desktop/src-tauri/src/main.rs`:

```rust
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct GenerateRequest {
    input_path: String,
    output_path: String,
    profile: String,
    format_instruction: String,
    llm_provider: String,
    llm_model: String,
    llm_base_url: String,
    api_key: String,
}
```

Change the command passed to Python from `generate` to `format`, and include the new args:

```rust
.args([
    "-m",
    "engine.cli",
    "format",
    "--input",
    &request.input_path,
    "--profile",
    &request.profile,
    "--format-instruction",
    &request.format_instruction,
    "--llm-provider",
    &request.llm_provider,
    "--llm-model",
    &request.llm_model,
    "--llm-base-url",
    &request.llm_base_url,
    "--api-key",
    &request.api_key,
    "--output",
    &request.output_path,
])
```

Keep the Tauri command name `generate_docx` for now to avoid extra frontend command renaming.

- [ ] **Step 4: Run frontend build**

Run:

```bash
cd apps/desktop
npm run build
```

Expected: PASS.

- [ ] **Step 5: Workspace checkpoint**

Run:

```bash
git status --short
git diff -- apps/desktop/src/types.ts apps/desktop/src/App.tsx apps/desktop/src-tauri/src/main.rs
```

Expected: desktop pass-through changes only. Do not commit.

## Task 8: Documentation, Final Verification, And Cleanup

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`

- [ ] **Step 1: Update README usage examples**

Modify `README.md` so the Python Engine section contains both Markdown and `.docx` examples:

````markdown
Format an existing `.docx`:

```bash
.venv/bin/python -m engine.cli format \
  --input input.docx \
  --profile official \
  --format-instruction "正文仿宋三号，行距28磅" \
  --llm-provider local \
  --output output.docx
```

Use an OpenAI-compatible provider:

```bash
.venv/bin/python -m engine.cli format \
  --input input.docx \
  --profile general \
  --format-instruction "标题居中，正文仿宋三号" \
  --llm-provider openai-compatible \
  --llm-base-url https://api.example.com/v1 \
  --llm-model deepseek-chat \
  --api-key "$PROVIDER_API_KEY" \
  --output output.docx
```

Use Anthropic Messages:

```bash
.venv/bin/python -m engine.cli format \
  --input input.docx \
  --profile general \
  --format-instruction "标题居中，正文仿宋三号" \
  --llm-provider anthropic-messages \
  --llm-model claude-sonnet-4-5 \
  --api-key "$ANTHROPIC_API_KEY" \
  --output output.docx
```
````

Keep the existing Markdown `generate` example and add one sentence that `generate` remains a Markdown-compatible alias path while `format` is the preferred general entry point.

- [ ] **Step 2: Update AGENTS handoff notes**

Modify `AGENTS.md` in the Current Scope section after implementation:

```markdown
- Direct `.docx` input formatting through the Python CLI `format` command.
- OpenAI Responses, OpenAI-compatible Chat Completions, and Anthropic Messages provider adapters for format instruction parsing.
```

Modify Explicit non-goals:

```markdown
- `.doc` legacy format support.
```

Modify the example commands to include:

```bash
.venv/bin/python -m engine.cli format \
  --input input.docx \
  --profile official \
  --format-instruction "正文仿宋三号，行距28磅" \
  --llm-provider local \
  --output output.docx
```

- [ ] **Step 3: Run full Python tests**

Run:

```bash
.venv/bin/python -m pytest -v
```

Expected: PASS, with Pandoc tests skipped only if Pandoc is unavailable.

- [ ] **Step 4: Run frontend build**

Run:

```bash
cd apps/desktop
npm run build
```

Expected: PASS.

- [ ] **Step 5: Check for generated files**

Run:

```bash
git status --short
```

Expected: source, test, docs, and package files only. Generated directories such as `.pytest_cache/`, `__pycache__/`, `node_modules/`, and `dist/` must not be staged or committed.

- [ ] **Step 6: Review final diff**

Run:

```bash
git diff --stat
git diff -- engine apps tests README.md AGENTS.md pyproject.toml
```

Expected: diff matches the approved second-round scope: `.docx` direct formatting, LLM provider adapters, desktop pass-through, and docs. Do not commit unless the user explicitly asks.

## Self-Review Checklist

- Spec coverage: `.docx` direct formatting is covered by Task 1; three model protocols are covered by Tasks 3, 4, and 5; CLI and desktop parameter flow are covered by Tasks 6 and 7; docs and verification are covered by Task 8.
- Safety boundary: every remote adapter returns `FormatOverride` only after local JSON parsing and Pydantic validation; formatter execution remains local.
- `.doc` boundary: Task 1 explicitly rejects `.doc`; no conversion dependency is introduced.
- Backward compatibility: `generate` remains available; provider alias `openai` maps to `openai-responses`.
- Test coverage: pipeline, CLI, provider settings, fake remote adapters, local parser compatibility, frontend build, and full pytest are included.
