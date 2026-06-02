"use client";

import Link from "next/link";
import { ArrowLeft, ArrowRight, RefreshCcw, Save, Settings, Wrench, X } from "lucide-react";
import { useEffect, useState } from "react";

import { employees } from "../../employees";

type ToolRecord = {
  id: string;
  name: string;
  description: string;
  provider: ToolProvider;
  enabled: boolean;
  allowed_roles: string[];
  connection: {
    base_url: string;
    has_api_key: boolean;
    model: string;
    endpoint_path: string;
    mcp_tool_name: string;
    timeout_seconds: number;
  };
  meta: {
    app_name: string;
    app_description: string;
    app_mode: string;
    user_input_form: Array<Record<string, unknown>>;
  };
  updated_at: string | null;
};

type ToolForm = {
  name: string;
  description: string;
  provider: ToolProvider;
  enabled: boolean;
  allowed_roles: string[];
  connection: {
    base_url: string;
    api_key: string;
    model: string;
    endpoint_path: string;
    mcp_tool_name: string;
    timeout_seconds: number;
  };
};

type ToolProvider = "dify" | "codex" | "mcp";

const emptyForm: ToolForm = {
  name: "",
  description: "",
  provider: "dify",
  enabled: true,
  allowed_roles: [],
  connection: {
    base_url: "",
    api_key: "",
    model: "",
    endpoint_path: "",
    mcp_tool_name: "",
    timeout_seconds: 60,
  },
};

export default function ToolsSettingsPage() {
  const [tools, setTools] = useState<ToolRecord[]>([]);
  const [selectedToolId, setSelectedToolId] = useState<string | null>(null);
  const [form, setForm] = useState<ToolForm>(emptyForm);
  const [status, setStatus] = useState("等待配置工具");
  const [busyAction, setBusyAction] = useState<string>("");
  const [testPayload, setTestPayload] = useState("{\n  \n}");
  const [testResult, setTestResult] = useState("");

  const selectedTool = tools.find((tool) => tool.id === selectedToolId) ?? null;

  useEffect(() => {
    loadTools();
  }, []);

  function fillForm(tool?: ToolRecord | null) {
    if (!tool) {
      setForm(emptyForm);
      return;
    }

    setForm({
      name: tool.name,
      description: tool.description,
      provider: tool.provider,
      enabled: tool.enabled,
      allowed_roles: tool.allowed_roles,
      connection: {
        base_url: tool.connection.base_url,
        api_key: "",
        model: tool.connection.model,
        endpoint_path: tool.connection.endpoint_path,
        mcp_tool_name: tool.connection.mcp_tool_name,
        timeout_seconds: tool.connection.timeout_seconds,
      },
    });
  }

  async function loadTools() {
    setBusyAction("load");
    try {
      const response = await fetch("/api/tools");
      const data = await response.json();
      setTools(data.tools ?? []);
      setStatus("已读取工具配置");
    } catch {
      setStatus("读取工具配置失败");
    } finally {
      setBusyAction("");
    }
  }

  function selectTool(tool: ToolRecord | null) {
    setSelectedToolId(tool?.id ?? null);
    fillForm(tool);
    setTestResult("");
  }

  function updateForm<K extends keyof ToolForm>(field: K, value: ToolForm[K]) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function updateProvider(provider: ToolProvider) {
    setForm((current) => ({
      ...current,
      provider,
      connection: {
        ...current.connection,
        endpoint_path: getDefaultEndpointPath(provider, current.connection.endpoint_path),
        timeout_seconds: current.connection.timeout_seconds || 60,
      },
    }));
    setTestPayload(getDefaultTestPayload(provider));
  }

  function updateConnection(field: keyof ToolForm["connection"], value: string | number) {
    setForm((current) => ({
      ...current,
      connection: {
        ...current.connection,
        [field]: value,
      },
    }));
  }

  function toggleRole(roleKey: string) {
    setForm((current) => ({
      ...current,
      allowed_roles: current.allowed_roles.includes(roleKey)
        ? current.allowed_roles.filter((key) => key !== roleKey)
        : [...current.allowed_roles, roleKey],
    }));
  }

  function toggleAllRoles() {
    setForm((current) => {
      const allRoleKeys = employees.map((employee) => employee.key);
      const hasAllRoles = allRoleKeys.every((key) => current.allowed_roles.includes(key));
      return {
        ...current,
        allowed_roles: hasAllRoles ? [] : allRoleKeys,
      };
    });
  }

  async function saveTool() {
    const method = selectedTool ? "PUT" : "POST";
    const url = selectedTool ? `/api/tools/${selectedTool.id}` : "/api/tools";

    setBusyAction("save");
    try {
      const response = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail ?? "save failed");
      }

      if (selectedTool) {
        setTools((current) => current.map((tool) => (tool.id === data.id ? data : tool)));
        selectTool(data);
      } else {
        setTools((current) => [...current, data]);
        selectTool(data);
      }
      setStatus("工具已保存");
    } catch {
      setStatus("保存工具失败");
    } finally {
      setBusyAction("");
    }
  }

  async function syncTool() {
    if (!selectedTool) {
      return;
    }

    setBusyAction("sync");
    try {
      const response = await fetch(`/api/tools/${selectedTool.id}/sync`, {
        method: "POST",
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail ?? "sync failed");
      }

      const nextTool = data.tool as ToolRecord;
      setTools((current) => current.map((tool) => (tool.id === nextTool.id ? nextTool : tool)));
      selectTool(nextTool);
      setStatus(`工具已同步：${data.synced_fields.join("、")}`);
    } catch {
      setStatus("同步工具失败");
    } finally {
      setBusyAction("");
    }
  }

  async function deleteSelectedTool() {
    if (!selectedTool) {
      return;
    }

    setBusyAction("delete");
    try {
      const response = await fetch(`/api/tools/${selectedTool.id}`, {
        method: "DELETE",
      });
      if (!response.ok) {
        throw new Error("delete failed");
      }
      setTools((current) => current.filter((tool) => tool.id !== selectedTool.id));
      selectTool(null);
      setStatus("工具已删除");
    } catch {
      setStatus("删除工具失败");
    } finally {
      setBusyAction("");
    }
  }

  async function testRunTool() {
    if (!selectedTool) {
      return;
    }

    setBusyAction("test");
    setTestResult("");
    try {
      const inputs = JSON.parse(testPayload);
      const response = await fetch(`/api/tools/${selectedTool.id}/test-run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          inputs,
          user: "workflow-chat-tools-page",
        }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail ?? "test failed");
      }
      setTestResult(JSON.stringify(data.result, null, 2));
      setStatus("测试执行完成");
    } catch (error) {
      setTestResult(error instanceof Error ? error.message : "测试执行失败");
      setStatus("测试执行失败");
    } finally {
      setBusyAction("");
    }
  }

  function getDefaultEndpointPath(provider: ToolProvider, currentPath: string) {
    if (currentPath) {
      return currentPath;
    }
    if (provider === "codex") {
      return "/responses";
    }
    if (provider === "mcp") {
      return "/mcp";
    }
    return "";
  }

  function getDefaultTestPayload(provider: ToolProvider) {
    if (provider === "codex") {
      return '{\n  "prompt": "请总结今天适合运营关注的 AI 新闻。"\n}';
    }
    if (provider === "mcp") {
      return '{\n  "query": "请获取今天适合运营关注的 AI 新闻"\n}';
    }
    return "{\n  \n}";
  }

  const providerLabel = form.provider === "codex" ? "Codex" : form.provider === "mcp" ? "MCP" : "Dify";

  return (
    <main className="shell">
      <section className="employeeHero">
        <Link className="backLink" href="/">
          <ArrowLeft aria-hidden="true" />
          返回首页
        </Link>
        <div className="employeeHeroGrid">
          <div>
            <p className="eyebrow">Tool Registry</p>
            <h1>工具管理</h1>
            <p className="lede">
              将 Dify workflow、Codex API 或 MCP 工具注册为平台能力，并授权给指定数字员工角色使用。
            </p>
          </div>
          <div className="statusPanel">
            <Settings aria-hidden="true" />
            <span>{status}</span>
          </div>
        </div>
      </section>

      <section className="toolWorkbench">
        <aside className="toolListPanel">
          <div className="panelHeader">
            <Wrench aria-hidden="true" />
            <h2>工具列表</h2>
            <button type="button" onClick={() => selectTool(null)}>
              新增
            </button>
          </div>

          <div className="toolList">
            {tools.length ? (
              tools.map((tool) => (
                <button
                  key={tool.id}
                  type="button"
                  className={`toolListItem${tool.id === selectedToolId ? " is-active" : ""}`}
                  onClick={() => selectTool(tool)}
                >
                  <span>{tool.name}</span>
                  <small>{tool.meta.app_mode || tool.provider}</small>
                </button>
              ))
            ) : (
              <p className="toolEmpty">还没有注册工具。</p>
            )}
          </div>
        </aside>

        <section className="settingsPanel">
          <div className="panelHeader">
            <Settings aria-hidden="true" />
            <h2>{selectedTool ? "编辑工具" : "新增工具"}</h2>
            <div className="toolActions">
              <button type="button" onClick={loadTools} disabled={busyAction !== ""}>
                <RefreshCcw aria-hidden="true" />
                刷新
              </button>
              {selectedTool ? (
                <button type="button" onClick={deleteSelectedTool} disabled={busyAction !== ""}>
                  <X aria-hidden="true" />
                  删除
                </button>
              ) : null}
              <button type="button" onClick={saveTool} disabled={busyAction !== ""}>
                <Save aria-hidden="true" />
                保存
              </button>
            </div>
          </div>

          <div className="settingsGrid toolSettingsGrid">
            <label>
              工具名称
              <input value={form.name} onChange={(event) => updateForm("name", event.target.value)} />
            </label>
            <label>
              Provider
              <select value={form.provider} onChange={(event) => updateProvider(event.target.value as ToolProvider)}>
                <option value="dify">Dify Workflow</option>
                <option value="codex">Codex API</option>
                <option value="mcp">MCP Tool</option>
              </select>
            </label>
            <label className="toggleLabel toggleCard">
              <input
                checked={form.enabled}
                onChange={(event) => updateForm("enabled", event.target.checked)}
                type="checkbox"
              />
              启用工具
            </label>
          </div>

          <label>
            工具说明
            <textarea value={form.description} onChange={(event) => updateForm("description", event.target.value)} />
          </label>

          <div className="settingsGrid toolSettingsGrid">
            <label>
              {providerLabel} Base URL
              <input
                value={form.connection.base_url}
                onChange={(event) => updateConnection("base_url", event.target.value)}
                placeholder={
                  form.provider === "codex"
                    ? "https://api.openai.com/v1"
                    : form.provider === "mcp"
                      ? "http://127.0.0.1:3001"
                      : "https://api.dify.ai/v1"
                }
              />
            </label>
            <label>
              {form.provider === "mcp" ? "API Key / Token（可选）" : "API Key"}
              <input
                value={form.connection.api_key}
                onChange={(event) => updateConnection("api_key", event.target.value)}
                placeholder={
                  selectedTool?.connection.has_api_key
                    ? "留空表示保留已保存密钥"
                    : form.provider === "codex"
                      ? "sk-xxx"
                      : form.provider === "mcp"
                        ? "Bearer token，可留空"
                        : "app-xxx"
                }
                type="password"
              />
            </label>
            {form.provider === "dify" ? (
              <label>
                元数据同步
                <button type="button" onClick={syncTool} disabled={!selectedTool || busyAction !== ""}>
                  <ArrowRight aria-hidden="true" />
                  读取 /info 和 /parameters
                </button>
              </label>
            ) : form.provider === "codex" ? (
              <label>
                模型名称
                <input
                  value={form.connection.model}
                  onChange={(event) => updateConnection("model", event.target.value)}
                  placeholder="gpt-5.1-codex 或兼容模型名"
                />
              </label>
            ) : (
              <label>
                MCP Tool Name
                <input
                  value={form.connection.mcp_tool_name}
                  onChange={(event) => updateConnection("mcp_tool_name", event.target.value)}
                  placeholder="服务端 tools/list 中的工具名，留空使用工具名称"
                />
              </label>
            )}
          </div>

          {form.provider === "codex" || form.provider === "mcp" ? (
            <div className="settingsGrid toolSettingsGrid">
              <label>
                Endpoint Path
                <input
                  value={form.connection.endpoint_path}
                  onChange={(event) => updateConnection("endpoint_path", event.target.value)}
                  placeholder={form.provider === "mcp" ? "/mcp" : "/responses"}
                />
              </label>
              <label>
                请求超时（秒）
                <input
                  min={5}
                  value={form.connection.timeout_seconds}
                  onChange={(event) => updateConnection("timeout_seconds", Number(event.target.value) || 60)}
                  type="number"
                />
              </label>
              <div className="settingsHintCard">
                {form.provider === "mcp" ? (
                  <>
                    MCP 工具会按 JSON-RPC 调用：
                    <code>tools/call</code>
                    <code>name</code>
                    <code>arguments</code>
                  </>
                ) : (
                  <>
                    Codex 工具会按 OpenAI Responses 兼容格式发送：
                    <code>model</code>
                    <code>input</code>
                    <code>metadata</code>
                  </>
                )}
              </div>
            </div>
          ) : null}

          <div className="toolRoles">
            <h3>授权角色</h3>
            <div className="roleChips">
              <label className="roleChip roleChipAll">
                <input
                  checked={employees.every((employee) => form.allowed_roles.includes(employee.key))}
                  onChange={toggleAllRoles}
                  type="checkbox"
                />
                <span>全部</span>
              </label>
              {employees.map((employee) => (
                <label className="roleChip" key={employee.key}>
                  <input
                    checked={form.allowed_roles.includes(employee.key)}
                    onChange={() => toggleRole(employee.key)}
                    type="checkbox"
                  />
                  <span>{employee.name}</span>
                </label>
              ))}
            </div>
          </div>

          {selectedTool ? (
            <>
              <div className="toolMetaPanel">
                <h3>{selectedTool.provider === "dify" ? "同步结果" : "连接配置"}</h3>
                {selectedTool.provider === "dify" ? (
                  <>
                    <p>应用名称：{selectedTool.meta.app_name || "未同步"}</p>
                    <p>应用模式：{selectedTool.meta.app_mode || "未同步"}</p>
                    <p>输入字段数：{selectedTool.meta.user_input_form.length}</p>
                  </>
                ) : (
                  <>
                    {selectedTool.provider === "mcp" ? (
                      <p>MCP 工具名：{selectedTool.connection.mcp_tool_name || selectedTool.name}</p>
                    ) : (
                      <p>模型名称：{selectedTool.connection.model || "未填写"}</p>
                    )}
                    <p>接口路径：{selectedTool.connection.endpoint_path || (selectedTool.provider === "mcp" ? "/mcp" : "/responses")}</p>
                    <p>超时时间：{selectedTool.connection.timeout_seconds} 秒</p>
                  </>
                )}
              </div>

              <div className="operatorConsole toolTestConsole">
                <section className="editorPanel">
                  <div className="panelHeader">
                    <Wrench aria-hidden="true" />
                    <h2>测试输入</h2>
                    <button type="button" onClick={testRunTool} disabled={busyAction !== ""}>
                      运行测试
                    </button>
                  </div>
                  <label>
                    {selectedTool.provider === "codex"
                      ? "Codex Inputs JSON"
                      : selectedTool.provider === "mcp"
                        ? "MCP Arguments JSON"
                        : "Workflow Inputs JSON"}
                    <textarea value={testPayload} onChange={(event) => setTestPayload(event.target.value)} />
                  </label>
                </section>

                <section className="resultPanel">
                  <h2>执行结果</h2>
                  <pre>{testResult || "等待测试执行"}</pre>
                </section>
              </div>
            </>
          ) : null}
        </section>
      </section>
    </main>
  );
}
