"use client";

import { GraduationCap, Pencil, Plus, RefreshCcw, Trash2, X } from "lucide-react";
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
  metadata: Record<string, unknown>;
  updated_at: string;
};

type SkillPackageFile = {
  path: string;
  content: string;
  size: number;
};

type SkillSearchResult = {
  skills: AgentSkillRecord[];
  markdown_context: string;
};

type AgentSkillPanelProps = {
  roleKey: string;
  roleName: string;
  compactLimit?: number;
};

type SkillFormState = {
  title: string;
  kind: AgentSkillRecord["kind"];
  summary: string;
  content: string;
  tags: string;
  importance: number;
  packageFiles: SkillPackageFile[];
};

const emptyForm: SkillFormState = {
  title: "",
  kind: "procedure",
  summary: "",
  content: "",
  tags: "",
  importance: 3,
  packageFiles: [],
};

const kindLabels: Record<AgentSkillRecord["kind"], string> = {
  workflow: "工作流",
  prompt: "提示词",
  tool_usage: "工具用法",
  procedure: "流程方法",
  domain: "领域技能",
};

const textFileExtensions = new Set([
  "txt",
  "md",
  "markdown",
  "json",
  "yaml",
  "yml",
  "csv",
  "tsv",
  "xml",
  "html",
  "css",
  "js",
  "ts",
  "tsx",
  "jsx",
  "py",
  "sql",
  "sh",
  "ps1",
  "license",
]);

export function AgentSkillPanel({ compactLimit, roleKey, roleName }: AgentSkillPanelProps) {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<SkillSearchResult>({ skills: [], markdown_context: "" });
  const [status, setStatus] = useState("等待读取 Skills");
  const [isLoading, setIsLoading] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [editingSkillId, setEditingSkillId] = useState<string | null>(null);
  const [deletingSkillId, setDeletingSkillId] = useState<string | null>(null);
  const [form, setForm] = useState<SkillFormState>(emptyForm);
  const [showAllSkills, setShowAllSkills] = useState(false);

  useEffect(() => {
    void loadSkills("");
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

  function openCreateForm() {
    setEditingSkillId(null);
    setForm(emptyForm);
    setShowForm(true);
    setStatus("正在新增人工 Skill");
  }

  function openEditForm(skill: AgentSkillRecord) {
    setEditingSkillId(skill.id);
    setForm({
      title: skill.title,
      kind: skill.kind,
      summary: skill.summary,
      content: skill.content,
      tags: skill.tags.join(", "),
      importance: skill.importance,
      packageFiles: [],
    });
    setShowForm(true);
    setStatus(`正在编辑：${skill.title}`);
  }

  function closeForm() {
    setEditingSkillId(null);
    setForm(emptyForm);
    setShowForm(false);
    setStatus("Skills 已就绪");
  }

  function buildPayload() {
    return {
      source_type: "manual",
      kind: form.kind,
      title: form.title.trim(),
      summary: form.summary.trim(),
      content: form.content.trim(),
      tags: form.tags
        .split(",")
        .map((tag) => tag.trim())
        .filter(Boolean),
      importance: Number(form.importance) || 3,
      package_files: form.packageFiles,
    };
  }

  async function saveSkill() {
    setIsLoading(true);
    try {
      const payload = buildPayload();
      const url = editingSkillId ? `/api/agents/${roleKey}/skills/${editingSkillId}` : `/api/agents/${roleKey}/skills`;
      const response = await fetch(url, {
        method: editingSkillId ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail ?? "save skill failed");
      }
      setStatus(editingSkillId ? "Skill 已更新" : "Skill 已新增");
      closeForm();
      await loadSkills();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Skill 保存失败");
    } finally {
      setIsLoading(false);
    }
  }

  async function deleteSkill(skill: AgentSkillRecord) {
    const confirmed = window.confirm(`确认删除 Skill「${skill.title}」吗？删除后会从该员工的 Skills Markdown 上下文中移除。`);
    if (!confirmed) {
      return;
    }
    setDeletingSkillId(skill.id);
    try {
      const response = await fetch(`/api/agents/${roleKey}/skills/${skill.id}`, {
        method: "DELETE",
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail ?? "delete skill failed");
      }
      if (editingSkillId === skill.id) {
        closeForm();
      }
      setStatus(`已删除 Skill：${skill.title}`);
      await loadSkills();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Skill 删除失败");
    } finally {
      setDeletingSkillId(null);
    }
  }

  async function importSkillFiles(fileList: FileList | null) {
    if (!fileList?.length) {
      return;
    }
    const files = Array.from(fileList).filter(isReadableTextFile);
    if (!files.length) {
      setStatus("没有识别到可读取的文本文件。");
      return;
    }
    try {
      const rawPackageFiles = await Promise.all(
        files.map(async (file) => ({
          path: getRelativeFilePath(file),
          content: await file.text(),
          size: file.size,
        })),
      );
      const rootName = getRootFolderName(files[0]);
      const packageFiles = normalizePackageFiles(rawPackageFiles, rootName);
      const entryFile = chooseEntryFile(packageFiles);
      const extensionTags = Array.from(new Set(packageFiles.map((file) => file.path.split(".").pop()?.toLowerCase()).filter(Boolean)));
      setForm((current) => ({
        ...current,
        title: current.title || rootName || entryFile?.path.replace(/\.[^.]+$/, "") || "未命名 Skill",
        summary: current.summary || `从 ${rootName || files[0].name} 上传的目录型 Skill 包。`,
        content: current.content || entryFile?.content || packageFiles.map((file) => `# ${file.path}\n\n${file.content}`).join("\n\n---\n\n"),
        tags: Array.from(new Set([...splitTags(current.tags), "skill_package", ...extensionTags])).join(", "),
        packageFiles,
      }));
      setStatus(`已读取 ${packageFiles.length} 个 Skill 包文件`);
    } catch {
      setStatus("文件读取失败，请确认目录内文件是文本格式。");
    }
  }

  const packageFilePaths = form.packageFiles.map((file) => file.path);
  const visibleSkills = compactLimit && result.skills.length > compactLimit ? result.skills.slice(0, compactLimit) : result.skills;

  return (
    <section className="settingsPanel skillPanel" aria-label={`${roleName} Skills 库`}>
      <div className="panelHeader">
        <GraduationCap aria-hidden="true" />
        <div>
          <h2>{roleName} Skills 库</h2>
          <p>{status}</p>
        </div>
        <div className="toolActions">
          <button type="button" onClick={showForm ? closeForm : openCreateForm}>
            {showForm ? <X aria-hidden="true" /> : <Plus aria-hidden="true" />}
            {showForm ? "收起表单" : "人工上传"}
          </button>
          <button type="button" onClick={() => loadSkills()} disabled={isLoading}>
            <RefreshCcw aria-hidden="true" />
            刷新
          </button>
          {compactLimit && result.skills.length > compactLimit ? (
            <button type="button" onClick={() => setShowAllSkills(true)}>
              查看更多
            </button>
          ) : null}
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

      {showForm ? (
        <div className="skillCreateForm">
          <div className="skillFormHeader">
            <strong>{editingSkillId ? "编辑 Skill" : "新增 Skill"}</strong>
            <span>{editingSkillId ? "重新上传目录会替换原 Skill 包文件" : "支持单文件，也支持包含 scripts 的目录型 Skill 包"}</span>
          </div>
          <label className="skillFileUpload">
            <span>上传 Skill 文件或文件夹</span>
            <div className="skillUploadChoices">
              <label>
                选择单个/多个文件
                <input
                  accept=".txt,.md,.markdown,.json,.yaml,.yml,.csv,.tsv,.xml,.html,.css,.js,.ts,.tsx,.jsx,.py,.sql,.sh,.ps1"
                  multiple
                  onChange={(event) => {
                    void importSkillFiles(event.target.files);
                    event.currentTarget.value = "";
                  }}
                  type="file"
                />
              </label>
              <label>
                选择整个文件夹作为 Skill 包
                <input
                  multiple
                  onChange={(event) => {
                    void importSkillFiles(event.target.files);
                    event.currentTarget.value = "";
                  }}
                  type="file"
                  // @ts-expect-error webkitdirectory is supported by Chromium-based browsers.
                  webkitdirectory="true"
                />
              </label>
            </div>
            <small>文件夹会被保存为一个 Skill 包：优先读取 SKILL.md 作为入口，scripts/*.py 等脚本会保留在包目录里。</small>
          </label>
          {packageFilePaths.length ? (
            <div className="skillPackagePreview">
              <strong>已读取文件</strong>
              <div>
                {packageFilePaths.slice(0, 12).map((path) => (
                  <span key={path}>{path}</span>
                ))}
                {packageFilePaths.length > 12 ? <span>+{packageFilePaths.length - 12} 个文件</span> : null}
              </div>
            </div>
          ) : null}
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
          <input
            min={1}
            max={5}
            type="number"
            value={form.importance}
            onChange={(event) => setForm((current) => ({ ...current, importance: Number(event.target.value) }))}
            placeholder="重要度 1-5"
          />
          <textarea value={form.content} onChange={(event) => setForm((current) => ({ ...current, content: event.target.value }))} placeholder="Skill 内容、步骤、约束或提示词" />
          <div className="skillFormActions">
            <button type="button" onClick={saveSkill} disabled={isLoading || !form.title.trim() || !form.content.trim()}>
              {editingSkillId ? "保存修改" : "保存 Skill"}
            </button>
            <button type="button" onClick={closeForm} disabled={isLoading}>
              取消
            </button>
          </div>
        </div>
      ) : null}

      <div className="memoryStats">
        <span>角色：{roleKey}</span>
        <span>Skill 数：{result.skills.length}</span>
        <span>
          人工上传 / 自我训练：{result.skills.filter((item) => item.source_type === "manual").length} /{" "}
          {result.skills.filter((item) => item.source_type === "self_trained").length}
        </span>
      </div>

      {result.skills.length ? (
        <div className="skillGrid">
          {visibleSkills.map((skill) => (
            <details className="memoryCard skillCard" key={skill.id}>
              <summary>
                <span>{skill.title}</span>
                <small>
                  {kindLabels[skill.kind]} · {skill.source_type === "manual" ? "人工上传" : "自我训练"}
                </small>
              </summary>
              <div className="skillCardActions">
                <button type="button" onClick={() => openEditForm(skill)}>
                  <Pencil aria-hidden="true" />
                  编辑
                </button>
                <button type="button" onClick={() => deleteSkill(skill)} disabled={deletingSkillId === skill.id}>
                  <Trash2 aria-hidden="true" />
                  {deletingSkillId === skill.id ? "删除中" : "删除"}
                </button>
              </div>
              <p>{skill.summary || "暂无摘要"}</p>
              <div className="memoryTags">
                {skill.tags.length ? skill.tags.map((tag) => <span key={tag}>{tag}</span>) : <span>无标签</span>}
              </div>
              {Array.isArray(skill.metadata?.package_file_paths) ? (
                <div className="skillPackagePreview">
                  <strong>Skill 包</strong>
                  <div>
                    {(skill.metadata.package_file_paths as string[]).slice(0, 8).map((path) => (
                      <span key={path}>{path}</span>
                    ))}
                  </div>
                </div>
              ) : null}
              <pre>{skill.content}</pre>
              <small>
                重要度 {skill.importance} · {skill.markdown_path || "未写入 Markdown"}
              </small>
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

      {showAllSkills ? (
        <div className="modalBackdrop" role="presentation" onMouseDown={() => setShowAllSkills(false)}>
          <section className="modalPanel employeeModalPanel" role="dialog" aria-modal="true" aria-label="全部 Skills" onMouseDown={(event) => event.stopPropagation()}>
            <div className="panelHeader">
              <GraduationCap aria-hidden="true" />
              <h2>{roleName}全部 Skills</h2>
              <button type="button" onClick={() => setShowAllSkills(false)}>
                <X aria-hidden="true" />
                关闭
              </button>
            </div>
            <div className="skillGrid">
              {result.skills.map((skill) => (
                <details className="memoryCard skillCard" key={skill.id}>
                  <summary>
                    <span>{skill.title}</span>
                    <small>
                      {kindLabels[skill.kind]} · {skill.source_type === "manual" ? "人工上传" : "自我训练"}
                    </small>
                  </summary>
                  <p>{skill.summary || "暂无摘要"}</p>
                  <pre>{skill.content}</pre>
                </details>
              ))}
            </div>
          </section>
        </div>
      ) : null}
    </section>
  );
}

function splitTags(value: string) {
  return value
    .split(",")
    .map((tag) => tag.trim())
    .filter(Boolean);
}

function getRelativeFilePath(file: File) {
  const withDirectory = file as File & { webkitRelativePath?: string };
  return withDirectory.webkitRelativePath || file.name;
}

function getRootFolderName(file: File) {
  const relativePath = getRelativeFilePath(file);
  return relativePath.includes("/") ? relativePath.split("/")[0] : file.name.replace(/\.[^.]+$/, "");
}

function isReadableTextFile(file: File) {
  const path = getRelativeFilePath(file).toLowerCase();
  const name = path.split("/").pop() || "";
  const extension = name.includes(".") ? name.split(".").pop() || "" : name;
  return textFileExtensions.has(extension) || file.type.startsWith("text/");
}

function chooseEntryFile(files: SkillPackageFile[]) {
  const lowerMap = new Map(files.map((file) => [file.path.toLowerCase(), file]));
  return (
    lowerMap.get("skill.md") ??
    Array.from(lowerMap.entries()).find(([path]) => path.endsWith("/skill.md"))?.[1] ??
    lowerMap.get("readme.md") ??
    Array.from(lowerMap.entries()).find(([path]) => path.endsWith("/readme.md"))?.[1] ??
    files.find((file) => file.path.toLowerCase().endsWith(".md")) ??
    files[0]
  );
}

function normalizePackageFiles(files: SkillPackageFile[], rootName: string) {
  if (!rootName) {
    return files;
  }
  const prefix = `${rootName}/`;
  const hasFolderPrefix = files.some((file) => file.path.startsWith(prefix));
  if (!hasFolderPrefix) {
    return files;
  }
  return files.map((file) => ({
    ...file,
    path: file.path.startsWith(prefix) ? file.path.slice(prefix.length) : file.path,
  }));
}
