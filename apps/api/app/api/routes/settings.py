from fastapi import APIRouter

from app.schemas.settings import (
    BossSettings,
    MemoryStorageSettings,
    MemoryStorageTestResponse,
    ModelSettings,
    ModelTestRequest,
    ModelTestResponse,
    NotificationSettings,
    NotificationTestResponse,
    PublicModelSettings,
    PublicMemoryStorageSettings,
    PublicNotificationSettings,
    TelegramWebhookSetupRequest,
    WeixinBotLoginStartResponse,
    WeixinBotLoginStatusResponse,
)
from app.services.boss_settings import read_boss_settings, write_boss_settings
from app.services.model_settings import read_public_model_settings, test_model_connection, update_model_settings
from app.services.memory_settings import (
    read_public_memory_settings,
    test_memory_storage_connection,
    update_memory_settings,
)
from app.services.notification_settings import (
    read_notification_settings,
    save_weixin_bot_target_user_id,
    save_weixin_bot_user_id,
)
from app.services.notification_settings import read_public_notification_settings, update_notification_settings
from app.services.notifications import (
    get_weixin_bot_login_status,
    send_telegram_test_message,
    send_weixin_bot_test_message,
    set_telegram_webhook,
    start_weixin_bot_login,
)
from app.services.weixin_cli import get_first_context_user_id, get_wxilink_business_status, start_wxilink_listen

router = APIRouter()


@router.get("/model-config", response_model=PublicModelSettings)
def get_model_config() -> PublicModelSettings:
    return read_public_model_settings()


@router.put("/model-config", response_model=PublicModelSettings)
def update_model_config(payload: ModelSettings) -> PublicModelSettings:
    return update_model_settings(payload)


@router.post("/model-config/test", response_model=ModelTestResponse)
def test_model_config(payload: ModelTestRequest) -> ModelTestResponse:
    return test_model_connection(payload)


@router.get("/memory-storage-config", response_model=PublicMemoryStorageSettings)
def get_memory_storage_config() -> PublicMemoryStorageSettings:
    return read_public_memory_settings()


@router.put("/memory-storage-config", response_model=PublicMemoryStorageSettings)
def update_memory_storage_config(payload: MemoryStorageSettings) -> PublicMemoryStorageSettings:
    return update_memory_settings(payload)


@router.post("/memory-storage-config/test", response_model=MemoryStorageTestResponse)
def test_memory_storage_config(payload: MemoryStorageSettings) -> MemoryStorageTestResponse:
    return test_memory_storage_connection(payload)


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


@router.post("/notification-config/test-weixin-bot", response_model=NotificationTestResponse)
def test_weixin_bot_notification(payload: NotificationSettings) -> NotificationTestResponse:
    try:
        result = send_weixin_bot_test_message(payload)
    except Exception as exc:
        return NotificationTestResponse(
            ok=False,
            channel="weixin_bot",
            message="微信 Bot 测试消息发送失败。",
            detail={"error": str(exc)},
        )

    if not result.get("ok"):
        return NotificationTestResponse(
            ok=False,
            channel="weixin_bot",
            message=str(result.get("message", "微信 Bot 测试消息发送失败。")),
            detail=dict(result),
        )

    return NotificationTestResponse(
        ok=True,
        channel="weixin_bot",
        message="微信 Bot 测试消息已发送。",
        detail={"response": result.get("response")},
    )


@router.post("/notification-config/weixin-bot-login", response_model=WeixinBotLoginStartResponse)
def start_weixin_bot_login_request(payload: NotificationSettings) -> WeixinBotLoginStartResponse:
    try:
        result = start_weixin_bot_login(payload)
    except Exception as exc:
        return WeixinBotLoginStartResponse(ok=False, message="微信 Bot 登录二维码获取失败。", detail={"error": str(exc)})

    if not result.get("ok"):
        return WeixinBotLoginStartResponse(
            ok=False,
            message=str(result.get("message", "微信 Bot 登录启动失败。")),
            detail=dict(result.get("detail", result)),
        )

    response = result.get("response", {})
    if not response.get("ok"):
        return WeixinBotLoginStartResponse(ok=False, message=str(response.get("message", "微信 Bot 登录启动失败。")), detail=response)

    return WeixinBotLoginStartResponse(
        ok=True,
        session_id=str(response.get("session_id", "")),
        message=str(response.get("message", "微信 Bot 登录已启动。")),
        detail=response,
    )


@router.post("/notification-config/weixin-bot-login/{session_id}", response_model=WeixinBotLoginStatusResponse)
def get_weixin_bot_login_status_request(session_id: str, payload: NotificationSettings) -> WeixinBotLoginStatusResponse:
    try:
        result = get_weixin_bot_login_status(session_id, payload)
    except Exception as exc:
        return WeixinBotLoginStatusResponse(ok=False, session_id=session_id, message="微信 Bot 登录状态读取失败。", error=str(exc))

    if not result.get("ok"):
        return WeixinBotLoginStatusResponse(
            ok=False,
            session_id=session_id,
            message=str(result.get("message", "微信 Bot 登录状态读取失败。")),
            error=str(result.get("message", "")),
            detail=dict(result.get("detail", result)),
        )

    response = result.get("response", {})
    account = response.get("account") if isinstance(response.get("account"), dict) else {}
    user_id = str(account.get("userId", "") or response.get("user_id", ""))
    if response.get("status") == "confirmed" and user_id:
        save_weixin_bot_user_id(user_id)

    return WeixinBotLoginStatusResponse(
        ok=bool(response.get("ok")),
        session_id=str(response.get("session_id", session_id)),
        status=str(response.get("status", "")),
        qr_status=str(response.get("qr_status", "")),
        qr_data_url=str(response.get("qr_data_url", "")),
        qr_content=str(response.get("qr_content", "")),
        user_id=user_id,
        message=str(response.get("message", "")),
        error=str(response.get("error", "")),
        detail=response,
    )


@router.post("/notification-config/weixin-bot-listen/start", response_model=NotificationTestResponse)
def start_weixin_bot_listen_request() -> NotificationTestResponse:
    try:
        result = start_wxilink_listen()
    except Exception as exc:
        return NotificationTestResponse(
            ok=False,
            channel="weixin_bot",
            message="weixinProxy listen 启动失败。",
            detail={"error": str(exc)},
        )
    return NotificationTestResponse(
        ok=bool(result.get("ok")),
        channel="weixin_bot",
        message=str(result.get("message", "weixinProxy listen 启动完成。")),
        detail=result,
    )


@router.post("/notification-config/weixin-bot-target/sync", response_model=NotificationTestResponse)
def sync_weixin_bot_target_request() -> NotificationTestResponse:
    target_user_id = get_first_context_user_id()
    if not target_user_id:
        return NotificationTestResponse(
            ok=False,
            channel="weixin_bot",
            message="暂未发现可推送的微信会话。请先启动监听，并用接收通知的微信号给 Bot 发一条消息。",
        )
    save_weixin_bot_target_user_id(target_user_id)
    return NotificationTestResponse(
        ok=True,
        channel="weixin_bot",
        message="微信推送目标已同步。",
        detail={"target_user_id": target_user_id},
    )


@router.get("/notification-config/weixin-bot-status", response_model=NotificationTestResponse)
def get_weixin_bot_business_status() -> NotificationTestResponse:
    status = get_wxilink_business_status()
    return NotificationTestResponse(
        ok=bool(status.get("ok")),
        channel="weixin_bot",
        message="微信业务推送已就绪。" if status.get("ok") else "微信业务推送尚未就绪。",
        detail=status,
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
