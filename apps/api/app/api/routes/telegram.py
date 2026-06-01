from typing import Any

from fastapi import APIRouter, Header, HTTPException

from app.services.notification_settings import read_notification_settings
from app.services.notifications import answer_telegram_callback_query
from app.services.playbooks import resolve_approval_and_advance

router = APIRouter()


@router.post("/webhook")
def telegram_webhook(
    update: dict[str, Any],
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict[str, Any]:
    settings = read_notification_settings()
    secret = settings.telegram.webhook_secret_token
    if secret and x_telegram_bot_api_secret_token != secret:
        raise HTTPException(status_code=403, detail="Invalid Telegram webhook secret token")

    callback_query = update.get("callback_query")
    if not callback_query:
        return {"ok": True, "ignored": True, "reason": "Only callback_query updates are handled."}

    callback_query_id = callback_query.get("id", "")
    callback_data = callback_query.get("data", "")
    action, approval_id = parse_approval_callback(callback_data)

    result = resolve_approval_and_advance(approval_id, approved=action == "approve")
    answer_telegram_callback_query(
        callback_query_id,
        "已通过，工作流将继续执行。" if action == "approve" else "已拒绝，工作流已停止或进入拒绝分支。",
    )

    return {
        "ok": True,
        "approval_id": approval_id,
        "action": action,
        "run_status": result.run.status,
    }


def parse_approval_callback(callback_data: str) -> tuple[str, str]:
    parts = callback_data.split(":")
    if len(parts) != 3 or parts[0] != "approval" or parts[1] not in {"approve", "reject"} or not parts[2]:
        raise HTTPException(status_code=400, detail="Unsupported Telegram callback data")
    return parts[1], parts[2]
