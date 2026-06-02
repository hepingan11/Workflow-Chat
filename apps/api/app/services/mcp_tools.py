from typing import Any

import httpx

from app.schemas.tools import ToolRecord


def execute_mcp_tool(tool: ToolRecord, inputs: dict[str, Any], user: str) -> dict[str, Any]:
    tool_name = tool.connection.mcp_tool_name or tool.name
    response = httpx.post(
        _build_mcp_url(tool.connection.base_url, tool.connection.endpoint_path),
        headers=_build_headers(tool.connection.api_key),
        json={
            "jsonrpc": "2.0",
            "id": f"workflow-chat-{tool.id}",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": inputs,
                "metadata": {
                    "user": user,
                    "tool_id": tool.id,
                },
            },
        },
        timeout=tool.connection.timeout_seconds,
    )
    response.raise_for_status()
    payload = response.json()
    if "error" in payload:
        raise ValueError(payload["error"])
    return payload


def _build_headers(api_key: str) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _build_mcp_url(base_url: str, endpoint_path: str) -> str:
    path = endpoint_path.strip() or "/mcp"
    if not path.startswith("/"):
        path = f"/{path}"
    return f"{base_url.rstrip('/')}{path}"
