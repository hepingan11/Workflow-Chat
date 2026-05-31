"use client";

import Link from "next/link";
import { ArrowLeft, ArrowRight, RefreshCcw, Save, Settings, Wrench, X } from "lucide-react";
import { useEffect, useState } from "react";

import { employees } from "../../employees";

type ToolRecord = {
  id: string;
  name: string;
  description: string;
  provider: "dify";
  enabled: boolean;
  allowed_roles: string[];
  connection: {
    base_url: string;
    has_api_key: boolean;
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
  provider: "dify";
  enabled: boolean;
  allowed_roles: string[];
  connection: {
    base_url: string;
    api_key: string;
  };
};

const emptyForm: ToolForm = {
  name: "",
  description: "",
  provider: "dify",
  enabled: true,
  allowed_roles: [],
  connection: {
    base_url: "",
    api_key: "",
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

  function updateConnection(field: keyof ToolForm["connection"], value: string) {
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
            <h1>Dify 工具管理</h1>
            <p className="lede">
              将 Dify workflow 注册为平台工具，读取工作流元数据，并授权给指定数字员工角色使用。
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
              <input value={form.provider} readOnly />
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
              Dify Base URL
              <input
                value={form.connection.base_url}
                onChange={(event) => updateConnection("base_url", event.target.value)}
                placeholder="https://api.dify.ai/v1"
              />
            </label>
            <label>
              App API Key
              <input
                value={form.connection.api_key}
                onChange={(event) => updateConnection("api_key", event.target.value)}
                placeholder={selectedTool?.connection.has_api_key ? "留空表示保留已保存密钥" : "app-xxx"}
                type="password"
              />
            </label>
            <label>
              元数据同步
              <button type="button" onClick={syncTool} disabled={!selectedTool || busyAction !== ""}>
                <ArrowRight aria-hidden="true" />
                读取 /info 和 /parameters
              </button>
            </label>
          </div>

          <div className="toolRoles">
            <h3>授权角色</h3>
            <div className="roleChips">
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
                <h3>同步结果</h3>
                <p>应用名称：{selectedTool.meta.app_name || "未同步"}</p>
                <p>应用模式：{selectedTool.meta.app_mode || "未同步"}</p>
                <p>输入字段数：{selectedTool.meta.user_input_form.length}</p>
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
                    Workflow Inputs JSON
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
