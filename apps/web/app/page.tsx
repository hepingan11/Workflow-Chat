"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { ArrowRight, FileText, Save, Settings, ShieldCheck, Wrench } from "lucide-react";

import { employees } from "./employees";

type ParsedPlaybook = {
  role_key: string;
  name: string;
  trigger: {
    type: "daily";
    time: string;
    timezone: string;
  };
  collaboration: {
    mode: "single_role" | "multi_role";
    owner_role_key: string;
    participant_role_keys: string[];
    handoff_strategy: "manual" | "auto";
    shared_context_keys: string[];
  };
  steps: Array<{
    id: string;
    name: string;
    type: "tool" | "human_approval" | "handoff" | "noop";
    role_key?: string | null;
    assignee_role_key?: string | null;
    participant_role_keys?: string[];
    depends_on_step_ids?: string[];
    handoff_to_role_key?: string | null;
    next_step_ids?: string[];
    on_approved_step_ids?: string[];
    on_rejected_step_ids?: string[];
    context_reads?: string[];
    context_writes?: string[];
    config: Record<string, unknown>;
  }>;
  referenced_tools: string[];
  unresolved_tools: string[];
};

type ToolSuggestion = {
  id: string;
  name: string;
  description?: string;
  source?: "builtin" | "dify";
  executable?: boolean;
};

type PublicToolRecord = {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
};

type SuggestionMode = "employee" | "tool";

const exampleCommands = [
  "@operator 每天早上8点使用#{Ai最新新闻获取}整理AI热点，生成短视频文案并发给我审批。",
  "@product_manager 每周一梳理需求优先级，交给@programmer 输出本周开发计划。",
  "@customer_support 每天18点汇总用户高频问题，交给@product_manager 生成产品改进建议。",
];

function detectMentionQuery(value: string, caretIndex: number) {
  const textBeforeCaret = value.slice(0, caretIndex);
  const match = textBeforeCaret.match(/(?:^|\s)@([^\s@]*)$/);
  if (!match || match.index === undefined) {
    return null;
  }

  const query = match[1] ?? "";
  const mentionStart = match.index + match[0].lastIndexOf("@");
  return { query, mentionStart, mentionEnd: caretIndex };
}

function detectToolQuery(value: string, caretIndex: number) {
  const textBeforeCaret = value.slice(0, caretIndex);
  const openIndex = textBeforeCaret.lastIndexOf("#{");
  if (openIndex >= 0) {
    const query = textBeforeCaret.slice(openIndex + 2);
    if (!query.includes("}")) {
      return { query, toolStart: openIndex, toolEnd: caretIndex, explicit: true };
    }
  }

  const hashIndex = textBeforeCaret.lastIndexOf("#");
  if (hashIndex < 0) {
    return null;
  }
  const tail = textBeforeCaret.slice(hashIndex + 1);
  if (tail.includes(" ") || tail.includes("@") || tail.includes("{") || tail.includes("}")) {
    return null;
  }
  return { query: tail, toolStart: hashIndex, toolEnd: caretIndex, explicit: false };
}

export default function Home() {
  const [command, setCommand] = useState("");
  const [status, setStatus] = useState("Control layer first");
  const [selectedRoleKey, setSelectedRoleKey] = useState("");
  const [mentionRange, setMentionRange] = useState<{ mentionStart: number; mentionEnd: number } | null>(null);
  const [toolRange, setToolRange] = useState<{ toolStart: number; toolEnd: number } | null>(null);
  const [suggestionMode, setSuggestionMode] = useState<SuggestionMode | null>(null);
  const [activeSuggestionIndex, setActiveSuggestionIndex] = useState(0);
  const [parsedPlaybook, setParsedPlaybook] = useState<ParsedPlaybook | null>(null);
  const [showPreview, setShowPreview] = useState(false);
  const [isBusy, setIsBusy] = useState(false);
  const [exampleIndex, setExampleIndex] = useState(0);
  const [typedExample, setTypedExample] = useState("");
  const [allTools, setAllTools] = useState<ToolSuggestion[]>([]);
  const [roleTools, setRoleTools] = useState<ToolSuggestion[]>([]);

  const filteredEmployees = useMemo(() => {
    if (!mentionRange || suggestionMode !== "employee") {
      return [];
    }
    const query = detectMentionQuery(command, mentionRange.mentionEnd)?.query.toLowerCase() ?? "";
    return employees.filter((employee) => {
      return employee.name.toLowerCase().includes(query) || employee.key.toLowerCase().includes(query);
    });
  }, [command, mentionRange, suggestionMode]);

  const filteredTools = useMemo(() => {
    if (!toolRange || suggestionMode !== "tool") {
      return [];
    }
    const query = detectToolQuery(command, toolRange.toolEnd)?.query.toLowerCase() ?? "";
    const candidateTools = selectedRoleKey ? roleTools : allTools;
    return candidateTools.filter((tool) => tool.name.toLowerCase().includes(query));
  }, [allTools, command, roleTools, selectedRoleKey, suggestionMode, toolRange]);

  useEffect(() => {
    const currentExample = exampleCommands[exampleIndex];
    let frame = 0;
    setTypedExample("");

    const typingTimer = window.setInterval(() => {
      frame += 1;
      setTypedExample(currentExample.slice(0, frame));
      if (frame >= currentExample.length) {
        window.clearInterval(typingTimer);
        window.setTimeout(() => {
          setExampleIndex((current) => (current + 1) % exampleCommands.length);
        }, 1800);
      }
    }, 42);

    return () => window.clearInterval(typingTimer);
  }, [exampleIndex]);

  useEffect(() => {
    fetch("/api/tools")
      .then((response) => response.json())
      .then((data) => {
        const nextTools = (data.tools ?? [])
          .filter((tool: PublicToolRecord) => tool.enabled)
          .map((tool: PublicToolRecord) => ({
            id: tool.id,
            name: tool.name,
            description: tool.description,
          }));
        setAllTools(nextTools);
      })
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!selectedRoleKey) {
      setRoleTools([]);
      return;
    }

    fetch(`/api/agents/${selectedRoleKey}/tools`)
      .then((response) => response.json())
      .then((data) => {
        const nextTools = (data.tools ?? []).filter((tool: ToolSuggestion) => tool.source === "dify");
        setRoleTools(nextTools);
      })
      .catch(() => setRoleTools([]));
  }, [selectedRoleKey]);

  function updateComposerState(value: string, caretIndex: number) {
    const mention = detectMentionQuery(value, caretIndex);
    const tool = detectToolQuery(value, caretIndex);

    setMentionRange(mention ? { mentionStart: mention.mentionStart, mentionEnd: mention.mentionEnd } : null);
    setToolRange(tool ? { toolStart: tool.toolStart, toolEnd: tool.toolEnd } : null);

    if (mention) {
      setSuggestionMode("employee");
      setActiveSuggestionIndex(0);
      return;
    }
    if (tool) {
      setSuggestionMode("tool");
      setActiveSuggestionIndex(0);
      return;
    }
    setSuggestionMode(null);
  }

  function applyEmployeeMention(employeeKey: string) {
    if (!mentionRange) {
      return;
    }
    const nextValue = `${command.slice(0, mentionRange.mentionStart)}@${employeeKey} ${command.slice(mentionRange.mentionEnd)}`;
    setCommand(nextValue);
    setSelectedRoleKey(employeeKey);
    setMentionRange(null);
    setSuggestionMode(null);
    setActiveSuggestionIndex(0);
  }

  function applyToolMention(toolName: string) {
    if (!toolRange) {
      return;
    }
    const nextValue = `${command.slice(0, toolRange.toolStart)}#{${toolName}} ${command.slice(toolRange.toolEnd)}`;
    setCommand(nextValue);
    setToolRange(null);
    setSuggestionMode(null);
    setActiveSuggestionIndex(0);
  }

  async function parseCommand() {
    if (!selectedRoleKey) {
      setStatus("请先通过 @ 选择一个员工角色");
      return;
    }

    setIsBusy(true);
    try {
      const response = await fetch("/api/playbooks/parse", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          role_key: selectedRoleKey,
          name: `${selectedRoleKey}-task`,
          natural_language: command,
        }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail ?? "parse failed");
      }
      setParsedPlaybook(data);
      setShowPreview(true);
      setStatus(`已解析给 ${selectedRoleKey} 的任务`);
    } catch (error) {
      setParsedPlaybook(null);
      setShowPreview(false);
      setStatus(error instanceof Error ? error.message : "解析失败");
    } finally {
      setIsBusy(false);
    }
  }

  async function savePlaybook() {
    if (!selectedRoleKey) {
      setStatus("请先通过 @ 选择一个员工角色");
      return;
    }

    setIsBusy(true);
    try {
      const response = await fetch("/api/playbooks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          role_key: selectedRoleKey,
          name: `${selectedRoleKey}-task`,
          natural_language: command,
        }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail ?? "save failed");
      }
      setStatus(`已保存 ${selectedRoleKey} 的任务剧本`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "保存失败");
    } finally {
      setIsBusy(false);
    }
  }

  const activeItems = suggestionMode === "employee" ? filteredEmployees : filteredTools;

  return (
    <main className="shell">
      <section className="masthead">
        <div>
          <p className="eyebrow">Digital Employee OS</p>
          <h1>Guiwuli数字员工</h1>
          <p className="lede">
            励志淘汰每一个职业, 让每一个人都能成为数字员工的老板;
            <br />
            Github: https://github.com/hepingan11/Guiwuli-Digital-Employee
          </p>
        </div>
        <div className="statusPanel">
          <ShieldCheck aria-hidden="true" />
          <span>{status}</span>
        </div>
      </section>

      <section className="homeComposerShell">
        <div className="homeComposerHeader">
          <p className="eyebrow">Natural Language Orchestration</p>
          <h2>一句话安排数字员工协作</h2>
          <p className="homeComposerHint">
            输入 `@` 选择员工，输入 `#` 或 `#{}` 选择工具。支持上下键与回车快速选择。
          </p>
        </div>

        <section className="commandCanvas">
          <div className="commandCanvasGlow" aria-hidden="true" />
          <div className="commandCanvasTop">
            <div className="commandExamples">
              <span className="commandExamplesLabel">示例</span>
              <div className="typewriterLine">
                <span>{typedExample}</span>
                <i className="typewriterCursor" aria-hidden="true" />
              </div>
            </div>
            <div className="toolActions">
              <button type="button" onClick={parseCommand} disabled={isBusy}>
                <FileText aria-hidden="true" />
                解析
              </button>
              <button type="button" onClick={savePlaybook} disabled={isBusy}>
                <Save aria-hidden="true" />
                保存剧本
              </button>
            </div>
          </div>

          <div className="mentionComposer commandComposer">
            <textarea
              value={command}
              onChange={(event) => {
                setCommand(event.target.value);
                updateComposerState(event.target.value, event.target.selectionStart ?? event.target.value.length);
              }}
              onClick={(event) => {
                const target = event.target as HTMLTextAreaElement;
                updateComposerState(target.value, target.selectionStart ?? target.value.length);
              }}
              onKeyDown={(event) => {
                if (!suggestionMode || !activeItems.length) {
                  return;
                }
                if (event.key === "ArrowDown") {
                  event.preventDefault();
                  setActiveSuggestionIndex((current) => (current + 1) % activeItems.length);
                }
                if (event.key === "ArrowUp") {
                  event.preventDefault();
                  setActiveSuggestionIndex((current) => (current - 1 + activeItems.length) % activeItems.length);
                }
                if (event.key === "Enter") {
                  event.preventDefault();
                  if (suggestionMode === "employee") {
                    applyEmployeeMention((activeItems[activeSuggestionIndex] as (typeof employees)[number]).key);
                  } else {
                    applyToolMention((activeItems[activeSuggestionIndex] as ToolSuggestion).name);
                  }
                }
                if (event.key === "Escape") {
                  setSuggestionMode(null);
                  setMentionRange(null);
                  setToolRange(null);
                }
              }}
              placeholder="输入你的任务，例如：@operator 每天早上8点使用#选择工具并发给我确认..."
            />

            {suggestionMode && activeItems.length ? (
              <div className="mentionMenu" role="listbox" aria-label={suggestionMode === "employee" ? "员工选择" : "工具选择"}>
                {suggestionMode === "employee"
                  ? filteredEmployees.map((employee, index) => (
                      <button
                        key={employee.key}
                        type="button"
                        className={`mentionOption${index === activeSuggestionIndex ? " is-active" : ""}`}
                        onMouseDown={(event) => {
                          event.preventDefault();
                          applyEmployeeMention(employee.key);
                        }}
                      >
                        <strong>@{employee.key}</strong>
                        <span>{employee.name}</span>
                      </button>
                    ))
                  : filteredTools.map((tool, index) => (
                      <button
                        key={tool.id}
                        type="button"
                        className={`mentionOption${index === activeSuggestionIndex ? " is-active" : ""}`}
                        onMouseDown={(event) => {
                          event.preventDefault();
                          applyToolMention(tool.name);
                        }}
                      >
                        <strong>#{tool.name}</strong>
                        <span>{tool.description || "已注册工具"}</span>
                      </button>
                    ))}
              </div>
            ) : null}
          </div>
        </section>

        {showPreview && parsedPlaybook ? (
          <div className="resultPanel homePreviewPanel">
            <h2>解析预览</h2>
            <pre>{JSON.stringify(parsedPlaybook, null, 2)}</pre>
          </div>
        ) : null}
      </section>

      <section className="quickActions" aria-label="服务配置">
        <Link className="serviceConfigButton" href="/settings/services">
          <Settings aria-hidden="true" />
          服务配置
          <ArrowRight aria-hidden="true" />
        </Link>
        <Link className="serviceConfigButton" href="/settings/tools">
          <Wrench aria-hidden="true" />
          工具管理
          <ArrowRight aria-hidden="true" />
        </Link>
      </section>

      <section className="employeeGrid" aria-label="数字员工角色">
        {employees.map((employee) => {
          const Icon = employee.icon;
          return (
            <Link className="employeeCard" href={employee.route} key={employee.key}>
              <div className="cardTop">
                <Icon aria-hidden="true" />
                <span data-status={employee.status}>{employee.status}</span>
              </div>
              <h2>{employee.name}</h2>
              <p>{employee.work}</p>
              <div className="cardAction">
                <code>{employee.key}</code>
                <ArrowRight aria-hidden="true" />
              </div>
            </Link>
          );
        })}
      </section>
    </main>
  );
}
