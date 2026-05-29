from pydantic import BaseModel, Field
from pydantic import ConfigDict


class AgentProfile(BaseModel):
    key: str
    name: str
    role: str
    description: str
    responsibilities: list[str] = Field(default_factory=list)
    tools_allowed: list[str] = Field(default_factory=list)
    approval_boundaries: list[str] = Field(default_factory=list)
    reserved: bool = False

    model_config = ConfigDict(from_attributes=True)
