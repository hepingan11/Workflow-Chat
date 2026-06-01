import json
import re

from app.services.time_parser.schemas import ParsedTime


def parse_structured_time_output(content: str) -> ParsedTime | None:
    try:
        data = json.loads(strip_json_fence(content))
        parsed = ParsedTime(**data)
    except Exception:
        return None

    if not is_valid_cron(parsed.cron):
        return None
    if parsed.trigger_type == "scheduled" and not parsed.run_at:
        return None
    return parsed


def is_valid_cron(value: str) -> bool:
    parts = value.split()
    if len(parts) != 5:
        return False
    return all(re.match(r"^[\d*/,\-]+$", part) for part in parts)


def strip_json_fence(content: str) -> str:
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?", "", content).strip()
        content = re.sub(r"```$", "", content).strip()
    return content
