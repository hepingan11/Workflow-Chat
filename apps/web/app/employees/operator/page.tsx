"use client";

import Link from "next/link";
import {
  ArrowLeft,
  CheckCheck,
  FileText,
  Megaphone,
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
  source: "builtin" | "dify";
  enabled: boolean;
  executable: boolean;
};

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
  unresolved_tools?: string[];
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
    type: "tool" | "human_approval" | "handoff" | "noop";
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
  steps: Array<{
    id: string;
    name: string;
    type: "tool" | "human_approval" | "handoff" | "noop";
    status: string;
    approval_id?: string | null;
    error?: string | null;
    output?: Record<string, unknown> | null;
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

export default function OperatorPage() {
  const [prompt, setPrompt] = useState("");
  const [title, setTitle] = useState("新品功能上线公告");
  const [copy, setCopy] = useState("我们准备发布一篇介绍数字员工运营控制能力的文章。");
  const [platforms, setPlatforms] = useState("公众号, 小红书, B站");
  const [materialUrl, setMaterialUrl] = useState("");
  const [result, setResult] = useState("等待提交");
  const [tools, setTools] = useState<AgentToolDefinition[]>([]);
  const [selectedToolId, setSelectedToolId] = useState("");
  const [toolInputs, setToolInputs] = useState('{\n  "topic": "今天的 AI 最新新闻"\n}');
  const [toolResult, setToolResult] = useState("等待工具执行");
  const [playbookName, setPlaybookName] = useState("AI 新闻视频日报");
  const [naturalLanguage, setNaturalLanguage] = useState(
    "对于运营：每天早上8点使用#{Ai最新新闻获取}工具获取最新的Ai新闻并整理成视频文案，使用#{视频生成}工具剪辑成视频，然后把消息发给我，我确认没问题后下午2点再使用#{抖音、小红书发布}工具发布到自媒体平台，有问题则不发布；",
  );
  const [parsedPlaybook, setParsedPlaybook] = useState<ParsedPlaybook | null>(null);
  const [playbooks, setPlaybooks] = useState<PlaybookRecord[]>([]);
  const [runs, setRuns] = useState<RunRecord[]>([]);
  const [approvals, setApprovals] = useState<ApprovalRecord[]>([]);
  const [selectedPlaybookId, setSelectedPlaybookId] = useState("");
  const [workflowStatus, setWorkflowStatus] = useState("等待编排");
  const [isBusy, setIsBusy] = useState(false);

  useEffect(() => {
    fetch("/api/operator/prompt")
      .then((response) => response.json())
      .then((data) => setPrompt(data.prompt ?? ""))
      .catch(() => setResult("无法读取提示词，请确认 API 代理或后端服务已启动。"));

    fetch("/api/agents/operator/tools")
      .then((response) => response.json())
      .then((data) => {
        const nextTools = data.tools ?? [];
        setTools(nextTools);
        const firstExecutable = nextTools.find((tool: AgentToolDefinition) => tool.source === "dify" && tool.executable);
        if (firstExecutable) {
          setSelectedToolId(firstExecutable.id);
        }
      })
      .catch(() => setToolResult("无法读取运营员工工具列表"));

    refreshAutomation();
  }, []);

  async function refreshAutomation() {
    try {
      const [playbooksResponse, runsResponse, approvalsResponse] = await Promise.all([
        fetch("/api/playbooks?role_key=operator"),
        fetch("/api/playbooks/runs"),
        fetch("/api/playbooks/approvals?role_key=operator"),
      ]);
      const playbookData = await playbooksResponse.json();
      const runsData = await runsResponse.json();
      const approvalsData = await approvalsResponse.json();
      setPlaybooks(playbookData ?? []);
      setRuns((runsData ?? []).filter((item: RunRecord) => item.role_key === "operator"));
      setApprovals(approvalsData ?? []);
      if (!selectedPlaybookId && Array.isArray(playbookData) && playbookData.length) {
        setSelectedPlaybookId(playbookData[0].id);
      }
    } catch {
      setWorkflowStatus("读取自动化任务失败");
    }
  }

  async function savePrompt() {
    setIsBusy(true);
    try {
      const response = await fetch("/api/operator/prompt", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      });
      if (!response.ok) {
        throw new Error("save failed");
      }
      setResult("提示词已保存");
    } catch {
      setResult("提示词保存失败");
    } finally {
      setIsBusy(false);
    }
  }

  async function submitPublish() {
    setIsBusy(true);
    try {
      const response = await fetch("/api/operator/publish", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title,
          copy,
          platforms: platforms
            .split(",")
            .map((item) => item.trim())
            .filter(Boolean),
          materials: materialUrl
            ? [
                {
                  name: "运营素材",
                  type: "link",
                  url: materialUrl,
                },
              ]
            : [],
          workflow_provider: "dify",
          dry_run: true,
        }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(JSON.stringify(data));
      }
      setResult(JSON.stringify(data, null, 2));
    } catch {
      setResult("发布控制请求失败");
    } finally {
      setIsBusy(false);
    }
  }

  async function executeTool() {
    if (!selectedToolId) {
      setToolResult("请先选择一个可执行工具");
      return;
    }

    setIsBusy(true);
    try {
      const inputs = JSON.parse(toolInputs);
      const response = await fetch(`/api/agents/operator/tools/${selectedToolId}/execute`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          inputs,
          user: "operator-employee-page",
        }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail ?? JSON.stringify(data));
      }
      setToolResult(JSON.stringify(data.result, null, 2));
    } catch (error) {
      setToolResult(error instanceof Error ? error.message : "工具执行失败");
    } finally {
      setIsBusy(false);
    }
  }

  async function parsePlaybook() {
    setIsBusy(true);
    try {
      const response = await fetch("/api/playbooks/parse", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          role_key: "operator",
          name: playbookName,
          natural_language: naturalLanguage,
        }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail ?? "parse failed");
      }
      setParsedPlaybook(data);
      setWorkflowStatus("已生成结构化执行计划");
    } catch (error) {
      setParsedPlaybook(null);
      setWorkflowStatus(error instanceof Error ? error.message : "任务解析失败");
    } finally {
      setIsBusy(false);
    }
  }

  async function savePlaybook() {
    setIsBusy(true);
    try {
      const response = await fetch("/api/playbooks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          role_key: "operator",
          name: playbookName,
          natural_language: naturalLanguage,
        }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail ?? "save failed");
      }
      setSelectedPlaybookId(data.id);
      setWorkflowStatus("任务剧本已保存");
      await refreshAutomation();
    } catch (error) {
      setWorkflowStatus(error instanceof Error ? error.message : "保存任务剧本失败");
    } finally {
      setIsBusy(false);
    }
  }

  async function triggerPlaybook() {
    if (!selectedPlaybookId) {
      setWorkflowStatus("请先选择一个任务剧本");
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
      await refreshAutomation();
    } catch (error) {
      setWorkflowStatus(error instanceof Error ? error.message : "触发运行失败");
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
      setWorkflowStatus(error instanceof Error ? error.message : "推进运行失败");
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
      setWorkflowStatus(error instanceof Error ? error.message : "审批操作失败");
    } finally {
      setIsBusy(false);
    }
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
            <p className="eyebrow">Operator Employee</p>
            <h1>运营员工管理</h1>
            <p className="lede">
              这里管理运营员工的整理提示词、发布工作流输入、已授权工具，以及自然语言编排的长期自动化任务。
            </p>
          </div>
          <div className="statusPanel">
            <ShieldCheck aria-hidden="true" />
            <span>{workflowStatus}</span>
          </div>
        </div>
      </section>

      <section className="operatorConsole" aria-label="运营发布控制台">
        <div className="editorPanel">
          <div className="panelHeader">
            <FileText aria-hidden="true" />
            <h2>整理提示词</h2>
            <button type="button" onClick={savePrompt} disabled={isBusy} title="保存提示词">
              <Save aria-hidden="true" />
              保存
            </button>
          </div>
          <textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} aria-label="运营整理提示词" />
        </div>

        <div className="publishPanel">
          <div className="panelHeader">
            <Megaphone aria-hidden="true" />
            <h2>发布工作流输入</h2>
            <button type="button" onClick={submitPublish} disabled={isBusy} title="生成工作流输入">
              <Play aria-hidden="true" />
              Dry Run
            </button>
          </div>
          <label>
            标题
            <input value={title} onChange={(event) => setTitle(event.target.value)} />
          </label>
          <label>
            平台
            <input value={platforms} onChange={(event) => setPlatforms(event.target.value)} />
          </label>
          <label>
            素材链接
            <input value={materialUrl} onChange={(event) => setMaterialUrl(event.target.value)} />
          </label>
          <label>
            文案
            <textarea value={copy} onChange={(event) => setCopy(event.target.value)} />
          </label>
        </div>
      </section>

      <section className="resultPanel" aria-label="执行结果">
        <h2>API 执行结果</h2>
        <pre>{result}</pre>
      </section>

      <section className="operatorConsole" aria-label="运营工具控制台">
        <div className="publishPanel">
          <div className="panelHeader">
            <Wrench aria-hidden="true" />
            <h2>运营授权工具</h2>
            <button type="button" onClick={executeTool} disabled={isBusy || !selectedToolId}>
              <Play aria-hidden="true" />
              执行工具
            </button>
          </div>
          <label>
            已授权工具
            <select value={selectedToolId} onChange={(event) => setSelectedToolId(event.target.value)}>
              <option value="">请选择工具</option>
              {tools.map((tool) => (
                <option key={tool.id} value={tool.id} disabled={!tool.executable}>
                  {tool.name} {tool.source === "builtin" ? "(内置)" : ""}
                </option>
              ))}
            </select>
          </label>
          <label>
            工具输入 JSON
            <textarea value={toolInputs} onChange={(event) => setToolInputs(event.target.value)} />
          </label>
        </div>

        <div className="resultPanel">
          <h2>工具执行结果</h2>
          <pre>{toolResult}</pre>
        </div>
      </section>

      <section className="settingsPanel">
        <div className="panelHeader">
          <ShieldCheck aria-hidden="true" />
          <h2>自然语言任务编排</h2>
          <div className="toolActions">
            <button type="button" onClick={refreshAutomation} disabled={isBusy}>
              <RefreshCcw aria-hidden="true" />
              刷新
            </button>
            <button type="button" onClick={parsePlaybook} disabled={isBusy}>
              <FileText aria-hidden="true" />
              解析
            </button>
            <button type="button" onClick={savePlaybook} disabled={isBusy}>
              <Save aria-hidden="true" />
              保存剧本
            </button>
          </div>
        </div>

        <label>
          剧本名称
          <input value={playbookName} onChange={(event) => setPlaybookName(event.target.value)} />
        </label>
        <label>
          自然语言描述
          <textarea value={naturalLanguage} onChange={(event) => setNaturalLanguage(event.target.value)} />
        </label>

        <div className="operatorConsole automationConsole">
          <div className="resultPanel">
            <h2>解析预览</h2>
            <pre>{parsedPlaybook ? JSON.stringify(parsedPlaybook, null, 2) : "等待解析"}</pre>
          </div>

          <div className="publishPanel">
            <div className="panelHeader">
              <Megaphone aria-hidden="true" />
              <h2>已保存剧本</h2>
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
              {playbooks.map((item) => (
                <article className="automationCard" key={item.id}>
                  <h3>{item.name}</h3>
                  <p>{item.natural_language}</p>
                  <code>{item.id}</code>
                </article>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="operatorConsole automationConsole" aria-label="运行与审批">
        <div className="publishPanel">
          <div className="panelHeader">
            <Play aria-hidden="true" />
            <h2>运行实例</h2>
          </div>
          <div className="automationList">
            {runs.length ? (
              runs.map((run) => (
                <article className="automationCard" key={run.id}>
                  <h3>{run.id}</h3>
                  <p>状态：{run.status}</p>
                  <p>调度时间：{run.scheduled_for}</p>
                  <button type="button" onClick={() => advanceRun(run.id)} disabled={isBusy}>
                    推进运行
                  </button>
                  <pre>{JSON.stringify(run.steps, null, 2)}</pre>
                </article>
              ))
            ) : (
              <p className="toolEmpty">还没有运行实例。</p>
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
    </main>
  );
}
