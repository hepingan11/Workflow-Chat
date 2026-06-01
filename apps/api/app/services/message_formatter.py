from typing import Any

import httpx
from pydantic import BaseModel

from app.services.boss_settings import read_boss_settings
from app.services.model_settings import read_model_settings
from app.services.notifications import stringify_message_content
from app.services.prompt_config import read_operator_prompt


class FormattedMessage(BaseModel):
    ok: bool
    content: str
    raw_content: str
    error: str | None = None
    model_name: str | None = None
    used_employee_prompt: bool = False
    used_boss_profile: bool = False


def format_message_for_boss(role_key: str, title: str, content: Any) -> FormattedMessage:
    model = select_message_model(role_key)
    raw_content = stringify_message_content(content)
    if not model:
        return FormattedMessage(
            ok=False,
            content="",
            raw_content=raw_content,
            error="消息推送需要先配置可用的全局模型或该员工角色模型。",
        )

    boss = read_boss_settings()
    employee_prompt = read_employee_prompt(role_key)

    try:
        response = httpx.post(
            f"{model['base_url'].rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {model['api_key']}",
                "Content-Type": "application/json",
            },
            json={
                "model": model["model_name"],
                "messages": [
                    {
                        "role": "system",
                        "content": build_format_system_prompt(employee_prompt),
                    },
                    {
                        "role": "user",
                        "content": build_format_user_prompt(
                            title=title,
                            content=raw_content,
                            preferred_name=boss.preferred_name,
                            boss_profile=boss.role_profile,
                        ),
                    },
                ],
                "temperature": 0.2,
            },
            timeout=10,
        )
        response.raise_for_status()
        formatted = response.json()["choices"][0]["message"]["content"].strip()
        if not formatted:
            return FormattedMessage(
                ok=False,
                content="",
                raw_content=raw_content,
                error="LLM 返回了空内容，消息未推送。",
                model_name=model["model_name"],
            )
        return FormattedMessage(
            ok=True,
            content=formatted,
            raw_content=raw_content,
            model_name=model["model_name"],
            used_employee_prompt=bool(employee_prompt),
            used_boss_profile=bool(boss.preferred_name or boss.role_profile),
        )
    except Exception as exc:
        return FormattedMessage(
            ok=False,
            content="",
            raw_content=raw_content,
            error=f"LLM 消息加工失败：{exc}",
            model_name=model.get("model_name"),
        )


def select_message_model(role_key: str) -> dict | None:
    settings = read_model_settings()
    role_config = settings.role_models.get(role_key)
    if role_config and role_config.enabled:
        candidate = role_config.model_dump()
    else:
        candidate = settings.global_model.model_dump()

    if not candidate.get("base_url") or not candidate.get("api_key") or not candidate.get("model_name"):
        return None
    return candidate


def read_employee_prompt(role_key: str) -> str:
    if role_key == "operator":
        return read_operator_prompt().prompt
    return ""


def build_format_system_prompt(employee_prompt: str) -> str:
    return "\n".join(
        [
            "你是数字员工的消息整理器。",
            "你的任务是严格基于三个输入来整理消息：原始节点输出、员工角色提示词、老板角色设定。",
            "不要编造事实，不要添加原始结果中不存在的数据。",
            "如果原始结果是 JSON，请提炼重点，而不是完整照抄。",
            "必须体现员工角色提示词里的职责边界和输出风格。",
            "必须根据老板称呼与老板角色设定调整语气、详略、风险提醒和下一步建议。",
            "输出只包含要发送的正文，不要解释你的处理过程。",
            "",
            "员工角色提示词：",
            employee_prompt or "无",
        ]
    )


def build_format_user_prompt(title: str, content: str, preferred_name: str, boss_profile: str) -> str:
    return "\n".join(
        [
            f"消息标题：{title}",
            f"老板称呼：{preferred_name or '老板'}",
            f"老板角色设定：{boss_profile or '未填写'}",
            "",
            "请把下面的原始执行结果加工成适合发给老板的消息。",
            "建议结构：称呼 + 简短结论 + 关键内容 + 风险/下一步建议。",
            "不要直接粘贴完整 JSON。除非数据本身非常短，否则必须总结。",
            "",
            "原始执行结果：",
            content,
        ]
    )
