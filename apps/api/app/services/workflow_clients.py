from typing import Any, Protocol

import httpx

from app.core.config import settings
from app.schemas.operator import WorkflowExecutionResult


class WorkflowClient(Protocol):
    provider: str

    def run(self, inputs: dict[str, Any], dry_run: bool = False) -> WorkflowExecutionResult:
        ...


class DifyWorkflowClient:
    provider = "dify"

    def run(self, inputs: dict[str, Any], dry_run: bool = False) -> WorkflowExecutionResult:
        request_payload = {
            "inputs": inputs,
            "response_mode": "blocking",
            "user": settings.dify_operator_publish_user,
        }

        if dry_run or not settings.dify_api_key:
            return WorkflowExecutionResult(
                provider=self.provider,
                dry_run=True,
                status="prepared",
                request_payload=request_payload,
                response_payload={
                    "message": "Dify API key is not configured; workflow call was prepared only.",
                },
            )

        response = httpx.post(
            f"{settings.dify_api_base_url.rstrip('/')}/workflows/run",
            headers={
                "Authorization": f"Bearer {settings.dify_api_key}",
                "Content-Type": "application/json",
            },
            json=request_payload,
            timeout=60,
        )
        response.raise_for_status()

        return WorkflowExecutionResult(
            provider=self.provider,
            dry_run=False,
            status="executed",
            request_payload=request_payload,
            response_payload=response.json(),
        )


def get_workflow_client(provider: str) -> WorkflowClient:
    if provider == "dify":
        return DifyWorkflowClient()
    raise ValueError(f"Unsupported workflow provider: {provider}")
