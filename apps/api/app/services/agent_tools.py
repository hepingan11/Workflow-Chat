from fastapi import HTTPException

from app.core.config import settings
from app.schemas.agent_tools import AgentToolDefinition, AgentToolExecuteResponse, AgentToolListResponse
from app.services.agent_registry import get_agent
from app.services.codex_tools import execute_codex_cli_tool, execute_llm_chat_response_tool
from app.services.dify_tools import execute_dify_tool
from app.services.mcp_tools import execute_mcp_tool
from app.services.tool_registry import get_tool, list_tools


def list_agent_tools(agent_key: str) -> AgentToolListResponse:
    agent = get_agent(agent_key)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    builtin_tools = [
        AgentToolDefinition(
            id=tool_name,
            name=tool_name,
            description="内置工具",
            source="builtin",
            enabled=True,
            executable=False,
        )
        for tool_name in agent.tools_allowed
    ]

    registered_tools = [
        AgentToolDefinition(
            id=tool.id,
            name=tool.name,
            description=tool.description,
            source=tool.provider,
            enabled=tool.enabled,
            executable=tool.enabled and (tool.provider in ("mcp", "codex_cli") or bool(tool.connection.api_key)),
            provider=tool.provider,
            meta={
                "app_mode": tool.meta.app_mode,
                "user_input_form": tool.meta.user_input_form,
                "base_url": tool.connection.base_url,
                "model": tool.connection.model,
                "endpoint_path": tool.connection.endpoint_path,
                "mcp_tool_name": tool.connection.mcp_tool_name,
                "working_directory": tool.connection.working_directory,
                "codex_command": tool.connection.codex_command,
                "approval_policy": tool.connection.approval_policy,
                "sandbox": tool.connection.sandbox,
            },
        )
        for tool in list_tools()
        if tool.enabled
    ]

    return AgentToolListResponse(agent_key=agent_key, tools=[*builtin_tools, *registered_tools])


def execute_agent_tool(agent_key: str, tool_id: str, inputs: dict, user: str | None = None) -> AgentToolExecuteResponse:
    agent = get_agent(agent_key)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    if tool_id in agent.tools_allowed:
        raise HTTPException(status_code=400, detail=f"Built-in tool is not directly executable yet: {tool_id}")

    tool = get_tool(tool_id)
    if tool is None:
        raise HTTPException(status_code=404, detail="Tool not found")
    if not tool.enabled:
        raise HTTPException(status_code=400, detail="Tool is disabled")
    if tool.provider not in ("mcp", "codex_cli") and not tool.connection.api_key:
        raise HTTPException(status_code=400, detail="Tool API key is required")

    resolved_user = user or f"{settings.app_name.lower().replace(' ', '-')}-{agent_key}"
    if tool.provider == "dify":
        result = execute_dify_tool(tool, inputs=inputs, user=resolved_user)
    elif tool.provider in ("codex", "llm_chat_response"):
        result = execute_llm_chat_response_tool(tool, inputs=inputs, user=resolved_user)
    elif tool.provider == "codex_cli":
        result = execute_codex_cli_tool(tool, inputs=inputs, user=resolved_user)
    elif tool.provider == "mcp":
        result = execute_mcp_tool(tool, inputs=inputs, user=resolved_user)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported tool provider: {tool.provider}")
    return AgentToolExecuteResponse(agent_key=agent_key, tool_id=tool_id, result=result)
