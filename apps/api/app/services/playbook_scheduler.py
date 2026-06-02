from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.schemas.playbooks import Playbook
from app.services.playbooks import (
    advance_run,
    list_playbooks,
    read_run_registry,
    to_public_run,
    trigger_playbook,
)

DEFAULT_TIMEZONE = "Asia/Shanghai"
SCHEDULER_INTERVAL_SECONDS = 15
ACTIVE_RUN_STATUSES = {"pending", "running", "scheduled"}
_scheduler: AsyncIOScheduler | None = None


def start_playbook_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler and _scheduler.running:
        return _scheduler

    scheduler = AsyncIOScheduler(timezone=DEFAULT_TIMEZONE)
    scheduler.add_job(
        run_scheduler_tick,
        trigger=IntervalTrigger(seconds=SCHEDULER_INTERVAL_SECONDS),
        id="playbook_scheduler_tick",
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )
    scheduler.start()
    _scheduler = scheduler
    return scheduler


def stop_playbook_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
    _scheduler = None


def run_scheduler_tick() -> dict[str, int]:
    created_runs = schedule_due_playbooks()
    advanced_runs = advance_runnable_runs()
    return {
        "created_runs": created_runs,
        "advanced_runs": advanced_runs,
    }


def schedule_due_playbooks() -> int:
    created_count = 0
    for playbook in list_playbooks():
        if playbook.status != "active":
            continue
        if playbook.trigger.type in {"immediate", "scheduled"}:
            continue
        if playbook.trigger.type == "immediate" and has_any_run(playbook.id):
            continue

        scheduled_for = get_due_scheduled_for(playbook)
        if not scheduled_for:
            continue
        if has_run_for_schedule(playbook.id, scheduled_for):
            continue

        trigger_playbook(playbook.id, scheduled_for=scheduled_for)
        created_count += 1
    return created_count


def advance_runnable_runs() -> int:
    advanced_count = 0
    runs = read_run_registry().runs
    for run in runs:
        if run.status not in ACTIVE_RUN_STATUSES:
            continue
        if not is_run_due(run.scheduled_for):
            continue
        advance_run(run.id)
        advanced_count += 1
    return advanced_count


def get_due_scheduled_for(playbook: Playbook) -> str | None:
    timezone = ZoneInfo(playbook.trigger.timezone or DEFAULT_TIMEZONE)
    now = datetime.now(timezone)

    if playbook.trigger.type == "immediate":
        return now.replace(microsecond=0).isoformat()

    if playbook.trigger.type == "scheduled" and playbook.trigger.run_at:
        target = parse_datetime(playbook.trigger.run_at, timezone)
        if target <= now:
            return target.isoformat()
        return None

    if playbook.trigger.type in {"daily", "recurring"}:
        target = datetime.combine(now.date(), parse_time_parts(playbook.trigger.time), tzinfo=timezone)
        if target <= now:
            return target.isoformat()
        return None

    return None


def has_run_for_schedule(playbook_id: str, scheduled_for: str) -> bool:
    for run in read_run_registry().runs:
        if run.playbook_id == playbook_id and normalize_iso(run.scheduled_for) == normalize_iso(scheduled_for):
            return True
    return False


def has_any_run(playbook_id: str) -> bool:
    return any(run.playbook_id == playbook_id for run in read_run_registry().runs)


def is_run_due(scheduled_for: str) -> bool:
    try:
        scheduled = datetime.fromisoformat(scheduled_for)
    except ValueError:
        return True
    if scheduled.tzinfo is None:
        scheduled = scheduled.replace(tzinfo=ZoneInfo(DEFAULT_TIMEZONE))
    return scheduled <= datetime.now(scheduled.tzinfo)


def parse_datetime(value: str, timezone: ZoneInfo) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone)
    return parsed.astimezone(timezone)


def parse_time_parts(value: str):
    hour, minute = [int(part) for part in value.split(":")[:2]]
    return datetime.min.time().replace(hour=hour, minute=minute)


def normalize_iso(value: str) -> str:
    try:
        return datetime.fromisoformat(value).replace(microsecond=0).isoformat()
    except ValueError:
        return value
