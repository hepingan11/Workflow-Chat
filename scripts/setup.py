#!/usr/bin/env python3
"""Install and initialize Workflow Chat.

This script is intentionally dependency-free so it can run before the API
environment exists. It writes the same local JSON files used by
/settings/services. Every configuration step is optional.
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / ".workflow-chat"
ROLE_KEYS = ["programmer", "customer_support", "product_manager", "operator", "ceo"]


def main() -> int:
    print("\nWorkflow Chat setup")
    print("=" * 48)
    print("所有配置都可以直接回车跳过，之后到 Web 页面 /settings/services 再配置。")

    ensure_env_file()
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    if ask_yes("是否安装/更新本地依赖？", default=True):
        install_dependencies()

    if ask_yes("是否现在进行基础配置？", default=True):
        configure_model()
        configure_boss()
        configure_memory()
        configure_notification()
    else:
        write_default_configs()

    print("\n完成。常用启动命令：")
    print("API:  .\\.venv\\Scripts\\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000  (Windows)")
    print("API:  ./.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000      (macOS/Linux)")
    print("Web:  cd apps/web && npm run dev")
    print("\n配置文件保存在 .workflow-chat/，可继续在 Web 的 /settings/services 修改。")
    return 0


def install_dependencies() -> None:
    python = ensure_venv()
    run([str(python), "-m", "pip", "install", "--upgrade", "pip"], cwd=ROOT)
    run([str(python), "-m", "pip", "install", "-e", "apps/api"], cwd=ROOT)
    if (ROOT / "apps/web/package.json").exists():
        run(["npm", "install"], cwd=ROOT / "apps/web")
    if ask_yes("是否安装微信 Bot 依赖 integrations/weixinProxy？", default=False):
        run(["npm", "install"], cwd=ROOT / "integrations/weixinProxy")


def ensure_venv() -> Path:
    venv_dir = ROOT / ".venv"
    python = venv_dir / ("Scripts/python.exe" if is_windows() else "bin/python")
    if not python.exists():
        run([sys.executable, "-m", "venv", str(venv_dir)], cwd=ROOT)
    return python


def configure_model() -> None:
    print("\n[1/4] LLM 接口配置")
    if not ask_yes("是否配置全局 AI API？", default=False):
        ensure_json("model-config.json", default_model_settings())
        return

    fmt = ask_choice(
        "接口格式",
        {
            "1": ("openai", "OpenAI Chat Completions"),
            "2": ("openai_responses", "OpenAI Responses"),
            "3": ("anthropic", "Anthropic"),
            "4": ("full_url", "完整 URL"),
        },
        default="1",
    )
    base_url = ask("Base URL", default=default_base_url(fmt))
    api_key = ask_secret("API Key")
    model_name = ask("模型名称", default="gpt-4.1-mini" if fmt != "anthropic" else "claude-3-5-sonnet-latest")

    config = default_model_settings()
    config["global_model"].update(
        {
            "format": fmt,
            "base_url": base_url,
            "api_key": api_key,
            "model_name": model_name,
        }
    )

    if ask_yes("是否为不同员工配置不同模型？", default=False):
        for role_key in ROLE_KEYS:
            if not ask_yes(f"为 {role_key} 启用单独模型？", default=False):
                continue
            role_fmt = ask_choice(
                f"{role_key} 接口格式",
                {
                    "1": ("openai", "OpenAI Chat Completions"),
                    "2": ("openai_responses", "OpenAI Responses"),
                    "3": ("anthropic", "Anthropic"),
                    "4": ("full_url", "完整 URL"),
                },
                default="1",
            )
            config["role_models"][role_key] = {
                "enabled": True,
                "format": role_fmt,
                "base_url": ask(f"{role_key} Base URL", default=base_url),
                "api_key": ask_secret(f"{role_key} API Key", default=api_key),
                "model_name": ask(f"{role_key} 模型名称", default=model_name),
            }

    write_json("model-config.json", config)


def configure_boss() -> None:
    print("\n[2/4] 您的设定")
    if not ask_yes("是否配置老板/用户设定？", default=False):
        ensure_json("boss-config.json", {"preferred_name": "", "role_profile": "", "updated_at": now()})
        return
    write_json(
        "boss-config.json",
        {
            "preferred_name": ask("怎么称呼您"),
            "role_profile": ask_multiline("您的角色设定"),
            "updated_at": now(),
        },
    )


def configure_memory() -> None:
    print("\n[3/4] 长期记忆配置")
    markdown_dir = ask("Markdown 记忆目录", default=".workflow-chat/memories")
    database_url = ""
    if ask_yes("是否配置 PostgreSQL？不配置也会使用本地 Markdown", default=False):
        database_url = ask_secret("PostgreSQL Database URL，例如 postgresql://user:password@host:port/db")
    write_json(
        "memory-storage-config.json",
        {
            "database_url": database_url,
            "markdown_dir": markdown_dir,
            "updated_at": now(),
        },
    )


def configure_notification() -> None:
    print("\n[4/4] 消息推送配置")
    channel = ask_choice(
        "通知渠道",
        {
            "0": ("none", "跳过/不启用"),
            "1": ("telegram", "Telegram"),
            "2": ("weixin_bot", "微信 Bot"),
        },
        default="0",
    )
    settings = default_notification_settings()
    settings["active_channel"] = channel

    if channel == "telegram":
        settings["telegram"].update(
            {
                "enabled": True,
                "bot_token": ask_secret("Telegram Bot Token"),
                "chat_id": ask("Telegram Chat ID"),
                "api_base_url": ask("Telegram API Base URL", default="https://api.telegram.org"),
                "parse_mode": ask("Parse Mode", default="HTML"),
                "message_prefix": ask("消息前缀", default="Workflow Chat"),
                "webhook_secret_token": ask_secret("Webhook Secret Token，可跳过", default=""),
            }
        )
    elif channel == "weixin_bot":
        print("微信 Bot 可先跳过，之后在 Web 页面扫码登录。")
        settings["weixin_bot"].update(
            {
                "enabled": True,
                "message_prefix": ask("消息前缀", default="Workflow Chat"),
                "timeout_seconds": int(ask("请求超时秒数", default="8") or "8"),
            }
        )

    write_json("notification-config.json", settings)


def write_default_configs() -> None:
    ensure_json("model-config.json", default_model_settings())
    ensure_json("boss-config.json", {"preferred_name": "", "role_profile": "", "updated_at": now()})
    ensure_json("memory-storage-config.json", {"database_url": "", "markdown_dir": ".workflow-chat/memories", "updated_at": now()})
    ensure_json("notification-config.json", default_notification_settings())


def default_model_settings() -> dict:
    return {
        "global_model": {"format": "openai", "base_url": "", "api_key": "", "model_name": ""},
        "role_models": {
            key: {"enabled": False, "format": "openai", "base_url": "", "api_key": "", "model_name": ""}
            for key in ROLE_KEYS
        },
        "updated_at": now(),
    }


def default_notification_settings() -> dict:
    return {
        "active_channel": "none",
        "telegram": {
            "enabled": False,
            "bot_token": "",
            "chat_id": "",
            "api_base_url": "https://api.telegram.org",
            "parse_mode": "HTML",
            "message_prefix": "Workflow Chat",
            "webhook_secret_token": "",
            "disable_web_page_preview": True,
        },
        "weixin_bot": {
            "enabled": False,
            "user_id": "",
            "target_user_id": "",
            "message_prefix": "Workflow Chat",
            "timeout_seconds": 8,
        },
        "updated_at": now(),
    }


def ensure_env_file() -> None:
    env = ROOT / ".env"
    example = ROOT / ".env.example"
    if env.exists() or not example.exists():
        return
    env.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
    print("已创建 .env")


def ensure_json(filename: str, data: dict) -> None:
    path = CONFIG_DIR / filename
    if not path.exists():
        write_json(filename, data)


def write_json(filename: str, data: dict) -> None:
    data["updated_at"] = now()
    path = CONFIG_DIR / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已写入 {path.relative_to(ROOT)}")


def run(command: list[str], cwd: Path) -> None:
    print(f"\n$ {' '.join(command)}")
    subprocess.run(command, cwd=str(cwd), check=True)


def ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{prompt}{suffix}: ").strip()
    return value or default


def ask_secret(prompt: str, default: str = "") -> str:
    return ask(prompt, default)


def ask_multiline(prompt: str) -> str:
    print(f"{prompt}（输入空行结束，可直接回车跳过）:")
    lines: list[str] = []
    while True:
        line = input("> ")
        if not line:
            break
        lines.append(line)
    return "\n".join(lines)


def ask_yes(prompt: str, default: bool) -> bool:
    suffix = "Y/n" if default else "y/N"
    value = input(f"{prompt} ({suffix}): ").strip().lower()
    if not value:
        return default
    return value in {"y", "yes", "1", "true", "是"}


def ask_choice(prompt: str, options: dict[str, tuple[str, str]], default: str) -> str:
    print(prompt)
    for key, (_, label) in options.items():
        print(f"  {key}. {label}")
    choice = ask("请选择", default=default)
    return options.get(choice, options[default])[0]


def default_base_url(fmt: str) -> str:
    if fmt == "anthropic":
        return "https://api.anthropic.com"
    return "https://api.openai.com/v1"


def now() -> str:
    return datetime.now(UTC).isoformat()


def is_windows() -> bool:
    return platform.system().lower().startswith("win")


if __name__ == "__main__":
    raise SystemExit(main())
