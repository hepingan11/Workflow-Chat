import json
import os
import subprocess
from pathlib import Path
from shutil import which
from typing import Any
from uuid import uuid4

from app.services.prompt_config import get_config_dir


GLOBAL_PACKAGE_NAME = "weixin-proxy-ilink"
WXILINK_COMMAND_NAMES = ["wxilink", "wxilink.cmd", "weixin-proxy-ilink", "weixin-proxy-ilink.cmd"]


def start_wxilink_login() -> dict[str, Any]:
    result = ensure_wxilink_installed()
    if not result.get("ok"):
        return result
    command = find_wxilink_command()
    if not command:
        return {"ok": False, "message": "未找到 wxilink 命令，请确认 weixin-proxy-ilink 已全局安装。"}

    try:
        subprocess.Popen(
            [command, "login"],
            cwd=str(get_wxilink_workdir()),
            env=build_wxilink_env(),
        )
    except OSError as exc:
        return {"ok": False, "message": f"wxilink login 启动失败：{exc}"}

    return {
        "ok": True,
        "session_id": "global-cli",
        "status": "manual_cli",
        "message": "wxilink login 已在后端终端启动，请查看终端二维码并扫码登录。",
        "command": f"{command} login",
        "state_path": str(get_wxilink_state_path()),
        "installed_now": result.get("installed_now", False),
    }


def read_wxilink_login_status(session_id: str) -> dict[str, Any]:
    state = read_wxilink_state()
    return {
        "ok": True,
        "session_id": session_id or "global-cli",
        "status": "confirmed" if state.get("token") else "manual_cli",
        "qr_status": "",
        "qr_data_url": "",
        "qr_content": "",
        "user_id": str(state.get("userId", "")),
        "message": "wxilink 已登录。" if state.get("token") else "请在终端执行 wxilink login 完成扫码登录。",
        "error": "",
        "account": {
            "userId": state.get("userId", ""),
            "accountId": state.get("accountId", ""),
            "baseUrl": state.get("baseUrl", ""),
        },
    }


def send_wxilink_message(user_id: str, text: str, timeout_seconds: int = 8) -> dict[str, Any]:
    result = ensure_wxilink_installed()
    if not result.get("ok"):
        return result
    if not user_id:
        return {"ok": False, "message": "微信推送目标 User ID 未配置，请先同步推送目标。"}

    node_command = find_node_command()
    if not node_command:
        return {"ok": False, "message": "未找到 node 命令，无法调用 weixin-proxy-ilink 发送消息。"}

    text_path = write_wxilink_message_text(text)
    script_path = Path(__file__).resolve().parent / "weixin_send_text.mjs"
    completed = subprocess.run(
        [node_command, str(script_path), user_id, str(text_path)],
        cwd=str(get_wxilink_workdir()),
        env=build_wxilink_env(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=max(timeout_seconds, 1),
    )
    return {
        "ok": completed.returncode == 0,
        "message": "微信消息已发送。" if completed.returncode == 0 else "微信消息发送失败。",
        "target_user_id": user_id,
        "command": "node weixin_send_text.mjs <target_user_id> <text-file>",
        "text_length": len(text),
        "text_preview": text[:500],
        "text_path": str(text_path),
        "stdout": completed.stdout[-2000:],
        "stderr": completed.stderr[-2000:],
        "returncode": completed.returncode,
    }


def get_first_context_user_id() -> str:
    state = read_wxilink_state()
    context_tokens = state.get("contextTokens") if isinstance(state.get("contextTokens"), dict) else {}
    sessions = state.get("sessions") if isinstance(state.get("sessions"), dict) else {}
    if sessions:
        sorted_sessions = sorted(
            sessions.items(),
            key=lambda item: item[1].get("updatedAt", 0) if isinstance(item[1], dict) else 0,
            reverse=True,
        )
        for user_id, _session in sorted_sessions:
            if user_id in context_tokens:
                return str(user_id)
    for user_id in context_tokens:
        return str(user_id)
    return ""


def read_wxilink_state() -> dict[str, Any]:
    state_path = get_wxilink_state_path()
    if not state_path.exists():
        return {}
    try:
        return json.loads(state_path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}


def get_wxilink_business_status() -> dict[str, Any]:
    state = read_wxilink_state()
    context_tokens = state.get("contextTokens") if isinstance(state.get("contextTokens"), dict) else {}
    sessions = state.get("sessions") if isinstance(state.get("sessions"), dict) else {}
    return {
        "ok": bool(state.get("token")) and bool(context_tokens),
        "logged_in": bool(state.get("token")),
        "bot_user_id": state.get("userId", ""),
        "available_target_user_ids": list(context_tokens.keys()),
        "session_count": len(sessions),
        "context_token_count": len(context_tokens),
        "suggested_target_user_id": get_first_context_user_id(),
        "state_path": str(get_wxilink_state_path()),
    }


def start_wxilink_listen() -> dict[str, Any]:
    result = ensure_wxilink_installed()
    if not result.get("ok"):
        return result
    command = find_wxilink_command()
    if not command:
        return {"ok": False, "message": "未找到 wxilink 命令，请确认 weixin-proxy-ilink 已全局安装。"}
    try:
        subprocess.Popen(
            [command, "listen"],
            cwd=str(get_wxilink_workdir()),
            env=build_wxilink_env(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError as exc:
        return {"ok": False, "message": f"wxilink listen 启动失败：{exc}"}
    return {"ok": True, "message": "wxilink listen 已启动。"}


def ensure_wxilink_installed() -> dict[str, Any]:
    if find_wxilink_command():
        return {"ok": True, "installed_now": False}

    npm_command = find_npm_command()
    if not npm_command:
        return {"ok": False, "message": "未找到 npm 命令，无法全局安装 weixin-proxy-ilink。"}

    install = subprocess.run(
        [npm_command, "install", "-g", GLOBAL_PACKAGE_NAME],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )
    return {
        "ok": install.returncode == 0 and bool(find_wxilink_command()),
        "installed_now": install.returncode == 0,
        "message": "weixin-proxy-ilink 已全局安装。" if install.returncode == 0 else "weixin-proxy-ilink 全局安装失败。",
        "stdout": install.stdout[-1500:],
        "stderr": install.stderr[-1500:],
        "returncode": install.returncode,
    }


def find_wxilink_command() -> str:
    for name in WXILINK_COMMAND_NAMES:
        command = which(name)
        if command:
            return command
    return ""


def find_npm_command() -> str:
    for name in ["npm", "npm.cmd"]:
        command = which(name)
        if command:
            return command
    return ""


def find_node_command() -> str:
    for name in ["node", "node.exe"]:
        command = which(name)
        if command:
            return command
    return ""


def get_wxilink_workdir() -> Path:
    workdir = get_config_dir() / "wxilink-cli"
    workdir.mkdir(parents=True, exist_ok=True)
    (workdir / ".weixin-proxy" / "media").mkdir(parents=True, exist_ok=True)
    return workdir


def write_wxilink_message_text(text: str) -> Path:
    message_dir = get_config_dir() / "wxilink-message-outbox"
    message_dir.mkdir(parents=True, exist_ok=True)
    path = message_dir / f"{uuid4().hex}.txt"
    path.write_text(text, encoding="utf-8")
    return path


def get_wxilink_state_path() -> Path:
    return get_wxilink_workdir() / ".weixin-proxy" / "state.json"


def build_wxilink_env() -> dict[str, str]:
    state_path = get_wxilink_state_path()
    media_dir = state_path.parent / "media"
    env = os.environ.copy()
    env["WEIXIN_PROXY_STATE"] = str(state_path)
    env["WEIXIN_PROXY_MEDIA_DIR"] = str(media_dir)
    package_entry = get_global_wxilink_package_entry()
    if package_entry:
        env["WXILINK_PACKAGE_ENTRY"] = str(package_entry)
    return env


def get_global_wxilink_package_entry() -> Path | None:
    npm_command = find_npm_command()
    if not npm_command:
        return None
    completed = subprocess.run(
        [npm_command, "root", "-g"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
    )
    if completed.returncode != 0:
        return None
    package_root = Path(completed.stdout.strip()) / GLOBAL_PACKAGE_NAME / "src" / "index.js"
    return package_root if package_root.exists() else None
