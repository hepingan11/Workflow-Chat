"use client";

import { Brain, RefreshCcw } from "lucide-react";
import { useEffect, useState } from "react";

type AgentMemoryRecord = {
  id: string;
  role_key: string;
  kind: "semantic" | "episodic" | "procedural" | "preference" | "pitfall";
  title: string;
  summary: string;
  content: string;
  source_type: string;
  source_id?: string | null;
  tags: string[];
  importance: number;
  markdown_path?: string | null;
  updated_at: string;
};

type MemorySearchResult = {
  memories: AgentMemoryRecord[];
  markdown_context: string;
};

type AgentMemoryPanelProps = {
  roleKey: string;
  roleName: string;
};

const kindLabels: Record<AgentMemoryRecord["kind"], string> = {
  semantic: "知识",
  episodic: "经验",
  procedural: "流程",
  preference: "偏好",
  pitfall: "避坑",
};

export function AgentMemoryPanel({ roleKey, roleName }: AgentMemoryPanelProps) {
  const [query, setQuery] = useState("");
  const [memory, setMemory] = useState<MemorySearchResult>({ memories: [], markdown_context: "" });
  const [status, setStatus] = useState("等待读取长期记忆");
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    loadMemory("");
  }, [roleKey]);

  async function loadMemory(nextQuery = query) {
    setIsLoading(true);
    try {
      const response = await fetch(`/api/agents/${roleKey}/memories?q=${encodeURIComponent(nextQuery)}&limit=30`, {
        cache: "no-store",
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail ?? "load memories failed");
      }
      setMemory({
        memories: data.memories ?? [],
        markdown_context: data.markdown_context ?? "",
      });
      setStatus("长期记忆已同步");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "长期记忆读取失败");
    } finally {
      setIsLoading(false);
    }
  }

  const grouped = memory.memories.reduce<Record<string, AgentMemoryRecord[]>>((acc, item) => {
    acc[item.kind] = [...(acc[item.kind] ?? []), item];
    return acc;
  }, {});

  return (
    <section className="settingsPanel memoryPanel" aria-label={`${roleName} 长期记忆库`}>
      <div className="panelHeader">
        <Brain aria-hidden="true" />
        <div>
          <h2>{roleName}长期记忆库</h2>
          <p>{status}</p>
        </div>
        <div className="toolActions">
          <button type="button" onClick={() => loadMemory()} disabled={isLoading}>
            <RefreshCcw aria-hidden="true" />
            刷新
          </button>
        </div>
      </div>

      <div className="memorySearchBar">
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              loadMemory();
            }
          }}
          placeholder="搜索经验、偏好、流程或避坑点"
        />
        <button type="button" onClick={() => loadMemory()} disabled={isLoading}>
          搜索
        </button>
      </div>

      <div className="memoryStats">
        <span>角色：{roleKey}</span>
        <span>数据库条目：{memory.memories.length}</span>
        <span>Markdown：{memory.markdown_context ? "已生成" : "暂无"}</span>
      </div>

      {memory.memories.length ? (
        <div className="memoryKindGrid">
          {Object.entries(grouped).map(([kind, items]) => (
            <article className="memoryKindCard" key={kind}>
              <h3>{kindLabels[kind as AgentMemoryRecord["kind"]] ?? kind}</h3>
              <div className="memoryList">
                {items.map((item) => (
                  <details className="memoryCard" key={item.id}>
                    <summary>
                      <span>{item.title}</span>
                      <small>重要度 {item.importance}</small>
                    </summary>
                    <p>{item.summary || "暂无摘要"}</p>
                    <div className="memoryTags">
                      {item.tags.length ? item.tags.map((tag) => <span key={tag}>{tag}</span>) : <span>无标签</span>}
                    </div>
                    <pre>{item.content}</pre>
                    <small>
                      来源：{item.source_type}
                      {item.source_id ? ` / ${item.source_id}` : ""} · {item.markdown_path || "未写入 Markdown"}
                    </small>
                  </details>
                ))}
              </div>
            </article>
          ))}
        </div>
      ) : (
        <p className="toolEmpty">这个员工暂时还没有数据库记忆。任务完成后会自动复盘并写入长期记忆。</p>
      )}

      <details className="memoryMarkdownPreview">
        <summary>查看 Markdown 记忆上下文</summary>
        <pre>{memory.markdown_context || "暂无 Markdown 记忆。每个角色会写入自己独立的 memories 目录。"}</pre>
      </details>
    </section>
  );
}
