# DocForge 第二轮开发设计

日期：2026-05-26

## 背景

DocForge 第一轮已经完成 Markdown 到 `.docx` 的基础链路：Pandoc 转换、Python 确定性格式整理、格式诊断、安全修复，以及 Tauri + React 桌面工作台。

第二轮开发聚焦两个方向：

- 让用户可以直接导入已有 `.docx` 文件并整理格式。
- 支持更多大模型 API 协议，降低用户对单一模型供应商的依赖。

本轮暂不支持 `.doc` 老格式。`.doc` 是二进制 Word 格式，`python-docx` 无法直接读取，可靠支持通常依赖 LibreOffice 等外部转换器。为避免把第二轮主线拖入外部环境兼容问题，本轮只接受 Markdown 和 `.docx`。

## 目标

第二轮交付后，DocForge 应支持两条输入路径：

```text
Markdown -> Pandoc base .docx -> deterministic Python formatting -> diagnosis
.docx -> deterministic Python formatting -> diagnosis
```

模型侧支持三类远程协议：

```text
OpenAI Responses API
OpenAI-compatible Chat Completions API
Anthropic Messages API
```

本地规则解析仍保留，用于离线开发、测试和没有 API Key 的基础场景。

## 非目标

本轮不做以下能力：

- `.doc` 老格式导入。
- Word/WPS 插件。
- 在线 Word 级预览。
- 让模型直接读取、生成或修改 `.docx` 文件。
- 让模型执行本地命令。
- 内容润色、扩写、改写或语义编辑。
- 为每个模型厂商硬编码完整专用业务逻辑。

## 设计原则

Python 引擎仍是业务源头。桌面端只负责收集参数、调用 CLI、展示状态和诊断结果。

模型层必须保持窄边界：模型只生成结构化候选结果，例如 `FormatOverride`、文档结构或诊断建议。本地程序必须对模型输出做 schema / Pydantic 校验，并且只有校验后的数据才能进入 formatter 或 fixer。

格式落地仍由本地确定性代码执行。无论模型协议来自 OpenAI、OpenAI-compatible 网关，还是 Anthropic Messages，最终都不能绕过本地类型模型和修复白名单。

## 文档输入流程

新增一个统一的文档处理管线，负责把不同输入准备为可格式化的 `.docx`。

```text
input path
  -> detect input kind
      .md       -> Pandoc 转临时 .docx
      .markdown -> Pandoc 转临时 .docx
      .docx     -> 直接作为源文档
      other     -> 明确报错
  -> parse format instruction
  -> apply_profile_formatting()
  -> diagnose_docx()
  -> JSON output
```

`.docx` 直接整理必须输出到新路径，不做原位覆盖。这样可以避免误改用户原始文件，也符合当前 `apply_profile_formatting(input_docx, output_docx, ...)` 的接口形态。

Markdown 路径继续保留现有行为，内部改为复用统一 pipeline，减少 `generate` 与新命令之间的重复逻辑。

## CLI 设计

保留现有 `generate` 命令作为 Markdown 生成入口，保证已有脚本可继续使用。

新增 `format` 命令作为统一整理入口，支持 `.md`、`.markdown` 和 `.docx`：

```bash
.venv/bin/python -m engine.cli format \
  --input input.docx \
  --profile official \
  --format-instruction "正文仿宋三号，行距28磅" \
  --llm-provider local \
  --output output.docx
```

当输入为 Markdown 时，`format` 与 `generate` 行为一致：

```bash
.venv/bin/python -m engine.cli format \
  --input input.md \
  --profile general \
  --format-instruction "标题二号小标宋居中，正文三号仿宋" \
  --llm-provider openai-responses \
  --output output.docx
```

模型参数统一为：

```text
--llm-provider local|openai-responses|openai-compatible|anthropic-messages
--llm-model MODEL
--llm-base-url URL
--api-key KEY
```

兼容策略：

- `--llm-provider openai` 可作为 `openai-responses` 的兼容别名，避免破坏第一轮命令。
- `--llm-provider local` 不要求 `--api-key`、`--llm-model` 或 `--llm-base-url`。
- `openai-compatible` 必须提供 `--llm-model`，通常也需要 `--llm-base-url` 和 `--api-key`。
- `anthropic-messages` 必须提供 Anthropic 模型名和 API Key，可选 `--llm-base-url` 以支持网关或代理。

## 模型协议适配

新增统一接口：

```text
LlmClient
  parse_format_instruction(instruction: str) -> FormatOverride
```

后续结构识别和诊断辅助也挂在同一接口下，但本轮实现优先围绕格式指令解析。

### local

继续使用当前 deterministic parser。它用于测试、基础离线体验和远程模型不可用时的退路。

### openai-responses

用于 OpenAI 官方模型。它保留当前 Responses API + JSON Schema 的方式，适合作为结构化输出最稳的路径。

默认模型可以继续使用当前代码里的轻量模型，但 CLI 和桌面端必须允许用户显式覆盖模型名。

### openai-compatible

用于第三方模型和网关，例如 DeepSeek、Qwen、Kimi、OpenRouter、LiteLLM 等兼容 `/v1/chat/completions` 的服务。

适配层使用 Chat Completions 风格请求。结构化输出按能力分级：

1. 如果目标服务支持 JSON Schema response format，传入 schema。
2. 如果只支持 JSON mode，要求返回 JSON object。
3. 如果只支持普通文本，提示词强约束只返回 JSON。

无论哪种方式，返回值都必须经过 `FormatOverride.model_validate(...)`。校验失败时返回清晰错误，不执行格式整理。

### anthropic-messages

用于 Claude 官方 API 或 Anthropic-format 网关。适配层使用 Messages API 的 messages 输入和文本输出。

Anthropic Messages 不等同于 OpenAI Chat Completions，也不等同于 Responses API。它是独立协议。本项目只在 adapter 层处理协议差异，业务层不感知 Anthropic 字段。

由于 Anthropic 原生结构化输出形态与 OpenAI JSON Schema 不同，本轮采用“提示词要求 JSON + 本地严格校验”的稳妥路线。后续如果需要，可再引入 tool use 作为结构化输出通道。

## 配置策略

第二轮先以 CLI 参数为主，不引入复杂配置文件。桌面端在界面中提供以下字段：

- 模型协议。
- Base URL。
- 模型名。
- API Key。

环境变量作为可选补充：

```text
OPENAI_API_KEY
ANTHROPIC_API_KEY
DOCFORGE_LLM_BASE_URL
DOCFORGE_LLM_MODEL
```

命令行参数优先级高于环境变量。没有传入参数时，adapter 再读取对应环境变量。

API Key 不写入项目文件，不出现在日志和诊断 JSON 中。

## 桌面端影响

桌面端需要从“Markdown 文件”输入改成“输入文件”，允许用户填写或选择 `.md`、`.markdown`、`.docx`。

操作按钮文案从“生成 docx”调整为“整理并导出 docx”或相近表达。状态提示需要区分：

- Markdown 转换中。
- `.docx` 格式整理中。
- 模型解析格式指令中。
- 诊断中。
- 已导出。

Tauri Rust 层继续只做 CLI 桥接。它需要传递新增字段，不实现格式逻辑或模型逻辑。

## 引擎影响

建议新增或重构以下模块：

```text
engine/pipeline.py
engine/llm/settings.py
engine/llm/base.py
engine/llm/openai_responses.py
engine/llm/openai_compatible.py
engine/llm/anthropic_messages.py
```

`engine/cli.py` 负责解析参数和调用 pipeline，不直接写模型分支逻辑。

`engine/formatter/docx_formatter.py` 继续负责确定性格式应用。本轮至少覆盖现有段落整理能力；表格、页眉页脚、脚注等复杂 Word 区域可以进入诊断提示或后续迭代，不作为第二轮必达范围。

## 错误处理

输入文件错误：

- 文件不存在：返回非零退出码和明确错误。
- 扩展名不支持：提示本轮仅支持 Markdown 和 `.docx`。
- 输出路径不是 `.docx`：提示必须输出 `.docx`。

模型错误：

- 缺少 API Key：提示对应 provider 需要 API Key。
- 缺少模型名：提示远程 provider 需要 `--llm-model`。
- 网络或鉴权失败：保留供应商错误摘要，但不输出 API Key。
- JSON 解析失败：提示模型未返回合法 JSON。
- Schema 校验失败：提示模型返回字段不符合 DocForge 可执行格式。

格式错误：

- `.docx` 文件无法打开：提示文件可能损坏或不是有效 `.docx`。
- 本地格式应用失败：返回错误并保留原始输入文件不变。

## 测试策略

Python 测试优先覆盖：

- `format` 命令接受 `.docx` 并输出格式化文档。
- `format` 命令接受 Markdown 并复用 Pandoc 路径。
- `format` 命令拒绝 `.doc` 和未知扩展名。
- `generate` 命令保持向后兼容。
- `local` provider 行为不变。
- `openai-responses` adapter 能用 fake client 验证 schema 参数和返回校验。
- `openai-compatible` adapter 能用 fake client 验证 Chat Completions 请求和 JSON 校验。
- `anthropic-messages` adapter 能用 fake client 验证 Messages 请求和 JSON 校验。
- 模型输出非法 JSON 或多余字段时失败，不进入 formatter。

桌面端测试以构建验证为主：

```bash
cd apps/desktop
npm run build
```

完整 Python 验证：

```bash
.venv/bin/python -m pytest -v
```

Pandoc 相关测试只在 Pandoc 可用时运行。

## 交付切分

建议分三步实现：

1. `.docx` 直接整理 pipeline 和 CLI `format`。
2. LLM adapter 抽象和三个 provider。
3. 桌面端参数与输入类型更新。

这样每一步都可以独立验证，也能在模型适配遇到供应商差异时不影响 `.docx` 直整主线。

## 验收标准

第二轮完成时应满足：

- 用户可以输入 `.docx`，选择 profile 和临时格式指令，导出新的 `.docx`。
- 用户可以继续输入 Markdown，行为与第一轮兼容。
- 用户可以选择 `local`、`openai-responses`、`openai-compatible`、`anthropic-messages`。
- 所有远程 provider 的输出都经过本地类型校验。
- 不支持 `.doc` 时给出明确提示。
- API Key 不进入日志、stdout JSON 或仓库文件。
- Python 测试通过。
- 前端构建通过。
