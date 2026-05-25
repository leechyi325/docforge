# DocForge

DocForge 文档格式智能整理桌面软件雏形。第一版支持 Markdown 转 `.docx`、文档 profile、临时格式指令、格式诊断和安全修复。

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
export DOCFORGE_PYTHON="$(pwd)/../../.venv/bin/python"
npm run tauri dev
```

## Notes

- Pandoc must be available on `PATH` for Markdown to `.docx` conversion.
- OpenAI integration is isolated in `engine/llm`. Use `--llm-provider openai --api-key "$OPENAI_API_KEY"` for API-backed parsing, or `--llm-provider local` for deterministic development tests.
- The current MVP does not support `.doc`, Word/WPS plugins, content rewriting, or online preview.
