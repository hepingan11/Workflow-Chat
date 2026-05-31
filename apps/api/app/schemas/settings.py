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
