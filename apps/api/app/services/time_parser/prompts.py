import json
from pathlib import Path

from app.services.time_parser.constants import DEFAULT_RELATIVE_MINUTES, DEFAULT_TIMEZONE

PROMPT_DIR = Path(__file__).resolve().parent / "prompts"


def load_prompt_template(name: str) -> str:
    return (PROMPT_DIR / name).read_text(encoding="utf-8")


def load_few_shot_examples() -> str:
    examples = json.loads((PROMPT_DIR / "examples.json").read_text(encoding="utf-8"))
    return json.dumps(examples, ensure_ascii=False, indent=2)


def render_time_messages(text: str, now_iso: str) -> list[dict[str, str]]:
    system_prompt = load_prompt_template("system.md")
    user_prompt = load_prompt_template("user.md").format(
        text=text,
        now_iso=now_iso,
        timezone=DEFAULT_TIMEZONE,
        default_relative_minutes=DEFAULT_RELATIVE_MINUTES,
        examples=load_few_shot_examples(),
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
