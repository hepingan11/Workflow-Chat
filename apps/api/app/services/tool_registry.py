import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.schemas.tools import (
    PublicDifyToolConnection,
    PublicToolRecord,
    PublicToolRegistry,
    ToolCreatePayload,
    ToolRecord,
    ToolRegistry,
    ToolUpdatePayload,
)
from app.services.prompt_config import get_config_dir


def get_tool_registry_path() -> Path:
    return get_config_dir() / "tools.json"


def read_tool_registry() -> ToolRegistry:
    path = get_tool_registry_path()
    if not path.exists():
        registry = ToolRegistry()
        write_tool_registry(registry)
        return registry

    data = json.loads(path.read_text(encoding="utf-8"))
    return ToolRegistry(**data)


def read_public_tool_registry() -> PublicToolRegistry:
    return to_public_tool_registry(read_tool_registry())


def write_tool_registry(registry: ToolRegistry) -> ToolRegistry:
    registry.updated_at = _now()
    get_tool_registry_path().write_text(
        json.dumps(registry.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return registry


def list_tools() -> list[ToolRecord]:
    return read_tool_registry().tools


def get_tool(tool_id: str) -> ToolRecord | None:
    registry = read_tool_registry()
    for tool in registry.tools:
        if tool.id == tool_id:
            return tool
    return None


def create_tool(payload: ToolCreatePayload) -> ToolRecord:
    registry = read_tool_registry()
    tool = ToolRecord(
        id=f"tool_{uuid4().hex[:12]}",
        name=payload.name,
        description=payload.description,
        provider=payload.provider,
        enabled=payload.enabled,
        allowed_roles=payload.allowed_roles,
        connection=payload.connection,
        updated_at=_now(),
    )
    registry.tools.append(tool)
    write_tool_registry(registry)
    return tool


def update_tool(tool_id: str, payload: ToolUpdatePayload) -> ToolRecord | None:
    registry = read_tool_registry()
    for index, tool in enumerate(registry.tools):
        if tool.id != tool_id:
            continue

        connection = payload.connection
        if not connection.api_key:
            connection = connection.model_copy(update={"api_key": tool.connection.api_key})

        updated = tool.model_copy(
            update={
                "name": payload.name,
                "description": payload.description,
                "provider": payload.provider,
                "enabled": payload.enabled,
                "allowed_roles": payload.allowed_roles,
                "connection": connection,
                "updated_at": _now(),
            }
        )
        registry.tools[index] = updated
        write_tool_registry(registry)
        return updated
    return None


def delete_tool(tool_id: str) -> bool:
    registry = read_tool_registry()
    original_count = len(registry.tools)
    registry.tools = [tool for tool in registry.tools if tool.id != tool_id]
    if len(registry.tools) == original_count:
        return False
    write_tool_registry(registry)
    return True


def save_tool(tool: ToolRecord) -> ToolRecord:
    registry = read_tool_registry()
    for index, current in enumerate(registry.tools):
        if current.id != tool.id:
            continue
        tool.updated_at = _now()
        registry.tools[index] = tool
        write_tool_registry(registry)
        return tool
    raise ValueError(f"Tool not found: {tool.id}")


def to_public_tool_registry(registry: ToolRegistry) -> PublicToolRegistry:
    return PublicToolRegistry(
        tools=[to_public_tool_record(tool) for tool in registry.tools],
        updated_at=registry.updated_at,
    )


def to_public_tool_record(tool: ToolRecord) -> PublicToolRecord:
    return PublicToolRecord(
        id=tool.id,
        name=tool.name,
        description=tool.description,
        provider=tool.provider,
        enabled=tool.enabled,
        allowed_roles=tool.allowed_roles,
        connection=PublicDifyToolConnection(
            base_url=tool.connection.base_url,
            has_api_key=bool(tool.connection.api_key),
            model=tool.connection.model,
            endpoint_path=tool.connection.endpoint_path,
            mcp_tool_name=tool.connection.mcp_tool_name,
            timeout_seconds=tool.connection.timeout_seconds,
        ),
        meta=tool.meta,
        updated_at=tool.updated_at,
    )


def _now() -> str:
    return datetime.now(UTC).isoformat()
