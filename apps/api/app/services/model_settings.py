import json
from datetime import UTC, datetime
from pathlib import Path

import httpx

from app.schemas.settings import (
    AiModelConfig,
    AiServiceFormat,
    ModelSettings,
    ModelTestRequest,
    ModelTestResponse,
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


def test_model_connection(payload: ModelTestRequest) -> ModelTestResponse:
    settings = _merge_saved_api_keys(payload.settings)
    config = settings.global_model
    missing_fields = [
        field
        for field in ["base_url", "api_key", "model_name"]
        if not getattr(config, field, "")
    ]
    if missing_fields:
        return ModelTestResponse(
            ok=False,
            message=f"模型测试失败：缺少 {', '.join(missing_fields)}。",
            detail={"missing_fields": missing_fields},
        )

    try:
        if config.format == AiServiceFormat.ANTHROPIC:
            return _test_anthropic_model(config)
        if config.format == AiServiceFormat.OPENAI_RESPONSES:
            return _test_openai_responses_model(config)
        return _test_openai_chat_model(config)
    except httpx.HTTPError as exc:
        return ModelTestResponse(
            ok=False,
            message=f"模型测试失败：网络或 HTTP 请求错误：{exc}",
            detail={"error": str(exc), "format": config.format},
        )
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        return ModelTestResponse(
            ok=False,
            message=f"模型测试失败：接口返回格式不符合预期：{exc}",
            detail={"error": str(exc), "format": config.format},
        )


def to_public_model_settings(settings: ModelSettings) -> PublicModelSettings:
    return PublicModelSettings(
        global_model=PublicAiModelConfig(
            format=settings.global_model.format,
            base_url=settings.global_model.base_url,
            has_api_key=bool(settings.global_model.api_key),
            model_name=settings.global_model.model_name,
        ),
        role_models={
            key: PublicRoleModelConfig(
                enabled=config.enabled,
                format=config.format,
                base_url=config.base_url,
                has_api_key=bool(config.api_key),
                model_name=config.model_name,
            )
            for key, config in settings.role_models.items()
        },
        updated_at=settings.updated_at,
    )


def extract_responses_text(data: dict) -> str:
    output_text = data.get("output_text")
    if isinstance(output_text, str):
        return output_text

    chunks: list[str] = []
    for output in data.get("output", []):
        for content in output.get("content", []):
            text = content.get("text")
            if isinstance(text, str):
                chunks.append(text)
    return "".join(chunks)


def _merge_saved_api_keys(payload: ModelSettings) -> ModelSettings:
    existing = read_model_settings()
    if not payload.global_model.api_key:
        payload.global_model.api_key = existing.global_model.api_key

    payload = _with_default_roles(payload)
    for key, config in payload.role_models.items():
        existing_config = existing.role_models.get(key)
        if existing_config and not config.api_key:
            config.api_key = existing_config.api_key
    return payload


def _test_openai_chat_model(config: AiModelConfig) -> ModelTestResponse:
    url = config.base_url if config.format == AiServiceFormat.FULL_URL else f"{config.base_url.rstrip('/')}/chat/completions"
    response = httpx.post(
        url,
        headers={
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": config.model_name,
            "messages": [
                {"role": "system", "content": "You are a concise health-check assistant."},
                {"role": "user", "content": "Reply with only: ok"},
            ],
            "temperature": 0,
            "max_tokens": 8,
        },
        timeout=15,
    )
    if response.status_code >= 400:
        return _failed_response(response, config)

    data = response.json()
    content = data["choices"][0]["message"]["content"].strip()
    return _success_response(config, response.status_code, content)


def _test_openai_responses_model(config: AiModelConfig) -> ModelTestResponse:
    response = httpx.post(
        f"{config.base_url.rstrip('/')}/responses",
        headers={
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": config.model_name,
            "instructions": "You are a concise health-check assistant.",
            "input": "Reply with only: ok",
            "temperature": 0,
            "max_output_tokens": 8,
        },
        timeout=15,
    )
    if response.status_code >= 400:
        return _failed_response(response, config)

    content = extract_responses_text(response.json()).strip()
    return _success_response(config, response.status_code, content)


def _test_anthropic_model(config: AiModelConfig) -> ModelTestResponse:
    response = httpx.post(
        f"{config.base_url.rstrip('/')}/v1/messages",
        headers={
            "x-api-key": config.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
        json={
            "model": config.model_name,
            "messages": [{"role": "user", "content": "Reply with only: ok"}],
            "max_tokens": 8,
        },
        timeout=15,
    )
    if response.status_code >= 400:
        return _failed_response(response, config)

    data = response.json()
    content_blocks = data.get("content", [])
    content = "".join(block.get("text", "") for block in content_blocks if block.get("type") == "text").strip()
    return _success_response(config, response.status_code, content)


def _success_response(config: AiModelConfig, status_code: int, content: str) -> ModelTestResponse:
    return ModelTestResponse(
        ok=bool(content),
        message=f"模型测试成功：{config.model_name} 可用。" if content else "模型测试失败：模型返回了空内容。",
        detail={
            "format": config.format,
            "model_name": config.model_name,
            "status_code": status_code,
            "reply": content,
        },
    )


def _failed_response(response: httpx.Response, config: AiModelConfig) -> ModelTestResponse:
    return ModelTestResponse(
        ok=False,
        message=f"模型测试失败：接口返回 HTTP {response.status_code}。",
        detail={
            "format": config.format,
            "model_name": config.model_name,
            "status_code": response.status_code,
            "response_preview": response.text[:800],
        },
    )


def _default_model_settings() -> ModelSettings:
    return ModelSettings(
        global_model=AiModelConfig(
            format=AiServiceFormat.OPENAI,
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
