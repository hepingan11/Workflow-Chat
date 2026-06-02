from typing import Any

import httpx

from app.schemas.tools import ToolRecord


def execute_codex_tool(tool: ToolRecord, inputs: dict[str, Any], user: str) -> dict[str, Any]:
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


def _extract_prompt(inputs: dict[str, Any]) -> str:
    for key in ("prompt", "task", "instruction", "input"):
        value = inputs.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return str(inputs)


def _build_codex_url(base_url: str, endpoint_path: str) -> str:
    path = endpoint_path.strip() or "/responses"
    if not path.startswith("/"):
        path = f"/{path}"
    return f"{base_url.rstrip('/')}{path}"
