import { ChevronDown, ChevronUp } from "lucide-react";

export type LogEntry = {
  timestamp: string;
  stage: string;
  message: string;
  progress?: number;
};

type Props = {
  logs: LogEntry[];
  expanded: boolean;
  onToggle: () => void;
};

const stageLabels: Record<string, string> = {
  preparing: "准备",
  converting: "转换",
  formatting: "格式化",
  diagnosing: "诊断",
  done: "完成",
};

export function LogPanel({ logs, expanded, onToggle }: Props) {
  return (
    <div className="log-panel">
      <button className="log-toggle" type="button" onClick={onToggle}>
        <span>处理日志 ({logs.length})</span>
        {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
      </button>
      {expanded && (
        <div className="log-list">
          {logs.map((entry, i) => (
            <div key={i} className="log-entry">
              <span className="log-time">{entry.timestamp}</span>
              <span className={`log-stage log-stage-${entry.stage}`}>
                {stageLabels[entry.stage] || entry.stage}
              </span>
              <span className="log-message">{entry.message}</span>
            </div>
          ))}
          {logs.length === 0 && <p className="log-empty">暂无日志</p>}
        </div>
      )}
    </div>
  );
}
