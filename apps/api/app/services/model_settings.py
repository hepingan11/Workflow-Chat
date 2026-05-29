import json
from datetime import UTC, datetime
from pathlib import Path

from app.schemas.settings import (
    AiModelConfig,
    ModelSettings,
    PublicAiModelConfig,
    PublicModelSettings,
    PublicRoleModelConfig,
    RoleModelConfig,
)
from app.services.prompt_config import get_config_dir

DEFAULT_ROLE_KEYS = [
    "programmer",
    "customer_support",
    "product_manager",
    "operator",
    "ceo",
]


def get_model_settings_path() -> Path:
    return get_config_dir() / "model-config.json"


def read_model_settings() -> ModelSettings:
    path = get_model_settings_path()
    if not path.exists():
        settings = _default_model_settings()
        write_model_settings(settings)
        return settings

    data = json.loads(path.read_text(encoding="utf-8"))
    settings = ModelSettings(**data)
    return _with_default_roles(settings)


def read_public_model_settings() -> PublicModelSettings:
    return to_public_model_settings(read_model_settings())


def write_model_settings(settings: ModelSettings) -> ModelSettings:
    settings = _with_default_roles(settings)
    settings.updated_at = datetime.now(UTC).isoformat()
    get_model_settings_path().write_text(
        json.dumps(settings.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return settings


def update_model_settings(payload: ModelSettings) -> PublicModelSettings:
    existing = read_model_settings()

    if not payload.global_model.api_key:
        payload.global_model.api_key = existing.global_model.api_key

    for key, config in payload.role_models.items():
        existing_config = existing.role_models.get(key)
        if existing_config and not config.api_key:
            config.api_key = existing_config.api_key

    saved = write_model_settings(payload)
    return to_public_model_settings(saved)


def to_public_model_settings(settings: ModelSettings) -> PublicModelSettings:
    return PublicModelSettings(
        global_model=PublicAiModelConfig(
            base_url=settings.global_model.base_url,
            has_api_key=bool(settings.global_model.api_key),
            model_name=settings.global_model.model_name,
        ),
        role_models={
            key: PublicRoleModelConfig(
                enabled=config.enabled,
                base_url=config.base_url,
                has_api_key=bool(config.api_key),
                model_name=config.model_name,
            )
            for key, config in settings.role_models.items()
        },
        updated_at=settings.updated_at,
    )


def _default_model_settings() -> ModelSettings:
    return ModelSettings(
        global_model=AiModelConfig(
            base_url="",
            api_key="",
            model_name="",
        ),
        role_models={key: RoleModelConfig() for key in DEFAULT_ROLE_KEYS},
    )


def _with_default_roles(settings: ModelSettings) -> ModelSettings:
    for key in DEFAULT_ROLE_KEYS:
        settings.role_models.setdefault(key, RoleModelConfig())
    return settings
