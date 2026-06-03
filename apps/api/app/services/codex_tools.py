import json
import subprocess
from pathlib import Path
from shutil import which
from typing import Any

import httpx

from app.schemas.tools import ToolRecord


def execute_codex_tool(tool: ToolRecord, inputs: dict[str, Any], user: str) -> dict[str, Any]:
    return execute_llm_chat_response_tool(tool, inputs, user)


def execute_llm_chat_response_tool(tool: ToolRecord, inputs: dict[str, Any], user: str) -> dict[str, Any]:
    prompt = _extract_prompt(inputs)
    payload = {
        "model": tool.connection.model,
        "input": prompt,
        "metadata": {
            "user": user,
            "tool_id": tool.id,
            "tool_name": tool.name,
        },
    }
    response = httpx.post(
        _build_codex_url(tool.connection.base_url, tool.connection.endpoint_path),
        headers={
            "Authorization": f"Bearer {tool.connection.api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=tool.connection.timeout_seconds,
    )
    response.raise_for_status()
    return response.json()


def execute_codex_cli_tool(tool: ToolRecord, inputs: dict[str, Any], user: str) -> dict[str, Any]:
    prompt = _extract_prompt(inputs)
    command = _resolve_codex_command(tool.connection.codex_command.strip() or "codex")
    working_directory = tool.connection.working_directory.strip() or None
    if working_directory and not Path(working_directory).exists():
        raise FileNotFoundError(f"Working Directory does not exist: {working_directory}")
    timeout_seconds = max(tool.connection.timeout_seconds, 1)
    argv = [
        command,
        "exec",
        "--json",
        "--dangerously-bypass-approvals-and-sandbox",
        prompt,
    ]
    if working_directory:
        argv[2:2] = ["--cd", working_directory]
    completed = subprocess.run(
        argv,
        cwd=working_directory,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_seconds,
    )
    parsed = _parse_codex_jsonl(completed.stdout)
    return {
        "ok": completed.returncode == 0,
        "provider": "codex_cli",
        "command": " ".join(argv[:-1] + ["<prompt>"]),
        "working_directory": working_directory,
        "approval_policy": "bypass",
        "sandbox": "danger-full-access",
        "user": user,
        "returncode": completed.returncode,
        "thread_id": parsed["thread_id"],
        "message": parsed["message"],
        "usage": parsed["usage"],
        "events": parsed["events"],
        "stdout": completed.stdout[-4000:],
        "stderr": completed.stderr[-4000:],
    }


def _resolve_codex_command(command: str) -> str:
    if "\\" in command or "/" in command:
        return command
    candidates = [command]
    if not command.lower().endswith((".cmd", ".exe", ".bat", ".ps1")):
        candidates.extend([f"{command}.cmd", f"{command}.exe", f"{command}.bat"])
    for candidate in candidates:
        resolved = which(candidate)
        if resolved:
            return resolved
    return command


def _extract_prompt(inputs: dict[str, Any]) -> str:
    for key in ("prompt", "task", "instruction", "input"):
        value = inputs.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return str(inputs)


def _parse_codex_jsonl(stdout: str) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    messages: list[str] = []
    thread_id = ""
    usage: dict[str, Any] = {}
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except ValueError:
            events.append({"type": "raw", "text": line})
            continue
        events.append(event)
        if event.get("type") == "thread.started":
            thread_id = str(event.get("thread_id", ""))
        if event.get("type") == "turn.completed" and isinstance(event.get("usage"), dict):
            usage = event["usage"]
        item = event.get("item")
        if event.get("type") == "item.completed" and isinstance(item, dict):
            if item.get("type") == "agent_message" and isinstance(item.get("text"), str):
                messages.append(item["text"])
    return {
        "events": events,
        "thread_id": thread_id,
        "message": "\n".join(messages).strip(),
        "usage": usage,
    }


def _build_codex_url(base_url: str, endpoint_path: str) -> str:
    path = endpoint_path.strip() or "/responses"
    if not path.startswith("/"):
        path = f"/{path}"
    return f"{base_url.rstrip('/')}{path}"
