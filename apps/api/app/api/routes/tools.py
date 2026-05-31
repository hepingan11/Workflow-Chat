from fastapi import APIRouter, HTTPException

from app.schemas.tools import (
    PublicToolRecord,
    PublicToolRegistry,
    ToolCreatePayload,
    ToolSyncResult,
    ToolUpdatePayload,
)
from app.services.dify_tools import execute_dify_tool, sync_dify_tool
from app.services.tool_registry import (
    create_tool,
    delete_tool,
    get_tool,
    read_public_tool_registry,
    to_public_tool_record,
    update_tool,
)

router = APIRouter()


@router.get("", response_model=PublicToolRegistry)
def read_tools() -> PublicToolRegistry:
    return read_public_tool_registry()


@router.post("", response_model=PublicToolRecord)
def create_tool_record(payload: ToolCreatePayload) -> PublicToolRecord:
    tool = create_tool(payload)
    return to_public_tool_record(tool)


@router.get("/{tool_id}", response_model=PublicToolRecord)
def read_tool(tool_id: str) -> PublicToolRecord:
    tool = get_tool(tool_id)
    if tool is None:
        raise HTTPException(status_code=404, detail="Tool not found")
    return to_public_tool_record(tool)


@router.put("/{tool_id}", response_model=PublicToolRecord)
def update_tool_record(tool_id: str, payload: ToolUpdatePayload) -> PublicToolRecord:
    tool = update_tool(tool_id, payload)
    if tool is None:
        raise HTTPException(status_code=404, detail="Tool not found")
    return to_public_tool_record(tool)


@router.delete("/{tool_id}")
def delete_tool_record(tool_id: str) -> dict[str, bool]:
    deleted = delete_tool(tool_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Tool not found")
    return {"deleted": True}


@router.post("/{tool_id}/sync", response_model=ToolSyncResult)
def sync_tool_record(tool_id: str) -> ToolSyncResult:
    tool = get_tool(tool_id)
    if tool is None:
        raise HTTPException(status_code=404, detail="Tool not found")
    if not tool.connection.api_key:
        raise HTTPException(status_code=400, detail="Tool API key is required for sync")

    try:
        synced, synced_fields = sync_dify_tool(tool)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to sync Dify tool: {exc}") from exc

    return ToolSyncResult(tool=to_public_tool_record(synced), synced_fields=synced_fields)


@router.post("/{tool_id}/test-run")
def test_run_tool_record(tool_id: str, payload: dict) -> dict:
    tool = get_tool(tool_id)
    if tool is None:
        raise HTTPException(status_code=404, detail="Tool not found")
    if not tool.connection.api_key:
        raise HTTPException(status_code=400, detail="Tool API key is required for test run")

    try:
        result = execute_dify_tool(
            tool,
            inputs=payload.get("inputs", {}),
            user=payload.get("user", "workflow-chat-tool-test"),
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to execute Dify tool: {exc}") from exc

    return {"tool_id": tool.id, "result": result}
