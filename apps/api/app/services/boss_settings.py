import json
from datetime import UTC, datetime
from pathlib import Path

from app.schemas.settings import BossSettings
from app.services.prompt_config import get_config_dir


def get_boss_settings_path() -> Path:
    return get_config_dir() / "boss-config.json"


def read_boss_settings() -> BossSettings:
    path = get_boss_settings_path()
    if not path.exists():
        settings = BossSettings()
        write_boss_settings(settings)
        return settings

    data = json.loads(path.read_text(encoding="utf-8"))
    return BossSettings(**data)


def write_boss_settings(settings: BossSettings) -> BossSettings:
    settings.updated_at = datetime.now(UTC).isoformat()
    get_boss_settings_path().write_text(
        json.dumps(settings.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return settings
