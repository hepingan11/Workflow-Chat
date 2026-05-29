from typing import Any

from app.schemas.operator import (
    OperatorPublishRequest,
    OperatorPublishResponse,
    PreparedWorkflowPayload,
)
from app.services.prompt_config import read_operator_prompt
from app.services.workflow_clients import get_workflow_client


def prepare_operator_workflow_payload(request: OperatorPublishRequest) -> PreparedWorkflowPayload:
    prompt_config = read_operator_prompt()
    material_list = [material.model_dump(mode="json") for material in request.materials]

    inputs: dict[str, Any] = {
        "control_prompt": prompt_config.prompt,
        "title": request.title,
        "copy": request.copy_text,
        "platforms": request.platforms,
        "materials": material_list,
        "campaign": request.campaign,
        "tone": request.tone,
        "workflow_inputs": request.workflow_inputs,
        "operator_contract": {
            "mode": "control_only",
            "must_not_publish_directly": True,
            "requires_approval_for_external_publish": True,
        },
    }

    return PreparedWorkflowPayload(
        provider=request.workflow_provider,
        prompt=prompt_config.prompt,
        inputs=inputs,
    )


def publish_operator_content(request: OperatorPublishRequest) -> OperatorPublishResponse:
    prepared = prepare_operator_workflow_payload(request)
    workflow_client = get_workflow_client(request.workflow_provider)
    workflow_result = workflow_client.run(prepared.inputs, dry_run=request.dry_run)

    return OperatorPublishResponse(
        status=workflow_result.status,
        prepared=prepared,
        workflow=workflow_result,
    )
