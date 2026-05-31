from typing import Any, Literal

from pydantic import BaseModel, Field


ToolProvider = Literal["dify"]


class DifyToolConnection(BaseModel):
    base_url: str
    api_key: str = ""


class DifyToolMeta(BaseModel):
    app_name: str = ""
    app_description: str = ""
    app_mode: str = ""
    user_input_form: list[dict[str, Any]] = Field(default_factory=list)


class ToolRecord(BaseModel):
    id: str
    name: str
    description: str = ""
    provider: ToolProvider = "dify"
    enabled: bool = True
    allowed_roles: list[str] = Field(default_factory=list)
    connection: DifyToolConnection
    meta: DifyToolMeta = Field(default_factory=DifyToolMeta)
    updated_at: str | None = None


class ToolRegistry(BaseModel):
    tools: list[ToolRecord] = Field(default_factory=list)
    updated_at: str | None = None


class ToolCreatePayload(BaseModel):
    name: str
    description: str = ""
    provider: ToolProvider = "dify"
    enabled: bool = True
    allowed_roles: list[str] = Field(default_factory=list)
    connection: DifyToolConnection


class ToolUpdatePayload(BaseModel):
    name: str
    description: str = ""
    provider: ToolProvider = "dify"
    enabled: bool = True
    allowed_roles: list[str] = Field(default_factory=list)
    connection: DifyToolConnection


class PublicDifyToolConnection(BaseModel):
    base_url: str
    has_api_key: bool = False


class PublicToolRecord(BaseModel):
    id: str
    name: str
    description: str = ""
    provider: ToolProvider = "dify"
    enabled: bool = True
    allowed_roles: list[str] = Field(default_factory=list)
    connection: PublicDifyToolConnection
    meta: DifyToolMeta = Field(default_factory=DifyToolMeta)
    updated_at: str | None = None


class PublicToolRegistry(BaseModel):
    tools: list[PublicToolRecord] = Field(default_factory=list)
    updated_at: str | None = None


class ToolSyncResult(BaseModel):
    tool: PublicToolRecord
    synced_fields: list[str] = Field(default_factory=list)
