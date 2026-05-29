from fastapi import APIRouter

from app.schemas.operator import (
    OperatorPromptConfig,
    OperatorPromptUpdate,
    OperatorPublishRequest,
    OperatorPublishResponse,
)
from app.services.operator_publish import publish_operator_content
from app.services.prompt_config import read_operator_prompt, write_operator_prompt

router = APIRouter()


@router.get("/prompt", response_model=OperatorPromptConfig)
def get_prompt() -> OperatorPromptConfig:
    return read_operator_prompt()


@router.put("/prompt", response_model=OperatorPromptConfig)
def update_prompt(payload: OperatorPromptUpdate) -> OperatorPromptConfig:
    return write_operator_prompt(payload.prompt)


@router.post("/publish", response_model=OperatorPublishResponse)
def publish(payload: OperatorPublishRequest) -> OperatorPublishResponse:
    return publish_operator_content(payload)
