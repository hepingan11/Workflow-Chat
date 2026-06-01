from pydantic import BaseModel, Field


class AiServiceFormat:
    OPENAI = "openai"
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


class TelegramNotificationConfig(BaseModel):
    enabled: bool = False
    bot_token: str = ""
    chat_id: str = ""
    api_base_url: str = "https://api.telegram.org"
    parse_mode: str = "HTML"
    message_prefix: str = "Workflow Chat"
    webhook_secret_token: str = ""
    disable_web_page_preview: bool = True


class NotificationSettings(BaseModel):
    active_channel: str = NotificationChannel.NONE
    telegram: TelegramNotificationConfig = Field(default_factory=TelegramNotificationConfig)
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


class PublicNotificationSettings(BaseModel):
    active_channel: str = NotificationChannel.NONE
    telegram: PublicTelegramNotificationConfig = Field(default_factory=PublicTelegramNotificationConfig)
    updated_at: str | None = None


class NotificationTestResponse(BaseModel):
    ok: bool
    channel: str = NotificationChannel.TELEGRAM
    message: str
    detail: dict = Field(default_factory=dict)


class TelegramWebhookSetupRequest(BaseModel):
    webhook_url: str
