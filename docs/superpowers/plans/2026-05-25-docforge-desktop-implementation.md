# DocForge Desktop MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a macOS-runnable desktop MVP that converts Markdown into formatted `.docx`, supports document profiles, parses temporary format instructions through OpenAI-compatible structured JSON, diagnoses format issues, and applies safe fixes.

**Architecture:** Keep the Python engine as the source of truth and expose it through a CLI. The Tauri desktop app remains a thin local UI that calls the CLI and displays generated files, status, and diagnosis results. Model output is never executed directly; it is validated into typed data and converted into whitelisted fix actions.

**Tech Stack:** Python 3.11+, pytest, pydantic, PyYAML, python-docx, OpenAI Python SDK, Pandoc CLI, Tauri, React, TypeScript, Vite.

**User Preference:** Do not create git commits unless the user explicitly asks. Use `git status --short` and `git diff` checkpoints instead of commit steps.

---

## File Structure

- Create `pyproject.toml`: Python package metadata, dependencies, pytest config.
- Create `engine/__init__.py`: package marker.
- Create `engine/models.py`: typed domain models for styles, profiles, issues, and fix actions.
- Create `engine/style_utils.py`: Chinese字号 conversion, unit parsing, and style merge helpers.
- Create `engine/profiles/loader.py`: load and validate YAML profiles.
- Create `engine/profiles/*.yaml`: built-in profiles for official documents, meeting minutes, briefings, speeches, and general formatted documents.
- Create `engine/llm/schemas.py`: JSON Schemas passed to the model and used for validation.
- Create `engine/llm/client.py`: OpenAI Responses API adapter and deterministic local fallback for tests.
- Create `engine/llm/prompts.py`: prompts for structure recognition, format instruction parsing, and diagnosis.
- Create `engine/converters/pandoc.py`: Pandoc wrapper.
- Create `engine/formatter/docx_formatter.py`: deterministic `.docx` formatting.
- Create `engine/diagnostics/diagnose.py`: local and model-assisted issue generation.
- Create `engine/fixer/apply_fixes.py`: whitelisted fix action executor.
- Create `engine/cli.py`: `generate`, `diagnose`, and `fix` commands.
- Create `tests/fixtures/*.md`: sample Markdown inputs.
- Create `tests/test_*.py`: engine test coverage.
- Create `apps/desktop/`: Tauri + React desktop app.

## Task 1: Python Package Scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `engine/__init__.py`
- Create: `tests/test_imports.py`

- [ ] **Step 1: Write the failing import test**

Create `tests/test_imports.py`:

```python
def test_engine_package_imports():
    import engine

    assert engine.__version__ == "0.1.0"
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
python -m pytest tests/test_imports.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'engine'` or `AttributeError: module 'engine' has no attribute '__version__'`.

- [ ] **Step 3: Add Python project metadata**

Create `pyproject.toml`:

```toml
[project]
name = "docforge"
version = "0.1.0"
description = "Desktop document formatting MVP"
requires-python = ">=3.11"
dependencies = [
  "openai>=1.0.0",
  "pydantic>=2.7.0",
  "python-docx>=1.1.0",
  "PyYAML>=6.0.0"
]

[project.optional-dependencies]
dev = [
  "pytest>=8.0.0"
]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

Create `engine/__init__.py`:

```python
__version__ = "0.1.0"
```

- [ ] **Step 4: Run the test to verify it passes**

Run:

```bash
python -m pytest tests/test_imports.py -v
```

Expected: PASS.

- [ ] **Step 5: Check the workspace**

Run:

```bash
git status --short
```

Expected: new package and test files are listed. Do not commit.

## Task 2: Domain Models And Style Normalization

**Files:**
- Create: `engine/models.py`
- Create: `engine/style_utils.py`
- Create: `tests/test_style_utils.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write failing tests for Chinese字号 and merge behavior**

Create `tests/test_style_utils.py`:

```python
from engine.models import ParagraphStyle
from engine.style_utils import chinese_size_to_pt, merge_style


def test_chinese_size_to_pt_maps_common_sizes():
    assert chinese_size_to_pt("二号") == 22.0
    assert chinese_size_to_pt("三号") == 16.0
    assert chinese_size_to_pt("小三") == 15.0
    assert chinese_size_to_pt("四号") == 14.0


def test_merge_style_ignores_none_values():
    base = ParagraphStyle(font="仿宋", size="三号", align="left", line_spacing="28pt")
    override = ParagraphStyle(font=None, size="二号", align="center", line_spacing=None)

    merged = merge_style(base, override)

    assert merged.font == "仿宋"
    assert merged.size == "二号"
    assert merged.align == "center"
    assert merged.line_spacing == "28pt"
```

Create `tests/test_models.py`:

```python
from engine.models import FixAction, Issue, Location, ParagraphStyle


def test_issue_requires_fix_action_shape():
    issue = Issue(
        id="issue_001",
        severity="warning",
        message="正文行距不符合要求",
        location=Location(type="paragraph", index=3),
        fix_action=FixAction(
            type="set_paragraph_format",
            target=Location(type="paragraph", index=3),
            properties=ParagraphStyle(font="仿宋", size="三号", line_spacing="28pt"),
        ),
    )

    assert issue.fix_action.properties.font == "仿宋"
    assert issue.location.index == 3
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest tests/test_style_utils.py tests/test_models.py -v
```

Expected: FAIL because `engine.models` and `engine.style_utils` do not exist.

- [ ] **Step 3: Implement typed models**

Create `engine/models.py`:

```python
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ParagraphStyle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    font: str | None = None
    size: str | None = None
    bold: bool | None = None
    align: Literal["left", "center", "right", "justify"] | None = None
    first_line_indent: str | None = None
    line_spacing: str | None = None
    space_before: str | None = None
    space_after: str | None = None


class PageSetup(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paper: str = "A4"
    margin_top: str = "3.7cm"
    margin_bottom: str = "3.5cm"
    margin_left: str = "2.8cm"
    margin_right: str = "2.6cm"


class Profile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    required_fields: list[str] = Field(default_factory=list)
    page: PageSetup = Field(default_factory=PageSetup)
    title: ParagraphStyle
    body: ParagraphStyle
    headings: dict[str, ParagraphStyle] = Field(default_factory=dict)
    special_sections: dict[str, ParagraphStyle] = Field(default_factory=dict)
    auto_fix_rules: list[str] = Field(default_factory=list)
    template: str | None = None


class FormatOverride(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: ParagraphStyle | None = None
    body: ParagraphStyle | None = None
    headings: dict[str, ParagraphStyle] = Field(default_factory=dict)
    page: PageSetup | None = None
    notes: list[str] = Field(default_factory=list)


class DocumentStructure(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_type: str
    title: str | None = None
    headings: list[str] = Field(default_factory=list)
    required_fields_present: dict[str, bool] = Field(default_factory=dict)


class Location(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["document", "paragraph", "section"]
    index: int | None = None
    key: str | None = None


class FixAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal[
        "set_paragraph_format",
        "apply_heading_style",
        "set_page_setup",
        "set_section_format",
    ]
    target: Location
    properties: ParagraphStyle | PageSetup


class Issue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    severity: Literal["info", "warning", "error"]
    message: str
    location: Location
    fix_action: FixAction | None = None
```

- [ ] **Step 4: Implement style utilities**

Create `engine/style_utils.py`:

```python
from __future__ import annotations

import re
from typing import TypeVar

from pydantic import BaseModel

from engine.models import ParagraphStyle

T = TypeVar("T", bound=BaseModel)

CHINESE_SIZE_TO_PT = {
    "初号": 42.0,
    "小初": 36.0,
    "一号": 26.0,
    "小一": 24.0,
    "二号": 22.0,
    "小二": 18.0,
    "三号": 16.0,
    "小三": 15.0,
    "四号": 14.0,
    "小四": 12.0,
    "五号": 10.5,
    "小五": 9.0,
}


def chinese_size_to_pt(size: str) -> float:
    if size in CHINESE_SIZE_TO_PT:
        return CHINESE_SIZE_TO_PT[size]
    if size.endswith("pt"):
        return float(size[:-2])
    if re.fullmatch(r"\d+(\.\d+)?", size):
        return float(size)
    raise ValueError(f"Unsupported font size: {size}")


def parse_length_to_pt(value: str) -> float:
    if value.endswith("pt"):
        return float(value[:-2])
    if value.endswith("cm"):
        return float(value[:-2]) * 28.3464567
    if value.endswith("mm"):
        return float(value[:-2]) * 2.83464567
    if value.endswith("em"):
        return float(value[:-2]) * 16.0
    raise ValueError(f"Unsupported length: {value}")


def merge_model(base: T, override: T | None) -> T:
    if override is None:
        return base
    data = base.model_dump()
    override_data = override.model_dump(exclude_none=True)
    for key, value in override_data.items():
        if isinstance(value, dict) and isinstance(data.get(key), dict):
            data[key] = {**data[key], **value}
        else:
            data[key] = value
    return type(base).model_validate(data)


def merge_style(base: ParagraphStyle, override: ParagraphStyle | None) -> ParagraphStyle:
    return merge_model(base, override)
```

- [ ] **Step 5: Run tests**

Run:

```bash
python -m pytest tests/test_style_utils.py tests/test_models.py -v
```

Expected: PASS.

## Task 3: Built-In Profile Loader

**Files:**
- Create: `engine/profiles/__init__.py`
- Create: `engine/profiles/loader.py`
- Create: `engine/profiles/general.yaml`
- Create: `engine/profiles/official.yaml`
- Create: `engine/profiles/meeting_minutes.yaml`
- Create: `engine/profiles/briefing.yaml`
- Create: `engine/profiles/speech.yaml`
- Create: `tests/test_profiles.py`

- [ ] **Step 1: Write failing profile tests**

Create `tests/test_profiles.py`:

```python
from engine.profiles.loader import list_profiles, load_profile


def test_general_profile_is_default_and_lightweight():
    profile = load_profile("general")

    assert profile.id == "general"
    assert profile.name == "通用格式文档"
    assert profile.required_fields == []
    assert profile.title.size == "二号"
    assert profile.body.font == "仿宋"
    assert profile.headings["heading_1"].font == "黑体"


def test_all_first_batch_profiles_load():
    ids = {profile.id for profile in list_profiles()}

    assert ids == {"official", "meeting_minutes", "briefing", "speech", "general"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest tests/test_profiles.py -v
```

Expected: FAIL because profile loader and YAML files do not exist.

- [ ] **Step 3: Implement profile loader**

Create `engine/profiles/__init__.py`:

```python
from engine.profiles.loader import list_profiles, load_profile

__all__ = ["list_profiles", "load_profile"]
```

Create `engine/profiles/loader.py`:

```python
from __future__ import annotations

from pathlib import Path

import yaml

from engine.models import Profile

PROFILE_DIR = Path(__file__).resolve().parent


def load_profile(profile_id: str) -> Profile:
    path = PROFILE_DIR / f"{profile_id}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Profile not found: {profile_id}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return Profile.model_validate(data)


def list_profiles() -> list[Profile]:
    profiles = []
    for path in sorted(PROFILE_DIR.glob("*.yaml")):
        profiles.append(Profile.model_validate(yaml.safe_load(path.read_text(encoding="utf-8"))))
    return profiles
```

- [ ] **Step 4: Add built-in profile YAML files**

Create `engine/profiles/general.yaml`:

```yaml
id: general
name: 通用格式文档
required_fields: []
page:
  paper: A4
  margin_top: 2.54cm
  margin_bottom: 2.54cm
  margin_left: 3.18cm
  margin_right: 3.18cm
title:
  font: 方正小标宋
  size: 二号
  bold: false
  align: center
  line_spacing: 28pt
body:
  font: 仿宋
  size: 三号
  align: justify
  first_line_indent: 2em
  line_spacing: 28pt
  space_before: 0pt
  space_after: 0pt
headings:
  heading_1:
    font: 黑体
    size: 三号
    bold: false
    align: left
    line_spacing: 28pt
  heading_2:
    font: 楷体
    size: 三号
    bold: false
    align: left
    line_spacing: 28pt
special_sections: {}
auto_fix_rules:
  - title_style
  - body_style
  - heading_style
  - page_setup
template: null
```

Create `engine/profiles/official.yaml`:

```yaml
id: official
name: 公文
required_fields:
  - title
  - body
page:
  paper: A4
  margin_top: 3.7cm
  margin_bottom: 3.5cm
  margin_left: 2.8cm
  margin_right: 2.6cm
title:
  font: 方正小标宋
  size: 二号
  bold: false
  align: center
  line_spacing: 28pt
body:
  font: 仿宋
  size: 三号
  align: justify
  first_line_indent: 2em
  line_spacing: 28pt
  space_before: 0pt
  space_after: 0pt
headings:
  heading_1:
    font: 黑体
    size: 三号
    bold: false
    align: left
    line_spacing: 28pt
  heading_2:
    font: 楷体
    size: 三号
    bold: false
    align: left
    line_spacing: 28pt
special_sections:
  attachment:
    font: 仿宋
    size: 三号
    align: left
    line_spacing: 28pt
  signature:
    font: 仿宋
    size: 三号
    align: right
    line_spacing: 28pt
auto_fix_rules:
  - title_style
  - body_style
  - heading_style
  - page_setup
  - attachment_style
  - signature_style
template: null
```

Create `engine/profiles/meeting_minutes.yaml`:

```yaml
id: meeting_minutes
name: 会议纪要
required_fields:
  - title
  - meeting_time
  - meeting_location
  - attendees
page:
  paper: A4
  margin_top: 2.54cm
  margin_bottom: 2.54cm
  margin_left: 3.18cm
  margin_right: 3.18cm
title:
  font: 黑体
  size: 二号
  bold: true
  align: center
  line_spacing: 28pt
body:
  font: 仿宋
  size: 三号
  align: justify
  first_line_indent: 2em
  line_spacing: 28pt
  space_before: 0pt
  space_after: 0pt
headings:
  heading_1:
    font: 黑体
    size: 三号
    bold: true
    align: left
    line_spacing: 28pt
special_sections:
  meeting_meta:
    font: 仿宋
    size: 三号
    align: left
    line_spacing: 28pt
auto_fix_rules:
  - title_style
  - body_style
  - heading_style
  - page_setup
  - required_fields
template: null
```

Create `engine/profiles/briefing.yaml`:

```yaml
id: briefing
name: 汇报材料
required_fields:
  - title
  - body
page:
  paper: A4
  margin_top: 2.54cm
  margin_bottom: 2.54cm
  margin_left: 3.18cm
  margin_right: 3.18cm
title:
  font: 黑体
  size: 二号
  bold: true
  align: center
  line_spacing: 30pt
body:
  font: 仿宋
  size: 三号
  align: justify
  first_line_indent: 2em
  line_spacing: 28pt
  space_before: 0pt
  space_after: 0pt
headings:
  heading_1:
    font: 黑体
    size: 三号
    bold: true
    align: left
    line_spacing: 28pt
  heading_2:
    font: 楷体
    size: 三号
    bold: true
    align: left
    line_spacing: 28pt
special_sections: {}
auto_fix_rules:
  - title_style
  - body_style
  - heading_style
  - page_setup
template: null
```

Create `engine/profiles/speech.yaml`:

```yaml
id: speech
name: 讲话稿
required_fields:
  - title
  - body
page:
  paper: A4
  margin_top: 2.54cm
  margin_bottom: 2.54cm
  margin_left: 3.18cm
  margin_right: 3.18cm
title:
  font: 方正小标宋
  size: 二号
  bold: false
  align: center
  line_spacing: 30pt
body:
  font: 仿宋
  size: 三号
  align: justify
  first_line_indent: 2em
  line_spacing: 28pt
  space_before: 0pt
  space_after: 0pt
headings:
  heading_1:
    font: 黑体
    size: 三号
    bold: true
    align: left
    line_spacing: 28pt
special_sections:
  salutation:
    font: 仿宋
    size: 三号
    align: left
    line_spacing: 28pt
auto_fix_rules:
  - title_style
  - body_style
  - heading_style
  - page_setup
template: null
```

- [ ] **Step 5: Run profile tests**

Run:

```bash
python -m pytest tests/test_profiles.py -v
```

Expected: PASS.

## Task 4: LLM Schemas And Format Instruction Parsing

**Files:**
- Create: `engine/llm/__init__.py`
- Create: `engine/llm/schemas.py`
- Create: `engine/llm/prompts.py`
- Create: `engine/llm/client.py`
- Create: `tests/test_llm_schemas.py`
- Create: `tests/test_format_instruction.py`

- [ ] **Step 1: Write failing schema and parser tests**

Create `tests/test_llm_schemas.py`:

```python
from engine.llm.schemas import FORMAT_OVERRIDE_SCHEMA, ISSUE_LIST_SCHEMA


def test_format_override_schema_requires_object():
    assert FORMAT_OVERRIDE_SCHEMA["type"] == "object"
    assert "properties" in FORMAT_OVERRIDE_SCHEMA
    assert "body" in FORMAT_OVERRIDE_SCHEMA["properties"]


def test_issue_list_schema_contains_fix_action():
    issue = ISSUE_LIST_SCHEMA["properties"]["issues"]["items"]
    assert "fix_action" in issue["properties"]
```

Create `tests/test_format_instruction.py`:

```python
from engine.llm.client import parse_format_instruction_locally


def test_local_format_instruction_parser_handles_common_request():
    override = parse_format_instruction_locally(
        "标题用方正小标宋二号居中，正文仿宋三号，行距固定28磅，一级标题黑体三号。"
    )

    assert override.title.font == "方正小标宋"
    assert override.title.size == "二号"
    assert override.title.align == "center"
    assert override.body.font == "仿宋"
    assert override.body.size == "三号"
    assert override.body.line_spacing == "28pt"
    assert override.headings["heading_1"].font == "黑体"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest tests/test_llm_schemas.py tests/test_format_instruction.py -v
```

Expected: FAIL because LLM files do not exist.

- [ ] **Step 3: Add schemas**

Create `engine/llm/__init__.py`:

```python
from engine.llm.client import OpenAIClient, parse_format_instruction_locally

__all__ = ["OpenAIClient", "parse_format_instruction_locally"]
```

Create `engine/llm/schemas.py`:

```python
FORMAT_OVERRIDE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "title": {"$ref": "#/$defs/paragraphStyle"},
        "body": {"$ref": "#/$defs/paragraphStyle"},
        "headings": {
            "type": "object",
            "additionalProperties": {"$ref": "#/$defs/paragraphStyle"},
        },
        "page": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "paper": {"type": "string"},
                "margin_top": {"type": "string"},
                "margin_bottom": {"type": "string"},
                "margin_left": {"type": "string"},
                "margin_right": {"type": "string"},
            },
        },
        "notes": {"type": "array", "items": {"type": "string"}},
    },
    "$defs": {
        "paragraphStyle": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "font": {"type": "string"},
                "size": {"type": "string"},
                "bold": {"type": "boolean"},
                "align": {"enum": ["left", "center", "right", "justify"]},
                "first_line_indent": {"type": "string"},
                "line_spacing": {"type": "string"},
                "space_before": {"type": "string"},
                "space_after": {"type": "string"},
            },
        }
    },
}

DOCUMENT_STRUCTURE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "document_type": {"type": "string"},
        "title": {"type": ["string", "null"]},
        "headings": {"type": "array", "items": {"type": "string"}},
        "required_fields_present": {
            "type": "object",
            "additionalProperties": {"type": "boolean"},
        },
    },
    "required": ["document_type", "title", "headings", "required_fields_present"],
}

ISSUE_LIST_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "issues": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "id": {"type": "string"},
                    "severity": {"enum": ["info", "warning", "error"]},
                    "message": {"type": "string"},
                    "location": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "type": {"enum": ["document", "paragraph", "section"]},
                            "index": {"type": ["integer", "null"]},
                            "key": {"type": ["string", "null"]},
                        },
                        "required": ["type", "index", "key"],
                    },
                    "fix_action": {
                        "type": ["object", "null"],
                        "additionalProperties": False,
                        "properties": {
                            "type": {
                                "enum": [
                                    "set_paragraph_format",
                                    "apply_heading_style",
                                    "set_page_setup",
                                    "set_section_format",
                                ]
                            },
                            "target": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "type": {"enum": ["document", "paragraph", "section"]},
                                    "index": {"type": ["integer", "null"]},
                                    "key": {"type": ["string", "null"]},
                                },
                                "required": ["type", "index", "key"],
                            },
                            "properties": {"type": "object"},
                        },
                        "required": ["type", "target", "properties"],
                    },
                },
                "required": ["id", "severity", "message", "location", "fix_action"],
            },
        }
    },
    "required": ["issues"],
}
```

- [ ] **Step 4: Add prompts and local parser**

Create `engine/llm/prompts.py`:

```python
STRUCTURE_PROMPT = """你是文档结构识别器。只识别结构，不改写正文。返回 JSON。"""

FORMAT_INSTRUCTION_PROMPT = """你是格式指令解析器。把用户的自然语言格式要求解析为 JSON。只返回可执行的格式字段。"""

DIAGNOSIS_PROMPT = """你是文档格式诊断器。根据 profile、临时格式要求和文档结构输出问题列表。每个可修复问题必须包含 fix_action。"""
```

Create `engine/llm/client.py`:

```python
from __future__ import annotations

import json
import os
import re
from typing import Any

from openai import OpenAI

from engine.llm.prompts import FORMAT_INSTRUCTION_PROMPT
from engine.llm.schemas import FORMAT_OVERRIDE_SCHEMA
from engine.models import FormatOverride, ParagraphStyle


class OpenAIClient:
    def __init__(self, api_key: str | None = None, model: str = "gpt-4.1-mini") -> None:
        self.model = model
        self.client = OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))

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
        raw_text = response.output_text
        return FormatOverride.model_validate(json.loads(raw_text))


def parse_format_instruction_locally(instruction: str) -> FormatOverride:
    title = ParagraphStyle()
    body = ParagraphStyle()
    headings: dict[str, ParagraphStyle] = {}

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

    return FormatOverride(title=title, body=body, headings=headings)


def _find_font(text: str, fonts: list[str]) -> str | None:
    for font in fonts:
        if font in text:
            return font
    return None


def _find_font_after(text: str, marker: str, fonts: list[str]) -> str | None:
    index = text.find(marker)
    if index == -1:
        return None
    return _find_font(text[index : index + 40], fonts)


def _find_size_near(text: str, marker: str) -> str | None:
    index = text.find(marker)
    if index == -1:
        return None
    window = text[index : index + 50]
    match = re.search(r"(初号|小初|一号|小一|二号|小二|三号|小三|四号|小四|五号|小五)", window)
    return match.group(1) if match else None
```

- [ ] **Step 5: Run LLM tests**

Run:

```bash
python -m pytest tests/test_llm_schemas.py tests/test_format_instruction.py -v
```

Expected: PASS.

## Task 5: Pandoc Converter

**Files:**
- Create: `engine/converters/__init__.py`
- Create: `engine/converters/pandoc.py`
- Create: `tests/test_pandoc_converter.py`
- Create: `tests/fixtures/general.md`

- [ ] **Step 1: Write failing converter tests**

Create `tests/fixtures/general.md`:

```markdown
# 关于加强内部材料格式管理的说明

## 一、总体要求

这是正文第一段。

## 二、工作安排

这是正文第二段。
```

Create `tests/test_pandoc_converter.py`:

```python
from pathlib import Path

import pytest

from engine.converters.pandoc import PandocNotFoundError, convert_markdown_to_docx


def test_convert_markdown_to_docx_reports_missing_pandoc(monkeypatch, tmp_path):
    monkeypatch.setattr("engine.converters.pandoc.shutil.which", lambda name: None)

    with pytest.raises(PandocNotFoundError):
        convert_markdown_to_docx(Path("tests/fixtures/general.md"), tmp_path / "out.docx")
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest tests/test_pandoc_converter.py -v
```

Expected: FAIL because converter files do not exist.

- [ ] **Step 3: Implement Pandoc wrapper**

Create `engine/converters/__init__.py`:

```python
from engine.converters.pandoc import PandocNotFoundError, convert_markdown_to_docx

__all__ = ["PandocNotFoundError", "convert_markdown_to_docx"]
```

Create `engine/converters/pandoc.py`:

```python
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


class PandocNotFoundError(RuntimeError):
    pass


def convert_markdown_to_docx(input_path: Path, output_path: Path, reference_doc: Path | None = None) -> Path:
    pandoc = shutil.which("pandoc")
    if pandoc is None:
        raise PandocNotFoundError("Pandoc is not installed or not available on PATH")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [pandoc, str(input_path), "-o", str(output_path)]
    if reference_doc is not None:
        command.extend(["--reference-doc", str(reference_doc)])

    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Pandoc failed: {result.stderr.strip()}")
    return output_path
```

- [ ] **Step 4: Run converter tests**

Run:

```bash
python -m pytest tests/test_pandoc_converter.py -v
```

Expected: PASS.

## Task 6: DOCX Formatter

**Files:**
- Create: `engine/formatter/__init__.py`
- Create: `engine/formatter/docx_formatter.py`
- Create: `tests/test_docx_formatter.py`

- [ ] **Step 1: Write failing formatter tests**

Create `tests/test_docx_formatter.py`:

```python
from pathlib import Path

from docx import Document

from engine.formatter.docx_formatter import apply_profile_formatting
from engine.profiles.loader import load_profile


def test_apply_profile_formatting_sets_title_and_body(tmp_path):
    source = tmp_path / "source.docx"
    output = tmp_path / "formatted.docx"

    doc = Document()
    doc.add_paragraph("测试标题")
    doc.add_paragraph("这是正文段落。")
    doc.save(source)

    apply_profile_formatting(source, output, load_profile("general"))

    formatted = Document(output)
    assert formatted.paragraphs[0].alignment == 1
    assert formatted.paragraphs[0].runs[0].font.name == "方正小标宋"
    assert formatted.paragraphs[1].runs[0].font.name == "仿宋"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest tests/test_docx_formatter.py -v
```

Expected: FAIL because formatter files do not exist.

- [ ] **Step 3: Implement formatter**

Create `engine/formatter/__init__.py`:

```python
from engine.formatter.docx_formatter import apply_profile_formatting

__all__ = ["apply_profile_formatting"]
```

Create `engine/formatter/docx_formatter.py`:

```python
from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt

from engine.models import FormatOverride, PageSetup, ParagraphStyle, Profile
from engine.style_utils import chinese_size_to_pt, merge_style, parse_length_to_pt

ALIGNMENT = {
    "left": WD_ALIGN_PARAGRAPH.LEFT,
    "center": WD_ALIGN_PARAGRAPH.CENTER,
    "right": WD_ALIGN_PARAGRAPH.RIGHT,
    "justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
}


def apply_profile_formatting(
    input_docx: Path,
    output_docx: Path,
    profile: Profile,
    override: FormatOverride | None = None,
) -> Path:
    document = Document(input_docx)
    _apply_page_setup(document, override.page if override and override.page else profile.page)

    title_style = merge_style(profile.title, override.title if override else None)
    body_style = merge_style(profile.body, override.body if override else None)
    heading_overrides = override.headings if override else {}

    for index, paragraph in enumerate(document.paragraphs):
        if index == 0:
            _apply_paragraph_style(paragraph, title_style)
        elif _looks_like_heading(paragraph.text):
            style_key = "heading_1" if paragraph.text.strip().startswith(("一、", "二、", "三、")) else "heading_2"
            base = profile.headings.get(style_key, body_style)
            _apply_paragraph_style(paragraph, merge_style(base, heading_overrides.get(style_key)))
        else:
            _apply_paragraph_style(paragraph, body_style)

    output_docx.parent.mkdir(parents=True, exist_ok=True)
    document.save(output_docx)
    return output_docx


def _apply_page_setup(document: Document, page: PageSetup) -> None:
    for section in document.sections:
        section.top_margin = Cm(parse_length_to_pt(page.margin_top) / 28.3464567)
        section.bottom_margin = Cm(parse_length_to_pt(page.margin_bottom) / 28.3464567)
        section.left_margin = Cm(parse_length_to_pt(page.margin_left) / 28.3464567)
        section.right_margin = Cm(parse_length_to_pt(page.margin_right) / 28.3464567)


def _apply_paragraph_style(paragraph, style: ParagraphStyle) -> None:
    if style.align:
        paragraph.alignment = ALIGNMENT[style.align]
    if style.first_line_indent:
        paragraph.paragraph_format.first_line_indent = Pt(parse_length_to_pt(style.first_line_indent))
    if style.line_spacing:
        paragraph.paragraph_format.line_spacing = Pt(parse_length_to_pt(style.line_spacing))
    if style.space_before:
        paragraph.paragraph_format.space_before = Pt(parse_length_to_pt(style.space_before))
    if style.space_after:
        paragraph.paragraph_format.space_after = Pt(parse_length_to_pt(style.space_after))

    runs = paragraph.runs or [paragraph.add_run("")]
    for run in runs:
        if style.font:
            run.font.name = style.font
            run._element.rPr.rFonts.set("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}eastAsia", style.font)
        if style.size:
            run.font.size = Pt(chinese_size_to_pt(style.size))
        if style.bold is not None:
            run.font.bold = style.bold


def _looks_like_heading(text: str) -> bool:
    stripped = text.strip()
    return stripped.startswith(("一、", "二、", "三、", "四、", "五、", "（一）", "（二）", "（三）"))
```

- [ ] **Step 4: Run formatter test**

Run:

```bash
python -m pytest tests/test_docx_formatter.py -v
```

Expected: PASS.

## Task 7: Diagnostics And Whitelisted Fixes

**Files:**
- Create: `engine/diagnostics/__init__.py`
- Create: `engine/diagnostics/diagnose.py`
- Create: `engine/fixer/__init__.py`
- Create: `engine/fixer/apply_fixes.py`
- Create: `tests/test_diagnostics_and_fixes.py`

- [ ] **Step 1: Write failing diagnostics and fixer tests**

Create `tests/test_diagnostics_and_fixes.py`:

```python
from docx import Document

from engine.diagnostics.diagnose import diagnose_docx
from engine.fixer.apply_fixes import apply_fixes
from engine.profiles.loader import load_profile


def test_diagnose_and_fix_body_font(tmp_path):
    source = tmp_path / "bad.docx"
    fixed = tmp_path / "fixed.docx"

    doc = Document()
    doc.add_paragraph("测试标题")
    doc.add_paragraph("正文段落")
    doc.save(source)

    profile = load_profile("general")
    issues = diagnose_docx(source, profile)

    assert any(issue.fix_action for issue in issues)

    apply_fixes(source, fixed, issues)
    remaining = diagnose_docx(fixed, profile)

    assert len([issue for issue in remaining if issue.severity == "error"]) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest tests/test_diagnostics_and_fixes.py -v
```

Expected: FAIL because diagnostics and fixer files do not exist.

- [ ] **Step 3: Implement diagnostics**

Create `engine/diagnostics/__init__.py`:

```python
from engine.diagnostics.diagnose import diagnose_docx

__all__ = ["diagnose_docx"]
```

Create `engine/diagnostics/diagnose.py`:

```python
from __future__ import annotations

from pathlib import Path

from docx import Document

from engine.models import FixAction, Issue, Location, ParagraphStyle, Profile


def diagnose_docx(input_docx: Path, profile: Profile) -> list[Issue]:
    document = Document(input_docx)
    issues: list[Issue] = []

    if not document.paragraphs:
        return [
            Issue(
                id="issue_empty_document",
                severity="error",
                message="文档没有段落内容",
                location=Location(type="document", index=None, key=None),
                fix_action=None,
            )
        ]

    for index, paragraph in enumerate(document.paragraphs):
        expected = profile.title if index == 0 else profile.body
        run = paragraph.runs[0] if paragraph.runs else None
        actual_font = run.font.name if run else None
        if expected.font and actual_font != expected.font:
            issues.append(
                Issue(
                    id=f"issue_paragraph_{index}_font",
                    severity="warning",
                    message=f"第 {index + 1} 段字体不符合要求，应为 {expected.font}",
                    location=Location(type="paragraph", index=index, key=None),
                    fix_action=FixAction(
                        type="set_paragraph_format",
                        target=Location(type="paragraph", index=index, key=None),
                        properties=ParagraphStyle(font=expected.font, size=expected.size, align=expected.align),
                    ),
                )
            )

    return issues
```

- [ ] **Step 4: Implement whitelisted fixer**

Create `engine/fixer/__init__.py`:

```python
from engine.fixer.apply_fixes import apply_fixes

__all__ = ["apply_fixes"]
```

Create `engine/fixer/apply_fixes.py`:

```python
from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

from engine.models import Issue, ParagraphStyle
from engine.style_utils import chinese_size_to_pt

ALLOWED_ACTIONS = {"set_paragraph_format", "apply_heading_style", "set_section_format"}
ALIGNMENT = {
    "left": WD_ALIGN_PARAGRAPH.LEFT,
    "center": WD_ALIGN_PARAGRAPH.CENTER,
    "right": WD_ALIGN_PARAGRAPH.RIGHT,
    "justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
}


def apply_fixes(input_docx: Path, output_docx: Path, issues: list[Issue], selected_issue_ids: set[str] | None = None) -> Path:
    document = Document(input_docx)
    selected = selected_issue_ids or {issue.id for issue in issues}

    for issue in issues:
        if issue.id not in selected or issue.fix_action is None:
            continue
        action = issue.fix_action
        if action.type not in ALLOWED_ACTIONS:
            continue
        if action.target.type != "paragraph" or action.target.index is None:
            continue
        if action.target.index >= len(document.paragraphs):
            continue
        if not isinstance(action.properties, ParagraphStyle):
            continue
        _apply_paragraph_properties(document.paragraphs[action.target.index], action.properties)

    output_docx.parent.mkdir(parents=True, exist_ok=True)
    document.save(output_docx)
    return output_docx


def _apply_paragraph_properties(paragraph, style: ParagraphStyle) -> None:
    if style.align:
        paragraph.alignment = ALIGNMENT[style.align]
    runs = paragraph.runs or [paragraph.add_run("")]
    for run in runs:
        if style.font:
            run.font.name = style.font
            run._element.rPr.rFonts.set("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}eastAsia", style.font)
        if style.size:
            run.font.size = Pt(chinese_size_to_pt(style.size))
```

- [ ] **Step 5: Run diagnostics and fixer tests**

Run:

```bash
python -m pytest tests/test_diagnostics_and_fixes.py -v
```

Expected: PASS.

## Task 8: Engine CLI

**Files:**
- Create: `engine/cli.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write failing CLI tests**

Create `tests/test_cli.py`:

```python
import json

from docx import Document

from engine.cli import main


def test_cli_diagnose_outputs_json(tmp_path, capsys):
    input_docx = tmp_path / "input.docx"
    doc = Document()
    doc.add_paragraph("标题")
    doc.add_paragraph("正文")
    doc.save(input_docx)

    exit_code = main(["diagnose", "--input", str(input_docx), "--profile", "general"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert "issues" in payload
```

- [ ] **Step 2: Run CLI test to verify it fails**

Run:

```bash
python -m pytest tests/test_cli.py -v
```

Expected: FAIL because `engine.cli` does not exist.

- [ ] **Step 3: Implement CLI**

Create `engine/cli.py`:

```python
from __future__ import annotations

import argparse
import json
from pathlib import Path

from pydantic import TypeAdapter

from engine.converters.pandoc import convert_markdown_to_docx
from engine.diagnostics.diagnose import diagnose_docx
from engine.fixer.apply_fixes import apply_fixes
from engine.formatter.docx_formatter import apply_profile_formatting
from engine.llm.client import parse_format_instruction_locally
from engine.models import Issue
from engine.profiles.loader import load_profile


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="docforge")
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate")
    generate.add_argument("--input", required=True)
    generate.add_argument("--profile", default="general")
    generate.add_argument("--format-instruction", default="")
    generate.add_argument("--llm-provider", choices=["local", "openai"], default="local")
    generate.add_argument("--api-key", default=None)
    generate.add_argument("--output", required=True)

    diagnose = subparsers.add_parser("diagnose")
    diagnose.add_argument("--input", required=True)
    diagnose.add_argument("--profile", default="general")

    fix = subparsers.add_parser("fix")
    fix.add_argument("--input", required=True)
    fix.add_argument("--issues", required=True)
    fix.add_argument("--output", required=True)

    args = parser.parse_args(argv)

    if args.command == "generate":
        profile = load_profile(args.profile)
        output_path = Path(args.output)
        temp_docx = output_path.with_suffix(".pandoc.docx")
        convert_markdown_to_docx(Path(args.input), temp_docx)
        override = None
        if args.format_instruction:
            if args.llm_provider == "openai":
                from engine.llm.client import OpenAIClient

                override = OpenAIClient(api_key=args.api_key).parse_format_instruction(args.format_instruction)
            else:
                override = parse_format_instruction_locally(args.format_instruction)
        apply_profile_formatting(temp_docx, output_path, profile, override)
        issues = diagnose_docx(output_path, profile)
        print(json.dumps({"output": str(output_path), "issues": [issue.model_dump() for issue in issues]}, ensure_ascii=False))
        return 0

    if args.command == "diagnose":
        issues = diagnose_docx(Path(args.input), load_profile(args.profile))
        print(json.dumps({"issues": [issue.model_dump() for issue in issues]}, ensure_ascii=False))
        return 0

    if args.command == "fix":
        payload = json.loads(Path(args.issues).read_text(encoding="utf-8"))
        issues = TypeAdapter(list[Issue]).validate_python(payload["issues"])
        apply_fixes(Path(args.input), Path(args.output), issues)
        print(json.dumps({"output": args.output}, ensure_ascii=False))
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run CLI tests**

Run:

```bash
python -m pytest tests/test_cli.py -v
```

Expected: PASS.

## Task 9: Desktop App Scaffold

**Files:**
- Create: `apps/desktop/package.json`
- Create: `apps/desktop/index.html`
- Create: `apps/desktop/src/main.tsx`
- Create: `apps/desktop/src/App.tsx`
- Create: `apps/desktop/src/App.css`
- Create: `apps/desktop/src/types.ts`
- Create: `apps/desktop/src-tauri/tauri.conf.json`
- Create: `apps/desktop/src-tauri/Cargo.toml`
- Create: `apps/desktop/src-tauri/src/main.rs`

- [ ] **Step 1: Add desktop package metadata**

Create `apps/desktop/package.json`:

```json
{
  "name": "docforge-desktop",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "tauri": "tauri"
  },
  "dependencies": {
    "@tauri-apps/api": "^2.0.0",
    "lucide-react": "^0.468.0",
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@tauri-apps/cli": "^2.0.0",
    "@types/react": "^18.3.1",
    "@types/react-dom": "^18.3.1",
    "@vitejs/plugin-react": "^4.3.0",
    "typescript": "^5.5.0",
    "vite": "^5.4.0"
  }
}
```

- [ ] **Step 2: Add React entry files**

Create `apps/desktop/index.html`:

```html
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>DocForge</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

Create `apps/desktop/src/main.tsx`:

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./App";
import "./App.css";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
```

Create `apps/desktop/src/types.ts`:

```ts
export type ProfileId = "general" | "official" | "meeting_minutes" | "briefing" | "speech";

export type Issue = {
  id: string;
  severity: "info" | "warning" | "error";
  message: string;
  location: {
    type: "document" | "paragraph" | "section";
    index: number | null;
    key: string | null;
  };
  fix_action: unknown | null;
};
```

- [ ] **Step 3: Add initial desktop UI**

Create `apps/desktop/src/App.tsx`:

```tsx
import { FileText, Wrench } from "lucide-react";
import type { Issue, ProfileId } from "./types";

const profiles: Array<{ id: ProfileId; label: string }> = [
  { id: "general", label: "通用格式文档" },
  { id: "official", label: "公文" },
  { id: "meeting_minutes", label: "会议纪要" },
  { id: "briefing", label: "汇报材料" },
  { id: "speech", label: "讲话稿" },
];

export function App() {
  const issues: Issue[] = [];

  return (
    <main className="shell">
      <header className="topbar">
        <div>
          <h1>DocForge</h1>
          <p>Markdown 转 docx，诊断格式问题，并执行安全修复。</p>
        </div>
        <button className="iconButton" title="设置 API Key" type="button">
          <Wrench size={18} />
        </button>
      </header>

      <section className="workspace">
        <aside className="panel">
          <label>
            Markdown 文件
            <input type="text" placeholder="/path/to/input.md" />
          </label>
          <label>
            文档类型
            <select defaultValue="general">
              {profiles.map((profile) => (
                <option key={profile.id} value={profile.id}>
                  {profile.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            临时格式指令
            <textarea placeholder="标题二号小标宋居中，正文三号仿宋，行距28磅" />
          </label>
          <button className="primary" type="button">
            <FileText size={18} />
            生成 docx
          </button>
        </aside>

        <section className="panel status">
          <h2>处理状态</h2>
          <ol>
            <li>等待选择文件</li>
            <li>等待生成基础 docx</li>
            <li>等待格式诊断</li>
          </ol>
        </section>

        <section className="panel issues">
          <h2>诊断问题</h2>
          {issues.length === 0 ? <p>暂无诊断结果</p> : null}
        </section>
      </section>
    </main>
  );
}
```

Create `apps/desktop/src/App.css`:

```css
* {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  color: #202124;
  background: #f5f7fa;
}

.shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.topbar {
  min-height: 76px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 24px;
  border-bottom: 1px solid #d8dde6;
  background: #ffffff;
}

.topbar h1 {
  margin: 0;
  font-size: 20px;
}

.topbar p {
  margin: 4px 0 0;
  color: #5f6673;
}

.workspace {
  flex: 1;
  display: grid;
  grid-template-columns: 320px minmax(280px, 1fr) minmax(320px, 420px);
  gap: 16px;
  padding: 16px;
}

.panel {
  background: #ffffff;
  border: 1px solid #d8dde6;
  border-radius: 8px;
  padding: 16px;
}

label {
  display: grid;
  gap: 6px;
  margin-bottom: 14px;
  font-size: 14px;
  color: #343a46;
}

input,
select,
textarea {
  width: 100%;
  border: 1px solid #c5ccd8;
  border-radius: 6px;
  padding: 10px;
  font: inherit;
}

textarea {
  min-height: 120px;
  resize: vertical;
}

button {
  border: 0;
  border-radius: 6px;
  cursor: pointer;
  font: inherit;
}

.primary {
  width: 100%;
  height: 40px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #ffffff;
  background: #1f6feb;
}

.iconButton {
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  color: #343a46;
  background: #eef2f7;
}
```

- [ ] **Step 4: Add Tauri scaffold files**

Create `apps/desktop/src-tauri/tauri.conf.json`:

```json
{
  "$schema": "https://schema.tauri.app/config/2",
  "productName": "DocForge",
  "version": "0.1.0",
  "identifier": "com.docforge.desktop",
  "build": {
    "beforeDevCommand": "npm run dev",
    "devUrl": "http://localhost:5173",
    "beforeBuildCommand": "npm run build",
    "frontendDist": "../dist"
  },
  "app": {
    "windows": [
      {
        "title": "DocForge",
        "width": 1200,
        "height": 760
      }
    ]
  }
}
```

Create `apps/desktop/src-tauri/Cargo.toml`:

```toml
[package]
name = "docforge-desktop"
version = "0.1.0"
edition = "2021"

[dependencies]
tauri = { version = "2", features = [] }
serde = { version = "1", features = ["derive"] }
serde_json = "1"

[build-dependencies]
tauri-build = { version = "2", features = [] }
```

Create `apps/desktop/src-tauri/src/main.rs`:

```rust
fn main() {
    tauri::Builder::default()
        .run(tauri::generate_context!())
        .expect("failed to run tauri application");
}
```

- [ ] **Step 5: Install dependencies and build frontend**

Run:

```bash
cd apps/desktop
npm install
npm run build
```

Expected: `dist/` is generated and TypeScript build passes.

If network access fails while installing dependencies, rerun `npm install` with escalation because dependency download is required for this task.

## Task 10: Desktop Calls Engine CLI

**Files:**
- Modify: `apps/desktop/src-tauri/Cargo.toml`
- Modify: `apps/desktop/src-tauri/src/main.rs`
- Modify: `apps/desktop/src/App.tsx`
- Modify: `apps/desktop/src/types.ts`

- [ ] **Step 1: Add frontend command types**

Modify `apps/desktop/src/types.ts`:

```ts
export type ProfileId = "general" | "official" | "meeting_minutes" | "briefing" | "speech";

export type Issue = {
  id: string;
  severity: "info" | "warning" | "error";
  message: string;
  location: {
    type: "document" | "paragraph" | "section";
    index: number | null;
    key: string | null;
  };
  fix_action: unknown | null;
};

export type GenerateRequest = {
  inputPath: string;
  outputPath: string;
  profile: ProfileId;
  formatInstruction: string;
  llmProvider: "local" | "openai";
  apiKey: string;
};

export type GenerateResponse = {
  output: string;
  issues: Issue[];
};
```

- [ ] **Step 2: Add Tauri command that runs Python CLI**

Modify `apps/desktop/src-tauri/Cargo.toml` so dependencies are:

```toml
[dependencies]
tauri = { version = "2", features = [] }
serde = { version = "1", features = ["derive"] }
serde_json = "1"
```

Modify `apps/desktop/src-tauri/src/main.rs`:

```rust
use serde::{Deserialize, Serialize};
use std::process::Command;

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct GenerateRequest {
    input_path: String,
    output_path: String,
    profile: String,
    format_instruction: String,
    llm_provider: String,
    api_key: String,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
struct EngineResult {
    stdout: String,
}

#[tauri::command]
fn generate_docx(request: GenerateRequest) -> Result<EngineResult, String> {
    let output = Command::new("python")
        .args([
            "-m",
            "engine.cli",
            "generate",
            "--input",
            &request.input_path,
            "--profile",
            &request.profile,
            "--format-instruction",
            &request.format_instruction,
            "--llm-provider",
            &request.llm_provider,
            "--api-key",
            &request.api_key,
            "--output",
            &request.output_path,
        ])
        .current_dir("../../")
        .output()
        .map_err(|error| error.to_string())?;

    if !output.status.success() {
        return Err(String::from_utf8_lossy(&output.stderr).to_string());
    }

    Ok(EngineResult {
        stdout: String::from_utf8_lossy(&output.stdout).to_string(),
    })
}

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![generate_docx])
        .run(tauri::generate_context!())
        .expect("failed to run tauri application");
}
```

- [ ] **Step 3: Wire React form to Tauri command**

Modify `apps/desktop/src/App.tsx`:

```tsx
import { invoke } from "@tauri-apps/api/core";
import { FileText, Wrench } from "lucide-react";
import { useState } from "react";
import type { GenerateResponse, Issue, ProfileId } from "./types";

const profiles: Array<{ id: ProfileId; label: string }> = [
  { id: "general", label: "通用格式文档" },
  { id: "official", label: "公文" },
  { id: "meeting_minutes", label: "会议纪要" },
  { id: "briefing", label: "汇报材料" },
  { id: "speech", label: "讲话稿" },
];

export function App() {
  const [inputPath, setInputPath] = useState("");
  const [outputPath, setOutputPath] = useState("");
  const [profile, setProfile] = useState<ProfileId>("general");
  const [formatInstruction, setFormatInstruction] = useState("");
  const [llmProvider, setLlmProvider] = useState<"local" | "openai">("openai");
  const [apiKey, setApiKey] = useState("");
  const [issues, setIssues] = useState<Issue[]>([]);
  const [status, setStatus] = useState("等待选择文件");

  async function handleGenerate() {
    setStatus("正在生成 docx");
    const result = await invoke<{ stdout: string }>("generate_docx", {
      request: { inputPath, outputPath, profile, formatInstruction, llmProvider, apiKey },
    });
    const payload = JSON.parse(result.stdout) as GenerateResponse;
    setIssues(payload.issues);
    setStatus(`已生成：${payload.output}`);
  }

  return (
    <main className="shell">
      <header className="topbar">
        <div>
          <h1>DocForge</h1>
          <p>Markdown 转 docx，诊断格式问题，并执行安全修复。</p>
        </div>
        <button className="iconButton" title="设置 API Key" type="button">
          <Wrench size={18} />
        </button>
      </header>

      <section className="workspace">
        <aside className="panel">
          <label>
            OpenAI API Key
            <input value={apiKey} onChange={(event) => setApiKey(event.target.value)} placeholder="sk-..." />
          </label>
          <label>
            解析方式
            <select value={llmProvider} onChange={(event) => setLlmProvider(event.target.value as "local" | "openai")}>
              <option value="openai">OpenAI API</option>
              <option value="local">本地规则解析</option>
            </select>
          </label>
          <label>
            Markdown 文件
            <input value={inputPath} onChange={(event) => setInputPath(event.target.value)} placeholder="/path/to/input.md" />
          </label>
          <label>
            输出 docx
            <input value={outputPath} onChange={(event) => setOutputPath(event.target.value)} placeholder="/path/to/output.docx" />
          </label>
          <label>
            文档类型
            <select value={profile} onChange={(event) => setProfile(event.target.value as ProfileId)}>
              {profiles.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            临时格式指令
            <textarea value={formatInstruction} onChange={(event) => setFormatInstruction(event.target.value)} placeholder="标题二号小标宋居中，正文三号仿宋，行距28磅" />
          </label>
          <button className="primary" type="button" onClick={handleGenerate}>
            <FileText size={18} />
            生成 docx
          </button>
        </aside>

        <section className="panel status">
          <h2>处理状态</h2>
          <p>{status}</p>
        </section>

        <section className="panel issues">
          <h2>诊断问题</h2>
          {issues.length === 0 ? <p>暂无诊断结果</p> : null}
          {issues.map((issue) => (
            <article key={issue.id} className="issue">
              <strong>{issue.severity}</strong>
              <p>{issue.message}</p>
            </article>
          ))}
        </section>
      </section>
    </main>
  );
}
```

- [ ] **Step 4: Build frontend**

Run:

```bash
cd apps/desktop
npm run build
```

Expected: TypeScript build passes.

## Task 11: End-To-End CLI Verification

**Files:**
- Create: `tests/test_e2e_cli.py`

- [ ] **Step 1: Write end-to-end test with Pandoc skip**

Create `tests/test_e2e_cli.py`:

```python
import shutil

import pytest
from docx import Document

from engine.cli import main


@pytest.mark.skipif(shutil.which("pandoc") is None, reason="pandoc is required for e2e conversion")
def test_generate_general_docx_from_markdown(tmp_path):
    input_md = tmp_path / "input.md"
    output_docx = tmp_path / "output.docx"
    input_md.write_text(
        "# 测试标题\n\n## 一、总体要求\n\n这是正文段落。\n",
        encoding="utf-8",
    )

    exit_code = main(
        [
            "generate",
            "--input",
            str(input_md),
            "--profile",
            "general",
            "--format-instruction",
            "标题用方正小标宋二号居中，正文仿宋三号，行距固定28磅",
            "--output",
            str(output_docx),
        ]
    )

    assert exit_code == 0
    assert output_docx.exists()
    doc = Document(output_docx)
    assert doc.paragraphs[0].text.strip() == "测试标题"
```

- [ ] **Step 2: Run all Python tests**

Run:

```bash
python -m pytest -v
```

Expected: PASS, with the e2e test skipped if Pandoc is not installed.

- [ ] **Step 3: Run manual CLI smoke test if Pandoc is installed**

Run:

```bash
python -m engine.cli generate --input tests/fixtures/general.md --profile general --format-instruction "标题用方正小标宋二号居中，正文仿宋三号，行距固定28磅" --llm-provider local --output /tmp/docforge-general.docx
```

Expected: JSON output includes `"output": "/tmp/docforge-general.docx"` and an `"issues"` array.

## Task 12: Documentation And Local Run Notes

**Files:**
- Create: `README.md`

- [ ] **Step 1: Add concise local run documentation**

Create `README.md`:

```markdown
# DocForge

DocForge 文档格式智能整理桌面软件雏形。第一版支持 Markdown 转 `.docx`、文档 profile、临时格式指令、格式诊断和安全修复。

## Python Engine

Install dev dependencies:

```bash
python -m pip install -e ".[dev]"
```

Run tests:

```bash
python -m pytest -v
```

Generate a docx:

```bash
python -m engine.cli generate \
  --input tests/fixtures/general.md \
  --profile general \
  --format-instruction "标题用方正小标宋二号居中，正文仿宋三号，行距固定28磅" \
  --llm-provider local \
  --output /tmp/docforge-general.docx
```

## Desktop

Install and run:

```bash
cd apps/desktop
npm install
npm run dev
```

Run Tauri during desktop development:

```bash
cd apps/desktop
npm run tauri dev
```

## Notes

- Pandoc must be available on `PATH` for Markdown to `.docx` conversion.
- OpenAI integration is isolated in `engine/llm`. Use `--llm-provider openai --api-key "$OPENAI_API_KEY"` for API-backed parsing, or `--llm-provider local` for deterministic development tests.
- The current MVP does not support `.doc`, Word/WPS plugins, content rewriting, or online preview.
```

- [ ] **Step 2: Verify docs commands are consistent**

Run:

```bash
rg -n "python -m engine.cli|npm run" README.md docs/superpowers/plans/2026-05-25-docforge-desktop-implementation.md
```

Expected: commands reference `engine.cli`, `npm run build`, `npm run dev`, and `npm run tauri dev`.

## Final Verification

- [ ] Run Python tests:

```bash
python -m pytest -v
```

Expected: PASS, with Pandoc e2e skipped only when Pandoc is unavailable.

- [ ] Run frontend build:

```bash
cd apps/desktop
npm run build
```

Expected: PASS.

- [ ] Check workspace:

```bash
git status --short
```

Expected: implementation files are listed as modified or untracked. Do not commit unless the user asks.

## Self-Review

Spec coverage:

- Markdown import and `.docx` export are covered by Tasks 5, 8, and 11.
- Five document profiles are covered by Task 3.
- Temporary format instructions are covered by Task 4 and used by Tasks 6, 8, and 10.
- OpenAI API key and provider selection are covered by Tasks 8 and 10.
- Pandoc basic conversion is covered by Task 5.
- `.docx` post-processing is covered by Task 6.
- Diagnosis and single/all fix foundations are covered by Task 7.
- Desktop shell is covered by Tasks 9 and 10.
- Testing and run notes are covered by Tasks 11 and 12.

Residual risk:

- OpenAI-backed parsing requires a real API key and network access, so automated tests use the local parser and schema tests instead of making live API calls.
