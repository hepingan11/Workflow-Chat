import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.services.prompt_config import get_config_dir


def get_run_monitor_path(run_id: str) -> Path:
    monitor_dir = get_config_dir() / "run-monitors"
    monitor_dir.mkdir(parents=True, exist_ok=True)
    return monitor_dir / f"{run_id}.json"


def read_run_monitor(run_id: str) -> dict[str, Any]:
    path = get_run_monitor_path(run_id)
    if not path.exists():
        return {
            "run_id": run_id,
            "status": "idle",
            "current_step_id": "",
            "events": [],
            "updated_at": None,
        }
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {
            "run_id": run_id,
            "status": "unreadable",
            "current_step_id": "",
            "events": [],
            "updated_at": None,
        }


def append_run_monitor_event(
    run_id: str,
    event_type: str,
    message: str,
    *,
    step_id: str | None = None,
    step_name: str | None = None,
    stream: str | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    monitor = read_run_monitor(run_id)
    event = {
        "time": _now(),
        "type": event_type,
        "step_id": step_id or "",
        "step_name": step_name or "",
        "stream": stream or "",
        "message": message,
        "payload": payload or {},
    }
    events = [*monitor.get("events", []), event]
    monitor.update(
        {
            "run_id": run_id,
            "status": event_type,
            "current_step_id": step_id or monitor.get("current_step_id", ""),
            "events": events[-300:],
            "updated_at": event["time"],
        }
    )
    get_run_monitor_path(run_id).write_text(
        json.dumps(monitor, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return monitor


def _now() -> str:
    return datetime.now(UTC).isoformat()
