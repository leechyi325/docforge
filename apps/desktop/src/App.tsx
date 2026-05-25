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
