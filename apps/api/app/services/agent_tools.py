from fastapi import HTTPException

from app.core.config import settings
from app.schemas.agent_tools import AgentToolDefinition, AgentToolExecuteResponse, AgentToolListResponse
from app.services.agent_registry import get_agent
from app.services.dify_tools import execute_dify_tool
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

    dify_tools = [
        AgentToolDefinition(
            id=tool.id,
            name=tool.name,
            description=tool.description,
            source="dify",
            enabled=tool.enabled,
            executable=tool.enabled and bool(tool.connection.api_key),
            provider=tool.provider,
            meta={
                "app_mode": tool.meta.app_mode,
                "user_input_form": tool.meta.user_input_form,
                "base_url": tool.connection.base_url,
            },
        )
        for tool in list_tools()
        if tool.enabled and agent_key in tool.allowed_roles
    ]

    return AgentToolListResponse(agent_key=agent_key, tools=[*builtin_tools, *dify_tools])


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
    if agent_key not in tool.allowed_roles:
        raise HTTPException(status_code=403, detail="Tool is not authorized for this agent")
    if not tool.connection.api_key:
        raise HTTPException(status_code=400, detail="Tool API key is required")

    result = execute_dify_tool(
        tool,
        inputs=inputs,
        user=user or f"{settings.app_name.lower().replace(' ', '-')}-{agent_key}",
    )
    return AgentToolExecuteResponse(agent_key=agent_key, tool_id=tool_id, result=result)
