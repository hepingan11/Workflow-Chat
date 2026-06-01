from datetime import datetime

import httpx

from app.services.model_settings import read_model_settings
from app.services.time_parser.constants import LLM_TIMEOUT_SECONDS
from app.services.time_parser.prompts import render_time_messages
from app.services.time_parser.schemas import ParsedTime
from app.services.time_parser.validators import parse_structured_time_output


def parse_time_by_llm(text: str, role_key: str | None, now: datetime) -> ParsedTime | None:
    model = select_model_config(role_key)
    if not model or not model.get("base_url") or not model.get("api_key") or not model.get("model_name"):
        return None

    try:
        response = httpx.post(
            f"{model['base_url'].rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {model['api_key']}",
                "Content-Type": "application/json",
            },
            json={
                "model": model["model_name"],
                "messages": render_time_messages(text, now.isoformat()),
                "temperature": 0,
                "response_format": {"type": "json_object"},
            },
            timeout=LLM_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return parse_structured_time_output(content)
    except Exception:
        return None


def select_model_config(role_key: str | None) -> dict | None:
    settings = read_model_settings()
    if role_key:
        role_config = settings.role_models.get(role_key)
        if role_config and role_config.enabled:
            return role_config.model_dump()
    return settings.global_model.model_dump()
