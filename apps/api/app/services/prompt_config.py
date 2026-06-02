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

DEFAULT_PRODUCT_MANAGER_PROMPT = """你是一个产品经理控制助手。
你的任务不是直接替团队完成所有执行动作，而是把业务目标整理成清晰、可验收、可协作的产品工作输入。

请执行：
1. 澄清目标、用户、场景、约束和成功指标。
2. 将需求拆成优先级、验收标准、风险点和依赖关系。
3. 标记需要人工确认的范围变更、模糊需求、资源冲突和高风险假设。
4. 输出应适合作为需求分析、PRD、任务编排或跨角色协作工作流的 inputs。
"""

DEFAULT_AGENT_PROMPTS = {
    "operator": {
        "name": "运营发布整理提示词",
        "prompt": DEFAULT_OPERATOR_PROMPT,
    },
    "product_manager": {
        "name": "产品经理需求整理提示词",
        "prompt": DEFAULT_PRODUCT_MANAGER_PROMPT,
    },
}


def get_config_dir() -> Path:
    path = Path(settings.config_dir)
    if not path.is_absolute():
        path = find_project_root() / path
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_operator_prompt_path() -> Path:
    return get_config_dir() / "operator-prompt.json"


def get_agent_prompt_path(role_key: str) -> Path:
    return get_config_dir() / f"{role_key}-prompt.json"


def read_operator_prompt() -> OperatorPromptConfig:
    return read_agent_prompt("operator")


def write_operator_prompt(prompt: str) -> OperatorPromptConfig:
    return write_agent_prompt("operator", prompt)


def read_agent_prompt(role_key: str) -> OperatorPromptConfig:
    if role_key == "operator":
        legacy_path = get_operator_prompt_path()
        path = get_agent_prompt_path(role_key)
        if legacy_path.exists() and not path.exists():
            data = json.loads(legacy_path.read_text(encoding="utf-8"))
            config = OperatorPromptConfig(**data)
            write_agent_prompt(role_key, config.prompt)

    path = get_agent_prompt_path(role_key)
    defaults = DEFAULT_AGENT_PROMPTS.get(
        role_key,
        {
            "name": f"{role_key} 角色提示词",
            "prompt": "你是一个数字员工控制助手。请把输入整理成清晰、可执行、可审计的工作流输入。",
        },
    )
    if not path.exists():
        config = OperatorPromptConfig(
            role_key=role_key,
            name=defaults["name"],
            prompt=defaults["prompt"],
            updated_at=_now(),
        )
        write_agent_prompt(role_key, config.prompt)
        return config

    data = json.loads(path.read_text(encoding="utf-8"))
    return OperatorPromptConfig(**data)


def write_agent_prompt(role_key: str, prompt: str) -> OperatorPromptConfig:
    defaults = DEFAULT_AGENT_PROMPTS.get(role_key, {"name": f"{role_key} 角色提示词"})
    config = OperatorPromptConfig(
        role_key=role_key,
        name=defaults["name"],
        prompt=prompt,
        updated_at=_now(),
    )
    get_agent_prompt_path(role_key).write_text(
        json.dumps(config.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if role_key == "operator":
        get_operator_prompt_path().write_text(
            json.dumps(config.model_dump(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return config


def read_legacy_operator_prompt() -> OperatorPromptConfig:
    path = get_operator_prompt_path()
    if not path.exists():
        config = OperatorPromptConfig(prompt=DEFAULT_OPERATOR_PROMPT, updated_at=_now())
        write_agent_prompt("operator", config.prompt)
        return config

    data = json.loads(path.read_text(encoding="utf-8"))
    return OperatorPromptConfig(**data)


def _now() -> str:
    return datetime.now(UTC).isoformat()
