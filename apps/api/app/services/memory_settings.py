import json
from datetime import UTC, datetime
from pathlib import Path

from app.core.config import settings
from app.schemas.settings import (
    MemoryStorageSettings,
    MemoryStorageTestResponse,
    PublicMemoryStorageSettings,
)
from app.services.prompt_config import get_config_dir


def get_memory_settings_path() -> Path:
    return get_config_dir() / "memory-storage-config.json"


def read_memory_settings() -> MemoryStorageSettings:
    path = get_memory_settings_path()
    if not path.exists():
        config = MemoryStorageSettings(
            database_url=settings.database_url,
            markdown_dir=settings.memory_markdown_dir,
        )
        write_memory_settings(config)
        return config

    data = json.loads(path.read_text(encoding="utf-8"))
    config = MemoryStorageSettings(**data)
    if not config.markdown_dir:
        config.markdown_dir = settings.memory_markdown_dir
    return config


def read_public_memory_settings() -> PublicMemoryStorageSettings:
    return to_public_memory_settings(read_memory_settings())


def update_memory_settings(payload: MemoryStorageSettings) -> PublicMemoryStorageSettings:
    existing = read_memory_settings()
    if not payload.database_url:
        payload.database_url = existing.database_url
    if not payload.markdown_dir:
        payload.markdown_dir = existing.markdown_dir or settings.memory_markdown_dir
    saved = write_memory_settings(payload)
    return to_public_memory_settings(saved)


def write_memory_settings(config: MemoryStorageSettings) -> MemoryStorageSettings:
    config.updated_at = datetime.now(UTC).isoformat()
    get_memory_settings_path().write_text(
        json.dumps(config.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return config


def test_memory_storage_connection(payload: MemoryStorageSettings | None = None) -> MemoryStorageTestResponse:
    config = payload or read_memory_settings()
    if not config.database_url:
        return MemoryStorageTestResponse(
            ok=False,
            message="PostgreSQL 测试失败：请先填写 Database URL。",
            detail={"missing_fields": ["database_url"]},
        )

    try:
        from app.services.agent_memory import ensure_memory_store

        ensured = ensure_memory_store(config)
        return MemoryStorageTestResponse(
            ok=ensured,
            message="PostgreSQL 记忆库连接成功，数据表已初始化。" if ensured else "PostgreSQL 记忆库未启用。",
            detail={"postgres_enabled": ensured},
        )
    except Exception as exc:
        return MemoryStorageTestResponse(
            ok=False,
            message=f"PostgreSQL 测试失败：{exc}",
            detail={"error": str(exc)},
        )


def to_public_memory_settings(config: MemoryStorageSettings) -> PublicMemoryStorageSettings:
    return PublicMemoryStorageSettings(
        database_url_preview=mask_database_url(config.database_url),
        has_database_url=bool(config.database_url),
        markdown_dir=config.markdown_dir,
        updated_at=config.updated_at,
    )


def mask_database_url(database_url: str) -> str:
    if not database_url:
        return ""
    if "@" not in database_url:
        return database_url[:16] + "***"
    prefix, suffix = database_url.rsplit("@", 1)
    scheme, _, credentials = prefix.partition("://")
    user = credentials.split(":", 1)[0]
    return f"{scheme}://{user}:***@{suffix}"
