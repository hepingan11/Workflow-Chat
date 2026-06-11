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
            sqlite_path=settings.memory_db_path,
            markdown_dir=settings.memory_markdown_dir,
        )
        write_memory_settings(config)
        return config

    data = json.loads(path.read_text(encoding="utf-8"))
    config = MemoryStorageSettings(**data)
    if not config.sqlite_path:
        config.sqlite_path = settings.memory_db_path
    if not config.markdown_dir:
        config.markdown_dir = settings.memory_markdown_dir
    return config


def read_public_memory_settings() -> PublicMemoryStorageSettings:
    return to_public_memory_settings(read_memory_settings())


def update_memory_settings(payload: MemoryStorageSettings) -> PublicMemoryStorageSettings:
    existing = read_memory_settings()
    if not payload.sqlite_path:
        payload.sqlite_path = existing.sqlite_path or settings.memory_db_path
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
    if not config.sqlite_path:
        config.sqlite_path = settings.memory_db_path

    try:
        from app.services.agent_memory import ensure_memory_store, get_memory_db_path

        ensured = ensure_memory_store(config)
        db_path = get_memory_db_path(config)
        return MemoryStorageTestResponse(
            ok=ensured,
            message=f"SQLite 记忆库连接成功，数据表已初始化：{db_path}",
            detail={"sqlite_enabled": ensured, "db_path": str(db_path)},
        )
    except Exception as exc:
        return MemoryStorageTestResponse(
            ok=False,
            message=f"SQLite 测试失败：{exc}",
            detail={"error": str(exc)},
        )


def to_public_memory_settings(config: MemoryStorageSettings) -> PublicMemoryStorageSettings:
    return PublicMemoryStorageSettings(
        sqlite_path=config.sqlite_path or settings.memory_db_path,
        markdown_dir=config.markdown_dir,
        updated_at=config.updated_at,
    )
