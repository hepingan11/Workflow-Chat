from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import agents, health, operator, playbooks, settings as settings_routes, telegram, tools
from app.core.config import settings
from app.services.playbook_scheduler import start_playbook_scheduler, stop_playbook_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_playbook_scheduler()
    try:
        yield
    finally:
        stop_playbook_scheduler()

app = FastAPI(
    title="Workflow Chat API",
    version="0.1.0",
    description="Digital Employee OS API scaffold.",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(agents.router, prefix="/agents", tags=["agents"])
app.include_router(operator.router, prefix="/operator", tags=["operator"])
app.include_router(playbooks.router, prefix="/playbooks", tags=["playbooks"])
app.include_router(settings_routes.router, prefix="/settings", tags=["settings"])
app.include_router(telegram.router, prefix="/telegram", tags=["telegram"])
app.include_router(tools.router, prefix="/tools", tags=["tools"])


@app.get("/")
def read_root() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "status": "scaffolded",
        "docs": "/docs",
    }
