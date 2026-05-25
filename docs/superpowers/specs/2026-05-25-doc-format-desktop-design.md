# 文档格式智能整理桌面软件设计

日期：2026-05-25

## 背景

用户日常使用 Markdown 编写初稿，再复制到 Word/WPS 中手工调整公文或其他材料格式。目标是开发一个桌面软件雏形，优先解决 Markdown 到规范 `.docx` 的自动转换、诊断和修复问题。

第一版允许调用外部 OpenAI API，优先追求识别与诊断效果。最终格式落地仍由本地程序确定性执行，避免让模型直接修改 Word 文件导致不可控结果。

## 产品目标

第一版产品是一个跨平台桌面软件雏形，先保证 macOS 开发可跑，后续打包 Windows。它支持用户导入 Markdown，选择文档类型，输入临时格式指令，生成符合规则的 `.docx`，并显示可直接修复的格式问题。

首批文档类型包括：

- 公文
- 会议纪要
- 汇报材料
- 讲话稿
- 通用格式文档

第一版聚焦格式处理，不做内容润色，不做 Word/WPS 插件，不支持 `.doc` 老格式。

## 核心流程

```text
导入 Markdown
  ↓
选择文档类型 profile
  ↓
填写临时格式指令
  ↓
OpenAI API 解析文档结构与临时格式要求
  ↓
Pandoc 生成基础 docx
  ↓
Python 后处理 docx 格式
  ↓
生成格式诊断问题列表
  ↓
用户选择单项修复或全部修复
  ↓
导出最终 docx
```

## 技术栈

桌面端使用 Tauri、React、TypeScript。Tauri 负责桌面壳、文件选择、调用本地命令和后续跨平台打包；React 负责简单工作台界面。

核心引擎使用 Python。Python 负责调用 Pandoc、处理 `.docx`、读取 profile 配置、调用 OpenAI API、生成诊断结果、执行修复动作。

Markdown 到基础 `.docx` 的转换使用 Pandoc。Pandoc 只负责基础结构转换，最终格式由后处理器统一精修。

`.docx` 处理优先使用 `python-docx`。当 `python-docx` 无法覆盖某些格式细节时，允许直接操作 OOXML。

OpenAI 调用使用 Responses API 和 Structured Outputs。模型只负责结构识别、临时格式指令解析和格式诊断，不直接写入文档文件。

## 项目结构

```text
docFormat/
├─ apps/
│  └─ desktop/
│     ├─ src/
│     ├─ src-tauri/
│     └─ package.json
├─ engine/
│  ├─ cli.py
│  ├─ converters/
│  │  └─ pandoc.py
│  ├─ llm/
│  │  ├─ client.py
│  │  ├─ prompts.py
│  │  └─ schemas.py
│  ├─ profiles/
│  │  ├─ official.yaml
│  │  ├─ meeting_minutes.yaml
│  │  ├─ briefing.yaml
│  │  ├─ speech.yaml
│  │  └─ general.yaml
│  ├─ templates/
│  ├─ formatter/
│  │  └─ docx_formatter.py
│  ├─ diagnostics/
│  │  └─ diagnose.py
│  └─ fixer/
│     └─ apply_fixes.py
├─ tests/
└─ docs/
```

## Profile 设计

每类文档使用一个 profile。profile 是 YAML 文件，定义文档结构、默认格式、可诊断问题和可修复动作。

profile 至少包含：

- 文档类型名称
- 必填结构字段
- 标题层级规则
- 默认字体字号
- 段落格式
- 页边距和纸张设置
- 特殊区域规则，如附件、落款、日期、会议要素
- 可自动修复的规则清单
- 对应 Pandoc reference docx 或模板路径

规则生效优先级为：

```text
系统默认规则 < 文档 profile < 用户临时格式指令
```

通用格式文档是轻量 profile，用于只需要控制基础版式的材料。它不要求复杂文档结构，只关注主标题、段落标题、正文字体字号、段落缩进、行距和段前段后。该 profile 适合临时材料、内部说明、一般通知、简单报告等格式要求较少的文件。

## 临时格式指令

用户可以用自然语言输入本次格式要求，例如：

```text
标题用方正小标宋二号居中，正文仿宋三号，行距固定28磅，一级标题黑体三号。
```

OpenAI API 将该指令解析为结构化配置：

```json
{
  "title": {
    "font": "方正小标宋",
    "size": "二号",
    "align": "center"
  },
  "body": {
    "font": "仿宋",
    "size": "三号",
    "line_spacing": "28pt"
  },
  "heading_1": {
    "font": "黑体",
    "size": "三号"
  }
}
```

本地引擎会校验解析结果，只接受已知字段、已知字号、合法单位和可执行格式项。无法确认的要求进入提示列表，不直接执行。

## OpenAI 使用边界

OpenAI API 负责三类任务：

1. 文档结构识别：从 Markdown 中识别标题、正文层级、附件、落款、日期、会议要素等。
2. 临时格式指令解析：把自然语言格式要求转换为结构化覆盖配置。
3. 格式诊断辅助：结合文档结构、profile 和临时格式指令，生成问题列表。

OpenAI API 不负责：

- 直接生成最终 Word 文件
- 直接修改 `.docx`
- 执行任意本地命令
- 擅自改写正文内容

所有模型输出都必须符合 JSON Schema，并经过本地校验后才进入后续流程。

## 诊断与修复模型

格式问题必须同时包含用户可读说明和本地可执行修复动作。

示例：

```json
{
  "id": "issue_001",
  "severity": "warning",
  "message": "正文行距不符合要求",
  "location": {
    "type": "paragraph",
    "index": 12
  },
  "fix_action": {
    "type": "set_paragraph_format",
    "target": {
      "type": "paragraph",
      "index": 12
    },
    "properties": {
      "font": "仿宋",
      "size": "三号",
      "line_spacing": "28pt"
    }
  }
}
```

本地 fixer 只执行白名单动作。第一版白名单包括：

- 设置段落字体、字号、加粗
- 设置段落对齐方式
- 设置行距、首行缩进、段前段后
- 应用标题样式
- 设置页边距和纸张大小
- 修复附件说明基础格式
- 修复落款和日期基础位置

修复动作执行后，系统重新运行诊断，刷新问题列表。

## 桌面端界面雏形

第一版界面保持工作台形态，不做复杂视觉设计。

页面区域包括：

- 顶部：OpenAI API Key 设置、输出目录设置
- 左侧：Markdown 文件选择、文档类型选择、临时格式指令输入
- 中间：转换与诊断状态
- 右侧：诊断问题列表
- 底部：生成 docx、重新诊断、修复选中、全部修复、导出最终文件

第一版不做 Word 级在线预览。用户通过生成 `.docx` 后在 Word 或 WPS 中检查结果。

## CLI 边界

Python 引擎以 CLI 方式暴露能力，桌面端调用 CLI。这能降低 Tauri 与 Python 的耦合，并为后续命令行、服务端或 skill 复用留出空间。

建议命令形态：

```text
python -m engine.cli generate \
  --input input.md \
  --profile official \
  --format-instruction "正文仿宋三号，行距28磅" \
  --output output.docx
```

诊断和修复也使用独立子命令：

```text
python -m engine.cli diagnose --input output.docx --profile official
python -m engine.cli fix --input output.docx --issues issues.json --output fixed.docx
```

## MVP 范围

第一版必须完成：

- Markdown 导入
- 文档类型选择
- 通用格式文档 profile
- 临时格式指令输入
- OpenAI 结构化解析
- Pandoc 基础转换
- `.docx` 后处理
- 诊断问题列表
- 单项修复和全部修复
- 最终 `.docx` 导出

第一版暂不做：

- 现有 `.docx` 原位复杂修复
- `.doc` 老格式支持
- Word/WPS 插件
- 内容润色
- 多人协作
- 模板市场
- 在线预览
- 完整商业化授权系统

## 错误处理

API Key 缺失时，桌面端提示用户配置，不进入模型解析流程。

OpenAI API 调用失败时，保留本地 Pandoc 转换能力，并提示用户诊断功能不可用。

Pandoc 不存在时，提示安装 Pandoc 或后续提供内置运行时。

模型返回 JSON 校验失败时，系统自动重试一次；仍失败则显示错误详情，并不执行任何修复。

修复动作不在白名单内时，标记为“仅建议，不可自动修复”。

## 测试策略

核心引擎优先测试，桌面端做基本集成验证。

测试覆盖：

- 临时格式指令解析 schema 校验
- profile 合并优先级
- Markdown 到 docx 的基础转换
- 字体、字号、行距、缩进、页边距后处理
- 诊断问题结构校验
- fix_action 白名单执行
- 修复后重新诊断

每类 profile 至少准备一个 Markdown 样例作为回归样本。

## 风险与对策

模型输出不稳定是最大风险。对策是使用 Structured Outputs、JSON Schema、本地校验、有限重试和白名单修复动作。

Pandoc 输出格式不满足公文要求。对策是把 Pandoc 定位为基础转换器，最终格式由 Python 后处理器控制。

Windows 打包复杂。对策是第一版先让核心引擎 CLI 化，桌面端只负责调用；后续再处理 Python、Pandoc 和模板资源的打包策略。

文档格式规则差异大。对策是 profile 化，把公文、会议纪要、汇报材料、讲话稿、通用格式文档拆成独立配置，避免把规则写死在代码里。

## 通过标准

第一版完成时，用户应能在 macOS 上启动桌面软件，选择一份 Markdown，选择公文、会议纪要或通用格式文档等 profile，输入临时格式指令，生成 `.docx`，看到格式诊断问题，并能对支持的问题执行单项修复或全部修复。

生成的 `.docx` 应能被 Word/WPS 打开，正文、标题、行距、页边距等基础格式应符合 profile 与临时格式指令的合并结果。
