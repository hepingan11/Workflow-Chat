import json
import os
import threading
import subprocess
from pathlib import Path
from shutil import which
from typing import Any
from uuid import uuid4

import httpx

from app.core.config import find_project_root
from app.schemas.tools import ToolRecord
from app.services.prompt_config import get_config_dir
from app.services.run_monitor import append_run_monitor_event


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
    native_context = _prepare_codex_native_context(inputs, working_directory)
    codex_working_directory = native_context["context_dir"] or working_directory
    if native_context["enabled"]:
        prompt = f"{_build_native_context_prompt_hint(native_context)}\n\n{prompt}"
    timeout_seconds = max(tool.connection.timeout_seconds, 1)
    monitor_context = _get_monitor_context(inputs)
    argv = [
        command,
        "exec",
        "--json",
        "--dangerously-bypass-approvals-and-sandbox",
    ]
    if codex_working_directory:
        argv[2:2] = ["--cd", codex_working_directory]
    append_run_monitor_event(
        monitor_context["run_id"],
        "codex_started",
        "Codex CLI started.",
        step_id=monitor_context["step_id"],
        step_name=monitor_context["step_name"],
        payload={
            "command": " ".join(argv),
            "prompt_transport": "stdin",
            "timeout_seconds": timeout_seconds,
            "native_context": native_context,
        },
    ) if monitor_context["run_id"] else None
    try:
        completed = _run_codex_process(
            argv,
            working_directory=codex_working_directory,
            prompt=prompt,
            timeout_seconds=timeout_seconds,
            monitor_context=monitor_context,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = _decode_process_output(exc.output or b"")
        stderr = _decode_process_output(exc.stderr or b"")
        return {
            "ok": False,
            "provider": "codex_cli",
            "command": " ".join(argv),
            "prompt_transport": "stdin",
            "working_directory": working_directory,
            "codex_working_directory": codex_working_directory,
            "native_context": native_context,
            "approval_policy": "bypass",
            "sandbox": "danger-full-access",
            "user": user,
            "returncode": None,
            "thread_id": "",
            "message": f"Codex CLI timed out after {timeout_seconds} seconds.",
            "usage": {},
            "events": [],
            "stdout": stdout[-4000:],
            "stderr": stderr[-4000:],
            "error": f"Codex CLI timed out after {timeout_seconds} seconds.",
        }
    parsed = _parse_codex_jsonl(completed.stdout)
    return {
        "ok": completed.returncode == 0,
        "provider": "codex_cli",
        "command": " ".join(argv),
        "prompt_transport": "stdin",
        "working_directory": working_directory,
        "codex_working_directory": codex_working_directory,
        "native_context": native_context,
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


def _run_codex_process(
    argv: list[str],
    *,
    working_directory: str | None,
    prompt: str,
    timeout_seconds: int,
    monitor_context: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(
        {
            "PYTHONIOENCODING": "utf-8",
            "PYTHONUTF8": "1",
            "NO_COLOR": "1",
            "FORCE_COLOR": "0",
        }
    )
    process = subprocess.Popen(
        argv,
        cwd=working_directory,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    stdout_lines: list[str] = []
    stderr_lines: list[str] = []

    def pump(stream, target: list[str], stream_name: str) -> None:
        if stream is None:
            return
        for line in stream:
            decoded = _decode_process_output(line)
            target.append(decoded)
            _append_codex_stream_event(monitor_context, stream_name, decoded)

    stdout_thread = threading.Thread(target=pump, args=(process.stdout, stdout_lines, "stdout"), daemon=True)
    stderr_thread = threading.Thread(target=pump, args=(process.stderr, stderr_lines, "stderr"), daemon=True)
    stdout_thread.start()
    stderr_thread.start()
    if process.stdin is not None:
        process.stdin.write(prompt.encode("utf-8"))
        process.stdin.close()
    try:
        returncode = process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired as exc:
        process.kill()
        stdout_thread.join(timeout=1)
        stderr_thread.join(timeout=1)
        stdout = "".join(stdout_lines)
        stderr = "".join(stderr_lines)
        if monitor_context["run_id"]:
            append_run_monitor_event(
                monitor_context["run_id"],
                "codex_timeout",
                f"Codex CLI timed out after {timeout_seconds} seconds.",
                step_id=monitor_context["step_id"],
                step_name=monitor_context["step_name"],
                payload={"stdout_tail": stdout[-2000:], "stderr_tail": stderr[-2000:]},
            )
        raise subprocess.TimeoutExpired(exc.cmd, exc.timeout, output=stdout, stderr=stderr) from exc
    stdout_thread.join(timeout=1)
    stderr_thread.join(timeout=1)
    return subprocess.CompletedProcess(
        args=argv,
        returncode=returncode,
        stdout="".join(stdout_lines),
        stderr="".join(stderr_lines),
    )


def _decode_process_output(raw: bytes | str) -> str:
    if isinstance(raw, str):
        return raw
    for encoding in ("utf-8", "utf-8-sig", "gb18030", "gbk", "cp936"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _append_codex_stream_event(monitor_context: dict[str, str], stream_name: str, line: str) -> None:
    run_id = monitor_context["run_id"]
    if not run_id:
        return
    clean_line = line.rstrip()
    if not clean_line:
        return
    payload: dict[str, Any] = {}
    message = clean_line
    event_type = "codex_terminal"
    if stream_name == "stdout":
        try:
            payload = json.loads(clean_line)
            event_type = str(payload.get("type", "codex_event"))
            item = payload.get("item") if isinstance(payload.get("item"), dict) else {}
            message = item.get("text") or payload.get("type") or clean_line
        except ValueError:
            pass
    append_run_monitor_event(
        run_id,
        event_type,
        str(message),
        step_id=monitor_context["step_id"],
        step_name=monitor_context["step_name"],
        stream=stream_name,
        payload=payload,
    )


def _get_monitor_context(inputs: dict[str, Any]) -> dict[str, str]:
    metadata = inputs.get("_monitor")
    if not isinstance(metadata, dict):
        metadata = {}
    return {
        "run_id": str(metadata.get("run_id", "")),
        "step_id": str(metadata.get("step_id", "")),
        "step_name": str(metadata.get("step_name", "")),
    }


def _prepare_codex_native_context(inputs: dict[str, Any], working_directory: str | None) -> dict[str, Any]:
    skill_packages = _extract_skill_packages(inputs)
    if not skill_packages:
        return {"enabled": False, "context_dir": "", "agents_path": "", "skill_packages": []}

    project_root = find_project_root()
    context_root = get_config_dir() / "codex-native-contexts"
    context_root.mkdir(parents=True, exist_ok=True)
    context_dir = context_root / f"ctx_{uuid4().hex[:12]}"
    context_dir.mkdir(parents=True, exist_ok=True)
    agents_path = context_dir / "AGENTS.md"
    original_working_directory = str(Path(working_directory).resolve()) if working_directory else str(project_root)
    agents_path.write_text(
        _build_codex_agents_md(
            original_working_directory=original_working_directory,
            skill_packages=skill_packages,
        ),
        encoding="utf-8",
    )
    return {
        "enabled": True,
        "context_dir": str(context_dir),
        "agents_path": str(agents_path),
        "original_working_directory": original_working_directory,
        "skill_packages": skill_packages,
    }


def _extract_skill_packages(inputs: dict[str, Any]) -> list[dict[str, Any]]:
    skills_context = inputs.get("skills")
    if not isinstance(skills_context, dict):
        return []
    skills = skills_context.get("skills")
    if not isinstance(skills, list):
        return []
    packages: list[dict[str, Any]] = []
    for skill in skills:
        if not isinstance(skill, dict):
            continue
        metadata = skill.get("metadata")
        if not isinstance(metadata, dict):
            continue
        package_root = metadata.get("package_root")
        if not isinstance(package_root, str) or not package_root.strip():
            continue
        resolved_root = _resolve_skill_package_root(package_root)
        if resolved_root is None:
            continue
        packages.append(
            {
                "skill_id": str(skill.get("id", "")),
                "title": str(skill.get("title", "")),
                "summary": str(skill.get("summary", "")),
                "kind": str(skill.get("kind", "")),
                "package_root": str(resolved_root),
                "entry_path": str(metadata.get("entry_path") or ""),
                "package_file_paths": [str(item) for item in metadata.get("package_file_paths", []) if item],
                "script_paths": [str(item) for item in metadata.get("script_paths", []) if item],
            }
        )
    return packages


def _resolve_skill_package_root(package_root: str) -> Path | None:
    project_root = find_project_root().resolve()
    raw_path = Path(package_root)
    candidate = raw_path if raw_path.is_absolute() else project_root / raw_path
    try:
        resolved = candidate.resolve()
    except OSError:
        return None
    allowed_root = (get_config_dir() / "skill-packages").resolve()
    try:
        resolved.relative_to(allowed_root)
    except ValueError:
        return None
    return resolved if resolved.exists() else None


def _build_codex_agents_md(*, original_working_directory: str, skill_packages: list[dict[str, Any]]) -> str:
    lines = [
        "# Codex Native Skill Context",
        "",
        "You are running inside a temporary Codex context directory created by Workflow Chat.",
        "",
        "## Original Working Directory",
        "",
        f"- `{original_working_directory}`",
        "",
        "When the task needs repository files, inspect or modify files in the original working directory above.",
        "The skill packages below are local resources selected for this workflow node.",
        "",
        "## Selected Skill Packages",
        "",
    ]
    for package in skill_packages:
        lines.extend(
            [
                f"### {package.get('title') or package.get('skill_id')}",
                "",
                f"- Skill ID: `{package.get('skill_id', '')}`",
                f"- Kind: `{package.get('kind', '')}`",
                f"- Package root: `{package.get('package_root', '')}`",
                f"- Entry file: `{package.get('entry_path') or 'SKILL.md or first markdown file'}`",
            ]
        )
        summary = str(package.get("summary") or "").strip()
        if summary:
            lines.extend(["", "Summary:", summary])
        file_paths = package.get("package_file_paths")
        if isinstance(file_paths, list) and file_paths:
            lines.extend(["", "Files:", *[f"- `{path}`" for path in file_paths]])
        script_paths = package.get("script_paths")
        if isinstance(script_paths, list) and script_paths:
            lines.extend(["", "Scripts:", *[f"- `{path}`" for path in script_paths]])
        lines.extend(
            [
                "",
                "Usage guidance:",
                "- Read the entry file before applying the skill.",
                "- Use scripts only when the task clearly needs them.",
                "- Treat package files as local helper resources, not as user-facing output by default.",
                "",
            ]
        )
    return "\n".join(lines)


def _build_native_context_prompt_hint(native_context: dict[str, Any]) -> str:
    lines = [
        "Codex native skill context is enabled for this task.",
        f"- Read AGENTS.md first: {native_context.get('agents_path', '')}",
        f"- Original working directory: {native_context.get('original_working_directory', '')}",
        "- Selected skill package roots:",
    ]
    for package in native_context.get("skill_packages", []):
        if isinstance(package, dict):
            lines.append(f"  - {package.get('title') or package.get('skill_id')}: {package.get('package_root')}")
    return "\n".join(lines)


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
    primary_prompt = ""
    for key in ("prompt", "task", "instruction", "input"):
        value = inputs.get(key)
        if isinstance(value, str) and value.strip():
            primary_prompt = value.strip()
            break

    supplemental_inputs = {
        key: value
        for key, value in inputs.items()
        if key not in {"prompt", "task", "instruction", "input"}
    }
    if not supplemental_inputs:
        return primary_prompt or json.dumps(inputs, ensure_ascii=False, indent=2)

    sections: list[str] = []
    if primary_prompt:
        sections.append(primary_prompt)
    else:
        sections.append("请根据以下结构化输入完成任务。")

    for key in ("previous_output", "fetched_result", "generated_asset", "shared_context", "long_term_memory", "skills"):
        if key in supplemental_inputs:
            sections.append(f"{key}:\n{_stringify_prompt_value(supplemental_inputs.pop(key))}")

    if supplemental_inputs:
        sections.append(f"other_inputs:\n{_stringify_prompt_value(supplemental_inputs)}")

    return "\n\n".join(section for section in sections if section.strip())


def _stringify_prompt_value(value: Any) -> str:
    if isinstance(value, str):
        return value.strip() or '""'
    try:
        return json.dumps(value, ensure_ascii=False, indent=2)
    except TypeError:
        return str(value)


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
