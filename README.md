# DocForge

DocForge 文档格式智能整理桌面软件雏形。当前版本支持 Markdown 和 `.docx` 格式整理、文档 profile、临时格式指令、格式诊断、安全修复，以及多种模型协议的格式指令解析。

## Current Status

- Code baseline through `d11fdf1` has been merged and pushed to `origin/main`.
- Main handoff note: [docs/handoff-2026-05-27.md](docs/handoff-2026-05-27.md).
- Preferred CLI entry point: `format`, which accepts Markdown and `.docx` input.
- Desktop processing requires the Tauri runtime. `npm run dev` is useful for UI-only work; use `npm run tauri dev` for real document processing.

## Python Engine

Install dev dependencies:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
```

Run tests:

```bash
.venv/bin/python -m pytest -v
```

Generate a docx:

```bash
.venv/bin/python -m engine.cli generate \
  --input tests/fixtures/general.md \
  --profile general \
  --format-instruction "标题用方正小标宋二号居中，正文仿宋三号，行距固定28磅" \
  --llm-provider local \
  --output /tmp/docforge-general.docx
```

`generate` remains the Markdown-compatible path. For general use, prefer `format`, which accepts Markdown and `.docx` input.

Format an existing docx:

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

## Desktop

Install frontend dependencies:

```bash
cd apps/desktop
npm install
```

Run the desktop app during development:

```bash
cd apps/desktop
export DOCFORGE_PYTHON="$(pwd)/../../.venv/bin/python"
npm run tauri dev
```

Use plain Vite only for UI-only checks:

```bash
cd apps/desktop
npm run dev
```

The browser page opened by `npm run dev` cannot call the Rust/Python backend. Document processing must be tested through Tauri or a packaged desktop app.

Verify desktop code:

```bash
cd apps/desktop
npm run build
cd src-tauri
cargo check
```

## Notes

- Pandoc must be available on `PATH` for Markdown to `.docx` conversion.
- LLM provider adapters are isolated in `engine/llm`. Supported providers are `local`, `openai`/`openai-responses`, `openai-compatible`, and `anthropic-messages`.
- Use `--llm-provider local` for deterministic development tests.
- API keys entered in the desktop app are passed to the Python child process through environment variables, not command-line argv.
- The current MVP does not support legacy `.doc` input, Word/WPS plugins, content rewriting, or online preview.
