from fastapi import FastAPI

from app.api.routes import agents, health, operator, playbooks, settings as settings_routes, tools
from app.core.config import settings

app = FastAPI(
    title="Workflow Chat API",
    version="0.1.0",
    description="Digital Employee OS API scaffold.",
)

app.include_router(health.router)
app.include_router(agents.router, prefix="/agents", tags=["agents"])
app.include_router(operator.router, prefix="/operator", tags=["operator"])
app.include_router(playbooks.router, prefix="/playbooks", tags=["playbooks"])
app.include_router(settings_routes.router, prefix="/settings", tags=["settings"])
app.include_router(tools.router, prefix="/tools", tags=["tools"])


@app.get("/")
def read_root() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "status": "scaffolded",
        "docs": "/docs",
    }
