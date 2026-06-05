from typing import Any, Literal

from pydantic import BaseModel, Field


SkillSourceType = Literal["manual", "self_trained"]
SkillKind = Literal["workflow", "prompt", "tool_usage", "procedure", "domain"]


class SkillPackageFile(BaseModel):
    path: str = Field(min_length=1)
    content: str = ""
    size: int = 0


class AgentSkillRecord(BaseModel):
    id: str
    role_key: str
    source_type: SkillSourceType = "manual"
    kind: SkillKind = "procedure"
    title: str
    summary: str = ""
    content: str
    tags: list[str] = Field(default_factory=list)
    importance: int = 3
    markdown_path: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str
    updated_at: str


class SkillCreateRequest(BaseModel):
    source_type: SkillSourceType = "manual"
    kind: SkillKind = "procedure"
    title: str = Field(min_length=1)
    summary: str = ""
    content: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)
    importance: int = 3
    metadata: dict[str, Any] = Field(default_factory=dict)
    package_files: list[SkillPackageFile] = Field(default_factory=list)


class SkillUpdateRequest(BaseModel):
    source_type: SkillSourceType | None = None
    kind: SkillKind | None = None
    title: str | None = Field(default=None, min_length=1)
    summary: str | None = None
    content: str | None = Field(default=None, min_length=1)
    tags: list[str] | None = None
    importance: int | None = None
    metadata: dict[str, Any] | None = None
    package_files: list[SkillPackageFile] | None = None


class SkillSearchResult(BaseModel):
    skills: list[AgentSkillRecord] = Field(default_factory=list)
    markdown_context: str = ""
