from html import escape
from typing import Any

import httpx

from app.schemas.playbooks import ApprovalRequest
from app.schemas.settings import NotificationChannel, NotificationSettings
from app.services.notification_settings import read_notification_settings


class NotificationResult(dict):
    pass


def send_approval_notification(approval: ApprovalRequest) -> NotificationResult:
    settings = read_notification_settings()
    if settings.active_channel == NotificationChannel.TELEGRAM:
        return send_telegram_approval_message(approval, settings)

    return NotificationResult(
        ok=False,
        channel=NotificationChannel.NONE,
        skipped=True,
        message="未启用通知推送渠道。",
    )


def send_message_push(title: str, content: Any, context: dict[str, Any] | None = None) -> NotificationResult:
    settings = read_notification_settings()
    if settings.active_channel == NotificationChannel.TELEGRAM:
        return send_telegram_message_push(title, content, context or {}, settings)

    return NotificationResult(
        ok=False,
        channel=NotificationChannel.NONE,
        skipped=True,
        message="未启用通知推送渠道。",
    )


def send_telegram_message_push(
    title: str,
    content: Any,
    context: dict[str, Any],
    settings: NotificationSettings | None = None,
) -> NotificationResult:
    settings = settings or read_notification_settings()
    telegram = settings.telegram

    if settings.active_channel != NotificationChannel.TELEGRAM:
        return NotificationResult(ok=False, channel="telegram", skipped=True, message="Telegram 未启用。")
    if not telegram.bot_token or not telegram.chat_id:
        return NotificationResult(ok=False, channel="telegram", skipped=True, message="Telegram Bot Token 或 Chat ID 未配置。")

    response = httpx.post(
        f"{telegram.api_base_url.rstrip('/')}/bot{telegram.bot_token}/sendMessage",
        json={
            "chat_id": telegram.chat_id,
            "text": build_telegram_push_text(title, content, context, telegram.message_prefix),
            "parse_mode": telegram.parse_mode,
            "disable_web_page_preview": telegram.disable_web_page_preview,
        },
        timeout=8,
    )
    response.raise_for_status()

    return NotificationResult(ok=True, channel="telegram", response=response.json())


def send_telegram_approval_message(
    approval: ApprovalRequest,
    settings: NotificationSettings | None = None,
) -> NotificationResult:
    settings = settings or read_notification_settings()
    telegram = settings.telegram

    if settings.active_channel != NotificationChannel.TELEGRAM:
        return NotificationResult(ok=False, channel="telegram", skipped=True, message="Telegram 未启用。")
    if not telegram.bot_token or not telegram.chat_id:
        return NotificationResult(ok=False, channel="telegram", skipped=True, message="Telegram Bot Token 或 Chat ID 未配置。")

    text = build_telegram_approval_text(approval, telegram.message_prefix)
    api_base_url = telegram.api_base_url.rstrip("/")
    response = httpx.post(
        f"{api_base_url}/bot{telegram.bot_token}/sendMessage",
        json={
            "chat_id": telegram.chat_id,
            "text": text,
            "parse_mode": telegram.parse_mode,
            "disable_web_page_preview": telegram.disable_web_page_preview,
            "reply_markup": {
                "inline_keyboard": [
                    [
                        {"text": "通过", "callback_data": f"approval:approve:{approval.id}"},
                        {"text": "拒绝", "callback_data": f"approval:reject:{approval.id}"},
                    ]
                ]
            },
        },
        timeout=8,
    )
    response.raise_for_status()

    return NotificationResult(ok=True, channel="telegram", response=response.json())


def answer_telegram_callback_query(callback_query_id: str, text: str) -> NotificationResult:
    settings = read_notification_settings()
    telegram = settings.telegram
    if not telegram.bot_token:
        return NotificationResult(ok=False, channel="telegram", skipped=True, message="Telegram Bot Token 未配置。")

    response = httpx.post(
        f"{telegram.api_base_url.rstrip('/')}/bot{telegram.bot_token}/answerCallbackQuery",
        json={
            "callback_query_id": callback_query_id,
            "text": text,
            "show_alert": False,
        },
        timeout=8,
    )
    response.raise_for_status()
    return NotificationResult(ok=True, channel="telegram", response=response.json())


def set_telegram_webhook(webhook_url: str) -> NotificationResult:
    settings = read_notification_settings()
    telegram = settings.telegram
    if not telegram.bot_token:
        return NotificationResult(ok=False, channel="telegram", skipped=True, message="Telegram Bot Token 未配置。")

    payload: dict[str, Any] = {
        "url": webhook_url,
        "allowed_updates": ["callback_query"],
    }
    if telegram.webhook_secret_token:
        payload["secret_token"] = telegram.webhook_secret_token

    response = httpx.post(
        f"{telegram.api_base_url.rstrip('/')}/bot{telegram.bot_token}/setWebhook",
        json=payload,
        timeout=8,
    )
    response.raise_for_status()
    return NotificationResult(ok=True, channel="telegram", response=response.json())


def send_telegram_test_message(settings: NotificationSettings | None = None) -> NotificationResult:
    settings = settings or read_notification_settings()
    telegram = settings.telegram

    if settings.active_channel != NotificationChannel.TELEGRAM:
        return NotificationResult(ok=False, channel="telegram", skipped=True, message="Telegram 未启用。")
    if not telegram.bot_token or not telegram.chat_id:
        return NotificationResult(ok=False, channel="telegram", skipped=True, message="Telegram Bot Token 或 Chat ID 未配置。")

    api_base_url = telegram.api_base_url.rstrip("/")
    text = "\n".join(
        [
            f"<b>{escape(telegram.message_prefix or 'Workflow Chat')}</b>",
            "",
            "Telegram 测试消息发送成功。",
            "后续审批确认消息会发送到这个会话。",
        ]
    )
    response = httpx.post(
        f"{api_base_url}/bot{telegram.bot_token}/sendMessage",
        json={
            "chat_id": telegram.chat_id,
            "text": text,
            "parse_mode": telegram.parse_mode,
            "disable_web_page_preview": telegram.disable_web_page_preview,
        },
        timeout=8,
    )
    response.raise_for_status()

    return NotificationResult(ok=True, channel="telegram", response=response.json())


def build_telegram_approval_text(approval: ApprovalRequest, prefix: str = "Workflow Chat") -> str:
    context_lines = render_context_lines(approval.context)
    return "\n".join(
        [
            f"<b>{escape(prefix)}</b>",
            "",
            "<b>需要你确认一个工作流节点</b>",
            f"审批 ID：<code>{escape(approval.id)}</code>",
            f"运行 ID：<code>{escape(approval.run_id)}</code>",
            f"角色：<code>{escape(approval.role_key)}</code>",
            f"节点：{escape(str(approval.context.get('step_name', approval.step_id)))}",
            "",
            escape(approval.message),
            *context_lines,
        ]
    )


def build_telegram_push_text(title: str, content: Any, context: dict[str, Any], prefix: str = "Workflow Chat") -> str:
    content_text = stringify_message_content(content)
    return "\n".join(
        [
            f"<b>{escape(prefix)}</b>",
            "",
            f"<b>{escape(title)}</b>",
            "",
            escape(content_text),
            *render_context_lines(context),
        ]
    )


def stringify_message_content(content: Any) -> str:
    if content is None:
        return "无输出内容。"
    if isinstance(content, str):
        return content
    try:
        return json_dumps(content)
    except TypeError:
        return str(content)


def json_dumps(value: Any) -> str:
    import json

    return json.dumps(value, ensure_ascii=False, indent=2)


def render_context_lines(context: dict[str, Any]) -> list[str]:
    if not context:
        return []

    lines = ["", "<b>上下文</b>"]
    for key in ["owner_role_key", "participant_role_keys", "run_id"]:
        if key not in context:
            continue
        value = context[key]
        if isinstance(value, list):
            value = "、".join(str(item) for item in value) or "无"
        lines.append(f"{escape(key)}：<code>{escape(str(value))}</code>")
    return lines
