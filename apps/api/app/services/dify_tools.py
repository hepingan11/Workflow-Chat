from typing import Any

import httpx

from app.schemas.tools import DifyToolMeta, ToolRecord
from app.services.tool_registry import save_tool


def sync_dify_tool(tool: ToolRecord) -> tuple[ToolRecord, list[str]]:
    headers = {
        "Authorization": f"Bearer {tool.connection.api_key}",
    }

    info_response = httpx.get(
        _build_dify_url(tool.connection.base_url, "/info"),
        headers=headers,
        timeout=30,
    )
    info_response.raise_for_status()
    info_payload = info_response.json()

    parameters_response = httpx.get(
        _build_dify_url(tool.connection.base_url, "/parameters"),
        headers=headers,
        timeout=30,
    )
    parameters_response.raise_for_status()
    parameters_payload = parameters_response.json()

    meta = DifyToolMeta(
        app_name=info_payload.get("name", ""),
        app_description=info_payload.get("description", ""),
        app_mode=info_payload.get("mode", ""),
        user_input_form=parameters_payload.get("user_input_form", []),
    )

    if meta.app_mode and meta.app_mode != "workflow":
        raise ValueError(f"Only Dify workflow apps are supported, got: {meta.app_mode}")

    synced_fields: list[str] = []
    if meta.app_name and tool.name != meta.app_name:
        tool.name = meta.app_name
        synced_fields.append("name")

    if meta.app_description != tool.description:
        tool.description = meta.app_description
        synced_fields.append("description")

    tool.meta = meta
    synced_fields.extend(["meta.app_mode", "meta.user_input_form"])

    saved = save_tool(tool)
    return saved, synced_fields


def execute_dify_tool(tool: ToolRecord, inputs: dict[str, Any], user: str) -> dict[str, Any]:
    response = httpx.post(
        _build_dify_url(tool.connection.base_url, "/workflows/run"),
        headers={
            "Authorization": f"Bearer {tool.connection.api_key}",
            "Content-Type": "application/json",
        },
        json={
            "inputs": inputs,
            "response_mode": "blocking",
            "user": user,
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def _build_dify_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}{path}"
