import re
from datetime import datetime, timedelta

from app.services.time_parser.constants import DEFAULT_RELATIVE_MINUTES, DEFAULT_TIMEZONE
from app.services.time_parser.schemas import ParsedTime


FUZZY_RELATIVE_KEYWORDS = [
    "待会",
    "待会儿",
    "等会",
    "等会儿",
    "等下",
    "稍后",
    "马上",
    "一会",
    "一会儿",
    "过会",
    "过会儿",
]

DAILY_KEYWORDS = ["每天", "每日", "天天"]


def parse_time_by_rules(text: str, now: datetime) -> ParsedTime | None:
    normalized = normalize_text(text)

    relative_minutes = extract_relative_minutes(normalized)
    if relative_minutes is not None:
        target = now + timedelta(minutes=relative_minutes)
        return scheduled_at(target, f"{relative_minutes} 分钟后执行")

    if any(keyword in normalized for keyword in FUZZY_RELATIVE_KEYWORDS):
        target = now + timedelta(minutes=DEFAULT_RELATIVE_MINUTES)
        return scheduled_at(target, f"未指定具体时间，默认 {DEFAULT_RELATIVE_MINUTES} 分钟后执行")

    fixed_time = extract_fixed_time(normalized)
    if fixed_time:
        if any(keyword in normalized for keyword in DAILY_KEYWORDS):
            return daily_at(fixed_time, f"每天 {fixed_time} 执行")
        target = next_fixed_datetime(now, fixed_time, force_tomorrow="明天" in normalized)
        return scheduled_at(target, f"{fixed_time} 执行")

    return None


def normalize_text(text: str) -> str:
    return (
        text.replace("：", ":")
        .replace("半", "半")
        .replace("　", " ")
        .strip()
    )


def extract_relative_minutes(text: str) -> int | None:
    patterns = [
        (r"(\d+)\s*(?:分钟|分|min|mins|minute|minutes)\s*后", 1),
        (r"(\d+)\s*(?:小时|hour|hours)\s*后", 60),
        (r"(\d+)\s*(?:天|day|days)\s*后", 60 * 24),
    ]
    for pattern, multiplier in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return int(match.group(1)) * multiplier
    return None


def extract_fixed_time(text: str) -> str | None:
    match = re.search(r"(\d{1,2})[:：](\d{2})", text)
    if match:
        return normalize_time(int(match.group(1)), int(match.group(2)))

    match = re.search(r"(凌晨|早上|上午|中午|下午|晚上|今晚)?\s*(\d{1,2})\s*点\s*(半|(\d{1,2})\s*分?)?", text)
    if not match:
        return None

    period = match.group(1) or ""
    hour = int(match.group(2))
    minute = 30 if match.group(3) == "半" else int(match.group(4) or 0)

    if period in {"下午", "晚上", "今晚"} and hour < 12:
        hour += 12
    if period == "中午" and hour < 11:
        hour += 12
    if period == "凌晨" and hour == 12:
        hour = 0

    return normalize_time(hour, minute)


def normalize_time(hour: int, minute: int) -> str:
    hour = max(0, min(hour, 23))
    minute = max(0, min(minute, 59))
    return f"{hour:02d}:{minute:02d}"


def scheduled_at(target: datetime, description: str) -> ParsedTime:
    time_value = target.strftime("%H:%M")
    return ParsedTime(
        trigger_type="scheduled",
        time=time_value,
        timezone=DEFAULT_TIMEZONE,
        cron=f"{target.minute} {target.hour} * * *",
        run_at=target.isoformat(),
        description=description,
    )


def daily_at(time_value: str, description: str) -> ParsedTime:
    hour, minute = [int(part) for part in time_value.split(":")]
    return ParsedTime(
        trigger_type="daily",
        time=time_value,
        timezone=DEFAULT_TIMEZONE,
        cron=f"{minute} {hour} * * *",
        run_at=None,
        description=description,
    )


def next_fixed_datetime(now: datetime, time_value: str, force_tomorrow: bool = False) -> datetime:
    hour, minute = [int(part) for part in time_value.split(":")]
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if force_tomorrow or target <= now:
        target += timedelta(days=1)
    return target
