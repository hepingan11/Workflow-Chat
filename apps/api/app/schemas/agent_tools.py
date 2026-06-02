from typing import Any, Literal

from pydantic import BaseModel, Field


ToolSource = Literal["builtin", "dify", "codex", "mcp"]


class AgentToolDefinition(BaseModel):
    id: str
    name: str
    description: str = ""
    source: ToolSource
    enabled: bool = True
    executable: bool = False
    provider: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


class AgentToolListResponse(BaseModel):
    agent_key: str
    tools: list[AgentToolDefinition] = Field(default_factory=list)


class AgentToolExecutePayload(BaseModel):
    inputs: dict[str, Any] = Field(default_factory=dict)
    user: str | None = None


class AgentToolExecuteResponse(BaseModel):
    agent_key: str
    tool_id: str
    result: dict[str, Any]
