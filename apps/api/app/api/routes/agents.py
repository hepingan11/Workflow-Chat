from fastapi import APIRouter, HTTPException

from app.schemas.agent import AgentProfile
from app.schemas.operator import OperatorPromptConfig, OperatorPromptUpdate
from app.schemas.agent_tools import AgentToolExecutePayload, AgentToolExecuteResponse, AgentToolListResponse
from app.services.agent_tools import execute_agent_tool, list_agent_tools
from app.services.agent_registry import get_agent, list_agents
from app.services.prompt_config import read_agent_prompt, write_agent_prompt

router = APIRouter()


@router.get("", response_model=list[AgentProfile])
def read_agents() -> list[AgentProfile]:
    return list_agents()


@router.get("/{agent_key}", response_model=AgentProfile)
def read_agent(agent_key: str) -> AgentProfile:
    agent = get_agent(agent_key)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.get("/{agent_key}/tools", response_model=AgentToolListResponse)
def read_agent_tools(agent_key: str) -> AgentToolListResponse:
    return list_agent_tools(agent_key)


@router.get("/{agent_key}/prompt", response_model=OperatorPromptConfig)
def read_agent_prompt_config(agent_key: str) -> OperatorPromptConfig:
    agent = get_agent(agent_key)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return read_agent_prompt(agent_key)


@router.put("/{agent_key}/prompt", response_model=OperatorPromptConfig)
def update_agent_prompt_config(agent_key: str, payload: OperatorPromptUpdate) -> OperatorPromptConfig:
    agent = get_agent(agent_key)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return write_agent_prompt(agent_key, payload.prompt)


@router.post("/{agent_key}/tools/{tool_id}/execute", response_model=AgentToolExecuteResponse)
def run_agent_tool(agent_key: str, tool_id: str, payload: AgentToolExecutePayload) -> AgentToolExecuteResponse:
    return execute_agent_tool(agent_key, tool_id, payload.inputs, payload.user)
