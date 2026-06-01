from datetime import datetime
from zoneinfo import ZoneInfo

from app.schemas.playbooks import PlaybookTrigger
from app.services.time_parser.constants import DEFAULT_TIMEZONE
from app.services.time_parser.llm import parse_time_by_llm
from app.services.time_parser.rules import daily_at, parse_time_by_rules
from app.services.time_parser.schemas import ParsedTime


def parse_trigger_time(text: str, role_key: str | None = None, now: datetime | None = None) -> PlaybookTrigger:
    current = now or datetime.now(ZoneInfo(DEFAULT_TIMEZONE))

    rule_result = parse_time_by_rules(text, current)
    if rule_result:
        return to_trigger(rule_result)

    llm_result = parse_time_by_llm(text, role_key, current)
    if llm_result:
        return to_trigger(llm_result)

    fallback = daily_at("09:00", "默认每天 09:00 执行")
    return to_trigger(fallback)


def to_trigger(parsed: ParsedTime) -> PlaybookTrigger:
    return PlaybookTrigger(
        type=parsed.trigger_type,
        time=parsed.time,
        timezone=parsed.timezone,
        cron=parsed.cron,
        run_at=parsed.run_at,
        description=parsed.description,
    )
