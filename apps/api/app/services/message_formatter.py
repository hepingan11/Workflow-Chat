from typing import Any

import httpx
from pydantic import BaseModel

from app.schemas.settings import AiServiceFormat
from app.services.boss_settings import read_boss_settings
from app.services.model_settings import extract_responses_text, read_model_settings
from app.services.notifications import stringify_message_content
from app.services.prompt_config import read_agent_prompt


class FormattedMessage(BaseModel):
    ok: bool
    content: str
    raw_content: str
    error: str | None = None
    model_name: str | None = None
    used_employee_prompt: bool = False
    used_boss_profile: bool = False
    detail: dict[str, Any] = {}


class LlmFormatError(Exception):
    def __init__(self, message: str, detail: dict[str, Any] | None = None):
        super().__init__(message)
        self.detail = detail or {}


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
    messages = [
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
    ]

    try:
        formatted = request_formatted_message(model, messages)
        if not formatted:
            return FormattedMessage(
                ok=False,
                content="",
                raw_content=raw_content,
                error="LLM 返回了空内容，消息未推送。",
                model_name=model["model_name"],
                detail={"format": model.get("format")},
            )
        return FormattedMessage(
            ok=True,
            content=formatted,
            raw_content=raw_content,
            model_name=model["model_name"],
            used_employee_prompt=bool(employee_prompt),
            used_boss_profile=bool(boss.preferred_name or boss.role_profile),
            detail={"format": model.get("format")},
        )
    except LlmFormatError as exc:
        return FormattedMessage(
            ok=False,
            content="",
            raw_content=raw_content,
            error=f"LLM 消息加工失败：{exc}",
            model_name=model.get("model_name"),
            detail=exc.detail,
        )
    except Exception as exc:
        return FormattedMessage(
            ok=False,
            content="",
            raw_content=raw_content,
            error=f"LLM 消息加工失败：{exc}",
            model_name=model.get("model_name"),
            detail={"format": model.get("format")},
        )


def request_formatted_message(model: dict, messages: list[dict[str, str]]) -> str:
    if model.get("format") == AiServiceFormat.OPENAI_RESPONSES:
        return request_openai_responses_message(model, messages)
    return request_openai_chat_message(model, messages)


def request_openai_responses_message(model: dict, messages: list[dict[str, str]]) -> str:
    url = f"{model['base_url'].rstrip('/')}/responses"
    instructions = next((item["content"] for item in messages if item["role"] == "system"), "")
    user_input = "\n\n".join(item["content"] for item in messages if item["role"] != "system")
    response = httpx.post(
        url,
        headers={
            "Authorization": f"Bearer {model['api_key']}",
            "Content-Type": "application/json",
        },
        json={
            "model": model["model_name"],
            "instructions": instructions,
            "input": user_input,
            "temperature": 0.2,
        },
        timeout=15,
    )
    ensure_successful_json_response(response, url, model)
    return extract_responses_text(response.json()).strip()


def request_openai_chat_message(model: dict, messages: list[dict[str, str]]) -> str:
    url = f"{model['base_url'].rstrip('/')}/chat/completions"
    response = httpx.post(
        url,
        headers={
            "Authorization": f"Bearer {model['api_key']}",
            "Content-Type": "application/json",
        },
        json={
            "model": model["model_name"],
            "messages": messages,
            "temperature": 0.2,
        },
        timeout=15,
    )
    ensure_successful_json_response(response, url, model)
    data = response.json()
    return data["choices"][0]["message"]["content"].strip()


def ensure_successful_json_response(response: httpx.Response, url: str, model: dict) -> None:
    detail = {
        "format": model.get("format"),
        "url": url,
        "status_code": response.status_code,
        "response_preview": response.text[:800],
    }
    if response.status_code >= 400:
        raise LlmFormatError(f"接口返回 HTTP {response.status_code}", detail)
    try:
        response.json()
    except ValueError as exc:
        raise LlmFormatError(f"接口返回不是合法 JSON：{exc}", detail) from exc


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
    return read_agent_prompt(role_key).prompt


def build_format_system_prompt(employee_prompt: str) -> str:
    return "\n".join(
        [
            "你是数字员工的消息整理器。",
            "你的任务是严格基于三个输入整理消息：原始节点输出、员工角色提示词、老板角色设定。",
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
