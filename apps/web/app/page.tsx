"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { ArrowRight, CheckCircle2, Clock3, FileText, GitBranch, Radar, MessageSquare, Save, Settings, ShieldCheck, Wrench } from "lucide-react";
import gsap from "gsap";
import { useGSAP } from "@gsap/react";

import { employees } from "./employees";

gsap.registerPlugin(useGSAP);

type ParsedPlaybook = {
  role_key: string;
  name: string;
  trigger: {
    type: "immediate" | "scheduled" | "daily" | "recurring";
    time: string;
    timezone: string;
    cron?: string | null;
    run_at?: string | null;
    description?: string | null;
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
    type: "tool" | "human_approval" | "message_push" | "handoff" | "noop";
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
  source?: "builtin" | "dify" | "codex" | "llm_chat_response" | "codex_cli" | "mcp";
  executable?: boolean;
};

type PublicToolRecord = {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
};

type AgentSkillRecord = {
  id: string;
  role_key: string;
  source_type: "manual" | "self_trained";
  kind: "workflow" | "prompt" | "tool_usage" | "procedure" | "domain";
  title: string;
  summary: string;
  tags: string[];
  importance: number;
};

type SuggestionMode = "employee" | "tool";

const exampleCommands = [
  "@operator 每天早上8点使用#{Ai最新新闻获取}整理AI热点，生成短视频文案并发给我审批。",
  "@product_manager 每周一梳理需求优先级，交给@programmer 输出本周开发计划。",
  "@customer_support 每天18点汇总用户高频问题，交给@product_manager 生成产品改进建议。",
];

function detectMentionQuery(value: string, caretIndex: number) {
  const textBeforeCaret = value.slice(0, caretIndex);
  const mentionStart = textBeforeCaret.lastIndexOf("@");
  if (mentionStart < 0) {
    return null;
  }

  const query = textBeforeCaret.slice(mentionStart + 1);
  if (query.includes(" ") || query.includes("@")) {
    return null;
  }

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

function getRoleName(roleKey?: string | null) {
  if (!roleKey) {
    return "未指定";
  }
  return employees.find((employee) => employee.key === roleKey)?.name ?? roleKey;
}

function getStepToolName(step: ParsedPlaybook["steps"][number]) {
  return typeof step.config.tool_name === "string" && step.config.tool_name ? step.config.tool_name : "无工具";
}

function getStepRunTime(step: ParsedPlaybook["steps"][number], playbook: ParsedPlaybook) {
  if (typeof step.config.run_at === "string" && step.config.run_at) {
    return `${step.config.run_at} 执行`;
  }
  if (step.type === "tool" && !step.depends_on_step_ids?.length) {
    return formatTriggerSummary(playbook);
  }
  if (step.depends_on_step_ids?.length) {
    return "上一步完成后执行";
  }
  return formatTriggerSummary(playbook);
}

function formatTriggerSummary(playbook: ParsedPlaybook) {
  if (playbook.trigger.run_at) {
    return `${playbook.trigger.run_at} 执行`;
  }
  if (playbook.trigger.cron) {
    return `${playbook.trigger.time} 执行 · cron: ${playbook.trigger.cron}`;
  }
  return `${playbook.trigger.time} 触发`;
}

function getStepPrompt(step: ParsedPlaybook["steps"][number]) {
  if (typeof step.config.message_template === "string" && step.config.message_template) {
    return step.config.message_template;
  }
  const inputTemplate = step.config.input_template;
  if (inputTemplate && typeof inputTemplate === "object" && Object.keys(inputTemplate).length) {
    return JSON.stringify(inputTemplate, null, 2);
  }
  if (step.type === "tool") {
    return step.config.needs_previous_output ? "使用上一步输出作为本次工具输入。" : "使用当前任务上下文作为工具输入。";
  }
  if (step.type === "handoff") {
    return typeof step.config.message_template === "string" ? step.config.message_template : "把当前上下文交接给下一个角色。";
  }
  if (step.type === "message_push") {
    return "读取上一步输出，并推送到已配置的通知渠道。";
  }
  return "无额外提示词。";
}

function getStepNextAction(step: ParsedPlaybook["steps"][number], playbook: ParsedPlaybook) {
  if (step.type === "human_approval") {
    const approved = step.on_approved_step_ids?.[0];
    const rejected = step.on_rejected_step_ids?.[0];
    return {
      label: "发送给我确认",
      detail: approved
        ? `确认没问题后进入 ${getStepName(playbook, approved)}${rejected ? `；拒绝后进入 ${getStepName(playbook, rejected)}` : "；拒绝后停止"}`
        : "确认节点用于人工检查；当前没有后续节点，确认后流程完成。",
    };
  }
  if (step.type === "handoff") {
    return {
      label: `交给 ${getRoleName(step.handoff_to_role_key)}`,
      detail: step.next_step_ids?.length ? `随后进入 ${step.next_step_ids.map((id) => getStepName(playbook, id)).join("、")}` : "交接后流程完成。",
    };
  }
  if (step.type === "message_push") {
    return {
      label: "推送给我",
      detail: step.next_step_ids?.length ? `推送完成后进入 ${step.next_step_ids.map((id) => getStepName(playbook, id)).join("、")}` : "推送完成后流程结束。",
    };
  }
  if (step.next_step_ids?.length) {
    return {
      label: "发送给下一个节点",
      detail: step.next_step_ids.map((id) => getStepName(playbook, id)).join("、"),
    };
  }
  return {
    label: "直接完成",
    detail: "该节点结束后没有后续动作。",
  };
}

function getStepName(playbook: ParsedPlaybook, stepId: string) {
  return playbook.steps.find((step) => step.id === stepId)?.name ?? stepId;
}

function getStepKindLabel(step: ParsedPlaybook["steps"][number]) {
  if (step.type === "tool") {
    return "工具执行";
  }
  if (step.type === "human_approval") {
    return "人工确认";
  }
  if (step.type === "message_push") {
    return "消息推送";
  }
  if (step.type === "handoff") {
    return "角色交接";
  }
  return "完成节点";
}

function getStepKindClass(step: ParsedPlaybook["steps"][number]) {
  return `is-${step.type.replace("_", "-")}`;
}

function getStepConnections(step: ParsedPlaybook["steps"][number], playbook: ParsedPlaybook) {
  const connections: Array<{ id: string; label: string; targetName: string; tone: "default" | "approved" | "rejected" }> = [];

  step.next_step_ids?.forEach((targetId) => {
    connections.push({
      id: `${step.id}-next-${targetId}`,
      label: step.type === "handoff" ? "交接后" : "下一步",
      targetName: getStepName(playbook, targetId),
      tone: "default",
    });
  });

  step.on_approved_step_ids?.forEach((targetId) => {
    connections.push({
      id: `${step.id}-approved-${targetId}`,
      label: "确认通过",
      targetName: getStepName(playbook, targetId),
      tone: "approved",
    });
  });

  step.on_rejected_step_ids?.forEach((targetId) => {
    connections.push({
      id: `${step.id}-rejected-${targetId}`,
      label: "确认拒绝",
      targetName: getStepName(playbook, targetId),
      tone: "rejected",
    });
  });

  return connections;
}

export default function Home() {
  const shellRef = useRef<HTMLElement | null>(null);
  const parseButtonRef = useRef<HTMLButtonElement | null>(null);
  const previewRef = useRef<HTMLDivElement | null>(null);
  const [command, setCommand] = useState("");
  const [status, setStatus] = useState("Control layer first");
  const [selectedRoleKey, setSelectedRoleKey] = useState("");
  const [mentionRange, setMentionRange] = useState<{ mentionStart: number; mentionEnd: number } | null>(null);
  const [toolRange, setToolRange] = useState<{ toolStart: number; toolEnd: number } | null>(null);
  const [suggestionTop, setSuggestionTop] = useState(64);
  const [suggestionMode, setSuggestionMode] = useState<SuggestionMode | null>(null);
  const [activeSuggestionIndex, setActiveSuggestionIndex] = useState(0);
  const [parsedPlaybook, setParsedPlaybook] = useState<ParsedPlaybook | null>(null);
  const [showPreview, setShowPreview] = useState(false);
  const [isBusy, setIsBusy] = useState(false);
  const [exampleIndex, setExampleIndex] = useState(0);
  const [typedExample, setTypedExample] = useState("");
  const [allTools, setAllTools] = useState<ToolSuggestion[]>([]);
  const [roleTools, setRoleTools] = useState<ToolSuggestion[]>([]);
  const [skillsByRole, setSkillsByRole] = useState<Record<string, AgentSkillRecord[]>>({});

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

  useGSAP(
    () => {
      const mm = gsap.matchMedia();
      mm.add(
        {
          reduceMotion: "(prefers-reduced-motion: reduce)",
          isDesktop: "(min-width: 860px)",
        },
        (context) => {
          const { reduceMotion, isDesktop } = context.conditions ?? {};
          if (reduceMotion) {
            gsap.set(".homeReveal", { autoAlpha: 1, y: 0, scale: 1 });
            return;
          }

          gsap.from(".homeReveal", {
            autoAlpha: 0,
            y: 28,
            scale: 0.98,
            duration: 0.8,
            ease: "power3.out",
            stagger: 0.09,
          });

          gsap.from(".parseCommandButton", {
            autoAlpha: 0,
            x: 18,
            rotation: -2,
            duration: 0.7,
            delay: 0.28,
            ease: "back.out(1.8)",
          });

          if (isDesktop) {
            gsap.to(".commandCanvasGlow", {
              x: 26,
              y: -18,
              scale: 1.08,
              duration: 5.5,
              repeat: -1,
              yoyo: true,
              ease: "sine.inOut",
            });
            gsap.to(".employeeCard", {
              y: -5,
              duration: 2.8,
              repeat: -1,
              yoyo: true,
              ease: "sine.inOut",
              stagger: { each: 0.18, from: "center" },
            });
          }
        },
      );

      return () => mm.revert();
    },
    { scope: shellRef },
  );

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
        const nextTools = (data.tools ?? []).filter((tool: ToolSuggestion) => tool.executable && tool.source !== "builtin");
        setRoleTools(nextTools);
      })
      .catch(() => setRoleTools([]));
  }, [selectedRoleKey]);

  function updateComposerState(value: string, caretIndex: number, target?: HTMLTextAreaElement) {
    const mention = detectMentionQuery(value, caretIndex);
    const tool = detectToolQuery(value, caretIndex);
    if (target) {
      const computed = window.getComputedStyle(target);
      const fontSize = Number.parseFloat(computed.fontSize) || 18;
      const lineHeight = Number.parseFloat(computed.lineHeight) || fontSize * 1.8;
      const paddingTop = Number.parseFloat(computed.paddingTop) || 22;
      const linesBeforeCaret = value.slice(0, caretIndex).split("\n").length - 1;
      const nextTop = paddingTop + linesBeforeCaret * lineHeight - target.scrollTop + lineHeight + 10;
      setSuggestionTop(Math.max(48, Math.min(nextTop, target.clientHeight - 24)));
    }

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

  function animateParseButton(kind: "enter" | "leave" | "press") {
    const button = parseButtonRef.current;
    if (!button) {
      return;
    }
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      return;
    }

    if (kind === "enter") {
      gsap.to(button, {
        y: -3,
        scale: 1.02,
        duration: 0.28,
        ease: "power2.out",
        overwrite: "auto",
      });
      gsap.to(button.querySelector(".parseButtonSweep"), {
        xPercent: 130,
        duration: 0.75,
        ease: "power3.out",
        overwrite: "auto",
      });
      return;
    }

    if (kind === "press") {
      gsap.fromTo(
        button,
        { scale: 0.98 },
        { scale: 1.02, duration: 0.22, ease: "back.out(2)", overwrite: "auto" },
      );
      return;
    }

    gsap.to(button, {
      y: 0,
      scale: 1,
      duration: 0.28,
      ease: "power2.out",
      overwrite: "auto",
    });
    gsap.set(button.querySelector(".parseButtonSweep"), { xPercent: -130 });
  }

  async function handleParseClick() {
    animateParseButton("press");
    await parseCommand();
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
      void loadSkillsForPlaybook(data);
      requestAnimationFrame(() => {
        previewRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
        if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches && previewRef.current) {
          gsap.fromTo(
            previewRef.current,
            { y: 18, boxShadow: "0 18px 50px rgb(32 33 31 / 12%)" },
            {
              y: 0,
              boxShadow: "0 30px 90px rgb(31 111 95 / 18%)",
              duration: 0.55,
              ease: "power3.out",
              yoyo: true,
              repeat: 1,
            },
          );
        }
      });
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
          steps: parsedPlaybook?.steps,
        }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail ?? "save failed");
      }
      setStatus(`已保存任务：${data.name}`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "保存失败");
    } finally {
      setIsBusy(false);
    }
  }

  const activeItems = suggestionMode === "employee" ? filteredEmployees : filteredTools;

  async function loadSkillsForPlaybook(playbook: ParsedPlaybook) {
    const roleKeys = Array.from(
      new Set(playbook.steps.map((step) => step.assignee_role_key || step.role_key || playbook.role_key).filter(Boolean) as string[]),
    );
    await Promise.all(
      roleKeys.map(async (roleKey) => {
        if (skillsByRole[roleKey]) {
          return;
        }
        try {
          const response = await fetch(`/api/agents/${roleKey}/skills?limit=50`, { cache: "no-store" });
          const data = await response.json();
          if (response.ok) {
            setSkillsByRole((current) => ({ ...current, [roleKey]: data.skills ?? [] }));
          }
        } catch {
          setSkillsByRole((current) => ({ ...current, [roleKey]: [] }));
        }
      }),
    );
  }

  function getStepRoleKey(step: ParsedPlaybook["steps"][number], playbook: ParsedPlaybook) {
    return step.assignee_role_key || step.role_key || playbook.role_key;
  }

  function getSelectedSkillIds(step: ParsedPlaybook["steps"][number]) {
    const selected = step.config.selected_skill_ids;
    return Array.isArray(selected) ? selected.filter((item): item is string => typeof item === "string") : [];
  }

  function toggleStepSkill(stepId: string, skillId: string) {
    setParsedPlaybook((current) => {
      if (!current) {
        return current;
      }
      return {
        ...current,
        steps: current.steps.map((step) => {
          if (step.id !== stepId) {
            return step;
          }
          const selected = new Set(getSelectedSkillIds(step));
          if (selected.has(skillId)) {
            selected.delete(skillId);
          } else {
            selected.add(skillId);
          }
          return {
            ...step,
            config: {
              ...step.config,
              selected_skill_ids: Array.from(selected),
            },
          };
        }),
      };
    });
  }

  return (
    <main className="shell homeShell" ref={shellRef}>
      <section className="masthead homeMasthead homeReveal">
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

      <section className="homeComposerShell homeReveal">
        <div className="homeComposerHeader">
          <p className="eyebrow">Natural Language Orchestration</p>
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
              <button
                className="parseCommandButton"
                type="button"
                ref={parseButtonRef}
                onClick={handleParseClick}
                onMouseEnter={() => animateParseButton("enter")}
                onMouseLeave={() => animateParseButton("leave")}
                disabled={isBusy}
              >
                <span className="parseButtonSweep" aria-hidden="true" />
                <span className="parseButtonSignal" aria-hidden="true" />
                <span className="parseButtonIcon">
                  {isBusy ? <Radar aria-hidden="true" /> : <FileText aria-hidden="true" />}
                </span>
                <span className="parseButtonText">
                  <strong>{isBusy ? "解析中" : "解析"}</strong>
                  <small>Compile workflow</small>
                </span>
              </button>
              
            </div>
          </div>

          <div className="mentionComposer commandComposer">
            <textarea
              value={command}
              onChange={(event) => {
                setCommand(event.target.value);
                updateComposerState(event.target.value, event.target.selectionStart ?? event.target.value.length, event.target);
              }}
              onClick={(event) => {
                const target = event.target as HTMLTextAreaElement;
                updateComposerState(target.value, target.selectionStart ?? target.value.length, target);
              }}
              onKeyUp={(event) => {
                if (["ArrowDown", "ArrowUp", "Enter", "Escape"].includes(event.key)) {
                  return;
                }
                const target = event.target as HTMLTextAreaElement;
                updateComposerState(target.value, target.selectionStart ?? target.value.length, target);
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
              <div
                className="mentionMenu"
                role="listbox"
                style={{ top: suggestionTop }}
                aria-label={suggestionMode === "employee" ? "员工选择" : "工具选择"}
              >
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
          <div className="flowPreviewPanel homePreviewPanel homeReveal" ref={previewRef}>
            <div className="flowPreviewHeader">
              <div>
                <p className="eyebrow">Parsed Playbook</p>
                <h2>{parsedPlaybook.name}</h2>
              </div>
              <div className="flowMeta">
                <span>{getRoleName(parsedPlaybook.role_key)}</span>
                <span>{parsedPlaybook.trigger.type}</span>
                <span>{parsedPlaybook.trigger.cron || parsedPlaybook.trigger.time}</span>
                <span>{parsedPlaybook.steps.length} 个节点</span>
              </div>
            </div>

            <div className="flowTriggerSummary">
              <Clock3 aria-hidden="true" />
              <div>
                <strong>触发时间</strong>
                <p>
                  {parsedPlaybook.trigger.description || formatTriggerSummary(parsedPlaybook)}
                  {parsedPlaybook.trigger.run_at ? `；run_at: ${parsedPlaybook.trigger.run_at}` : ""}
                  {parsedPlaybook.trigger.cron ? `；cron: ${parsedPlaybook.trigger.cron}` : ""}
                </p>
              </div>
            </div>

            <div className="workflowCanvas" aria-label="解析后的流程节点画布">
              <div className="workflowCanvasHeader">
                <div>
                  <p className="eyebrow">Workflow Canvas</p>
                  <strong>节点会按执行顺序展开，右侧端口代表输出，连线标签代表进入下一节点的条件。</strong>
                </div>
                <div className="workflowLegend" aria-label="节点图例">
                  <span data-tone="tool">工具</span>
                  <span data-tone="approval">确认</span>
                  <span data-tone="handoff">交接</span>
                </div>
              </div>

              <div className="workflowGraph">
              {parsedPlaybook.steps.map((step, index) => {
                const nextAction = getStepNextAction(step, parsedPlaybook);
                const connections = getStepConnections(step, parsedPlaybook);
                return (
                  <article className={`flowNode ${getStepKindClass(step)}`} key={step.id}>
                    <div className="flowNodeIndex">
                      <span>{index + 1}</span>
                    </div>
                    <div className="flowNodeBody">
                      <i className="nodePort nodePortIn" aria-hidden="true" />
                      <i className="nodePort nodePortOut" aria-hidden="true" />
                      <div className="flowNodeTop">
                        <div>
                          <span className="flowNodeKind">{getStepKindLabel(step)}</span>
                          <h3>{step.name}</h3>
                        </div>
                        <span className="flowNodeId">{step.id}</span>
                      </div>

                      <div className="flowFacts">
                        <span>
                          <ShieldCheck aria-hidden="true" />
                          角色：{getRoleName(step.assignee_role_key || step.role_key || parsedPlaybook.role_key)}
                        </span>
                        <span>
                          <Wrench aria-hidden="true" />
                          工具：{step.type === "tool" ? getStepToolName(step) : "不使用工具"}
                        </span>
                        <span>
                          <Clock3 aria-hidden="true" />
                          时间：{getStepRunTime(step, parsedPlaybook)}
                        </span>
                      </div>

                      <div className="flowPrompt">
                        <strong>{step.type === "human_approval" ? "确认消息" : step.type === "message_push" ? "推送内容来源" : "执行提示词/输入"}</strong>
                        <p>{getStepPrompt(step)}</p>
                      </div>

                      <div className="flowSkillPicker">
                        <strong>节点 Skills</strong>
                        <p>当前节点角色：{getRoleName(getStepRoleKey(step, parsedPlaybook))}</p>
                        <div className="flowSkillList">
                          {(skillsByRole[getStepRoleKey(step, parsedPlaybook)] ?? []).length ? (
                            (skillsByRole[getStepRoleKey(step, parsedPlaybook)] ?? []).map((skill) => {
                              const checked = getSelectedSkillIds(step).includes(skill.id);
                              return (
                                <label className="flowSkillChip" key={skill.id}>
                                  <input checked={checked} onChange={() => toggleStepSkill(step.id, skill.id)} type="checkbox" />
                                  <span>{skill.title}</span>
                                  <small>{skill.kind} · {skill.source_type === "manual" ? "人工" : "自训"}</small>
                                </label>
                              );
                            })
                          ) : (
                            <span className="flowSkillEmpty">该角色暂无 Skills，可到员工管理页人工上传。</span>
                          )}
                        </div>
                      </div>

                      <div className="flowNextAction">
                        {step.type === "human_approval" ? <MessageSquare aria-hidden="true" /> : <CheckCircle2 aria-hidden="true" />}
                        <div>
                          <strong>{nextAction.label}</strong>
                          <p>{nextAction.detail}</p>
                        </div>
                      </div>

                      <div className="flowConnections" aria-label={`${step.name} 的后续连线`}>
                        {connections.length ? (
                          connections.map((connection) => (
                            <div className="flowConnection" data-tone={connection.tone} key={connection.id}>
                              <GitBranch aria-hidden="true" />
                              <span>{connection.label}</span>
                              <ArrowRight aria-hidden="true" />
                              <strong>{connection.targetName}</strong>
                            </div>
                          ))
                        ) : (
                          <div className="flowConnection is-terminal">
                            <CheckCircle2 aria-hidden="true" />
                            <span>流程结束</span>
                          </div>
                        )}
                      </div>
                    </div>
                  </article>
                );
              })}
              </div>
            </div>

            {parsedPlaybook.unresolved_tools.length ? (
              <div className="flowWarning">
                未解析工具：{parsedPlaybook.unresolved_tools.join("、")}。保存剧本前需要先在工具管理中注册并授权。
              </div>
            ) : null}

            <div className="flowPreviewActions">
              <button type="button" onClick={savePlaybook} disabled={isBusy || Boolean(parsedPlaybook.unresolved_tools.length)}>
                <Save aria-hidden="true" />
                保存任务
              </button>
              <span>
                保存后可在对应员工管理页查看任务、运行实例和执行节点日志。
              </span>
            </div>
          </div>
        ) : null}
      </section>

      <section className="quickActions homeReveal" aria-label="服务配置">
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

      <section className="employeeGrid homeReveal" aria-label="数字员工角色">
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
