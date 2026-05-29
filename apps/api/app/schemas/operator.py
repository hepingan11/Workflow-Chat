from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class MaterialInput(BaseModel):
    name: str
    type: Literal["image", "video", "audio", "document", "link", "other"] = "other"
    url: HttpUrl | None = None
    content: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class OperatorPublishRequest(BaseModel):
    title: str
    copy_text: str
    platforms: list[str] = Field(default_factory=list)
    materials: list[MaterialInput] = Field(default_factory=list)
    campaign: str | None = None
    tone: str | None = None
    workflow_provider: Literal["dify"] = "dify"
    workflow_inputs: dict[str, Any] = Field(default_factory=dict)
    dry_run: bool = False

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="before")
    @classmethod
    def accept_copy_field(cls, data: Any) -> Any:
        if isinstance(data, dict) and "copy" in data and "copy_text" not in data:
            data = {**data, "copy_text": data["copy"]}
        return data


class PreparedWorkflowPayload(BaseModel):
    provider: str
    prompt: str
    inputs: dict[str, Any]


class WorkflowExecutionResult(BaseModel):
    provider: str
    dry_run: bool
    status: str
    request_payload: dict[str, Any]
    response_payload: dict[str, Any] | None = None


class OperatorPublishResponse(BaseModel):
    status: str
    prepared: PreparedWorkflowPayload
    workflow: WorkflowExecutionResult


class OperatorPromptConfig(BaseModel):
    role_key: str = "operator"
    name: str = "运营发布整理提示词"
    prompt: str
    updated_at: str | None = None


class OperatorPromptUpdate(BaseModel):
    prompt: str = Field(min_length=1)
