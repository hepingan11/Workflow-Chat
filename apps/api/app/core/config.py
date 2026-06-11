from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def find_env_file() -> str:
    current = Path(__file__).resolve()
    for parent in current.parents:
        candidate = parent / ".env"
        if candidate.exists():
            return str(candidate)
    return ".env"


def find_project_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "README.md").exists():
            return parent
    return Path.cwd()


class Settings(BaseSettings):
    app_name: str = "Workflow Chat"
    app_env: str = "development"
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    config_dir: str = ".workflow-chat"
    memory_db_path: str = ".workflow-chat/memory.db"
    memory_markdown_dir: str = ".workflow-chat/memories"
    default_workflow_provider: str = "dify"
    dify_api_base_url: str = "https://api.dify.ai/v1"
    dify_api_key: str = ""
    dify_operator_publish_user: str = "workflow-chat-operator"

    model_config = SettingsConfigDict(
        env_file=find_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
