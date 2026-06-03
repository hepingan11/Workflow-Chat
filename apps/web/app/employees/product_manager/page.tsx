"use client";

import Link from "next/link";
import {
  ArrowLeft,
  CheckCheck,
  FileText,
  BriefcaseBusiness,
  Play,
  RefreshCcw,
  Save,
  ShieldCheck,
  Wrench,
  X,
} from "lucide-react";
import { useEffect, useState } from "react";

type AgentToolDefinition = {
  id: string;
  name: string;
  description: string;
  source: "builtin" | "dify" | "codex" | "mcp";
  enabled: boolean;
  executable: boolean;
};

type PlaybookRecord = {
  id: string;
  role_key: string;
  name: string;
  natural_language: string;
  trigger: {
    time: string;
  };
  steps: Array<{
    id: string;
    name: string;
    type: "tool" | "human_approval" | "message_push" | "handoff" | "noop";
  }>;
  status: string;
};

type RunRecord = {
  id: string;
  playbook_id: string;
  role_key: string;
  status: string;
  scheduled_for: string;
  current_step_index: number;
  shared_context?: Record<string, unknown>;
  steps: Array<{
    id: string;
    name: string;
    type: "tool" | "human_approval" | "message_push" | "handoff" | "noop";
    status: string;
    approval_id?: string | null;
    error?: string | null;
    output?: Record<string, unknown> | null;
    config?: Record<string, unknown>;
    context_reads?: string[];
    context_writes?: string[];
  }>;
};

type ApprovalRecord = {
  id: string;
  run_id: string;
  playbook_id: string;
  role_key: string;
  step_id: string;
  status: "pending" | "approved" | "rejected";
  message: string;
};

const ROLE_KEY = "product_manager";
const ROLE_NAME = "产品经理";
const ROLE_ENGLISH_NAME = "Product Manager Employee";

export default function ProductManagerPage() {
  const [prompt, setPrompt] = useState("");
  const [tools, setTools] = useState<AgentToolDefinition[]>([]);
  const [selectedToolId, setSelectedToolId] = useState("");
  const [toolInputs, setToolInputs] = useState('{\n  "requirement": "用户希望支持自然语言创建任务并查看执行进度",\n  "goal": "整理需求拆解、验收标准和风险点"\n}');
  const [toolResult, setToolResult] = useState("");
  const [showToolResult, setShowToolResult] = useState(false);
  const [playbooks, setPlaybooks] = useState<PlaybookRecord[]>([]);
  const [runs, setRuns] = useState<RunRecord[]>([]);
  const [approvals, setApprovals] = useState<ApprovalRecord[]>([]);
  const [selectedPlaybookId, setSelectedPlaybookId] = useState("");
  const [selectedRunId, setSelectedRunId] = useState("");
  const [workflowStatus, setWorkflowStatus] = useState("等待编排");
  const [isBusy, setIsBusy] = useState(false);

  useEffect(() => {
    fetch(`/api/agents/${ROLE_KEY}/prompt`)
      .then((response) => response.json())
      .then((data) => setPrompt(data.prompt ?? ""))
      .catch(() => setWorkflowStatus("无法读取提示词，请确认后端服务已启动。"));

    fetch(`/api/agents/${ROLE_KEY}/tools`)
      .then((response) => response.json())
      .then((data) => {
        const nextTools = data.tools ?? [];
        setTools(nextTools);
        const firstExecutable = nextTools.find((tool: AgentToolDefinition) => tool.source !== "builtin" && tool.executable);
        if (firstExecutable) {
          setSelectedToolId(firstExecutable.id);
        }
      })
      .catch(() => setWorkflowStatus(`无法读取${ROLE_NAME}工具列表。`));

    refreshAutomation();
  }, []);

  async function refreshAutomation() {
    try {
      const [playbooksResponse, runsResponse, approvalsResponse] = await Promise.all([
        fetch(`/api/playbooks?role_key=${ROLE_KEY}`),
        fetch("/api/playbooks/runs"),
        fetch(`/api/playbooks/approvals?role_key=${ROLE_KEY}`),
      ]);
      const playbookData = await playbooksResponse.json();
      const runsData = await runsResponse.json();
      const approvalsData = await approvalsResponse.json();
      const roleRuns = (runsData ?? []).filter((item: RunRecord) => item.role_key === ROLE_KEY);

      setPlaybooks(playbookData ?? []);
      setRuns(roleRuns);
      setApprovals(approvalsData ?? []);

      if (!selectedPlaybookId && Array.isArray(playbookData) && playbookData.length) {
        setSelectedPlaybookId(playbookData[0].id);
      }
      if (!selectedRunId && roleRuns.length) {
        setSelectedRunId(roleRuns[0].id);
      }
    } catch {
      setWorkflowStatus("读取自动化任务失败。");
    }
  }

  async function savePrompt() {
    setIsBusy(true);
    try {
      const response = await fetch(`/api/agents/${ROLE_KEY}/prompt`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      });
      if (!response.ok) {
        throw new Error("save failed");
      }
      setWorkflowStatus("提示词已保存。");
    } catch {
      setWorkflowStatus("提示词保存失败。");
    } finally {
      setIsBusy(false);
    }
  }

  async function executeTool() {
    if (!selectedToolId) {
      setToolResult("请先选择一个可执行工具。");
      setShowToolResult(true);
      return;
    }

    setIsBusy(true);
    try {
      const inputs = JSON.parse(toolInputs);
      const response = await fetch(`/api/agents/${ROLE_KEY}/tools/${selectedToolId}/execute`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          inputs,
          user: "product-manager-employee-page",
        }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail ?? JSON.stringify(data));
      }
      setToolResult(JSON.stringify(data.result, null, 2));
      setShowToolResult(true);
    } catch (error) {
      setToolResult(error instanceof Error ? error.message : "工具执行失败。");
      setShowToolResult(true);
    } finally {
      setIsBusy(false);
    }
  }

  async function triggerPlaybook() {
    if (!selectedPlaybookId) {
      setWorkflowStatus("请先选择一个任务剧本。");
      return;
    }

    setIsBusy(true);
    try {
      const response = await fetch(`/api/playbooks/${selectedPlaybookId}/trigger`, {
        method: "POST",
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail ?? "trigger failed");
      }
      setWorkflowStatus(`已创建运行实例 ${data.id}`);
      setSelectedRunId(data.id);
      await refreshAutomation();
    } catch (error) {
      setWorkflowStatus(error instanceof Error ? error.message : "触发运行失败。");
    } finally {
      setIsBusy(false);
    }
  }

  async function deletePlaybook(playbookId: string, playbookName: string) {
    const confirmed = window.confirm(`确定删除任务「${playbookName}」吗？相关运行实例和审批记录也会一起清理。`);
    if (!confirmed) {
      return;
    }

    setIsBusy(true);
    try {
      const response = await fetch(`/api/playbooks/${playbookId}`, {
        method: "DELETE",
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail ?? "delete failed");
      }
      setWorkflowStatus(`已删除任务 ${data.name}`);
      setSelectedPlaybookId((current) => (current === playbookId ? "" : current));
      setSelectedRunId("");
      await refreshAutomation();
    } catch (error) {
      setWorkflowStatus(error instanceof Error ? error.message : "删除任务失败。");
    } finally {
      setIsBusy(false);
    }
  }

  async function deleteRun(runId: string) {
    const confirmed = window.confirm(`确定删除运行实例 ${runId} 吗？相关审批记录也会一起清理。`);
    if (!confirmed) {
      return;
    }

    setIsBusy(true);
    try {
      const response = await fetch(`/api/playbooks/runs/${runId}`, {
        method: "DELETE",
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail ?? "delete run failed");
      }
      setWorkflowStatus(`已删除运行实例 ${runId}`);
      setSelectedRunId((current) => (current === runId ? "" : current));
      await refreshAutomation();
    } catch (error) {
      setWorkflowStatus(error instanceof Error ? error.message : "删除运行实例失败。");
    } finally {
      setIsBusy(false);
    }
  }

  async function advanceRun(runId: string) {
    setIsBusy(true);
    try {
      const response = await fetch(`/api/playbooks/runs/${runId}/advance`, {
        method: "POST",
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail ?? "advance failed");
      }
      setWorkflowStatus(`运行已推进到 ${data.run.status}`);
      await refreshAutomation();
    } catch (error) {
      setWorkflowStatus(error instanceof Error ? error.message : "推进运行失败。");
    } finally {
      setIsBusy(false);
    }
  }

  async function resolveApproval(approvalId: string, approved: boolean) {
    setIsBusy(true);
    try {
      const response = await fetch(`/api/playbooks/approvals/${approvalId}/${approved ? "approve" : "reject"}`, {
        method: "POST",
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail ?? "approval failed");
      }
      setWorkflowStatus(`审批已${approved ? "通过" : "拒绝"}`);
      await refreshAutomation();
    } catch (error) {
      setWorkflowStatus(error instanceof Error ? error.message : "审批操作失败。");
    } finally {
      setIsBusy(false);
    }
  }

  const selectedRun = runs.find((run) => run.id === selectedRunId) ?? runs[0];

  function getPlaybookName(playbookId: string) {
    const playbook = playbooks.find((item) => item.id === playbookId);
    if (playbook) {
      return playbook.name;
    }
    const run = runs.find((item) => item.playbook_id === playbookId);
    const archivedName = run?.shared_context?.playbook_name;
    return typeof archivedName === "string" && archivedName ? `${archivedName}（一次性任务）` : `${playbookId}（一次性任务）`;
  }

  function getStepTypeLabel(type: string) {
    if (type === "tool") {
      return "工具执行";
    }
    if (type === "human_approval") {
      return "人工确认";
    }
    if (type === "message_push") {
      return "消息推送";
    }
    if (type === "handoff") {
      return "角色交接";
    }
    return "流程节点";
  }

  return (
    <main className="shell">
      <section className="employeeHero">
        <Link className="backLink" href="/">
          <ArrowLeft aria-hidden="true" />
          返回员工列表
        </Link>
        <div className="employeeHeroGrid">
          <div>
            <p className="eyebrow">{ROLE_ENGLISH_NAME}</p>
            <h1>{ROLE_NAME}管理</h1>
            <p className="lede">管理产品经理提示词、授权工具、需求任务、运行实例和节点执行日志。</p>
          </div>
          <div className="statusPanel">
            <BriefcaseBusiness aria-hidden="true" />
            <span>{workflowStatus}</span>
          </div>
        </div>
      </section>

      <section className="settingsPanel" aria-label="产品经理提示词配置">
        <div className="editorPanel">
          <div className="panelHeader">
            <FileText aria-hidden="true" />
            <h2>需求整理提示词</h2>
            <button type="button" onClick={savePrompt} disabled={isBusy} title="保存提示词">
              <Save aria-hidden="true" />
              保存
            </button>
          </div>
          <textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} aria-label="产品经理需求整理提示词" />
        </div>
      </section>

      <section className="settingsPanel" aria-label="产品经理授权工具">
        <div className="panelHeader">
          <Wrench aria-hidden="true" />
          <h2>产品经理授权工具</h2>
          <button type="button" onClick={executeTool} disabled={isBusy || !selectedToolId}>
            <Play aria-hidden="true" />
            测试运行
          </button>
        </div>
        <div className="toolList operatorToolList">
          {tools.length ? (
            tools.map((tool) => (
              <button
                type="button"
                className={`toolListItem${tool.id === selectedToolId ? " is-active" : ""}`}
                key={tool.id}
                onClick={() => setSelectedToolId(tool.id)}
                disabled={!tool.executable}
              >
                <strong>{tool.name}</strong>
                <small>{tool.description || "暂无描述"}</small>
                <code>{tool.source} · {tool.executable ? "可执行" : "不可执行"}</code>
              </button>
            ))
          ) : (
            <p className="toolEmpty">当前没有授权工具。</p>
          )}
        </div>
        <label>
          工具输入 JSON
          <textarea value={toolInputs} onChange={(event) => setToolInputs(event.target.value)} />
        </label>
      </section>

      <section className="settingsPanel">
        <div className="panelHeader">
          <ShieldCheck aria-hidden="true" />
          <h2>当前产品任务</h2>
          <div className="toolActions">
            <button type="button" onClick={refreshAutomation} disabled={isBusy}>
              <RefreshCcw aria-hidden="true" />
              刷新
            </button>
          </div>
        </div>

        <div className="operatorConsole automationConsole">
          <div className="publishPanel">
            <div className="panelHeader">
              <BriefcaseBusiness aria-hidden="true" />
              <h2>任务列表</h2>
              <button type="button" onClick={triggerPlaybook} disabled={isBusy || !selectedPlaybookId}>
                <Play aria-hidden="true" />
                触发运行
              </button>
            </div>
            <label>
              当前剧本
              <select value={selectedPlaybookId} onChange={(event) => setSelectedPlaybookId(event.target.value)}>
                <option value="">请选择剧本</option>
                {playbooks.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name} ({item.trigger.time})
                  </option>
                ))}
              </select>
            </label>
            <div className="automationList">
              {playbooks.length ? (
                playbooks.map((item) => (
                  <article className="automationCard" key={item.id}>
                    <div className="automationCardHeader">
                      <h3>{item.name}</h3>
                      <button type="button" onClick={() => deletePlaybook(item.id, item.name)} disabled={isBusy}>
                        <X aria-hidden="true" />
                        删除
                      </button>
                    </div>
                    <p>{item.natural_language}</p>
                    <div className="taskMetaGrid">
                      <span>状态：{item.status}</span>
                      <span>触发：{item.trigger.time}</span>
                      <span>节点：{item.steps.length}</span>
                    </div>
                    <div className="stepPills">
                      {item.steps.map((step) => (
                        <span key={step.id}>{getStepTypeLabel(step.type)} · {step.name}</span>
                      ))}
                    </div>
                    <code>{item.id}</code>
                  </article>
                ))
              ) : (
                <p className="toolEmpty">当前产品经理角色还没有长期任务。一次性任务会直接进入运行实例。</p>
              )}
            </div>
          </div>

          <div className="publishPanel">
            <div className="panelHeader">
              <Play aria-hidden="true" />
              <h2>运行实例</h2>
            </div>
            <label>
              当前运行
              <select value={selectedRunId} onChange={(event) => setSelectedRunId(event.target.value)}>
                <option value="">请选择运行实例</option>
                {runs.map((run) => (
                  <option key={run.id} value={run.id}>
                    {getPlaybookName(run.playbook_id)} · {run.status}
                  </option>
                ))}
              </select>
            </label>
            <div className="automationList">
              {runs.length ? (
                runs.map((run) => (
                  <article className="automationCard" key={run.id}>
                    <div className="automationCardHeader">
                      <h3>{getPlaybookName(run.playbook_id)}</h3>
                      <button type="button" onClick={() => deleteRun(run.id)} disabled={isBusy} title="删除运行实例">
                        <X aria-hidden="true" />
                        删除
                      </button>
                    </div>
                    <p>运行 ID：{run.id}</p>
                    <div className="taskMetaGrid">
                      <span>状态：{run.status}</span>
                      <span>当前节点：{run.current_step_index + 1}</span>
                      <span>调度：{run.scheduled_for}</span>
                    </div>
                    <button type="button" onClick={() => advanceRun(run.id)} disabled={isBusy}>
                      推进运行
                    </button>
                  </article>
                ))
              ) : (
                <p className="toolEmpty">还没有运行实例。</p>
              )}
            </div>
          </div>
        </div>
      </section>

      <section className="operatorConsole automationConsole" aria-label="节点日志与审批">
        <div className="publishPanel">
          <div className="panelHeader">
            <FileText aria-hidden="true" />
            <h2>执行节点日志</h2>
          </div>
          <div className="automationList">
            {selectedRun?.steps.length ? (
              selectedRun.steps.map((step, index) => (
                <details className="automationCard nodeLogCard" key={step.id}>
                  <summary className="nodeLogHeader">
                    <span>{index + 1}</span>
                    <div>
                      <h3>{step.name}</h3>
                      <p>{getStepTypeLabel(step.type)} · {step.status}</p>
                    </div>
                  </summary>
                  <div className="nodeLogBody">
                    <div className="taskMetaGrid">
                      <span>节点 ID：{step.id}</span>
                      <span>审批：{step.approval_id || "无"}</span>
                      <span>读写：{[...(step.context_reads ?? []), ...(step.context_writes ?? [])].join(" / ") || "无"}</span>
                    </div>
                    {step.error ? <p className="nodeError">错误：{step.error}</p> : null}
                    <pre className="nodeLogPre">
                      {JSON.stringify(
                        {
                          config: step.config ?? {},
                          output: step.output ?? {},
                        },
                        null,
                        2,
                      )}
                    </pre>
                  </div>
                </details>
              ))
            ) : (
              <p className="toolEmpty">请选择一个运行实例查看节点日志。</p>
            )}
          </div>
        </div>

        <div className="publishPanel">
          <div className="panelHeader">
            <CheckCheck aria-hidden="true" />
            <h2>待审批事项</h2>
          </div>
          <div className="automationList">
            {approvals.length ? (
              approvals.map((approval) => (
                <article className="automationCard" key={approval.id}>
                  <h3>{approval.id}</h3>
                  <p>{approval.message}</p>
                  <p>状态：{approval.status}</p>
                  <div className="toolActions">
                    <button type="button" onClick={() => resolveApproval(approval.id, true)} disabled={isBusy}>
                      <CheckCheck aria-hidden="true" />
                      通过
                    </button>
                    <button type="button" onClick={() => resolveApproval(approval.id, false)} disabled={isBusy}>
                      <X aria-hidden="true" />
                      拒绝
                    </button>
                  </div>
                </article>
              ))
            ) : (
              <p className="toolEmpty">当前没有待审批事项。</p>
            )}
          </div>
        </div>
      </section>

      {showToolResult ? (
        <div className="modalBackdrop" role="presentation" onMouseDown={() => setShowToolResult(false)}>
          <section className="modalPanel toolResultModal" role="dialog" aria-modal="true" aria-label="工具测试运行结果" onMouseDown={(event) => event.stopPropagation()}>
            <div className="panelHeader">
              <Wrench aria-hidden="true" />
              <h2>工具测试运行结果</h2>
              <button type="button" onClick={() => setShowToolResult(false)}>
                <X aria-hidden="true" />
                关闭
              </button>
            </div>
            <pre>{toolResult}</pre>
          </section>
        </div>
      ) : null}
    </main>
  );
}
