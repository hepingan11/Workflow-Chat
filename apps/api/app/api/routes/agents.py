from fastapi import APIRouter, HTTPException

from app.schemas.agent import AgentProfile
from app.services.agent_registry import get_agent, list_agents

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
