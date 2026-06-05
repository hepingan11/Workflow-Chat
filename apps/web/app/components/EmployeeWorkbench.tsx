"use client";

import Link from "next/link";
import { ArrowLeft, CheckCheck, FileText, Play, RefreshCcw, Save, ShieldCheck, X } from "lucide-react";
import { useEffect, useState } from "react";

import { getEmployee } from "../employees";
import { AgentMemoryPanel } from "./AgentMemoryPanel";
import { AgentSkillPanel } from "./AgentSkillPanel";

type PlaybookRecord = {
  id: string;
  name: string;
  natural_language: string;
  trigger: { time: string };
  steps: Array<{ id: string; name: string; type: string }>;
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
    type: string;
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
  status: "pending" | "approved" | "rejected";
  message: string;
};

type RunMonitorEvent = {
  time: string;
  type: string;
  step_id: string;
  step_name: string;
  stream: string;
  message: string;
};

type RunMonitor = {
  run_id: string;
  status: string;
  events: RunMonitorEvent[];
};

type EmployeeWorkbenchProps = {
  roleKey: string;
};

const promptTitles: Record<string, string> = {
  operator: "角色提示词",
  programmer: "程序员系统提示词",
  customer_support: "客服系统提示词",
  product_manager: "产品经理系统提示词",
};

export function EmployeeWorkbench({ roleKey }: EmployeeWorkbenchProps) {
  const employee = getEmployee(roleKey);
  const Icon = employee?.icon ?? ShieldCheck;
  const roleName = employee?.name ?? roleKey;
  const [prompt, setPrompt] = useState("");
  const [playbooks, setPlaybooks] = useState<PlaybookRecord[]>([]);
  const [runs, setRuns] = useState<RunRecord[]>([]);
  const [approvals, setApprovals] = useState<ApprovalRecord[]>([]);
  const [workflowStatus, setWorkflowStatus] = useState("等待编排");
  const [isBusy, setIsBusy] = useState(false);
  const [selectedRunId, setSelectedRunId] = useState("");
  const [monitoringRunId, setMonitoringRunId] = useState("");
  const [runMonitor, setRunMonitor] = useState<RunMonitor | null>(null);
  const [promptModalOpen, setPromptModalOpen] = useState(false);
  const [runModalOpen, setRunModalOpen] = useState(false);
  const [taskModalOpen, setTaskModalOpen] = useState(false);

  useEffect(() => {
    fetch(`/api/agents/${roleKey}/prompt`)
      .then((response) => response.json())
      .then((data) => setPrompt(data.prompt ?? ""))
      .catch(() => setWorkflowStatus("无法读取提示词，请确认后端服务已启动。"));
    void refreshAutomation();
  }, [roleKey]);

  useEffect(() => {
    if (!monitoringRunId) {
      return undefined;
    }
    let cancelled = false;
    async function pollMonitor() {
      try {
        const response = await fetch(`/api/playbooks/runs/${monitoringRunId}/monitor`, { cache: "no-store" });
        const data = await response.json();
        if (!cancelled) {
          setRunMonitor(data);
        }
      } catch {
        if (!cancelled) {
          setWorkflowStatus("实时监控读取失败");
        }
      }
    }
    void pollMonitor();
    const timer = window.setInterval(pollMonitor, 1500);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [monitoringRunId]);

  async function refreshAutomation() {
    try {
      const [playbooksResponse, runsResponse, approvalsResponse] = await Promise.all([
        fetch(`/api/playbooks?role_key=${roleKey}`),
        fetch("/api/playbooks/runs"),
        fetch(`/api/playbooks/approvals?role_key=${roleKey}`),
      ]);
      const playbookData = await playbooksResponse.json();
      const runsData = await runsResponse.json();
      const approvalsData = await approvalsResponse.json();
      const roleRuns = (runsData ?? []).filter((item: RunRecord) => item.role_key === roleKey);
      setPlaybooks(playbookData ?? []);
      setRuns(roleRuns);
      setApprovals(approvalsData ?? []);
      setSelectedRunId((current) => current || roleRuns?.[0]?.id || "");
    } catch {
      setWorkflowStatus("读取自动化任务失败。");
    }
  }

  async function savePrompt() {
    setIsBusy(true);
    try {
      const response = await fetch(`/api/agents/${roleKey}/prompt`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      });
      if (!response.ok) {
        throw new Error("save failed");
      }
      setWorkflowStatus("提示词已保存。");
      setPromptModalOpen(false);
    } catch {
      setWorkflowStatus("提示词保存失败。");
    } finally {
      setIsBusy(false);
    }
  }

  async function triggerPlaybook(playbookId: string) {
    setIsBusy(true);
    try {
      const response = await fetch(`/api/playbooks/${playbookId}/trigger`, { method: "POST" });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail ?? "trigger failed");
      }
      setWorkflowStatus(`已创建运行实例 ${data.id}`);
      setSelectedRunId(data.id);
      setMonitoringRunId(data.id);
      await refreshAutomation();
    } catch (error) {
      setWorkflowStatus(error instanceof Error ? error.message : "触发运行失败。");
    } finally {
      setIsBusy(false);
    }
  }

  async function deletePlaybook(playbookId: string, playbookName: string) {
    if (!window.confirm(`确定删除任务「${playbookName}」吗？相关运行实例和审批记录也会一起清理。`)) {
      return;
    }
    setIsBusy(true);
    try {
      const response = await fetch(`/api/playbooks/${playbookId}`, { method: "DELETE" });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail ?? "delete failed");
      }
      setWorkflowStatus(`已删除任务 ${data.name}`);
      await refreshAutomation();
    } catch (error) {
      setWorkflowStatus(error instanceof Error ? error.message : "删除任务失败。");
    } finally {
      setIsBusy(false);
    }
  }

  async function deleteRun(runId: string) {
    if (!window.confirm(`确定删除运行实例 ${runId} 吗？相关审批记录也会一起清理。`)) {
      return;
    }
    setIsBusy(true);
    try {
      const response = await fetch(`/api/playbooks/runs/${runId}`, { method: "DELETE" });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail ?? "delete run failed");
      }
      setWorkflowStatus(`已删除运行实例 ${data.id ?? runId}`);
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
    setSelectedRunId(runId);
    setMonitoringRunId(runId);
    try {
      const response = await fetch(`/api/playbooks/runs/${runId}/advance`, { method: "POST" });
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
      const response = await fetch(`/api/playbooks/approvals/${approvalId}/${approved ? "approve" : "reject"}`, { method: "POST" });
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
  const activeMonitorEvents = runMonitor?.events ?? [];
  const codexMonitorEvents = activeMonitorEvents.filter((event) => event.type.startsWith("codex") || event.stream);

  function getPlaybookName(playbookId: string) {
    const playbook = playbooks.find((item) => item.id === playbookId);
    if (playbook) {
      return playbook.name;
    }
    const run = runs.find((item) => item.playbook_id === playbookId);
    const archivedName = run?.shared_context?.playbook_name;
    return typeof archivedName === "string" && archivedName ? `${archivedName}（一次性任务）` : `${playbookId}（一次性任务）`;
  }

  return (
    <main className={`shell employeeWorkbenchShell${runMonitor ? " has-monitor" : ""}`}>
      {runMonitor ? (
        <aside className="employeeMonitorRail is-active" aria-label="运行实时监控">
          <div className="panelHeader">
            <RefreshCcw aria-hidden="true" />
            <h2>实时监控</h2>
          </div>
          <MonitorPanel codexMonitorEvents={codexMonitorEvents} runMonitor={runMonitor} selectedRun={selectedRun} />
        </aside>
      ) : null}

      <section className="employeeHero employeeWorkbenchHero">
        <Link className="backLink" href="/">
          <ArrowLeft aria-hidden="true" />
          返回员工列表
        </Link>
        <div className="employeeHeroGrid">
          <div>
            <p className="eyebrow">{roleKey}</p>
            <h1>{roleName}管理</h1>
            <p className="lede">{employee?.mission ?? `管理 ${roleName} 的提示词、任务、运行实例和执行日志。`}</p>
          </div>
          <div className="statusPanel">
            <Icon aria-hidden="true" />
            <span>{workflowStatus}</span>
          </div>
        </div>
      </section>

      <section className="employeeTopGrid">
        <RunsPreview
          advanceRun={advanceRun}
          deleteRun={deleteRun}
          getPlaybookName={getPlaybookName}
          isBusy={isBusy}
          onMore={() => setRunModalOpen(true)}
          runs={runs}
        />
        <TasksPreview
          deletePlaybook={deletePlaybook}
          isBusy={isBusy}
          onMore={() => setTaskModalOpen(true)}
          playbooks={playbooks}
          triggerPlaybook={triggerPlaybook}
        />
      </section>

      <section className="employeePromptStrip">
        <div>
          <span className="eyebrow">System Prompt</span>
          <h2>{promptTitles[roleKey] ?? "角色提示词"}</h2>
        </div>
        <button type="button" onClick={() => setPromptModalOpen(true)}>
          查看/修改
        </button>
      </section>

      <section className="employeeKnowledgeGrid">
        <AgentMemoryPanel roleKey={roleKey} roleName={roleName} />
        <AgentSkillPanel roleKey={roleKey} roleName={roleName} compactLimit={6} />
      </section>

      <section className="employeeFullRow">
        <NodeLogs selectedRun={selectedRun} />
      </section>

      <section className="employeeFullRow">
        <ApprovalList approvals={approvals} isBusy={isBusy} resolveApproval={resolveApproval} />
      </section>

      {promptModalOpen ? (
        <Modal title={promptTitles[roleKey] ?? "角色提示词"} onClose={() => setPromptModalOpen(false)}>
          <textarea className="employeePromptEditor" value={prompt} onChange={(event) => setPrompt(event.target.value)} />
          <div className="toolActions">
            <button type="button" onClick={savePrompt} disabled={isBusy}>
              <Save aria-hidden="true" />
              保存提示词
            </button>
          </div>
        </Modal>
      ) : null}

      {runModalOpen ? (
        <Modal title="全部运行实例" onClose={() => setRunModalOpen(false)}>
          <RunListBody advanceRun={advanceRun} deleteRun={deleteRun} getPlaybookName={getPlaybookName} isBusy={isBusy} runs={runs} />
        </Modal>
      ) : null}

      {taskModalOpen ? (
        <Modal title="全部任务列表" onClose={() => setTaskModalOpen(false)}>
          <TaskListBody deletePlaybook={deletePlaybook} isBusy={isBusy} playbooks={playbooks} triggerPlaybook={triggerPlaybook} />
        </Modal>
      ) : null}
    </main>
  );
}

function RunsPreview(props: {
  advanceRun: (runId: string) => void;
  deleteRun: (runId: string) => void;
  getPlaybookName: (playbookId: string) => string;
  isBusy: boolean;
  onMore: () => void;
  runs: RunRecord[];
}) {
  return (
    <section className="employeeBoardPanel">
      <PanelTitle title="运行实例" count={props.runs.length} onMore={props.runs.length > 3 ? props.onMore : undefined} />
      <RunListBody {...props} runs={props.runs.slice(0, 3)} />
    </section>
  );
}

function TasksPreview(props: {
  deletePlaybook: (id: string, name: string) => void;
  isBusy: boolean;
  onMore: () => void;
  playbooks: PlaybookRecord[];
  triggerPlaybook: (playbookId: string) => void;
}) {
  return (
    <section className="employeeBoardPanel">
      <PanelTitle title="任务列表" count={props.playbooks.length} onMore={props.playbooks.length > 3 ? props.onMore : undefined} />
      <TaskListBody {...props} playbooks={props.playbooks.slice(0, 3)} />
    </section>
  );
}

function PanelTitle({ count, onMore, title }: { count: number; onMore?: () => void; title: string }) {
  return (
    <div className="employeeBoardTitle">
      <h2>{title}</h2>
      <div className="toolActions">
        <span>{count} 条</span>
        {onMore ? (
          <button type="button" onClick={onMore}>
            查看更多
          </button>
        ) : null}
      </div>
    </div>
  );
}

function RunListBody({
  advanceRun,
  deleteRun,
  getPlaybookName,
  isBusy,
  runs,
}: {
  advanceRun: (runId: string) => void;
  deleteRun: (runId: string) => void;
  getPlaybookName: (playbookId: string) => string;
  isBusy: boolean;
  runs: RunRecord[];
}) {
  return (
    <div className="automationList employeePreviewList">
      {runs.length ? (
        runs.map((run) => (
          <article className="automationCard employeePreviewCard" key={run.id}>
            <div className="automationCardHeader">
              <h3>{getPlaybookName(run.playbook_id)}</h3>
              <button type="button" onClick={() => deleteRun(run.id)} disabled={isBusy}>
                <X aria-hidden="true" />
                删除
              </button>
            </div>
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
  );
}

function TaskListBody({
  deletePlaybook,
  isBusy,
  playbooks,
  triggerPlaybook,
}: {
  deletePlaybook: (id: string, name: string) => void;
  isBusy: boolean;
  playbooks: PlaybookRecord[];
  triggerPlaybook: (playbookId: string) => void;
}) {
  return (
    <div className="automationList employeePreviewList">
      {playbooks.length ? (
        playbooks.map((item) => (
          <article className="automationCard employeePreviewCard" key={item.id}>
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
            <button type="button" onClick={() => triggerPlaybook(item.id)} disabled={isBusy}>
              <Play aria-hidden="true" />
              触发运行
            </button>
          </article>
        ))
      ) : (
        <p className="toolEmpty">当前角色还没有长期任务。一次性任务会直接进入运行实例。</p>
      )}
    </div>
  );
}

function MonitorPanel({
  codexMonitorEvents,
  runMonitor,
  selectedRun,
}: {
  codexMonitorEvents: RunMonitorEvent[];
  runMonitor: RunMonitor | null;
  selectedRun?: RunRecord;
}) {
  if (!runMonitor) {
    return <p className="toolEmpty">推进某个运行实例后，这里会显示实时步骤和 Codex 终端信息。</p>;
  }
  return (
    <div className="employeeMonitorStack">
      <div className="automationList">
        {selectedRun?.steps.map((step, index) => (
          <article className="automationCard" key={step.id}>
            <h3>
              {index + 1}. {step.name}
            </h3>
            <div className="taskMetaGrid">
              <span>类型：{getStepTypeLabel(step.type)}</span>
              <span>状态：{step.status}</span>
            </div>
          </article>
        ))}
      </div>
      <pre className="nodeLogPre employeeMonitorPre">
        {codexMonitorEvents.length
          ? codexMonitorEvents
              .slice(-40)
              .map((event) => `[${event.time}] ${event.stream || event.type} ${event.step_name || event.step_id}\n${event.message}`)
              .join("\n\n")
          : "等待 Codex 或终端输出..."}
      </pre>
    </div>
  );
}

function NodeLogs({ selectedRun }: { selectedRun?: RunRecord }) {
  return (
    <section className="publishPanel employeeWidePanel">
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
                  <p>
                    {getStepTypeLabel(step.type)} · {step.status}
                  </p>
                </div>
              </summary>
              <div className="nodeLogBody">
                <div className="taskMetaGrid">
                  <span>节点 ID：{step.id}</span>
                  <span>审批：{step.approval_id || "无"}</span>
                  <span>读写：{[...(step.context_reads ?? []), ...(step.context_writes ?? [])].join(" / ") || "无"}</span>
                </div>
                {step.error ? <p className="nodeError">错误：{step.error}</p> : null}
                <pre className="nodeLogPre">{JSON.stringify({ config: step.config ?? {}, output: step.output ?? {} }, null, 2)}</pre>
              </div>
            </details>
          ))
        ) : (
          <p className="toolEmpty">请选择一个运行实例查看节点日志。</p>
        )}
      </div>
    </section>
  );
}

function ApprovalList({
  approvals,
  isBusy,
  resolveApproval,
}: {
  approvals: ApprovalRecord[];
  isBusy: boolean;
  resolveApproval: (approvalId: string, approved: boolean) => void;
}) {
  return (
    <section className="publishPanel employeeWidePanel">
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
    </section>
  );
}

function Modal({ children, onClose, title }: { children: React.ReactNode; onClose: () => void; title: string }) {
  return (
    <div className="modalBackdrop" role="presentation" onMouseDown={onClose}>
      <section className="modalPanel employeeModalPanel" role="dialog" aria-modal="true" aria-label={title} onMouseDown={(event) => event.stopPropagation()}>
        <div className="panelHeader">
          <ShieldCheck aria-hidden="true" />
          <h2>{title}</h2>
          <button type="button" onClick={onClose}>
            <X aria-hidden="true" />
            关闭
          </button>
        </div>
        {children}
      </section>
    </div>
  );
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
