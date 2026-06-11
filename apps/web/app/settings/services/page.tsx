"use client";

import Link from "next/link";
import { ArrowLeft, Bell, ChevronDown, Database, Save, Send, Settings, SlidersHorizontal } from "lucide-react";
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

type NotificationChannel = "none" | "telegram" | "weixin_bot";

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
  weixin_bot: {
    enabled: boolean;
    user_id: string;
    target_user_id: string;
    message_prefix: string;
    timeout_seconds: number;
  };
};

type BossSettingsForm = {
  preferred_name: string;
  role_profile: string;
};

type MemoryStorageForm = {
  sqlite_path: string;
  markdown_dir: string;
};

type ToastState = {
  message: string;
  tone: "info" | "success" | "error";
};

type WeixinLoginState = {
  open: boolean;
  sessionId: string;
  status: string;
  qrStatus: string;
  qrDataUrl: string;
  userId: string;
  message: string;
  error: string;
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
    weixin_bot: {
      enabled: false,
      user_id: "",
      target_user_id: "",
      message_prefix: "Workflow Chat",
      timeout_seconds: 8,
    },
  };
}

export default function ServicesSettingsPage() {
  const [form, setForm] = useState<ModelSettingsForm>(createEmptyForm);
  const [bossForm, setBossForm] = useState<BossSettingsForm>({ preferred_name: "", role_profile: "" });
  const [notificationForm, setNotificationForm] = useState<NotificationSettingsForm>(createEmptyNotificationForm);
  const [memoryForm, setMemoryForm] = useState<MemoryStorageForm>({
    sqlite_path: ".workflow-chat/memory.db",
    markdown_dir: ".workflow-chat/memories",
  });
  const [status, setStatus] = useState("等待配置");
  const [toast, setToast] = useState<ToastState | null>(null);
  const [weixinLogin, setWeixinLogin] = useState<WeixinLoginState>({
    open: false,
    sessionId: "",
    status: "",
    qrStatus: "",
    qrDataUrl: "",
    userId: "",
    message: "",
    error: "",
  });
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [isBusy, setIsBusy] = useState(false);

  useEffect(() => {
    if (!toast) {
      return;
    }
    const timer = window.setTimeout(() => setToast(null), toast.tone === "error" ? 5200 : 3600);
    return () => window.clearTimeout(timer);
  }, [toast]);

  useEffect(() => {
    if (!weixinLogin.open || !weixinLogin.sessionId || weixinLogin.status === "confirmed" || weixinLogin.status === "failed") {
      return;
    }

    const timer = window.setInterval(async () => {
      try {
        const response = await fetch(`/api/settings/notification-config/weixin-bot-login/${weixinLogin.sessionId}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(notificationForm),
        });
        const data = await response.json();
        const errorMessage = !response.ok || !data.ok ? getApiErrorMessage(data, "读取微信登录状态失败") : "";
        setWeixinLogin((current) => ({
          ...current,
          status: data.status ?? current.status,
          qrStatus: data.qr_status ?? current.qrStatus,
          qrDataUrl: data.qr_data_url ?? current.qrDataUrl,
          userId: data.user_id ?? current.userId,
          message: data.message ?? current.message,
          error: errorMessage || data.error || data.detail?.error_detail?.message || "",
        }));
        if (data.user_id) {
          setNotificationForm((current) => ({
            ...current,
            weixin_bot: {
              ...current.weixin_bot,
              user_id: data.user_id,
            },
          }));
        }
        if (data.status === "confirmed") {
          notify("微信 Bot 登录成功", "success");
        }
        if (errorMessage || data.status === "failed") {
          notify(errorMessage || data.error || data.detail?.error_detail?.message || "微信 Bot 登录失败", "error");
        }
      } catch (error) {
        setWeixinLogin((current) => ({
          ...current,
          error: error instanceof Error ? error.message : "读取微信登录状态失败",
        }));
      }
    }, 1500);

    return () => window.clearInterval(timer);
  }, [notificationForm, weixinLogin.open, weixinLogin.sessionId, weixinLogin.status]);

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
          weixin_bot: {
            enabled: data.active_channel === "weixin_bot",
            user_id: data.weixin_bot?.user_id ?? "",
            target_user_id: data.weixin_bot?.target_user_id ?? "",
            message_prefix: data.weixin_bot?.message_prefix ?? "Workflow Chat",
            timeout_seconds: data.weixin_bot?.timeout_seconds ?? 8,
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

    fetch("/api/settings/memory-storage-config")
      .then((response) => response.json())
      .then((data) => {
        setMemoryForm({
          sqlite_path: data.sqlite_path ?? ".workflow-chat/memory.db",
          markdown_dir: data.markdown_dir ?? ".workflow-chat/memories",
        });
      })
      .catch(() => setStatus("读取长期记忆配置失败"));
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
      weixin_bot: {
        ...current.weixin_bot,
        enabled: channel === "weixin_bot",
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

  function updateWeixinBot(field: keyof NotificationSettingsForm["weixin_bot"], value: string | number | boolean) {
    setNotificationForm((current) => ({
      ...current,
      weixin_bot: {
        ...current.weixin_bot,
        [field]: value,
      },
    }));
  }

  function updateMemory(field: keyof MemoryStorageForm, value: string) {
    setMemoryForm((current) => ({
      ...current,
      [field]: value,
    }));
  }

  function notify(message: string, tone: ToastState["tone"] = "info") {
    setToast({ message, tone });
  }

  function getApiErrorMessage(data: unknown, fallback: string) {
    if (!data || typeof data !== "object") {
      return fallback;
    }

    const payload = data as {
      message?: unknown;
      detail?: {
        error?: unknown;
        response?: {
          message?: unknown;
          stdout?: unknown;
          stderr?: unknown;
        };
        url?: unknown;
        status_code?: unknown;
        response_preview?: unknown;
      };
    };
    const message = typeof payload.message === "string" && payload.message ? payload.message : fallback;
    const detail = payload.detail ?? {};
    const parts = [
      typeof detail.status_code === "number" ? `HTTP ${detail.status_code}` : "",
      typeof detail.url === "string" && detail.url ? `URL: ${detail.url}` : "",
      typeof detail.response_preview === "string" && detail.response_preview ? `返回: ${detail.response_preview}` : "",
      typeof detail.error === "string" && detail.error ? `错误: ${detail.error}` : "",
      typeof detail.response?.message === "string" && detail.response.message ? detail.response.message : "",
      typeof detail.response?.stderr === "string" && detail.response.stderr ? `stderr: ${detail.response.stderr}` : "",
      typeof detail.response?.stdout === "string" && detail.response.stdout ? `stdout: ${detail.response.stdout}` : "",
    ].filter(Boolean);

    return parts.length ? `${message} ${parts.join(" | ")}` : message;
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
      notify("服务配置已保存", "success");
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
      notify("保存服务配置失败", "error");
    } finally {
      setIsBusy(false);
    }
  }

  async function testModelConnection() {
    setIsBusy(true);
    notify("正在测试 AI 接口...", "info");
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
      notify(data.detail?.reply ? `${data.message} 返回：${data.detail.reply}` : data.message, "success");
    } catch (error) {
      notify(error instanceof Error ? error.message : "模型接口测试失败", "error");
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
      notify("老板设定已保存", "success");
    } catch {
      setStatus("保存老板设定失败");
      notify("保存老板设定失败", "error");
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
      notify("通知推送配置已保存", "success");
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
      notify("保存通知推送配置失败", "error");
    } finally {
      setIsBusy(false);
    }
  }

  async function testTelegramConnection() {
    setIsBusy(true);
    notify("正在发送 Telegram 测试消息...", "info");
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
      notify(data.message ?? "Telegram 测试消息已发送", "success");
    } catch (error) {
      notify(error instanceof Error ? error.message : "Telegram 测试失败", "error");
    } finally {
      setIsBusy(false);
    }
  }

  async function testWeixinBotConnection() {
    setIsBusy(true);
    notify("正在通过 integrations/weixinProxy 发送微信测试消息...", "info");
    try {
      const response = await fetch("/api/settings/notification-config/test-weixin-bot", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(notificationForm),
      });
      const data = await response.json();
      if (!response.ok || !data.ok) {
        throw new Error(getApiErrorMessage(data, "微信 Bot 测试失败"));
      }
      notify(data.message ?? "微信 Bot 测试消息已发送", "success");
    } catch (error) {
      notify(error instanceof Error ? error.message : "微信 Bot 测试失败", "error");
    } finally {
      setIsBusy(false);
    }
  }

  async function startWeixinBotListen() {
    setIsBusy(true);
    notify("正在启动 integrations/weixinProxy listen...", "info");
    try {
      const response = await fetch("/api/settings/notification-config/weixin-bot-listen/start", {
        method: "POST",
      });
      const data = await response.json();
      if (!response.ok || !data.ok) {
        throw new Error(getApiErrorMessage(data, "微信 Bot 监听启动失败"));
      }
      notify(data.message ?? "weixinProxy listen 已启动", "success");
    } catch (error) {
      notify(error instanceof Error ? error.message : "微信 Bot 监听启动失败", "error");
    } finally {
      setIsBusy(false);
    }
  }

  async function syncWeixinBotTarget() {
    setIsBusy(true);
    notify("正在同步微信推送目标...", "info");
    try {
      const response = await fetch("/api/settings/notification-config/weixin-bot-target/sync", {
        method: "POST",
      });
      const data = await response.json();
      if (!response.ok || !data.ok) {
        throw new Error(getApiErrorMessage(data, "微信推送目标同步失败"));
      }
      const targetUserId = data.detail?.target_user_id ?? "";
      if (targetUserId) {
        setNotificationForm((current) => ({
          ...current,
          weixin_bot: {
            ...current.weixin_bot,
            target_user_id: targetUserId,
          },
        }));
      }
      notify(data.message ?? "微信推送目标已同步", "success");
    } catch (error) {
      notify(error instanceof Error ? error.message : "微信推送目标同步失败", "error");
    } finally {
      setIsBusy(false);
    }
  }

  async function startWeixinBotLogin() {
    setIsBusy(true);
    notify("正在生成微信登录二维码...", "info");
    setWeixinLogin({
      open: true,
      sessionId: "",
      status: "pending",
      qrStatus: "",
      qrDataUrl: "",
      userId: "",
      message: "正在生成二维码...",
      error: "",
    });
    try {
      const response = await fetch("/api/settings/notification-config/weixin-bot-login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(notificationForm),
      });
      const data = await response.json();
      if (!response.ok || !data.ok) {
        throw new Error(getApiErrorMessage(data, "微信登录二维码生成失败"));
      }
      setWeixinLogin((current) => ({
        ...current,
        sessionId: data.session_id,
        status: data.detail?.status ?? "running",
        message: data.message || "二维码会在稍后显示，请准备扫码。",
      }));
    } catch (error) {
      setWeixinLogin((current) => ({
        ...current,
        status: "failed",
        error: error instanceof Error ? error.message : "微信登录二维码生成失败",
        message: "微信登录二维码生成失败",
      }));
      notify(error instanceof Error ? error.message : "微信登录二维码生成失败", "error");
    } finally {
      setIsBusy(false);
    }
  }

  async function saveMemoryStorageSettings() {
    setIsBusy(true);
    try {
      const response = await fetch("/api/settings/memory-storage-config", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sqlite_path: memoryForm.sqlite_path,
          markdown_dir: memoryForm.markdown_dir,
        }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail ?? "save failed");
      }
      setMemoryForm({
        sqlite_path: data.sqlite_path ?? ".workflow-chat/memory.db",
        markdown_dir: data.markdown_dir ?? ".workflow-chat/memories",
      });
      setStatus("长期记忆配置已保存");
      notify("长期记忆配置已保存", "success");
    } catch {
      setStatus("保存长期记忆配置失败");
      notify("保存长期记忆配置失败", "error");
    } finally {
      setIsBusy(false);
    }
  }

  async function testMemoryStorageConnection() {
    setIsBusy(true);
    notify("正在测试 SQLite 记忆库...", "info");
    try {
      const response = await fetch("/api/settings/memory-storage-config/test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sqlite_path: memoryForm.sqlite_path,
          markdown_dir: memoryForm.markdown_dir,
        }),
      });
      const data = await response.json();
      if (!response.ok || !data.ok) {
        throw new Error(data.message ?? "SQLite 测试失败");
      }
      notify(data.message ?? "SQLite 记忆库连接成功", "success");
    } catch (error) {
      notify(error instanceof Error ? error.message : "SQLite 测试失败", "error");
    } finally {
      setIsBusy(false);
    }
  }

  return (
    <main className="shell">
      {toast ? (
        <div className="settingsToast" data-tone={toast.tone} role="status" aria-live="polite">
          <span>{toast.tone === "success" ? "完成" : toast.tone === "error" ? "出错" : "处理中"}</span>
          <p>{toast.message}</p>
        </div>
      ) : null}

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

      <section className="settingsPanel" aria-label="长期记忆数据库配置">
        <div className="panelHeader">
          <Database aria-hidden="true" />
          <h2>长期记忆数据库</h2>
          <button type="button" onClick={saveMemoryStorageSettings} disabled={isBusy} title="保存长期记忆配置">
            <Save aria-hidden="true" />
            保存记忆配置
          </button>
          <button type="button" onClick={testMemoryStorageConnection} disabled={isBusy} title="测试 SQLite 记忆库">
            <Send aria-hidden="true" />
            测试连接
          </button>
        </div>
        <p className="settingsIntro">
          每个数字员工的长期记忆会写入本地 SQLite 结构化索引，同时归档为 Markdown，方便人工查看和编辑。无需任何外部数据库服务。
        </p>
        <div className="settingsGrid bossSettingsGrid">
          <label className="wideField">
            SQLite 数据库路径
            <input
              value={memoryForm.sqlite_path}
              onChange={(event) => updateMemory("sqlite_path", event.target.value)}
              placeholder=".workflow-chat/memory.db"
            />
            <small>
              本地单文件数据库，提供按相关度排序的 top-N 检索。相对路径以项目根目录为基准，留空使用默认 `.workflow-chat/memory.db`。
            </small>
          </label>
          <label>
            Markdown 记忆目录
            <input
              value={memoryForm.markdown_dir}
              onChange={(event) => updateMemory("markdown_dir", event.target.value)}
              placeholder=".workflow-chat/memories"
            />
            <small>Markdown 是可读、可人工编辑的记忆主存；SQLite 仅作为检索索引。</small>
          </label>
          <div className="settingsHintCard">
            保存后任务完成会自动复盘：
            <code>agent_task_memories</code>
            <code>agent_memories</code>
            <code>.md</code>
          </div>
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
          {notificationForm.active_channel === "weixin_bot" ? (
            <button type="button" onClick={testWeixinBotConnection} disabled={isBusy} title="通过 integrations/weixinProxy 发送测试消息">
              <Send aria-hidden="true" />
              测试发送
            </button>
          ) : null}
          {notificationForm.active_channel === "weixin_bot" ? (
            <button type="button" onClick={startWeixinBotListen} disabled={isBusy} title="启动 integrations/weixinProxy listen 接收消息">
              <Send aria-hidden="true" />
              启动监听
            </button>
          ) : null}
          {notificationForm.active_channel === "weixin_bot" ? (
            <button type="button" onClick={syncWeixinBotTarget} disabled={isBusy} title="从 listen 收到的会话中同步推送目标">
              <Send aria-hidden="true" />
              同步目标
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
          <label className="notificationChannelCard">
            <input
              checked={notificationForm.active_channel === "weixin_bot"}
              name="notification-channel"
              onChange={() => updateNotificationChannel("weixin_bot")}
              type="radio"
            />
            <span>
              <strong>微信 Bot</strong>
              <small>统一使用 integrations/weixinProxy 登录、监听和发送。</small>
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
        ) : notificationForm.active_channel === "weixin_bot" ? (
          <div className="settingsGrid notificationSettingsGrid">
            <label>
              消息前缀
              <input
                value={notificationForm.weixin_bot.message_prefix}
                onChange={(event) => updateWeixinBot("message_prefix", event.target.value)}
                placeholder="Workflow Chat"
              />
            </label>
            <label>
              请求超时（秒）
              <input
                min={1}
                value={notificationForm.weixin_bot.timeout_seconds}
                onChange={(event) => updateWeixinBot("timeout_seconds", Number(event.target.value) || 8)}
                type="number"
              />
            </label>
            <div className="settingsHintCard">
              Bot 登录账号 User ID：
              <code>{notificationForm.weixin_bot.user_id || "尚未扫码登录"}</code>
            </div>
            <div className="settingsHintCard">
              当前推送目标 User ID：
              <code>{notificationForm.weixin_bot.target_user_id || "尚未绑定，请启动监听后让目标微信发一条消息"}</code>
            </div>
            <label>
              在线扫码连接
              <button type="button" onClick={startWeixinBotLogin} disabled={isBusy}>
                <Send aria-hidden="true" />
                生成登录二维码
              </button>
              <small>后端会自动检测 integrations/weixinProxy 本地依赖；未安装时会在该目录执行 npm install。</small>
            </label>
            <div className="settingsHintCard">
              本地命令：
              <code>cd integrations/weixinProxy</code>
              <code>npm run login</code>
              <code>npm run listen</code>
              <code>npm run send -- &lt;user_id&gt; &lt;text&gt;</code>
            </div>
          </div>
        ) : (
          <div className="emptyInlineNotice">
            <Send aria-hidden="true" />
            <span>当前未启用外部通知。审批消息仍会保存在系统审批列表里。</span>
          </div>
        )}
      </section>

      {weixinLogin.open ? (
        <div className="modalBackdrop" role="presentation" onMouseDown={() => setWeixinLogin((current) => ({ ...current, open: false }))}>
          <section
            className="modalPanel weixinLoginModal"
            role="dialog"
            aria-modal="true"
            aria-label="微信 Bot 扫码登录"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <div className="panelHeader">
              <Bell aria-hidden="true" />
              <h2>微信 Bot 扫码登录</h2>
              <button type="button" onClick={() => setWeixinLogin((current) => ({ ...current, open: false }))}>
                关闭
              </button>
            </div>
            <div className="weixinQrBox">
              {weixinLogin.qrDataUrl ? (
                <img src={weixinLogin.qrDataUrl} alt="微信登录二维码" />
              ) : (
                <div className="weixinQrPlaceholder">等待二维码生成...</div>
              )}
            </div>
            <div className="taskMetaGrid">
              <span>会话：{weixinLogin.sessionId || "生成中"}</span>
              <span>状态：{weixinLogin.status || "pending"}</span>
              <span>扫码状态：{weixinLogin.qrStatus || "等待"}</span>
              <span>微信 User ID：{weixinLogin.userId || notificationForm.weixin_bot.user_id || "等待登录"}</span>
            </div>
            <p className="settingsIntro">{weixinLogin.error || weixinLogin.message || "请使用微信扫码并确认登录。"}</p>
          </section>
        </div>
      ) : null}
    </main>
  );
}
