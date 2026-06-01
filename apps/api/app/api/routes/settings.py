from fastapi import APIRouter

from app.schemas.settings import (
    BossSettings,
    ModelSettings,
    NotificationSettings,
    NotificationTestResponse,
    PublicModelSettings,
    PublicNotificationSettings,
    TelegramWebhookSetupRequest,
)
from app.services.boss_settings import read_boss_settings, write_boss_settings
from app.services.model_settings import read_public_model_settings, update_model_settings
from app.services.notification_settings import read_notification_settings
from app.services.notification_settings import read_public_notification_settings, update_notification_settings
from app.services.notifications import send_telegram_test_message, set_telegram_webhook

router = APIRouter()


@router.get("/model-config", response_model=PublicModelSettings)
def get_model_config() -> PublicModelSettings:
    return read_public_model_settings()


@router.put("/model-config", response_model=PublicModelSettings)
def update_model_config(payload: ModelSettings) -> PublicModelSettings:
    return update_model_settings(payload)


@router.get("/boss-config", response_model=BossSettings)
def get_boss_config() -> BossSettings:
    return read_boss_settings()


@router.put("/boss-config", response_model=BossSettings)
def update_boss_config(payload: BossSettings) -> BossSettings:
    return write_boss_settings(payload)


@router.get("/notification-config", response_model=PublicNotificationSettings)
def get_notification_config() -> PublicNotificationSettings:
    return read_public_notification_settings()


@router.put("/notification-config", response_model=PublicNotificationSettings)
def update_notification_config(payload: NotificationSettings) -> PublicNotificationSettings:
    return update_notification_settings(payload)


@router.post("/notification-config/test-telegram", response_model=NotificationTestResponse)
def test_telegram_notification(payload: NotificationSettings) -> NotificationTestResponse:
    existing = read_notification_settings()
    if not payload.telegram.bot_token:
        payload.telegram.bot_token = existing.telegram.bot_token

    try:
        result = send_telegram_test_message(payload)
    except Exception as exc:
        return NotificationTestResponse(
            ok=False,
            message="Telegram 测试消息发送失败。",
            detail={"error": str(exc)},
        )

    if not result.get("ok"):
        return NotificationTestResponse(
            ok=False,
            message=str(result.get("message", "Telegram 测试消息发送失败。")),
            detail=dict(result),
        )

    return NotificationTestResponse(
        ok=True,
        message="Telegram 测试消息已发送。",
        detail={"response": result.get("response")},
    )


@router.post("/notification-config/telegram-webhook", response_model=NotificationTestResponse)
def setup_telegram_webhook(payload: TelegramWebhookSetupRequest) -> NotificationTestResponse:
    try:
        result = set_telegram_webhook(payload.webhook_url)
    except Exception as exc:
        return NotificationTestResponse(
            ok=False,
            message="Telegram Webhook 配置失败。",
            detail={"error": str(exc)},
        )

    if not result.get("ok"):
        return NotificationTestResponse(
            ok=False,
            message=str(result.get("message", "Telegram Webhook 配置失败。")),
            detail=dict(result),
        )

    return NotificationTestResponse(
        ok=True,
        message="Telegram Webhook 已配置。",
        detail={"response": result.get("response")},
    )
