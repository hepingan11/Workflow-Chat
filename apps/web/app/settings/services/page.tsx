"use client";

import Link from "next/link";
import { ArrowLeft, ChevronDown, Save, Settings, SlidersHorizontal } from "lucide-react";
import { useEffect, useState } from "react";

import { employees } from "../../employees";

type AiServiceFormat = "openai" | "anthropic" | "full_url";

const formatOptions: Array<{ value: AiServiceFormat; label: string }> = [
  { value: "openai", label: "OpenAI" },
  { value: "anthropic", label: "Anthropic" },
  { value: "full_url", label: "完整 URL" },
];

function getBaseUrlPlaceholder(format: AiServiceFormat) {
  if (format === "anthropic") {
    return "https://api.anthropic.com";
  }
  if (format === "full_url") {
    return "输入完整请求 URL";
  }
  return "https://api.openai.com/v1";
}

function getBaseUrlHint(format: AiServiceFormat) {
  if (format === "anthropic") {
    return "使用 Anthropic 兼容地址，通常填写 API 根地址。";
  }
  if (format === "full_url") {
    return "直接填写完整请求地址，不再依赖默认路径拼接。";
  }
  return "使用 OpenAI 兼容地址，通常填写 API 根地址。";
}

type RoleModelConfig = {
  enabled: boolean;
  format: AiServiceFormat;
  base_url: string;
  api_key: string;
  model_name: string;
};

type ModelSettingsForm = {
  global_model: {
    format: AiServiceFormat;
    base_url: string;
    api_key: string;
    model_name: string;
  };
  role_models: Record<string, RoleModelConfig>;
};

const emptyRoleConfig: RoleModelConfig = {
  enabled: false,
  format: "openai",
  base_url: "",
  api_key: "",
  model_name: "",
};

function createEmptyForm(): ModelSettingsForm {
  return {
    global_model: {
      format: "openai",
      base_url: "",
      api_key: "",
      model_name: "",
    },
    role_models: Object.fromEntries(employees.map((employee) => [employee.key, { ...emptyRoleConfig }])),
  };
}

export default function ServicesSettingsPage() {
  const [form, setForm] = useState<ModelSettingsForm>(createEmptyForm);
  const [status, setStatus] = useState("等待配置");
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [isBusy, setIsBusy] = useState(false);

  useEffect(() => {
    fetch("/api/settings/model-config")
      .then((response) => response.json())
      .then((data) => {
        setForm({
          global_model: {
            format: data.global_model?.format ?? "openai",
            base_url: data.global_model?.base_url ?? "",
            api_key: "",
            model_name: data.global_model?.model_name ?? "",
          },
          role_models: Object.fromEntries(
            employees.map((employee) => {
              const roleConfig = data.role_models?.[employee.key] ?? {};
              return [
                employee.key,
                {
                  enabled: roleConfig.enabled ?? false,
                  format: roleConfig.format ?? "openai",
                  base_url: roleConfig.base_url ?? "",
                  api_key: "",
                  model_name: roleConfig.model_name ?? "",
                },
              ];
            }),
          ),
        });
        setStatus(data.global_model?.has_api_key ? "已读取配置，密钥已隐藏" : "已读取配置");
      })
      .catch(() => setStatus("读取服务配置失败"));
  }, []);

  function updateGlobal(field: keyof ModelSettingsForm["global_model"], value: string) {
    setForm((current) => ({
      ...current,
      global_model: {
        ...current.global_model,
        [field]: value,
      },
    }));
  }

  function updateRole(key: string, patch: Partial<RoleModelConfig>) {
    setForm((current) => ({
      ...current,
      role_models: {
        ...current.role_models,
        [key]: {
          ...current.role_models[key],
          ...patch,
        },
      },
    }));
  }

  async function saveSettings() {
    setIsBusy(true);
    try {
      const response = await fetch("/api/settings/model-config", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      if (!response.ok) {
        throw new Error("save failed");
      }
      setStatus("服务配置已保存");
      setForm((current) => ({
        ...current,
        global_model: {
          ...current.global_model,
          api_key: "",
        },
        role_models: Object.fromEntries(
          Object.entries(current.role_models).map(([key, config]) => [
            key,
            {
              ...config,
              api_key: "",
            },
          ]),
        ),
      }));
    } catch {
      setStatus("保存服务配置失败");
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
            <p className="eyebrow">Service Settings</p>
            <h1>服务配置</h1>
            <p className="lede">
              配置全局 AI API，并在高级选项里为不同职位覆盖 base URL、API Key 和模型名称。
            </p>
          </div>
          <div className="statusPanel">
            <Settings aria-hidden="true" />
            <span>{status}</span>
          </div>
        </div>
      </section>

      <section className="settingsPanel" aria-label="全局模型配置">
        <div className="panelHeader">
          <Settings aria-hidden="true" />
          <h2>全局 AI API</h2>
          <button type="button" onClick={saveSettings} disabled={isBusy} title="保存服务配置">
            <Save aria-hidden="true" />
            保存
          </button>
        </div>
        <div className="settingsGrid">
          <label>
            Base URL
            <input
              value={form.global_model.base_url}
              onChange={(event) => updateGlobal("base_url", event.target.value)}
              placeholder={getBaseUrlPlaceholder(form.global_model.format)}
            />
            <small>{getBaseUrlHint(form.global_model.format)}</small>
          </label>
          <label>
            接口格式
            <select
              value={form.global_model.format}
              onChange={(event) => updateGlobal("format", event.target.value as AiServiceFormat)}
            >
              {formatOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            API Key
            <input
              value={form.global_model.api_key}
              onChange={(event) => updateGlobal("api_key", event.target.value)}
              placeholder="留空表示保留已保存密钥"
              type="password"
            />
          </label>
          <label>
            模型名称
            <input
              value={form.global_model.model_name}
              onChange={(event) => updateGlobal("model_name", event.target.value)}
              placeholder="gpt-4.1-mini"
            />
          </label>
        </div>
      </section>

      <section className="settingsPanel" aria-label="高级模型配置">
        <button
          className="advancedToggle"
          type="button"
          onClick={() => setAdvancedOpen((open) => !open)}
          aria-expanded={advancedOpen}
        >
          <SlidersHorizontal aria-hidden="true" />
          高级选项：按职位覆盖模型配置
          <ChevronDown aria-hidden="true" />
        </button>

        {advancedOpen ? (
          <div className="roleConfigGrid">
            {employees.map((employee) => {
              const roleConfig = form.role_models[employee.key] ?? emptyRoleConfig;
              const Icon = employee.icon;
              return (
                <article className="roleConfigCard" key={employee.key}>
                  <div className="cardTop">
                    <Icon aria-hidden="true" />
                    <label className="toggleLabel">
                      <input
                        checked={roleConfig.enabled}
                        onChange={(event) => updateRole(employee.key, { enabled: event.target.checked })}
                        type="checkbox"
                      />
                      启用覆盖
                    </label>
                  </div>
                  <h2>{employee.name}</h2>
                  <label>
                    接口格式
                    <select
                      value={roleConfig.format}
                      onChange={(event) => updateRole(employee.key, { format: event.target.value as AiServiceFormat })}
                    >
                      {formatOptions.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Base URL
                    <input
                      value={roleConfig.base_url}
                      onChange={(event) => updateRole(employee.key, { base_url: event.target.value })}
                      placeholder={getBaseUrlPlaceholder(roleConfig.format)}
                    />
                    <small>{getBaseUrlHint(roleConfig.format)} 留空则使用全局配置。</small>
                  </label>
                  <label>
                    API Key
                    <input
                      value={roleConfig.api_key}
                      onChange={(event) => updateRole(employee.key, { api_key: event.target.value })}
                      placeholder="留空表示保留已保存密钥"
                      type="password"
                    />
                  </label>
                  <label>
                    模型名称
                    <input
                      value={roleConfig.model_name}
                      onChange={(event) => updateRole(employee.key, { model_name: event.target.value })}
                      placeholder="留空则使用全局模型"
                    />
                  </label>
                </article>
              );
            })}
          </div>
        ) : null}
      </section>
    </main>
  );
}
