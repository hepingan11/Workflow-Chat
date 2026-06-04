"use client";

import { GraduationCap, Plus, RefreshCcw } from "lucide-react";
import { useEffect, useState } from "react";

type AgentSkillRecord = {
  id: string;
  role_key: string;
  source_type: "manual" | "self_trained";
  kind: "workflow" | "prompt" | "tool_usage" | "procedure" | "domain";
  title: string;
  summary: string;
  content: string;
  tags: string[];
  importance: number;
  markdown_path?: string | null;
  updated_at: string;
};

type SkillSearchResult = {
  skills: AgentSkillRecord[];
  markdown_context: string;
};

type AgentSkillPanelProps = {
  roleKey: string;
  roleName: string;
};

const kindLabels: Record<AgentSkillRecord["kind"], string> = {
  workflow: "工作流",
  prompt: "提示词",
  tool_usage: "工具用法",
  procedure: "流程方法",
  domain: "领域技能",
};

export function AgentSkillPanel({ roleKey, roleName }: AgentSkillPanelProps) {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<SkillSearchResult>({ skills: [], markdown_context: "" });
  const [status, setStatus] = useState("等待读取 Skills");
  const [isLoading, setIsLoading] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({
    title: "",
    kind: "procedure" as AgentSkillRecord["kind"],
    summary: "",
    content: "",
    tags: "",
    importance: 3,
  });

  useEffect(() => {
    loadSkills("");
  }, [roleKey]);

  async function loadSkills(nextQuery = query) {
    setIsLoading(true);
    try {
      const response = await fetch(`/api/agents/${roleKey}/skills?q=${encodeURIComponent(nextQuery)}&limit=30`, {
        cache: "no-store",
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail ?? "load skills failed");
      }
      setResult({ skills: data.skills ?? [], markdown_context: data.markdown_context ?? "" });
      setStatus("Skills 已同步");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Skills 读取失败");
    } finally {
      setIsLoading(false);
    }
  }

  async function createSkill() {
    setIsLoading(true);
    try {
      const response = await fetch(`/api/agents/${roleKey}/skills`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          source_type: "manual",
          kind: form.kind,
          title: form.title,
          summary: form.summary,
          content: form.content,
          tags: form.tags
            .split(",")
            .map((tag) => tag.trim())
            .filter(Boolean),
          importance: form.importance,
        }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail ?? "create skill failed");
      }
      setShowCreate(false);
      setForm({ title: "", kind: "procedure", summary: "", content: "", tags: "", importance: 3 });
      await loadSkills();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Skill 新增失败");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <section className="settingsPanel skillPanel" aria-label={`${roleName} Skills 库`}>
      <div className="panelHeader">
        <GraduationCap aria-hidden="true" />
        <div>
          <h2>{roleName} Skills 库</h2>
          <p>{status}</p>
        </div>
        <div className="toolActions">
          <button type="button" onClick={() => setShowCreate((value) => !value)}>
            <Plus aria-hidden="true" />
            人工上传
          </button>
          <button type="button" onClick={() => loadSkills()} disabled={isLoading}>
            <RefreshCcw aria-hidden="true" />
            刷新
          </button>
        </div>
      </div>

      <div className="memorySearchBar">
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="搜索工具用法、流程方法、提示词或领域技能"
        />
        <button type="button" onClick={() => loadSkills()} disabled={isLoading}>
          搜索
        </button>
      </div>

      {showCreate ? (
        <div className="skillCreateForm">
          <input value={form.title} onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))} placeholder="Skill 标题" />
          <select value={form.kind} onChange={(event) => setForm((current) => ({ ...current, kind: event.target.value as AgentSkillRecord["kind"] }))}>
            {Object.entries(kindLabels).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
          <input value={form.summary} onChange={(event) => setForm((current) => ({ ...current, summary: event.target.value }))} placeholder="摘要" />
          <input value={form.tags} onChange={(event) => setForm((current) => ({ ...current, tags: event.target.value }))} placeholder="标签，用英文逗号分隔" />
          <textarea value={form.content} onChange={(event) => setForm((current) => ({ ...current, content: event.target.value }))} placeholder="Skill 内容、步骤、约束或提示词" />
          <button type="button" onClick={createSkill} disabled={isLoading || !form.title || !form.content}>
            保存 Skill
          </button>
        </div>
      ) : null}

      <div className="memoryStats">
        <span>角色：{roleKey}</span>
        <span>Skill 数：{result.skills.length}</span>
        <span>人工上传 / 自我训练：{result.skills.filter((item) => item.source_type === "manual").length} / {result.skills.filter((item) => item.source_type === "self_trained").length}</span>
      </div>

      {result.skills.length ? (
        <div className="skillGrid">
          {result.skills.map((skill) => (
            <details className="memoryCard skillCard" key={skill.id}>
              <summary>
                <span>{skill.title}</span>
                <small>{kindLabels[skill.kind]} · {skill.source_type === "manual" ? "人工上传" : "自我训练"}</small>
              </summary>
              <p>{skill.summary || "暂无摘要"}</p>
              <div className="memoryTags">
                {skill.tags.length ? skill.tags.map((tag) => <span key={tag}>{tag}</span>) : <span>无标签</span>}
              </div>
              <pre>{skill.content}</pre>
              <small>重要度 {skill.importance} · {skill.markdown_path || "未写入 Markdown"}</small>
            </details>
          ))}
        </div>
      ) : (
        <p className="toolEmpty">这个员工暂时还没有 Skills。可以先通过“人工上传”添加，后续再接入自我训练。</p>
      )}

      <details className="memoryMarkdownPreview">
        <summary>查看 Skills Markdown 上下文</summary>
        <pre>{result.markdown_context || "暂无 Skills Markdown。每个角色会写入自己独立的 skills 目录。"}</pre>
      </details>
    </section>
  );
}
