import json
import re
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException

from app.schemas.playbooks import (
    ApprovalRegistry,
    ApprovalRequest,
    CollaborationPolicy,
    Playbook,
    PlaybookCreateRequest,
    PlaybookExecuteResponse,
    PlaybookParseRequest,
    PlaybookParseResponse,
    PlaybookRegistry,
    PlaybookRun,
    PlaybookRunRegistry,
    PlaybookRunStep,
    PlaybookStep,
    PlaybookTrigger,
    PublicPlaybookRun,
)
from app.services.agent_registry import get_agent
from app.services.agent_tools import execute_agent_tool
from app.services.prompt_config import get_config_dir
from app.services.tool_registry import list_tools


def get_playbook_registry_path() -> Path:
    return get_config_dir() / "playbooks.json"


def get_run_registry_path() -> Path:
    return get_config_dir() / "playbook-runs.json"


def get_approval_registry_path() -> Path:
    return get_config_dir() / "approvals.json"


def read_playbook_registry() -> PlaybookRegistry:
    return _read_registry(get_playbook_registry_path(), PlaybookRegistry)


def write_playbook_registry(registry: PlaybookRegistry) -> PlaybookRegistry:
    return _write_registry(get_playbook_registry_path(), registry)


def read_run_registry() -> PlaybookRunRegistry:
    return _read_registry(get_run_registry_path(), PlaybookRunRegistry)


def write_run_registry(registry: PlaybookRunRegistry) -> PlaybookRunRegistry:
    return _write_registry(get_run_registry_path(), registry)


def read_approval_registry() -> ApprovalRegistry:
    return _read_registry(get_approval_registry_path(), ApprovalRegistry)


def write_approval_registry(registry: ApprovalRegistry) -> ApprovalRegistry:
    return _write_registry(get_approval_registry_path(), registry)


def parse_playbook(payload: PlaybookParseRequest) -> PlaybookParseResponse:
    agent = get_agent(payload.role_key)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    natural_language = payload.natural_language.strip()
    trigger_time = _extract_trigger_time(natural_language)
    tool_names = _extract_tool_names(natural_language)
    if len(tool_names) < 2:
        raise HTTPException(status_code=400, detail="至少需要在描述中引用两个工具，例如 #{工具名}")

    tool_map, unresolved_tools = _resolve_tools(payload.role_key, tool_names)
    publish_time = _extract_publish_time(natural_language) or "14:00"

    steps: list[PlaybookStep] = []
    if tool_names:
        steps.append(
            PlaybookStep(
                id="step_fetch_source",
                name=f"执行 {tool_names[0]}",
                type="tool",
                role_key=payload.role_key,
                assignee_role_key=payload.role_key,
                next_step_ids=["step_generate_asset" if len(tool_names) >= 2 else "step_request_approval"],
                context_writes=["fetched_result"],
                config={
                    "tool_id": tool_map.get(tool_names[0], {}).get("id", ""),
                    "tool_name": tool_names[0],
                    "run_at": trigger_time,
                    "input_template": {"topic": "AI 最新新闻"},
                    "needs_previous_output": False,
                },
            )
        )

    if len(tool_names) >= 2:
        steps.append(
            PlaybookStep(
                id="step_generate_asset",
                name=f"执行 {tool_names[1]}",
                type="tool",
                role_key=payload.role_key,
                assignee_role_key=payload.role_key,
                depends_on_step_ids=["step_fetch_source"],
                next_step_ids=["step_request_approval"],
                context_reads=["fetched_result"],
                context_writes=["generated_asset"],
                config={
                    "tool_id": tool_map.get(tool_names[1], {}).get("id", ""),
                    "tool_name": tool_names[1],
                    "input_template": {},
                    "needs_previous_output": True,
                },
            )
        )

    steps.append(
        PlaybookStep(
            id="step_request_approval",
            name="请求人工审批",
            type="human_approval",
            role_key=payload.role_key,
            assignee_role_key=payload.role_key,
            depends_on_step_ids=["step_generate_asset" if len(tool_names) >= 2 else "step_fetch_source"],
            on_approved_step_ids=["step_publish"] if len(tool_names) >= 3 else [],
            on_rejected_step_ids=[],
            context_reads=["generated_asset" if len(tool_names) >= 2 else "fetched_result"],
            config={
                "channel": "message",
                "message_template": "请确认今日运营内容是否可发布；若有问题则不发布。",
                "proceed_if": "approved",
            },
        )
    )

    if len(tool_names) >= 3:
        steps.append(
            PlaybookStep(
                id="step_publish",
                name=f"执行 {tool_names[2]}",
                type="tool",
                role_key=payload.role_key,
                assignee_role_key=payload.role_key,
                depends_on_step_ids=["step_request_approval"],
                context_reads=["generated_asset"],
                context_writes=["publish_result"],
                config={
                    "tool_id": tool_map.get(tool_names[2], {}).get("id", ""),
                    "tool_name": tool_names[2],
                    "run_at": publish_time,
                    "input_template": {},
                    "needs_previous_output": True,
                },
            )
        )

    return PlaybookParseResponse(
        role_key=payload.role_key,
        name=payload.name or f"{agent.name}自动任务",
        trigger=PlaybookTrigger(time=trigger_time),
        collaboration=CollaborationPolicy(owner_role_key=payload.role_key),
        steps=steps,
        referenced_tools=tool_names,
        unresolved_tools=unresolved_tools,
    )


def create_playbook(payload: PlaybookCreateRequest) -> Playbook:
    parsed = parse_playbook(
        PlaybookParseRequest(
            role_key=payload.role_key,
            natural_language=payload.natural_language,
            name=payload.name,
        )
    )
    if parsed.unresolved_tools:
        raise HTTPException(
            status_code=400,
            detail=f"以下工具尚未注册或未授权给该角色：{', '.join(parsed.unresolved_tools)}",
        )
    registry = read_playbook_registry()
    playbook = Playbook(
        id=f"playbook_{uuid4().hex[:12]}",
        role_key=payload.role_key,
        name=parsed.name,
        natural_language=payload.natural_language,
        trigger=parsed.trigger,
        collaboration=parsed.collaboration,
        steps=parsed.steps,
        updated_at=_now(),
    )
    registry.playbooks.append(playbook)
    write_playbook_registry(registry)
    return playbook


def list_playbooks(role_key: str | None = None) -> list[Playbook]:
    playbooks = read_playbook_registry().playbooks
    if role_key:
        return [item for item in playbooks if item.role_key == role_key]
    return playbooks


def get_playbook(playbook_id: str) -> Playbook | None:
    for item in read_playbook_registry().playbooks:
        if item.id == playbook_id:
            return item
    return None


def trigger_playbook(playbook_id: str) -> PublicPlaybookRun:
    playbook = get_playbook(playbook_id)
    if playbook is None:
        raise HTTPException(status_code=404, detail="Playbook not found")

    run_registry = read_run_registry()
    run = PlaybookRun(
        id=f"run_{uuid4().hex[:12]}",
        playbook_id=playbook.id,
        role_key=playbook.role_key,
        owner_role_key=playbook.collaboration.owner_role_key,
        participant_role_keys=playbook.collaboration.participant_role_keys,
        status="pending",
        scheduled_for=_today_with_time(playbook.trigger.time),
        steps=[
            PlaybookRunStep(
                id=step.id,
                name=step.name,
                type=step.type,
                role_key=step.role_key,
                assignee_role_key=step.assignee_role_key,
                participant_role_keys=step.participant_role_keys,
                depends_on_step_ids=step.depends_on_step_ids,
                handoff_to_role_key=step.handoff_to_role_key,
                next_step_ids=step.next_step_ids,
                on_approved_step_ids=step.on_approved_step_ids,
                on_rejected_step_ids=step.on_rejected_step_ids,
                context_reads=step.context_reads,
                context_writes=step.context_writes,
                status="pending",
                config=step.config,
            )
            for step in playbook.steps
        ],
        current_step_id=playbook.steps[0].id if playbook.steps else None,
        updated_at=_now(),
    )
    run_registry.runs.append(run)
    write_run_registry(run_registry)
    return to_public_run(run)


def list_runs(playbook_id: str | None = None) -> list[PublicPlaybookRun]:
    runs = read_run_registry().runs
    if playbook_id:
      runs = [item for item in runs if item.playbook_id == playbook_id]
    return [to_public_run(run) for run in runs]


def list_approvals(role_key: str | None = None) -> list[ApprovalRequest]:
    approvals = read_approval_registry().approvals
    if role_key:
        return [item for item in approvals if item.role_key == role_key]
    return approvals


def advance_run(run_id: str) -> PlaybookExecuteResponse:
    run_registry = read_run_registry()
    approval_registry = read_approval_registry()
    run = next((item for item in run_registry.runs if item.id == run_id), None)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    while True:
        step = _get_current_step(run)
        if step is None:
            break

        if step.type == "human_approval":
            approval = _get_or_create_approval(run, step, approval_registry)
            step.approval_id = approval.id
            if approval.status == "pending":
                step.status = "waiting_approval"
                run.status = "waiting_approval"
                break
            if approval.status == "rejected":
                step.status = "cancelled"
                run.status = "cancelled"
                _advance_to_next(run, step, approved=False)
                run.updated_at = _now()
                break
            step.status = "completed"
            step.output = {"approval_status": approval.status}
            _write_step_output_to_context(run, step)
            _advance_to_next(run, step, approved=True)
            continue

        if step.type == "tool":
            scheduled_time = step.config.get("run_at")
            if scheduled_time and step.id != run.steps[0].id and not _time_ready(scheduled_time):
                step.status = "scheduled"
                run.status = "scheduled"
                break

            step.status = "running"
            try:
                tool_inputs = _build_tool_inputs(run, step)
                tool_result = execute_agent_tool(
                    step.assignee_role_key or run.role_key,
                    step.config["tool_id"],
                    tool_inputs,
                    user=f"playbook-{run.playbook_id}",
                )
                step.status = "completed"
                step.output = tool_result.result
                _write_step_output_to_context(run, step)
                _advance_to_next(run, step)
                run.status = "running"
            except Exception as exc:
                step.status = "failed"
                step.error = str(exc)
                run.status = "failed"
                break
            continue

        if step.type == "handoff":
            step.status = "completed"
            _advance_to_next(run, step)
            continue

        if step.type == "noop":
            step.status = "completed"
            _advance_to_next(run, step)
            continue

    if all(item.status in {"completed", "cancelled"} for item in run.steps) and run.status not in {"failed", "cancelled"}:
        run.status = "completed"

    run.updated_at = _now()
    write_run_registry(run_registry)
    write_approval_registry(approval_registry)
    approvals = [item for item in approval_registry.approvals if item.run_id == run.id]
    return PlaybookExecuteResponse(run=to_public_run(run), approvals=approvals)


def resolve_approval(approval_id: str, approved: bool) -> ApprovalRequest:
    registry = read_approval_registry()
    approval = next((item for item in registry.approvals if item.id == approval_id), None)
    if approval is None:
        raise HTTPException(status_code=404, detail="Approval not found")
    approval.status = "approved" if approved else "rejected"
    approval.updated_at = _now()
    write_approval_registry(registry)
    return approval


def to_public_run(run: PlaybookRun) -> PublicPlaybookRun:
    return PublicPlaybookRun(**run.model_dump())


def _resolve_tools(role_key: str, tool_names: list[str]) -> tuple[dict[str, dict], list[str]]:
    tools = {tool.name: tool for tool in list_tools() if tool.enabled and role_key in tool.allowed_roles}
    resolved: dict[str, dict] = {}
    unresolved: list[str] = []
    for tool_name in tool_names:
        tool = tools.get(tool_name)
        if tool is None:
            unresolved.append(tool_name)
            continue
        resolved[tool_name] = {"id": tool.id}
    return resolved, unresolved


def _extract_tool_names(text: str) -> list[str]:
    matches = re.findall(r"#\{([^}]+)\}", text)
    tool_names: list[str] = []
    for match in matches:
        for item in match.split(","):
            name = item.strip()
            if name and name not in tool_names:
                tool_names.append(name)
    return tool_names


def _extract_trigger_time(text: str) -> str:
    if "8点" in text or "08:00" in text:
        return "08:00"
    return "09:00"


def _extract_publish_time(text: str) -> str | None:
    if "下午2点" in text or "14:00" in text:
        return "14:00"
    return None


def _build_tool_inputs(run: PlaybookRun, step: PlaybookRunStep) -> dict:
    if not step.config.get("needs_previous_output"):
        return {
            **step.config.get("input_template", {}),
            "shared_context": run.shared_context,
        }

    previous_output = None
    current_index = next((index for index, item in enumerate(run.steps) if item.id == step.id), 0)
    for previous_step in reversed(run.steps[:current_index]):
        if previous_step.output:
            previous_output = previous_step.output
            break

    inputs = {
        **step.config.get("input_template", {}),
        "previous_output": previous_output,
        "playbook_run_id": run.id,
        "shared_context": run.shared_context,
    }
    for key in step.context_reads:
        if key in run.shared_context:
            inputs[key] = run.shared_context[key]
    return inputs


def _get_or_create_approval(
    run: PlaybookRun,
    step: PlaybookRunStep,
    registry: ApprovalRegistry,
) -> ApprovalRequest:
    approval = next((item for item in registry.approvals if item.run_id == run.id and item.step_id == step.id), None)
    if approval:
        return approval

    approval = ApprovalRequest(
        id=f"approval_{uuid4().hex[:12]}",
        run_id=run.id,
        playbook_id=run.playbook_id,
        role_key=run.role_key,
        requested_by_role_key=step.assignee_role_key or run.role_key,
        target_role_key="user",
        step_id=step.id,
        message=step.config.get("message_template", "请审批"),
        context={
            "run_id": run.id,
            "step_name": step.name,
            "owner_role_key": run.owner_role_key,
            "participant_role_keys": run.participant_role_keys,
        },
        updated_at=_now(),
    )
    registry.approvals.append(approval)
    return approval


def _get_current_step(run: PlaybookRun) -> PlaybookRunStep | None:
    if run.current_step_id:
        for step in run.steps:
            if step.id == run.current_step_id:
                return step
    for step in run.steps:
        if step.status == "pending":
            return step
    return None


def _advance_to_next(run: PlaybookRun, step: PlaybookRunStep, approved: bool | None = None) -> None:
    next_ids = step.next_step_ids
    if approved is True and step.on_approved_step_ids:
        next_ids = step.on_approved_step_ids
    if approved is False:
        next_ids = step.on_rejected_step_ids

    if next_ids:
        run.current_step_id = next_ids[0]
        next_index = next((index for index, item in enumerate(run.steps) if item.id == next_ids[0]), run.current_step_index)
        run.current_step_index = next_index
        return

    current_index = next((index for index, item in enumerate(run.steps) if item.id == step.id), run.current_step_index)
    run.current_step_index = current_index + 1
    run.current_step_id = run.steps[current_index + 1].id if current_index + 1 < len(run.steps) else None


def _write_step_output_to_context(run: PlaybookRun, step: PlaybookRunStep) -> None:
    if not step.output:
        return
    for key in step.context_writes:
        run.shared_context[key] = step.output


def _read_registry(path: Path, schema):
    if not path.exists():
        registry = schema()
        _write_registry(path, registry)
        return registry
    data = json.loads(path.read_text(encoding="utf-8"))
    return schema(**data)


def _write_registry(path: Path, registry):
    registry.updated_at = _now()
    path.write_text(json.dumps(registry.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")
    return registry


def _today_with_time(time_value: str) -> str:
    today = datetime.now(UTC).astimezone().date().isoformat()
    return f"{today}T{time_value}:00"


def _time_ready(time_value: str) -> bool:
    now = datetime.now().strftime("%H:%M")
    return now >= time_value


def _now() -> str:
    return datetime.now(UTC).isoformat()
