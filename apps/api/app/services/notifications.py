import json
from html import escape
from typing import Any

import httpx

from app.schemas.playbooks import ApprovalRequest
from app.schemas.settings import NotificationChannel, NotificationSettings
from app.services.notification_settings import read_notification_settings, save_weixin_bot_target_user_id
from app.services.weixin_cli import (
    get_first_context_user_id,
    read_wxilink_login_status,
    send_wxilink_message,
    start_wxilink_login,
)


class NotificationResult(dict):
    pass


def send_approval_notification(approval: ApprovalRequest) -> NotificationResult:
    settings = read_notification_settings()
    if settings.active_channel == NotificationChannel.TELEGRAM:
        return send_telegram_approval_message(approval, settings)
    if settings.active_channel == NotificationChannel.WEIXIN_BOT:
        return send_weixin_bot_approval_message(approval, settings)

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
    if settings.active_channel == NotificationChannel.WEIXIN_BOT:
        return send_weixin_bot_message_push(title, content, context or {}, settings)

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


def send_weixin_bot_message_push(
    title: str,
    content: Any,
    context: dict[str, Any],
    settings: NotificationSettings | None = None,
) -> NotificationResult:
    settings = settings or read_notification_settings()
    if settings.active_channel != NotificationChannel.WEIXIN_BOT:
        return NotificationResult(ok=False, channel="weixin_bot", skipped=True, message="微信 Bot 未启用。")
    target_user_id = resolve_weixin_target_user_id(settings)
    if not target_user_id:
        return missing_weixin_target_result()
    result = send_wxilink_message(
        user_id=target_user_id,
        text=build_weixin_push_text(title, content, context, settings.weixin_bot.message_prefix),
        timeout_seconds=settings.weixin_bot.timeout_seconds,
    )
    return build_weixin_notification_result(result, target_user_id)


def send_weixin_bot_approval_message(
    approval: ApprovalRequest,
    settings: NotificationSettings | None = None,
) -> NotificationResult:
    settings = settings or read_notification_settings()
    if settings.active_channel != NotificationChannel.WEIXIN_BOT:
        return NotificationResult(ok=False, channel="weixin_bot", skipped=True, message="微信 Bot 未启用。")
    target_user_id = resolve_weixin_target_user_id(settings)
    if not target_user_id:
        return missing_weixin_target_result()
    result = send_wxilink_message(
        user_id=target_user_id,
        text=build_weixin_approval_text(approval, settings.weixin_bot.message_prefix),
        timeout_seconds=settings.weixin_bot.timeout_seconds,
    )
    return build_weixin_notification_result(result, target_user_id)


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


def send_weixin_bot_test_message(settings: NotificationSettings | None = None) -> NotificationResult:
    settings = settings or read_notification_settings()
    if settings.active_channel != NotificationChannel.WEIXIN_BOT:
        return NotificationResult(ok=False, channel="weixin_bot", skipped=True, message="微信 Bot 未启用。")
    text = "\n".join(
        [
            f"【{settings.weixin_bot.message_prefix or 'Workflow Chat'}】",
            "",
            "微信 Bot 测试消息发送成功。",
            "后续审批确认和消息推送会发送到这个微信会话。",
        ]
    )
    target_user_id = resolve_weixin_target_user_id(settings)
    if not target_user_id:
        return missing_weixin_target_result()
    result = send_wxilink_message(target_user_id, text, settings.weixin_bot.timeout_seconds)
    return build_weixin_notification_result(result, target_user_id)


def start_weixin_bot_login(settings: NotificationSettings | None = None) -> NotificationResult:
    result = start_wxilink_login()
    return NotificationResult(ok=bool(result.get("ok")), channel="weixin_bot", response=result, message=result.get("message", ""))


def get_weixin_bot_login_status(session_id: str, settings: NotificationSettings | None = None) -> NotificationResult:
    payload = read_wxilink_login_status(session_id)
    return NotificationResult(ok=bool(payload.get("ok")), channel="weixin_bot", response=payload, message=payload.get("message", ""))


def resolve_weixin_target_user_id(settings: NotificationSettings) -> str:
    if settings.weixin_bot.target_user_id:
        return settings.weixin_bot.target_user_id
    target_user_id = get_first_context_user_id()
    if target_user_id:
        save_weixin_bot_target_user_id(target_user_id)
    return target_user_id


def missing_weixin_target_result() -> NotificationResult:
    return NotificationResult(
        ok=False,
        channel="weixin_bot",
        message="微信推送目标未绑定。请先点击“启动监听”，然后用要接收通知的微信号给 Bot 发一条消息，待 listen 接收后再测试发送。",
    )


def build_weixin_notification_result(result: dict[str, Any], target_user_id: str) -> NotificationResult:
    return NotificationResult(
        ok=bool(result.get("ok")),
        channel="weixin_bot",
        target_user_id=target_user_id,
        response=result,
        message=result.get("message", ""),
    )


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


def build_weixin_approval_text(approval: ApprovalRequest, prefix: str = "Workflow Chat") -> str:
    context_lines = render_plain_context_lines(approval.context)
    return "\n".join(
        [
            f"【{prefix}】",
            "",
            "需要你确认一个工作流节点",
            f"审批 ID：{approval.id}",
            f"运行 ID：{approval.run_id}",
            f"角色：{approval.role_key}",
            f"节点：{approval.context.get('step_name', approval.step_id)}",
            "",
            approval.message,
            "",
            "请回到 Workflow Chat 审批列表或 Telegram 内联按钮完成确认。",
            *context_lines,
        ]
    )


def build_weixin_push_text(title: str, content: Any, context: dict[str, Any], prefix: str = "Workflow Chat") -> str:
    content_text = stringify_message_content(content)
    return "\n".join(
        [
            f"【{prefix}】",
            "",
            title,
            "",
            content_text,
            *render_plain_context_lines(context),
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


def render_plain_context_lines(context: dict[str, Any]) -> list[str]:
    if not context:
        return []
    lines = ["", "上下文"]
    for key in ["owner_role_key", "participant_role_keys", "run_id"]:
        if key not in context:
            continue
        value = context[key]
        if isinstance(value, list):
            value = "、".join(str(item) for item in value) or "无"
        lines.append(f"{key}：{value}")
    return lines
