import json
from datetime import UTC, datetime
from pathlib import Path

from app.schemas.settings import (
    NotificationChannel,
    NotificationSettings,
    PublicNotificationSettings,
    PublicTelegramNotificationConfig,
    PublicWeixinBotNotificationConfig,
)
from app.services.prompt_config import get_config_dir


def get_notification_settings_path() -> Path:
    return get_config_dir() / "notification-config.json"


def read_notification_settings() -> NotificationSettings:
    path = get_notification_settings_path()
    if not path.exists():
        settings = NotificationSettings()
        write_notification_settings(settings)
        return settings

    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return _normalize_notification_settings(NotificationSettings(**data))


def read_public_notification_settings() -> PublicNotificationSettings:
    return to_public_notification_settings(read_notification_settings())


def write_notification_settings(settings: NotificationSettings) -> NotificationSettings:
    settings = _normalize_notification_settings(settings)
    settings.updated_at = datetime.now(UTC).isoformat()
    get_notification_settings_path().write_text(
        json.dumps(settings.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return settings


def update_notification_settings(payload: NotificationSettings) -> PublicNotificationSettings:
    existing = read_notification_settings()

    if not payload.telegram.bot_token:
        payload.telegram.bot_token = existing.telegram.bot_token
    if not payload.telegram.webhook_secret_token:
        payload.telegram.webhook_secret_token = existing.telegram.webhook_secret_token
    if not payload.weixin_bot.user_id:
        payload.weixin_bot.user_id = existing.weixin_bot.user_id
    if not payload.weixin_bot.target_user_id:
        payload.weixin_bot.target_user_id = existing.weixin_bot.target_user_id

    saved = write_notification_settings(payload)
    return to_public_notification_settings(saved)


def to_public_notification_settings(settings: NotificationSettings) -> PublicNotificationSettings:
    return PublicNotificationSettings(
        active_channel=settings.active_channel,
        telegram=PublicTelegramNotificationConfig(
            enabled=settings.telegram.enabled,
            has_bot_token=bool(settings.telegram.bot_token),
            chat_id=settings.telegram.chat_id,
            api_base_url=settings.telegram.api_base_url,
            parse_mode=settings.telegram.parse_mode,
            message_prefix=settings.telegram.message_prefix,
            has_webhook_secret_token=bool(settings.telegram.webhook_secret_token),
            disable_web_page_preview=settings.telegram.disable_web_page_preview,
        ),
        weixin_bot=PublicWeixinBotNotificationConfig(
            enabled=settings.weixin_bot.enabled,
            user_id=settings.weixin_bot.user_id,
            target_user_id=settings.weixin_bot.target_user_id,
            message_prefix=settings.weixin_bot.message_prefix,
            timeout_seconds=settings.weixin_bot.timeout_seconds,
        ),
        updated_at=settings.updated_at,
    )


def _normalize_notification_settings(settings: NotificationSettings) -> NotificationSettings:
    if settings.active_channel not in {NotificationChannel.NONE, NotificationChannel.TELEGRAM, NotificationChannel.WEIXIN_BOT}:
        settings.active_channel = NotificationChannel.NONE

    settings.telegram.enabled = settings.active_channel == NotificationChannel.TELEGRAM
    settings.weixin_bot.enabled = settings.active_channel == NotificationChannel.WEIXIN_BOT
    if settings.active_channel == NotificationChannel.TELEGRAM and not settings.telegram.enabled:
        settings.active_channel = NotificationChannel.NONE
    if settings.active_channel == NotificationChannel.WEIXIN_BOT and not settings.weixin_bot.enabled:
        settings.active_channel = NotificationChannel.NONE
    if not settings.telegram.api_base_url:
        settings.telegram.api_base_url = "https://api.telegram.org"
    if not settings.telegram.parse_mode:
        settings.telegram.parse_mode = "HTML"
    if not settings.weixin_bot.message_prefix:
        settings.weixin_bot.message_prefix = "Workflow Chat"
    if settings.weixin_bot.timeout_seconds <= 0:
        settings.weixin_bot.timeout_seconds = 8
    return settings


def save_weixin_bot_user_id(user_id: str) -> NotificationSettings:
    settings = read_notification_settings()
    settings.weixin_bot.user_id = user_id
    return write_notification_settings(settings)


def save_weixin_bot_target_user_id(target_user_id: str) -> NotificationSettings:
    settings = read_notification_settings()
    settings.weixin_bot.target_user_id = target_user_id
    return write_notification_settings(settings)
