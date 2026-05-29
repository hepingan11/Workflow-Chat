import json
from datetime import UTC, datetime
from pathlib import Path

from app.core.config import find_project_root, settings
from app.schemas.operator import OperatorPromptConfig

DEFAULT_OPERATOR_PROMPT = """你是一个运营发布控制助手。
你的任务不是直接发布内容，而是把用户提供的文案和素材整理成稳定、清晰、可审计的工作流输入。

请执行：
1. 保留原始文案的核心意图，不编造事实。
2. 根据目标平台整理标题、正文、话题标签、素材清单和注意事项。
3. 标记需要人工确认的风险，例如夸大承诺、价格信息、隐私信息、版权风险、外部链接风险。
4. 输出应适合作为发布工作流的 inputs，不要执行真实发布动作。
"""


def get_config_dir() -> Path:
    path = Path(settings.config_dir)
    if not path.is_absolute():
        path = find_project_root() / path
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_operator_prompt_path() -> Path:
    return get_config_dir() / "operator-prompt.json"


def read_operator_prompt() -> OperatorPromptConfig:
    path = get_operator_prompt_path()
    if not path.exists():
        config = OperatorPromptConfig(prompt=DEFAULT_OPERATOR_PROMPT, updated_at=_now())
        write_operator_prompt(config.prompt)
        return config

    data = json.loads(path.read_text(encoding="utf-8"))
    return OperatorPromptConfig(**data)


def write_operator_prompt(prompt: str) -> OperatorPromptConfig:
    config = OperatorPromptConfig(prompt=prompt, updated_at=_now())
    get_operator_prompt_path().write_text(
        json.dumps(config.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return config


def _now() -> str:
    return datetime.now(UTC).isoformat()
