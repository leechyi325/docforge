import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { open, save } from "@tauri-apps/plugin-dialog";
import { FileText, Wrench } from "lucide-react";
import { useEffect, useState } from "react";
import { LogPanel, type LogEntry } from "./LogPanel";
import { SettingsPage } from "./SettingsPage";
import type { AppSettings, GenerateResponse, Issue, ProfileId, StructureSummary } from "./types";

const profiles: Array<{ id: ProfileId; label: string }> = [
  { id: "default", label: "AI 智能识别" },
  { id: "general", label: "通用格式文档" },
];

const missingTauriRuntimeMessage = "当前页面没有连接到 Tauri 桌面运行时。请使用 `cd apps/desktop && npm run tauri dev` 启动，或打开打包后的 DocForge 应用。";

type TauriWindow = Window &
  typeof globalThis & {
    __TAURI_INTERNALS__?: {
      invoke?: unknown;
    };
  };

function isTauriInvokeAvailable() {
  return typeof (window as TauriWindow).__TAURI_INTERNALS__?.invoke === "function";
}

function getErrorMessage(error: unknown) {
  if (typeof error === "string") {
    if (error.includes("Cannot read properties of undefined") && error.includes("invoke")) {
      return missingTauriRuntimeMessage;
    }

    return error.trim() || "处理失败，请检查输入路径、Python 环境或模型配置。";
  }

  if (error instanceof Error) {
    if (error.message.includes("Cannot read properties of undefined") && error.message.includes("invoke")) {
      return missingTauriRuntimeMessage;
    }

    return error.message;
  }

  return "处理失败，请检查输入路径、Python 环境或模型配置。";
}

function formatStructureSummary(summary: StructureSummary | null) {
  if (!summary) return "";
  const labels: Array<[string, string]> = [
    ["title", "标题"],
    ["date", "日期"],
    ["department", "部门"],
    ["heading_1", "一级标题"],
    ["heading_2", "二级标题"],
    ["heading_3", "三级标题"],
    ["table", "表格"],
    ["unknown", "未识别段落"],
  ];
  const parts = labels
    .map(([key, label]) => [label, summary[key]] as const)
    .filter(([, count]) => typeof count === "number" && count > 0)
    .map(([label, count]) => `${label} ${count} 个`);
  return parts.length > 0 ? `AI 已识别：${parts.join("，")}。` : "";
}

export function App() {
  const [inputPath, setInputPath] = useState("");
  const [outputPath, setOutputPath] = useState("");
  const [profile, setProfile] = useState<ProfileId>("general");
  const [formatInstruction, setFormatInstruction] = useState("");
  const [issues, setIssues] = useState<Issue[]>([]);
  const [structureSummary, setStructureSummary] = useState<StructureSummary | null>(null);
  const [status, setStatus] = useState("等待选择文件");

  const defaultSettings: AppSettings = { llmProvider: "local", llmModel: "", llmBaseUrl: "", apiKey: "" };
  const [settings, setSettings] = useState<AppSettings>(defaultSettings);
  const [showSettings, setShowSettings] = useState(false);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [progress, setProgress] = useState(0);
  const [logExpanded, setLogExpanded] = useState(false);

  useEffect(() => {
    invoke<AppSettings>("load_settings").then(setSettings).catch(() => {});
  }, []);

  useEffect(() => {
    const unlisten = listen<string>("engine-progress", (event) => {
      try {
        const data = JSON.parse(event.payload);
        const entry: LogEntry = {
          timestamp: new Date().toLocaleTimeString(),
          stage: data.stage || "unknown",
          message: data.message || "",
          progress: data.progress,
        };
        setLogs((prev) => [...prev, entry]);
        if (data.progress !== undefined) {
          setProgress(data.progress);
        }
        if (data.stage) {
          setStatus(data.message || data.stage);
        }
      } catch {
        // Non-JSON stderr line, ignore
      }
    });
    return () => {
      unlisten.then((fn) => fn());
    };
  }, []);

  async function handleSelectInput() {
    const selected = await open({
      multiple: false,
      filters: [{ name: "文档文件", extensions: ["md", "markdown", "docx"] }],
    });
    if (selected) {
      setInputPath(selected);
      const suggested = selected.replace(/\.(md|markdown|docx)$/i, ".docx");
      if (!outputPath) {
        setOutputPath(suggested);
      }
    }
  }

  async function handleSelectOutput() {
    const selected = await save({
      filters: [{ name: "Word 文档", extensions: ["docx"] }],
      defaultPath: outputPath || undefined,
    });
    if (selected) {
      setOutputPath(selected);
    }
  }

  async function validateBeforeGenerate(): Promise<boolean> {
    try {
      const inputResult = await invoke<{ valid: boolean; error: string | null }>("validate_path", { path: inputPath, pathType: "input" });
      if (!inputResult.valid) {
        setStatus(`输入路径无效：${inputResult.error}`);
        return false;
      }
      const outputResult = await invoke<{ valid: boolean; error: string | null }>("validate_path", { path: outputPath, pathType: "output" });
      if (!outputResult.valid) {
        setStatus(`输出路径无效：${outputResult.error}`);
        return false;
      }
      return true;
    } catch (error) {
      setStatus(`路径校验失败：${getErrorMessage(error)}`);
      return false;
    }
  }

  async function handleGenerate() {
    if (!(await validateBeforeGenerate())) return;
    setStatus(inputPath.trim().toLowerCase().endsWith(".docx") ? "正在整理 docx 格式" : "正在转换并整理 docx");
    setIssues([]);
    setStructureSummary(null);
    setLogs([]);
    setProgress(0);

    try {
      if (!isTauriInvokeAvailable()) {
        throw new Error(missingTauriRuntimeMessage);
      }

      const result = await invoke<{ stdout: string }>("generate_docx", {
        request: {
          inputPath, outputPath, profile, formatInstruction,
          llmProvider: settings.llmProvider,
          llmModel: settings.llmModel,
          llmBaseUrl: settings.llmBaseUrl,
          apiKey: settings.apiKey,
        },
      });
      const payload = JSON.parse(result.stdout) as GenerateResponse;
      setIssues(payload.issues);
      setStructureSummary(payload.structure_summary ?? null);
      setStatus(`已生成：${payload.output}`);
    } catch (error) {
      setStatus(`处理失败：${getErrorMessage(error)}`);
    }
  }

  return (
    <main className="shell">
      <header className="topbar">
        <div>
          <h1>DocForge</h1>
          <p>Markdown / docx 智能整理，AI 可辅助识别结构，格式落地由本地引擎执行。</p>
        </div>
        <button className="iconButton" title="AI 设置" type="button" onClick={() => setShowSettings(true)}>
          <Wrench size={18} />
        </button>
      </header>

      <section className="workspace">
        <aside className="panel">
          <label>
            输入文件
            <div className="path-input">
              <input value={inputPath} onChange={(event) => setInputPath(event.target.value)} placeholder="/path/to/input.md 或 /path/to/input.docx" />
              <button className="iconButton" type="button" onClick={handleSelectInput} title="浏览文件">
                <FileText size={16} />
              </button>
            </div>
          </label>
          <label>
            输出 docx
            <div className="path-input">
              <input value={outputPath} onChange={(event) => setOutputPath(event.target.value)} placeholder="/path/to/output.docx" />
              <button className="iconButton" type="button" onClick={handleSelectOutput} title="选择保存位置">
                <FileText size={16} />
              </button>
            </div>
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
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${progress * 100}%` }} />
          </div>
          <p>{status}</p>
          {structureSummary && <p className="structure-summary">{formatStructureSummary(structureSummary)}</p>}
          <LogPanel logs={logs} expanded={logExpanded} onToggle={() => setLogExpanded(!logExpanded)} />
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

      {showSettings && (
        <SettingsPage
          settings={settings}
          onClose={() => setShowSettings(false)}
          onSaved={(s) => { setSettings(s); setShowSettings(false); }}
        />
      )}
    </main>
  );
}
