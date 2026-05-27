import { invoke } from "@tauri-apps/api/core";
import { Save, X } from "lucide-react";
import { useState } from "react";
import type { AppSettings, LlmProvider } from "./types";

type Props = {
  settings: AppSettings;
  onClose: () => void;
  onSaved: (settings: AppSettings) => void;
};

export function SettingsPage({ settings, onClose, onSaved }: Props) {
  const [provider, setProvider] = useState<LlmProvider>(settings.llmProvider);
  const [model, setModel] = useState(settings.llmModel);
  const [baseUrl, setBaseUrl] = useState(settings.llmBaseUrl);
  const [apiKey, setApiKey] = useState(settings.apiKey);
  const [status, setStatus] = useState("");

  async function handleSave() {
    try {
      const updated: AppSettings = { llmProvider: provider, llmModel: model, llmBaseUrl: baseUrl, apiKey };
      await invoke("save_settings", { settings: updated });
      onSaved(updated);
      setStatus("已保存");
      setTimeout(() => setStatus(""), 2000);
    } catch (error) {
      setStatus(`保存失败：${error}`);
    }
  }

  return (
    <div className="settings-overlay">
      <div className="settings-panel">
        <div className="settings-header">
          <h2>AI 设置</h2>
          <button className="iconButton" type="button" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        <label>
          解析方式
          <select value={provider} onChange={(e) => setProvider(e.target.value as LlmProvider)}>
            <option value="local">本地规则解析</option>
            <option value="openai-responses">OpenAI Responses API</option>
            <option value="openai-compatible">OpenAI-compatible Chat Completions</option>
            <option value="anthropic-messages">Anthropic Messages API</option>
          </select>
        </label>

        <label>
          模型名称
          <input value={model} onChange={(e) => setModel(e.target.value)} placeholder="gpt-4.1-mini" />
        </label>

        <label>
          Base URL
          <input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} placeholder="https://api.example.com/v1" />
        </label>

        <label>
          API Key
          <input type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)} placeholder="sk-..." />
        </label>

        <div className="settings-footer">
          {status && <span className="settings-status">{status}</span>}
          <button className="primary" type="button" onClick={handleSave}>
            <Save size={16} />
            保存设置
          </button>
        </div>
      </div>
    </div>
  );
}
