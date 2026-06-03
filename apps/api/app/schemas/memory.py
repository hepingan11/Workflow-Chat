from typing import Any, Literal

from pydantic import BaseModel, Field


MemoryKind = Literal["semantic", "episodic", "procedural", "preference", "pitfall"]


class AgentMemoryRecord(BaseModel):
    id: str
    role_key: str
    kind: MemoryKind
    title: str
    summary: str
    content: str
    source_type: str = "manual"
    source_id: str | None = None
    tags: list[str] = Field(default_factory=list)
    importance: int = 3
    markdown_path: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str
    updated_at: str


class AgentTaskMemoryRecord(BaseModel):
    id: str
    role_key: str
    task_id: str
    task_title: str
    user_input: str = ""
    execution_summary: str = ""
    status: str = ""
    raw_payload: dict[str, Any] = Field(default_factory=dict)
    created_at: str
    completed_at: str | None = None


class MemorySearchResult(BaseModel):
    memories: list[AgentMemoryRecord] = Field(default_factory=list)
    markdown_context: str = ""


class MemoryCreateRequest(BaseModel):
    kind: MemoryKind = "semantic"
    title: str
    summary: str = ""
    content: str
    tags: list[str] = Field(default_factory=list)
    importance: int = 3
    source_type: str = "manual"
    source_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TaskReflectionResult(BaseModel):
    task: AgentTaskMemoryRecord
    memories: list[AgentMemoryRecord] = Field(default_factory=list)
