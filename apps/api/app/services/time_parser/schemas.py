from typing import Literal

from pydantic import BaseModel, Field

from app.services.time_parser.constants import DEFAULT_TIMEZONE


TriggerType = Literal["immediate", "scheduled", "daily", "recurring"]


class ParsedTime(BaseModel):
    trigger_type: TriggerType = "daily"
    time: str = Field(pattern=r"^\d{2}:\d{2}$")
    timezone: str = DEFAULT_TIMEZONE
    cron: str
    run_at: str | None = None
    description: str
