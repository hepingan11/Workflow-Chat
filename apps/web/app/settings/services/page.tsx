"use client";

import Link from "next/link";
import { ArrowLeft, Bell, ChevronDown, Save, Send, Settings, SlidersHorizontal } from "lucide-react";
import { useEffect, useState } from "react";

import { employees } from "../../employees";

type AiServiceFormat = "openai" | "openai_responses" | "anthropic" | "full_url";

const formatOptions: Array<{ value: AiServiceFormat; label: string }> = [
  { value: "openai", label: "OpenAI Chat Completions" },
  { value: "openai_responses", label: "OpenAI Responses" },
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
  if (format === "openai_responses") {
    return "填写 OpenAI Responses 兼容的 API 根地址，例如 https://api.openai.com/v1；系统会自动请求 /responses。";
  }
  if (format === "openai") {
    return "填写 OpenAI Chat Completions 兼容的 API 根地址，例如 https://api.openai.com/v1；系统会自动请求 /chat/completions。";
  }
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

type NotificationChannel = "none" | "telegram";

type NotificationSettingsForm = {
  active_channel: NotificationChannel;
  telegram: {
    enabled: boolean;
    bot_token: string;
    chat_id: string;
    api_base_url: string;
    parse_mode: string;
    message_prefix: string;
    webhook_secret_token: string;
    disable_web_page_preview: boolean;
  };
};

type BossSettingsForm = {
  preferred_name: string;
  role_profile: string;
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

function createEmptyNotificationForm(): NotificationSettingsForm {
  return {
    active_channel: "none",
    telegram: {
      enabled: false,
      bot_token: "",
      chat_id: "",
      api_base_url: "https://api.telegram.org",
      parse_mode: "HTML",
      message_prefix: "Workflow Chat",
      webhook_secret_token: "",
      disable_web_page_preview: true,
    },
  };
}

export default function ServicesSettingsPage() {
  const [form, setForm] = useState<ModelSettingsForm>(createEmptyForm);
  const [bossForm, setBossForm] = useState<BossSettingsForm>({ preferred_name: "", role_profile: "" });
  const [notificationForm, setNotificationForm] = useState<NotificationSettingsForm>(createEmptyNotificationForm);
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

    fetch("/api/settings/notification-config")
      .then((response) => response.json())
      .then((data) => {
        setNotificationForm({
          active_channel: data.active_channel ?? "none",
          telegram: {
            enabled: data.active_channel === "telegram",
            bot_token: "",
            chat_id: data.telegram?.chat_id ?? "",
            api_base_url: data.telegram?.api_base_url ?? "https://api.telegram.org",
            parse_mode: data.telegram?.parse_mode ?? "HTML",
            message_prefix: data.telegram?.message_prefix ?? "Workflow Chat",
            webhook_secret_token: "",
            disable_web_page_preview: data.telegram?.disable_web_page_preview ?? true,
          },
        });
      })
      .catch(() => setStatus("读取通知配置失败"));

    fetch("/api/settings/boss-config")
      .then((response) => response.json())
      .then((data) => {
        setBossForm({
          preferred_name: data.preferred_name ?? "",
          role_profile: data.role_profile ?? "",
        });
      })
      .catch(() => setStatus("读取老板设定失败"));
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

  function updateNotificationChannel(channel: NotificationChannel) {
    setNotificationForm((current) => ({
      ...current,
      active_channel: channel,
      telegram: {
        ...current.telegram,
        enabled: channel === "telegram",
      },
    }));
  }

  function updateBoss(field: keyof BossSettingsForm, value: string) {
    setBossForm((current) => ({
      ...current,
      [field]: value,
    }));
  }

  function updateTelegram(field: keyof NotificationSettingsForm["telegram"], value: string | boolean) {
    setNotificationForm((current) => ({
      ...current,
      telegram: {
        ...current.telegram,
        [field]: value,
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

  async function testModelConnection() {
    setIsBusy(true);
    setStatus("正在测试 AI 接口...");
    try {
      const response = await fetch("/api/settings/model-config/test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          settings: form,
        }),
      });
      const data = await response.json();
      if (!response.ok || !data.ok) {
        const extra = data.detail?.response_preview || data.detail?.error || "";
        throw new Error(extra ? `${data.message} ${extra}` : data.message ?? "模型接口测试失败");
      }
      setStatus(data.detail?.reply ? `${data.message} 返回：${data.detail.reply}` : data.message);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "模型接口测试失败");
    } finally {
      setIsBusy(false);
    }
  }

  async function saveBossSettings() {
    setIsBusy(true);
    try {
      const response = await fetch("/api/settings/boss-config", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(bossForm),
      });
      if (!response.ok) {
        throw new Error("save failed");
      }
      setStatus("老板设定已保存");
    } catch {
      setStatus("保存老板设定失败");
    } finally {
      setIsBusy(false);
    }
  }

  async function saveNotificationSettings() {
    setIsBusy(true);
    try {
      const response = await fetch("/api/settings/notification-config", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(notificationForm),
      });
      if (!response.ok) {
        throw new Error("save failed");
      }
      setStatus("通知推送配置已保存");
      setNotificationForm((current) => ({
        ...current,
        telegram: {
          ...current.telegram,
          bot_token: "",
          webhook_secret_token: "",
        },
      }));
    } catch {
      setStatus("保存通知推送配置失败");
    } finally {
      setIsBusy(false);
    }
  }

  async function testTelegramConnection() {
    setIsBusy(true);
    setStatus("正在发送 Telegram 测试消息...");
    try {
      const response = await fetch("/api/settings/notification-config/test-telegram", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(notificationForm),
      });
      const data = await response.json();
      if (!response.ok || !data.ok) {
        throw new Error(data.message ?? "Telegram 测试失败");
      }
      setStatus(data.message ?? "Telegram 测试消息已发送");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Telegram 测试失败");
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
          <button type="button" onClick={() => testModelConnection()} disabled={isBusy} title="Test global AI model">
            <Send aria-hidden="true" />
            测试接口
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

      <section className="settingsPanel" aria-label="老板设定">
        <div className="panelHeader">
          <Settings aria-hidden="true" />
          <h2>老板设定</h2>
          <button type="button" onClick={saveBossSettings} disabled={isBusy} title="保存老板设定">
            <Save aria-hidden="true" />
            保存设定
          </button>
        </div>
        <p className="settingsIntro">
          数字员工在向你汇报、推送消息时，会参考这里的称呼和角色设定来组织表达。
        </p>
        <div className="settingsGrid bossSettingsGrid">
          <label>
            怎么称呼您
            <input
              value={bossForm.preferred_name}
              onChange={(event) => updateBoss("preferred_name", event.target.value)}
              placeholder="例如：平安、老板、何总"
            />
          </label>
          <label className="wideField">
            您的角色设定
            <textarea
              value={bossForm.role_profile}
              onChange={(event) => updateBoss("role_profile", event.target.value)}
              placeholder="例如：我是这个项目的负责人，偏好简洁结论、风险提醒和下一步建议。"
            />
          </label>
        </div>
      </section>

      <section className="settingsPanel" aria-label="通知推送配置">
        <div className="panelHeader">
          <Bell aria-hidden="true" />
          <h2>通知推送配置</h2>
          <button type="button" onClick={saveNotificationSettings} disabled={isBusy} title="保存通知推送配置">
            <Save aria-hidden="true" />
            保存通知
          </button>
          {notificationForm.active_channel === "telegram" ? (
            <button type="button" onClick={testTelegramConnection} disabled={isBusy} title="发送 Telegram 测试消息">
              <Send aria-hidden="true" />
              测试连接
            </button>
          ) : null}
        </div>

        <p className="settingsIntro">
          审批节点创建后，会通过这里选择的通讯工具把确认消息推送给你。当前一次只能选择一种通讯工具。
        </p>

        <div className="notificationChannelGrid" role="radiogroup" aria-label="通知推送渠道">
          <label className="notificationChannelCard">
            <input
              checked={notificationForm.active_channel === "none"}
              name="notification-channel"
              onChange={() => updateNotificationChannel("none")}
              type="radio"
            />
            <span>
              <strong>不启用</strong>
              <small>只在系统内生成审批记录，不主动推送消息。</small>
            </span>
          </label>
          <label className="notificationChannelCard">
            <input
              checked={notificationForm.active_channel === "telegram"}
              name="notification-channel"
              onChange={() => updateNotificationChannel("telegram")}
              type="radio"
            />
            <span>
              <strong>Telegram</strong>
              <small>通过 Telegram Bot API 发送审批确认消息。</small>
            </span>
          </label>
        </div>

        {notificationForm.active_channel === "telegram" ? (
          <div className="settingsGrid notificationSettingsGrid">
            <label>
              Bot Token
              <input
                value={notificationForm.telegram.bot_token}
                onChange={(event) => updateTelegram("bot_token", event.target.value)}
                placeholder="留空表示保留已保存 Token，例如 123456:ABC-DEF..."
                type="password"
              />
              <small>从 Telegram 的 BotFather 创建 Bot 后获取。</small>
            </label>
            <label>
              Chat ID
              <input
                value={notificationForm.telegram.chat_id}
                onChange={(event) => updateTelegram("chat_id", event.target.value)}
                placeholder="例如 123456789 或 -1001234567890"
              />
              <small>支持个人、群组或频道 Chat ID。</small>
            </label>
            <label>
              API Base URL
              <input
                value={notificationForm.telegram.api_base_url}
                onChange={(event) => updateTelegram("api_base_url", event.target.value)}
                placeholder="https://api.telegram.org"
              />
              <small>默认使用官方 Telegram Bot API 地址。</small>
            </label>
            <label>
              Parse Mode
              <select
                value={notificationForm.telegram.parse_mode}
                onChange={(event) => updateTelegram("parse_mode", event.target.value)}
              >
                <option value="HTML">HTML</option>
                <option value="MarkdownV2">MarkdownV2</option>
                <option value="">纯文本</option>
              </select>
            </label>
            <label>
              消息前缀
              <input
                value={notificationForm.telegram.message_prefix}
                onChange={(event) => updateTelegram("message_prefix", event.target.value)}
                placeholder="Workflow Chat"
              />
            </label>
            <label>
              Webhook Secret Token
              <input
                value={notificationForm.telegram.webhook_secret_token}
                onChange={(event) => updateTelegram("webhook_secret_token", event.target.value)}
                placeholder="留空表示保留已保存 Secret"
                type="password"
              />
              <small>用于校验 Telegram 回调请求头 X-Telegram-Bot-Api-Secret-Token。</small>
            </label>
            <label className="toggleCard">
              <span className="toggleLabel">
                <input
                  checked={notificationForm.telegram.disable_web_page_preview}
                  onChange={(event) => updateTelegram("disable_web_page_preview", event.target.checked)}
                  type="checkbox"
                />
                禁用链接预览
              </span>
            </label>
            <div className="settingsHintCard">
              Telegram Webhook 地址通常配置为：
              <code>/telegram/webhook</code>
              。部署后请在 Bot API 的 setWebhook 中填写你的公网 API 地址。
            </div>
          </div>
        ) : (
          <div className="emptyInlineNotice">
            <Send aria-hidden="true" />
            <span>当前未启用外部通知。审批消息仍会保存在系统审批列表里。</span>
          </div>
        )}
      </section>
    </main>
  );
}
