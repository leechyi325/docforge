# AGENTS.md

This file is the handoff guide for agents working on DocForge.

## Project Snapshot

DocForge is a desktop MVP for intelligent document formatting. The first usable path is:

```text
Markdown -> Pandoc base .docx -> deterministic Python formatting -> diagnosis -> whitelisted fixes
```

The product is aimed at users who draft in Markdown and then need Word/WPS-ready documents with specific formatting rules. Initial document profiles include:

- `general`: lightweight formatted documents that mainly care about title, body font/size, paragraph headings, indentation, and spacing.
- `official`: government-style official documents.
- `meeting_minutes`: meeting minutes.
- `briefing`: briefing/reporting materials.
- `speech`: speeches.

The project name is DocForge. Keep that name in user-facing docs and package/app copy unless the user explicitly renames it.

## Current Scope

Implemented MVP capabilities:

- Markdown input.
- Direct `.docx` input formatting through the Python CLI `format` command.
- Profile selection.
- Temporary natural-language format instructions.
- Local deterministic fallback for instruction parsing and tests.
- Optional OpenAI Responses, OpenAI-compatible Chat Completions, and Anthropic Messages provider adapters for format instruction parsing through the Python engine.
- Pandoc conversion from Markdown to `.docx`.
- Deterministic `.docx` post-formatting with `python-docx`.
- Format diagnosis.
- Safe fix actions through a whitelist.
- Tauri + React desktop workbench that calls the Python CLI.

Explicit non-goals for the current MVP:

- `.doc` legacy format support.
- Word/WPS plugin integration.
- Online Word-grade preview.
- Broad content rewriting or style polishing.
- Letting the model directly edit `.docx` files or execute local commands.

## Architecture

Python is the source of truth. The desktop app should stay a thin local UI that calls the CLI.

Key areas:

- `engine/cli.py`: CLI entry point for `format`, `generate`, `diagnose`, and `fix`.
- `engine/models.py`: typed domain models for profiles, styles, issues, and fix actions.
- `engine/style_utils.py`: Chinese font size conversion, unit parsing, and style merge helpers.
- `engine/profiles/*.yaml`: built-in document profile definitions.
- `engine/profiles/loader.py`: profile loading and validation.
- `engine/llm/client.py`: LLM provider dispatch and local deterministic fallback.
- `engine/llm/prompts.py`: prompts for structure recognition, format instruction parsing, and diagnosis.
- `engine/llm/schemas.py`: JSON schemas and validation boundaries for model outputs.
- `engine/converters/pandoc.py`: Pandoc wrapper.
- `engine/formatter/docx_formatter.py`: deterministic `.docx` formatting.
- `engine/diagnostics/diagnose.py`: diagnosis generation.
- `engine/fixer/apply_fixes.py`: whitelist-based fix executor.
- `apps/desktop/src`: React UI.
- `apps/desktop/src-tauri`: Tauri shell and Python CLI invocation.
- `docs/superpowers/specs/2026-05-25-docforge-desktop-design.md`: design spec.
- `docs/superpowers/plans/2026-05-25-docforge-desktop-implementation.md`: implementation plan/history.

## Model Boundary

OpenAI can help with:

- Document structure recognition.
- Parsing temporary natural-language format instructions into structured overrides.
- Format diagnosis assistance.

OpenAI must not:

- Generate the final Word file directly.
- Modify `.docx` files directly.
- Execute arbitrary local commands.
- Rewrite document content unless a future request explicitly adds that scope.

All model outputs must be schema-validated and converted into local typed data before use. Fixes must go through `FixAction` and the whitelist in `engine/fixer/apply_fixes.py`.

Use local deterministic parsing for normal tests:

```bash
.venv/bin/python -m engine.cli generate \
  --input tests/fixtures/general.md \
  --profile general \
  --format-instruction "标题用方正小标宋二号居中，正文仿宋三号，行距固定28磅" \
  --llm-provider local \
  --output /tmp/docforge-general.docx
```

Use `format` for the preferred general entry point, including direct `.docx` formatting:

```bash
.venv/bin/python -m engine.cli format \
  --input input.docx \
  --profile official \
  --format-instruction "正文仿宋三号，行距28磅" \
  --llm-provider local \
  --output output.docx
```

Use API-backed providers only when needed:

```bash
.venv/bin/python -m engine.cli generate \
  --input input.md \
  --profile official \
  --format-instruction "正文仿宋三号，行距28磅" \
  --llm-provider openai \
  --api-key "$OPENAI_API_KEY" \
  --output output.docx
```

## Profiles

Profile precedence is:

```text
system defaults < document profile < temporary user format instruction
```

When adding or changing a profile:

- Add or update a YAML file in `engine/profiles/`.
- Keep style fields aligned with `engine/models.py`.
- Add tests for loading and any new behavior.
- Prefer adding deterministic formatting rules before adding model-dependent logic.
- Keep `general` simple and forgiving; it is for documents with only basic formatting requirements.

## Desktop App

The desktop is a Tauri + React + TypeScript workbench. It should remain functional and direct for now; visual polish and complex page layout are later work.

The desktop invokes the Python engine through the CLI. Use `DOCFORGE_PYTHON` to point Tauri at the virtualenv Python during local development:

```bash
cd apps/desktop
export DOCFORGE_PYTHON="$(pwd)/../../.venv/bin/python"
npm run tauri dev
```

Do not duplicate formatting business logic in React or Rust unless there is a strong reason. Keep formatting, diagnosis, and fixing inside the Python engine. The desktop should pass provider, model, and base URL settings through to the CLI rather than reimplementing provider behavior. API keys collected by the desktop should be passed to the child process through provider environment variables, not CLI argv.

## Development Setup

Prefer the virtualenv Python. In this environment, plain `python` may not exist.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
```

Install desktop dependencies:

```bash
cd apps/desktop
npm install
```

Pandoc must be available on `PATH` for Markdown to `.docx` conversion. The previous verified local Pandoc path was `/opt/homebrew/bin/pandoc`.

Network access may be restricted in agent sessions. If `pip install`, `npm install`, or package downloads fail with network/sandbox errors, request escalation instead of working around it.

## Verification

For Python engine changes:

```bash
.venv/bin/python -m pytest -v
```

For a focused test:

```bash
.venv/bin/python -m pytest tests/test_cli.py -v
```

For desktop frontend changes:

```bash
cd apps/desktop
npm run build
```

For Pandoc conversion behavior, run the relevant tests only when Pandoc is installed:

```bash
.venv/bin/python -m pytest tests/test_pandoc_converter.py tests/test_e2e_cli.py -v
```

Known verification state after the MVP merge:

- Python test suite: 14 passed.
- Frontend build: passed.
- Pandoc e2e: passed when Pandoc was available.
- Rust/Tauri compile check was not run because `cargo` was not installed in the environment.

Known verification state after the second-round implementation:

- Python test suite: 43 passed.
- Frontend build: passed.
- Pandoc e2e: passed when Pandoc was available.
- Rust/Tauri compile check was not run because `cargo` was not installed in the environment.

Do not claim Tauri/Rust compilation is verified unless you actually run it successfully.

## Git And Generated Files

`main` already includes the desktop MVP implementation. The previous implementation worktree was merged and removed.

Do not commit generated or dependency directories:

- `.venv/`
- `node_modules/`
- `dist/`
- `.pytest_cache/`
- `__pycache__/`

The user previously said not to commit unless explicitly requested. Check `git status --short` and `git diff` before and after edits, and do not revert unrelated user changes.

## Coding Notes

- Use `rg` and `rg --files` for repository search.
- Use `apply_patch` for manual file edits.
- Keep model-facing schemas strict and local execution conservative.
- Add tests near the behavior being changed.
- Keep comments sparse and useful.
- Prefer extending current modules over adding new abstractions unless the existing shape clearly needs one.
