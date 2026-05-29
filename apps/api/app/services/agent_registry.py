from app.schemas.agent import AgentProfile
from app.services.default_agents import DEFAULT_AGENTS


def list_agents() -> list[AgentProfile]:
    return sorted(DEFAULT_AGENTS.values(), key=lambda agent: (agent.reserved, agent.key))


def get_agent(agent_key: str) -> AgentProfile | None:
    return DEFAULT_AGENTS.get(agent_key)
