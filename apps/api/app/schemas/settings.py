from pydantic import BaseModel, Field


class AiServiceFormat:
    OPENAI = "openai"
    OPENAI_RESPONSES = "openai_responses"
    ANTHROPIC = "anthropic"
    FULL_URL = "full_url"


class AiModelConfig(BaseModel):
    format: str = AiServiceFormat.OPENAI
    base_url: str = ""
    api_key: str = ""
    model_name: str = ""


class RoleModelConfig(BaseModel):
    enabled: bool = False
    format: str = AiServiceFormat.OPENAI
    base_url: str = ""
    api_key: str = ""
    model_name: str = ""


class ModelSettings(BaseModel):
    global_model: AiModelConfig = Field(default_factory=AiModelConfig)
    role_models: dict[str, RoleModelConfig] = Field(default_factory=dict)
    updated_at: str | None = None


class ModelTestRequest(BaseModel):
    settings: ModelSettings = Field(default_factory=ModelSettings)


class ModelTestResponse(BaseModel):
    ok: bool
    message: str
    detail: dict = Field(default_factory=dict)


class MemoryStorageSettings(BaseModel):
    sqlite_path: str = ".workflow-chat/memory.db"
    markdown_dir: str = ".workflow-chat/memories"
    updated_at: str | None = None


class PublicMemoryStorageSettings(BaseModel):
    sqlite_path: str = ".workflow-chat/memory.db"
    markdown_dir: str = ".workflow-chat/memories"
    updated_at: str | None = None


class MemoryStorageTestResponse(BaseModel):
    ok: bool
    message: str
    detail: dict = Field(default_factory=dict)


class PublicAiModelConfig(BaseModel):
    format: str = AiServiceFormat.OPENAI
    base_url: str = ""
    has_api_key: bool = False
    model_name: str = ""


class PublicRoleModelConfig(BaseModel):
    enabled: bool = False
    format: str = AiServiceFormat.OPENAI
    base_url: str = ""
    has_api_key: bool = False
    model_name: str = ""


class PublicModelSettings(BaseModel):
    global_model: PublicAiModelConfig = Field(default_factory=PublicAiModelConfig)
    role_models: dict[str, PublicRoleModelConfig] = Field(default_factory=dict)
    updated_at: str | None = None


class BossSettings(BaseModel):
    preferred_name: str = ""
    role_profile: str = ""
    updated_at: str | None = None


class NotificationChannel:
    NONE = "none"
    TELEGRAM = "telegram"
    WEIXIN_BOT = "weixin_bot"


class TelegramNotificationConfig(BaseModel):
    enabled: bool = False
    bot_token: str = ""
    chat_id: str = ""
    api_base_url: str = "https://api.telegram.org"
    parse_mode: str = "HTML"
    message_prefix: str = "Workflow Chat"
    webhook_secret_token: str = ""
    disable_web_page_preview: bool = True


class WeixinBotNotificationConfig(BaseModel):
    enabled: bool = False
    user_id: str = ""
    target_user_id: str = ""
    message_prefix: str = "Workflow Chat"
    timeout_seconds: int = 8


class NotificationSettings(BaseModel):
    active_channel: str = NotificationChannel.NONE
    telegram: TelegramNotificationConfig = Field(default_factory=TelegramNotificationConfig)
    weixin_bot: WeixinBotNotificationConfig = Field(default_factory=WeixinBotNotificationConfig)
    updated_at: str | None = None


class PublicTelegramNotificationConfig(BaseModel):
    enabled: bool = False
    has_bot_token: bool = False
    chat_id: str = ""
    api_base_url: str = "https://api.telegram.org"
    parse_mode: str = "HTML"
    message_prefix: str = "Workflow Chat"
    has_webhook_secret_token: bool = False
    disable_web_page_preview: bool = True


class PublicWeixinBotNotificationConfig(BaseModel):
    enabled: bool = False
    user_id: str = ""
    target_user_id: str = ""
    message_prefix: str = "Workflow Chat"
    timeout_seconds: int = 8


class PublicNotificationSettings(BaseModel):
    active_channel: str = NotificationChannel.NONE
    telegram: PublicTelegramNotificationConfig = Field(default_factory=PublicTelegramNotificationConfig)
    weixin_bot: PublicWeixinBotNotificationConfig = Field(default_factory=PublicWeixinBotNotificationConfig)
    updated_at: str | None = None


class NotificationTestResponse(BaseModel):
    ok: bool
    channel: str = NotificationChannel.TELEGRAM
    message: str
    detail: dict = Field(default_factory=dict)


class WeixinBotLoginStartResponse(BaseModel):
    ok: bool
    session_id: str = ""
    message: str = ""
    detail: dict = Field(default_factory=dict)


class WeixinBotLoginStatusResponse(BaseModel):
    ok: bool
    session_id: str = ""
    status: str = ""
    qr_status: str = ""
    qr_data_url: str = ""
    qr_content: str = ""
    user_id: str = ""
    message: str = ""
    error: str = ""
    detail: dict = Field(default_factory=dict)


class TelegramWebhookSetupRequest(BaseModel):
    webhook_url: str
