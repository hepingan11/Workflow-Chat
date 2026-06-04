from typing import Any, Literal

from pydantic import BaseModel, Field


PlaybookStepType = Literal["tool", "human_approval", "message_push", "handoff", "noop"]
PlaybookStatus = Literal["active", "paused"]
RunStatus = Literal["pending", "running", "waiting_approval", "scheduled", "completed", "failed", "cancelled"]
ApprovalStatus = Literal["pending", "approved", "rejected"]


class CollaborationPolicy(BaseModel):
    mode: Literal["single_role", "multi_role"] = "single_role"
    owner_role_key: str
    participant_role_keys: list[str] = Field(default_factory=list)
    handoff_strategy: Literal["manual", "auto"] = "manual"
    shared_context_keys: list[str] = Field(default_factory=list)


class PlaybookTrigger(BaseModel):
    type: Literal["immediate", "scheduled", "daily", "recurring"] = "daily"
    time: str
    timezone: str = "Asia/Shanghai"
    cron: str | None = None
    run_at: str | None = None
    description: str | None = None


class ToolStepConfig(BaseModel):
    tool_id: str
    tool_name: str
    run_at: str | None = None
    input_template: dict[str, Any] = Field(default_factory=dict)
    needs_previous_output: bool = False


class ApprovalStepConfig(BaseModel):
    channel: Literal["message"] = "message"
    message_template: str
    proceed_if: Literal["approved"] = "approved"


class PlaybookStep(BaseModel):
    id: str
    name: str
    type: PlaybookStepType
    role_key: str | None = None
    assignee_role_key: str | None = None
    participant_role_keys: list[str] = Field(default_factory=list)
    depends_on_step_ids: list[str] = Field(default_factory=list)
    handoff_to_role_key: str | None = None
    next_step_ids: list[str] = Field(default_factory=list)
    on_approved_step_ids: list[str] = Field(default_factory=list)
    on_rejected_step_ids: list[str] = Field(default_factory=list)
    context_reads: list[str] = Field(default_factory=list)
    context_writes: list[str] = Field(default_factory=list)
    config: dict[str, Any] = Field(default_factory=dict)


class Playbook(BaseModel):
    id: str
    role_key: str
    name: str
    natural_language: str
    trigger: PlaybookTrigger
    collaboration: CollaborationPolicy
    steps: list[PlaybookStep] = Field(default_factory=list)
    status: PlaybookStatus = "active"
    updated_at: str | None = None


class PlaybookRegistry(BaseModel):
    playbooks: list[Playbook] = Field(default_factory=list)
    updated_at: str | None = None


class PlaybookRunStep(BaseModel):
    id: str
    name: str
    type: PlaybookStepType
    role_key: str | None = None
    assignee_role_key: str | None = None
    participant_role_keys: list[str] = Field(default_factory=list)
    depends_on_step_ids: list[str] = Field(default_factory=list)
    handoff_to_role_key: str | None = None
    next_step_ids: list[str] = Field(default_factory=list)
    on_approved_step_ids: list[str] = Field(default_factory=list)
    on_rejected_step_ids: list[str] = Field(default_factory=list)
    context_reads: list[str] = Field(default_factory=list)
    context_writes: list[str] = Field(default_factory=list)
    status: RunStatus = "pending"
    config: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] | None = None
    approval_id: str | None = None
    error: str | None = None


class PlaybookRun(BaseModel):
    id: str
    playbook_id: str
    role_key: str
    owner_role_key: str
    participant_role_keys: list[str] = Field(default_factory=list)
    status: RunStatus = "pending"
    scheduled_for: str
    steps: list[PlaybookRunStep] = Field(default_factory=list)
    current_step_index: int = 0
    current_step_id: str | None = None
    shared_context: dict[str, Any] = Field(default_factory=dict)
    updated_at: str | None = None


class PlaybookRunRegistry(BaseModel):
    runs: list[PlaybookRun] = Field(default_factory=list)
    updated_at: str | None = None


class ApprovalRequest(BaseModel):
    id: str
    run_id: str
    playbook_id: str
    role_key: str
    requested_by_role_key: str | None = None
    target_role_key: str | None = None
    step_id: str
    status: ApprovalStatus = "pending"
    message: str
    context: dict[str, Any] = Field(default_factory=dict)
    updated_at: str | None = None


class ApprovalRegistry(BaseModel):
    approvals: list[ApprovalRequest] = Field(default_factory=list)
    updated_at: str | None = None


class PlaybookParseRequest(BaseModel):
    role_key: str
    natural_language: str = Field(min_length=1)
    name: str | None = None


class PlaybookCreateRequest(BaseModel):
    role_key: str
    natural_language: str = Field(min_length=1)
    name: str = Field(min_length=1)
    steps: list[PlaybookStep] | None = None


class PlaybookParseResponse(BaseModel):
    role_key: str
    name: str
    trigger: PlaybookTrigger
    collaboration: CollaborationPolicy
    steps: list[PlaybookStep] = Field(default_factory=list)
    referenced_tools: list[str] = Field(default_factory=list)
    unresolved_tools: list[str] = Field(default_factory=list)


class PublicPlaybookRun(BaseModel):
    id: str
    playbook_id: str
    role_key: str
    owner_role_key: str
    participant_role_keys: list[str] = Field(default_factory=list)
    status: RunStatus
    scheduled_for: str
    steps: list[PlaybookRunStep] = Field(default_factory=list)
    current_step_index: int = 0
    shared_context: dict[str, Any] = Field(default_factory=dict)
    updated_at: str | None = None


class PlaybookExecuteResponse(BaseModel):
    run: PublicPlaybookRun
    approvals: list[ApprovalRequest] = Field(default_factory=list)
