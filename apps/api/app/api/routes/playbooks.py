from fastapi import APIRouter

from app.schemas.playbooks import (
    ApprovalRequest,
    Playbook,
    PlaybookCreateRequest,
    PlaybookExecuteResponse,
    PlaybookParseRequest,
    PlaybookParseResponse,
    PublicPlaybookRun,
)
from app.services.playbooks import (
    advance_run,
    create_playbook,
    list_approvals,
    list_playbooks,
    list_runs,
    parse_playbook,
    resolve_approval,
    trigger_playbook,
)

router = APIRouter()


@router.post("/parse", response_model=PlaybookParseResponse)
def parse_playbook_request(payload: PlaybookParseRequest) -> PlaybookParseResponse:
    return parse_playbook(payload)


@router.get("", response_model=list[Playbook])
def read_playbooks(role_key: str | None = None) -> list[Playbook]:
    return list_playbooks(role_key)


@router.post("", response_model=Playbook)
def create_playbook_request(payload: PlaybookCreateRequest) -> Playbook:
    return create_playbook(payload)


@router.get("/runs", response_model=list[PublicPlaybookRun])
def read_runs(playbook_id: str | None = None) -> list[PublicPlaybookRun]:
    return list_runs(playbook_id)


@router.post("/{playbook_id}/trigger", response_model=PublicPlaybookRun)
def trigger_playbook_request(playbook_id: str) -> PublicPlaybookRun:
    return trigger_playbook(playbook_id)


@router.post("/runs/{run_id}/advance", response_model=PlaybookExecuteResponse)
def advance_run_request(run_id: str) -> PlaybookExecuteResponse:
    return advance_run(run_id)


@router.get("/approvals", response_model=list[ApprovalRequest])
def read_approvals(role_key: str | None = None) -> list[ApprovalRequest]:
    return list_approvals(role_key)


@router.post("/approvals/{approval_id}/approve", response_model=ApprovalRequest)
def approve_request(approval_id: str) -> ApprovalRequest:
    return resolve_approval(approval_id, approved=True)


@router.post("/approvals/{approval_id}/reject", response_model=ApprovalRequest)
def reject_request(approval_id: str) -> ApprovalRequest:
    return resolve_approval(approval_id, approved=False)
