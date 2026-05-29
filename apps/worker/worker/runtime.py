from pydantic import BaseModel


class RuntimeStatus(BaseModel):
    name: str
    message: str
    roles: list[str]


def describe_runtime() -> RuntimeStatus:
    return RuntimeStatus(
        name="Workflow Chat Worker",
        message="Agent runtime scaffold is ready. Task polling will be implemented next.",
        roles=[
            "programmer",
            "customer_support",
            "product_manager",
            "operator",
            "ceo(reserved)",
        ],
    )
