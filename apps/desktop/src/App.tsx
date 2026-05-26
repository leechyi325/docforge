import { invoke } from "@tauri-apps/api/core";
import { FileText, Wrench } from "lucide-react";
import { useState } from "react";
import type { GenerateResponse, Issue, LlmProvider, ProfileId } from "./types";

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
  const [llmProvider, setLlmProvider] = useState<LlmProvider>("local");
  const [llmModel, setLlmModel] = useState("");
  const [llmBaseUrl, setLlmBaseUrl] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [issues, setIssues] = useState<Issue[]>([]);
  const [status, setStatus] = useState("等待选择文件");

  async function handleGenerate() {
    setStatus(inputPath.trim().toLowerCase().endsWith(".docx") ? "正在整理 docx 格式" : "正在转换并整理 docx");
    const result = await invoke<{ stdout: string }>("generate_docx", {
      request: { inputPath, outputPath, profile, formatInstruction, llmProvider, llmModel, llmBaseUrl, apiKey },
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
            API Key
            <input type="password" value={apiKey} onChange={(event) => setApiKey(event.target.value)} placeholder="OpenAI / Anthropic / 网关 API Key" />
          </label>
          <label>
            解析方式
            <select value={llmProvider} onChange={(event) => setLlmProvider(event.target.value as LlmProvider)}>
              <option value="local">本地规则解析</option>
              <option value="openai-responses">OpenAI Responses API</option>
              <option value="openai-compatible">OpenAI-compatible Chat Completions</option>
              <option value="anthropic-messages">Anthropic Messages API</option>
            </select>
          </label>
          <label>
            模型名称
            <input value={llmModel} onChange={(event) => setLlmModel(event.target.value)} placeholder="gpt-4.1-mini" />
          </label>
          <label>
            Base URL
            <input value={llmBaseUrl} onChange={(event) => setLlmBaseUrl(event.target.value)} placeholder="https://api.example.com/v1" />
          </label>
          <label>
            输入文件
            <input value={inputPath} onChange={(event) => setInputPath(event.target.value)} placeholder="/path/to/input.md 或 /path/to/input.docx" />
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
            整理并导出 docx
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
