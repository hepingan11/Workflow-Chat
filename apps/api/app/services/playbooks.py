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
from app.services.agent_memory import record_completed_run_memory, retrieve_role_memory
from app.services.agent_skills import retrieve_role_skills
from app.services.message_formatter import format_message_for_boss, request_formatted_message, select_message_model
from app.services.notifications import send_approval_notification, send_message_push
from app.services.prompt_config import get_config_dir
from app.services.run_monitor import append_run_monitor_event, read_run_monitor
from app.services.time_parser import parse_trigger_time
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
    trigger = parse_trigger_time(natural_language, payload.role_key)
    trigger_time = trigger.time
    tool_names = _extract_tool_names(natural_language)

    tool_map, unresolved_tools = _resolve_tools(payload.role_key, tool_names)
    publish_time = _extract_publish_time(natural_language) or "14:00"
    needs_approval = _requires_human_approval(natural_language)
    needs_message_push = _requires_message_push(natural_language)
    terminal_step_id = _terminal_message_step_id(needs_approval, needs_message_push)

    steps: list[PlaybookStep] = []
    if not tool_names:
        steps.append(
            PlaybookStep(
                id="step_request_approval" if needs_approval else "step_push_message",
                name="请求人工审批" if needs_approval else "推送消息给我",
                type="human_approval" if needs_approval else "message_push",
                role_key=payload.role_key,
                assignee_role_key=payload.role_key,
                context_reads=[],
                config={
                    "channel": "message",
                    "message_template": natural_language or ("请确认是否执行该任务。" if needs_approval else "任务消息推送"),
                    "proceed_if": "approved",
                },
            )
        )

    if tool_names:
        steps.append(
            PlaybookStep(
                id="step_fetch_source",
                name=f"执行 {tool_names[0]}",
                type="tool",
                role_key=payload.role_key,
                assignee_role_key=payload.role_key,
                next_step_ids=["step_generate_asset"] if len(tool_names) >= 2 else ([terminal_step_id] if terminal_step_id else []),
                context_writes=["fetched_result"],
                config={
                    "tool_id": tool_map.get(tool_names[0], {}).get("id", ""),
                    "tool_name": tool_names[0],
                    "run_at": trigger_time,
                    "input_template": _build_initial_tool_input_template(
                        natural_language,
                        tool_names[0],
                        tool_map.get(tool_names[0], {}),
                        payload.role_key,
                    ),
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
                next_step_ids=[terminal_step_id] if terminal_step_id else [],
                context_reads=["fetched_result"],
                context_writes=["generated_asset"],
                config={
                    "tool_id": tool_map.get(tool_names[1], {}).get("id", ""),
                    "tool_name": tool_names[1],
                    "input_template": {
                        "prompt": _build_followup_tool_prompt(natural_language, tool_names[1]),
                    },
                    "needs_previous_output": True,
                },
            )
        )

    if tool_names and needs_approval:
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

    if tool_names and needs_message_push and not needs_approval:
        steps.append(
            PlaybookStep(
                id="step_push_message",
                name="推送结果给我",
                type="message_push",
                role_key=payload.role_key,
                assignee_role_key=payload.role_key,
                depends_on_step_ids=["step_generate_asset" if len(tool_names) >= 2 else "step_fetch_source"],
                context_reads=["generated_asset" if len(tool_names) >= 2 else "fetched_result"],
                config={
                    "channel": "message",
                    "message_template": "已完成任务，以下是执行结果。",
                    "include_previous_output": True,
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
                    "input_template": {
                        "prompt": _build_followup_tool_prompt(natural_language, tool_names[2]),
                    },
                    "needs_previous_output": True,
                },
            )
        )

    return PlaybookParseResponse(
        role_key=payload.role_key,
        name=payload.name or f"{agent.name}自动任务",
        trigger=trigger,
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
        name=append_random_suffix(parsed.name),
        natural_language=payload.natural_language,
        trigger=parsed.trigger,
        collaboration=parsed.collaboration,
        steps=payload.steps or parsed.steps,
        updated_at=_now(),
    )
    registry.playbooks.append(playbook)
    write_playbook_registry(registry)
    if is_one_shot_playbook(playbook):
        create_run_from_playbook(playbook, scheduled_for=get_initial_scheduled_for(playbook))
        remove_playbook_definition(playbook.id)
    return playbook


def append_random_suffix(name: str) -> str:
    return f"{name}-{uuid4().hex[:6]}"


def is_one_shot_playbook(playbook: Playbook) -> bool:
    return playbook.trigger.type in {"immediate", "scheduled"}


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


def delete_playbook(playbook_id: str) -> Playbook:
    registry = read_playbook_registry()
    playbook = next((item for item in registry.playbooks if item.id == playbook_id), None)
    if playbook is None:
        raise HTTPException(status_code=404, detail="Playbook not found")

    registry.playbooks = [item for item in registry.playbooks if item.id != playbook_id]
    write_playbook_registry(registry)

    run_registry = read_run_registry()
    run_registry.runs = [item for item in run_registry.runs if item.playbook_id != playbook_id]
    write_run_registry(run_registry)

    approval_registry = read_approval_registry()
    approval_registry.approvals = [item for item in approval_registry.approvals if item.playbook_id != playbook_id]
    write_approval_registry(approval_registry)

    return playbook


def remove_playbook_definition(playbook_id: str) -> Playbook | None:
    registry = read_playbook_registry()
    playbook = next((item for item in registry.playbooks if item.id == playbook_id), None)
    if playbook is None:
        return None

    registry.playbooks = [item for item in registry.playbooks if item.id != playbook_id]
    write_playbook_registry(registry)
    return playbook


def trigger_playbook(playbook_id: str, scheduled_for: str | None = None) -> PublicPlaybookRun:
    playbook = get_playbook(playbook_id)
    if playbook is None:
        raise HTTPException(status_code=404, detail="Playbook not found")

    return create_run_from_playbook(playbook, scheduled_for=scheduled_for)


def create_run_from_playbook(playbook: Playbook, scheduled_for: str | None = None) -> PublicPlaybookRun:
    run_registry = read_run_registry()
    run = PlaybookRun(
        id=f"run_{uuid4().hex[:12]}",
        playbook_id=playbook.id,
        role_key=playbook.role_key,
        owner_role_key=playbook.collaboration.owner_role_key,
        participant_role_keys=playbook.collaboration.participant_role_keys,
        status="pending",
        scheduled_for=scheduled_for or get_initial_scheduled_for(playbook),
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
        shared_context={
            "playbook_name": playbook.name,
            "natural_language": playbook.natural_language,
        },
        updated_at=_now(),
    )
    run_registry.runs.append(run)
    write_run_registry(run_registry)
    return to_public_run(run)


def get_initial_scheduled_for(playbook: Playbook) -> str:
    if playbook.trigger.type == "immediate":
        return _now()
    return playbook.trigger.run_at or _today_with_time(playbook.trigger.time)


def list_runs(playbook_id: str | None = None) -> list[PublicPlaybookRun]:
    runs = read_run_registry().runs
    if playbook_id:
      runs = [item for item in runs if item.playbook_id == playbook_id]
    return [to_public_run(run) for run in runs]


def get_run_monitor(run_id: str) -> dict:
    return read_run_monitor(run_id)


def delete_run(run_id: str) -> PublicPlaybookRun:
    registry = read_run_registry()
    run = next((item for item in registry.runs if item.id == run_id), None)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    registry.runs = [item for item in registry.runs if item.id != run_id]
    write_run_registry(registry)

    approval_registry = read_approval_registry()
    approval_registry.approvals = [item for item in approval_registry.approvals if item.run_id != run_id]
    write_approval_registry(approval_registry)
    return to_public_run(run)


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

        step.error = None

        append_run_monitor_event(
            run.id,
            "step_started",
            f"Step started: {step.name}",
            step_id=step.id,
            step_name=step.name,
            payload={"step_type": step.type, "status": step.status},
        )

        if step.type == "human_approval":
            approval = _get_or_create_approval(run, step, approval_registry)
            step.approval_id = approval.id
            if approval.status == "pending":
                step.status = "waiting_approval"
                run.status = "waiting_approval"
                break
            if approval.status == "rejected":
                step.status = "cancelled"
                step.error = None
                run.status = "cancelled"
                _advance_to_next(run, step, approved=False)
                run.updated_at = _now()
                break
            step.status = "completed"
            step.error = None
            step.output = {"approval_status": approval.status}
            _write_step_output_to_context(run, step)
            append_run_monitor_event(run.id, "step_completed", f"Step completed: {step.name}", step_id=step.id, step_name=step.name)
            _advance_to_next(run, step, approved=True)
            continue

        if step.type == "message_push":
            step.status = "running"
            step.error = None
            raw_content = None
            formatted_content = None
            try:
                raw_content = _build_message_push_content(run, step)
                formatted_content = format_message_for_boss(
                    step.assignee_role_key or run.role_key,
                    step.config.get("message_template", "工作流消息"),
                    raw_content,
                )
                if not formatted_content.ok:
                    raise RuntimeError(formatted_content.error or "LLM 消息加工失败，消息未推送。")
                message_result = send_message_push(
                    title=step.config.get("message_template", "工作流消息"),
                    content=formatted_content.content,
                    context={
                        "run_id": run.id,
                        "step_name": step.name,
                        "owner_role_key": run.owner_role_key,
                        "participant_role_keys": run.participant_role_keys,
                    },
                )
                if not message_result.get("ok"):
                    step.output = {
                        "notification": message_result,
                        "formatted_message": formatted_content.content,
                        "formatting": {
                            "model_name": formatted_content.model_name,
                            "used_employee_prompt": formatted_content.used_employee_prompt,
                            "used_boss_profile": formatted_content.used_boss_profile,
                        },
                    }
                    raise RuntimeError(str(message_result.get("message", "消息推送失败。")))
                step.status = "completed"
                step.error = None
                step.output = {
                    "notification": message_result,
                    "formatted_message": formatted_content.content,
                    "formatting": {
                        "model_name": formatted_content.model_name,
                        "used_employee_prompt": formatted_content.used_employee_prompt,
                        "used_boss_profile": formatted_content.used_boss_profile,
                    },
                }
                _write_step_output_to_context(run, step)
                append_run_monitor_event(run.id, "step_completed", f"Step completed: {step.name}", step_id=step.id, step_name=step.name)
                _advance_to_next(run, step)
                run.status = "running"
            except Exception as exc:
                step.status = "failed"
                step.error = str(exc)
                append_run_monitor_event(run.id, "step_failed", str(exc), step_id=step.id, step_name=step.name)
                step.output = {
                    **(step.output or {}),
                    "formatting": (step.output or {}).get("formatting")
                    or (formatted_content.model_dump() if formatted_content else None),
                    "raw_content_preview": str(raw_content)[:1000] if raw_content is not None else None,
                }
                run.status = "failed"
                break
            continue

        if step.type == "tool":
            scheduled_time = step.config.get("run_at")
            if scheduled_time and step.id != run.steps[0].id and not _time_ready(scheduled_time):
                step.status = "scheduled"
                run.status = "scheduled"
                break

            step.status = "running"
            step.error = None
            try:
                tool_inputs = _build_tool_inputs(run, step)
                tool_inputs["_monitor"] = {
                    "run_id": run.id,
                    "step_id": step.id,
                    "step_name": step.name,
                }
                tool_result = execute_agent_tool(
                    step.assignee_role_key or run.role_key,
                    step.config["tool_id"],
                    tool_inputs,
                    user=f"playbook-{run.playbook_id}",
                )
                step.status = "completed"
                step.error = None
                step.output = tool_result.result
                _write_step_output_to_context(run, step)
                append_run_monitor_event(run.id, "step_completed", f"Step completed: {step.name}", step_id=step.id, step_name=step.name)
                _advance_to_next(run, step)
                run.status = "running"
            except Exception as exc:
                step.status = "failed"
                step.error = str(exc)
                append_run_monitor_event(run.id, "step_failed", str(exc), step_id=step.id, step_name=step.name)
                run.status = "failed"
                break
            continue

        if step.type == "handoff":
            step.status = "completed"
            step.error = None
            append_run_monitor_event(run.id, "step_completed", f"Step completed: {step.name}", step_id=step.id, step_name=step.name)
            _advance_to_next(run, step)
            continue

        if step.type == "noop":
            step.status = "completed"
            step.error = None
            append_run_monitor_event(run.id, "step_completed", f"Step completed: {step.name}", step_id=step.id, step_name=step.name)
            _advance_to_next(run, step)
            continue

    if all(item.status in {"completed", "cancelled"} for item in run.steps) and run.status not in {"failed", "cancelled"}:
        run.status = "completed"

    run.updated_at = _now()
    if run.status in {"completed", "cancelled", "failed"} and not run.shared_context.get("memory_reflection_done"):
        reflection = record_completed_run_memory(run)
        run.shared_context["memory_reflection_done"] = reflection.task.id if reflection else "skipped"
    write_run_registry(run_registry)
    write_approval_registry(approval_registry)
    cleanup_one_shot_playbook_after_run(run)
    approvals = [item for item in approval_registry.approvals if item.run_id == run.id]
    return PlaybookExecuteResponse(run=to_public_run(run), approvals=approvals)


def cleanup_one_shot_playbook_after_run(run: PlaybookRun) -> None:
    if run.status not in {"completed", "cancelled"}:
        return

    playbook = get_playbook(run.playbook_id)
    if playbook is None:
        return
    if playbook.trigger.type not in {"immediate", "scheduled"}:
        return

    remove_playbook_definition(playbook.id)


def resolve_approval(approval_id: str, approved: bool) -> ApprovalRequest:
    registry = read_approval_registry()
    approval = next((item for item in registry.approvals if item.id == approval_id), None)
    if approval is None:
        raise HTTPException(status_code=404, detail="Approval not found")
    approval.status = "approved" if approved else "rejected"
    approval.updated_at = _now()
    write_approval_registry(registry)
    return approval


def resolve_approval_and_advance(approval_id: str, approved: bool) -> PlaybookExecuteResponse:
    approval = resolve_approval(approval_id, approved)
    return advance_run(approval.run_id)


def to_public_run(run: PlaybookRun) -> PublicPlaybookRun:
    return PublicPlaybookRun(**run.model_dump())


def _resolve_tools(role_key: str, tool_names: list[str]) -> tuple[dict[str, dict], list[str]]:
    tools = {tool.name: tool for tool in list_tools() if tool.enabled}
    resolved: dict[str, dict] = {}
    unresolved: list[str] = []
    for tool_name in tool_names:
        tool = tools.get(tool_name)
        if tool is None:
            unresolved.append(tool_name)
            continue
        resolved[tool_name] = {
            "id": tool.id,
            "name": tool.name,
            "description": tool.description,
            "provider": tool.provider,
        }
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


def _extract_publish_time(text: str) -> str | None:
    if "下午2点" in text or "14:00" in text:
        return "14:00"
    return None


def _requires_human_approval(text: str) -> bool:
    return any(keyword in text for keyword in ["审批", "确认", "审核", "没问题后", "通过后", "同意后"])


def _terminal_message_step_id(needs_approval: bool, needs_message_push: bool) -> str | None:
    if needs_approval:
        return "step_request_approval"
    if needs_message_push:
        return "step_push_message"
    return None


def _requires_message_push(text: str) -> bool:
    keywords = [
        "\u53d1\u7ed9\u6211",
        "\u53d1\u9001\u7ed9\u6211",
        "\u63a8\u9001\u7ed9\u6211",
        "\u901a\u77e5\u6211",
        "\u544a\u8bc9\u6211",
        "\u63d0\u9192\u6211",
        "\u6d88\u606f\u63d0\u793a\u6211",
        "\u53d1\u6d88\u606f\u7ed9\u6211",
        "\u53d1\u6d88\u606f\u63d0\u793a\u6211",
        "\u628a\u7ed3\u679c\u53d1\u6211",
        "\u5b8c\u6210\u540e\u544a\u8bc9\u6211",
        "\u505a\u5b8c\u540e\u544a\u8bc9\u6211",
    ]
    normalized = re.sub(r"\s+", "", text)
    return any(keyword in normalized for keyword in keywords)


def _build_initial_tool_input_template(
    natural_language: str,
    tool_name: str,
    tool_info: dict,
    role_key: str,
) -> dict:
    provider = str(tool_info.get("provider") or "")
    if provider in {"codex", "llm_chat_response", "codex_cli"}:
        return {
            "prompt": _refine_tool_prompt_with_llm(
                natural_language,
                tool_name,
                tool_info,
                role_key,
            )
        }
    return {"topic": _extract_tool_topic(natural_language, tool_name)}


def _extract_tool_topic(natural_language: str, tool_name: str) -> str:
    text = _strip_mentions_and_tool_refs(natural_language)
    text = _strip_message_push_intent(text)
    text = re.sub(r"\b(use|with)\b", "", text, flags=re.IGNORECASE)
    text = text.replace("使用", "").replace("运行", "").replace("执行", "").replace(tool_name, "")
    text = re.sub(r"\s+", " ", text).strip(" ，,。；;")
    return text or natural_language.strip() or tool_name


def _build_initial_tool_prompt(natural_language: str, tool_name: str, tool_info: dict) -> str:
    task = _strip_message_push_intent(_strip_mentions_and_tool_refs(natural_language)).strip(" ，,。；;")
    tool_description = str(tool_info.get("description") or "").strip()
    lines = [
        f"你正在作为工具「{tool_name}」执行用户任务。",
        f"用户原始需求：{natural_language}",
    ]
    if tool_description:
        lines.append(f"工具说明：{tool_description}")
    lines.extend(
        [
            "",
            "请完成以下执行目标：",
            task or natural_language,
            "",
            "执行要求：",
            "1. 直接完成用户要求的实际操作或检查，不要把任务改写成无关主题。",
            "2. 如果涉及本地文件、目录或终端环境，请基于当前工作目录和可访问环境进行检查。",
            "3. 输出清晰的执行结果，包含发现、关键路径/文件名和必要的下一步建议。",
            "4. 如果遇到权限、路径或环境限制，请说明具体限制和你已经尝试的操作。",
        ]
    )
    return "\n".join(lines)


def _refine_tool_prompt_with_llm(
    natural_language: str,
    tool_name: str,
    tool_info: dict,
    role_key: str,
) -> str:
    fallback = _build_initial_tool_prompt(natural_language, tool_name, tool_info)
    model = select_message_model(role_key)
    if not model:
        return fallback

    system_prompt = (
        "你是工作流工具输入整理器。你的任务是把用户自然语言需求整理成适合交给工具执行的 prompt。\n"
        "只输出 prompt 正文，不要输出 JSON，不要解释过程。\n"
        "必须保留用户的真实意图，不要替换成默认主题，不要编造用户没有要求的任务。\n"
        "如果用户要求“发给我/告诉我/推送给我”，不要让当前工具负责发消息；当前工具只需产出可被下一步推送的结果。"
    )
    user_prompt = "\n".join(
        [
            f"角色：{role_key}",
            f"工具名称：{tool_name}",
            f"工具类型：{tool_info.get('provider') or 'unknown'}",
            f"工具说明：{tool_info.get('description') or '未填写'}",
            "",
            f"用户原始需求：{natural_language}",
            "",
            "请生成适合该工具执行的 prompt。",
            "要求：",
            "1. prompt 必须能直接交给工具执行。",
            "2. 如果是 Codex/Codex CLI，请写成面向代码代理/终端代理的具体执行指令。",
            "3. 不要包含消息推送动作，只说明需要产出的结果内容。",
            "4. 不要使用 topic 字段，不要输出结构化 JSON。",
        ]
    )
    try:
        refined = request_formatted_message(
            model,
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        ).strip()
    except Exception:
        return fallback
    return refined or fallback


def _strip_mentions_and_tool_refs(text: str) -> str:
    text = re.sub(r"@\w+", "", text)
    text = re.sub(r"#\{[^}]+\}", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _strip_message_push_intent(text: str) -> str:
    patterns = [
        r"(然后|并且|再)?\s*(发给我|发送给我|推送给我|通知我|告诉我|提醒我|发消息给我|把结果发我)\s*$",
        r"(完成后|做完后)\s*(发给我|告诉我|通知我|提醒我)\s*$",
    ]
    result = text
    for pattern in patterns:
        result = re.sub(pattern, "", result).strip()
    return result


def _build_followup_tool_prompt(natural_language: str, tool_name: str) -> str:
    return (
        f"请根据上一步工具输出继续完成当前任务。当前工具：{tool_name}。\n"
        f"用户原始需求：{natural_language}\n"
        "要求：\n"
        "1. 优先使用 previous_output / fetched_result 中的内容作为输入。\n"
        "2. 如果用户要求生成文件、文档、代码或素材，请直接按要求产出。\n"
        "3. 如果需要返回给用户，请输出清晰的执行结果摘要、生成内容位置和下一步建议。\n"
        "4. 不要只复述上一步结果，要完成当前工具应该承担的加工动作。"
    )


def _build_tool_inputs(run: PlaybookRun, step: PlaybookRunStep) -> dict:
    role_key = step.assignee_role_key or run.role_key
    query = str(run.shared_context.get("natural_language") or run.shared_context.get("playbook_name") or "")
    memory = retrieve_role_memory(role_key, query)
    selected_skill_ids = step.config.get("selected_skill_ids")
    if not isinstance(selected_skill_ids, list):
        selected_skill_ids = None
    skills = retrieve_role_skills(role_key, query, skill_ids=selected_skill_ids)
    if not step.config.get("needs_previous_output"):
        return {
            **step.config.get("input_template", {}),
            "shared_context": run.shared_context,
            "long_term_memory": memory.model_dump(),
            "skills": skills.model_dump(),
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
        "long_term_memory": memory.model_dump(),
        "skills": skills.model_dump(),
    }
    for key in step.context_reads:
        if key in run.shared_context:
            inputs[key] = run.shared_context[key]
    return inputs


def _build_message_push_content(run: PlaybookRun, step: PlaybookRunStep):
    for key in step.context_reads:
        if key in run.shared_context:
            return run.shared_context[key]

    current_index = next((index for index, item in enumerate(run.steps) if item.id == step.id), 0)
    for previous_step in reversed(run.steps[:current_index]):
        if previous_step.output:
            return previous_step.output
    return run.shared_context or step.config.get("message_template")


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
    try:
        notification_result = send_approval_notification(approval)
        approval.context["notification"] = notification_result
    except Exception as exc:
        approval.context["notification"] = {
            "ok": False,
            "channel": "telegram",
            "error": str(exc),
        }
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
