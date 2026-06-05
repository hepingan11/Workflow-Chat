# 一条命令安装与基础配置

本项目提供交互式初始化脚本，用于安装依赖并写入 `/settings/services` 对应的本地配置文件。

## 未拉取仓库时一条命令部署

Windows PowerShell:

```powershell
$script = iwr https://raw.githubusercontent.com/hepingan11/Workflow-Chat/main/scripts/bootstrap.ps1 -UseBasicParsing
[Text.Encoding]::UTF8.GetString($script.RawContentStream.ToArray()) | iex
```

macOS / Linux:

```bash
curl -fsSL https://raw.githubusercontent.com/hepingan11/Workflow-Chat/main/scripts/bootstrap.sh | bash
```

可选环境变量：

```powershell
$env:WORKFLOW_CHAT_REPO_URL="https://github.com/hepingan11/Workflow-Chat.git"
$env:WORKFLOW_CHAT_BRANCH="main"
$env:WORKFLOW_CHAT_INSTALL_DIR="D:\Workflow-Chat"
$script = iwr https://raw.githubusercontent.com/hepingan11/Workflow-Chat/main/scripts/bootstrap.ps1 -UseBasicParsing
[Text.Encoding]::UTF8.GetString($script.RawContentStream.ToArray()) | iex
```

```bash
WORKFLOW_CHAT_REPO_URL="https://github.com/hepingan11/Workflow-Chat.git" \
WORKFLOW_CHAT_BRANCH="main" \
WORKFLOW_CHAT_INSTALL_DIR="$HOME/Workflow-Chat" \
curl -fsSL https://raw.githubusercontent.com/hepingan11/Workflow-Chat/main/scripts/bootstrap.sh | bash
```

脚本会自动 clone 或更新仓库，然后调用本地 `setup.ps1` / `setup.sh`。

要求本机已安装：

- Git
- Python 3.11+
- Node.js / npm

## Windows

```powershell
.\setup.ps1
```

## macOS / Linux

```bash
chmod +x ./setup.sh
./setup.sh
```

## 脚本会做什么

- 创建 `.env`，如果当前还不存在。
- 创建 `.workflow-chat/` 本地配置目录。
- 可选安装 API 依赖：`.venv` + `pip install -e apps/api`。
- 可选安装 Web 依赖：`cd apps/web && npm install`。
- 可选安装微信 Bot 依赖：`cd integrations/weixinProxy && npm install`。
- 可选写入 LLM 接口配置：`.workflow-chat/model-config.json`。
- 可选写入消息推送配置：`.workflow-chat/notification-config.json`。
- 可选写入“老板/用户设定”：`.workflow-chat/boss-config.json`。
- 可选写入长期记忆配置：`.workflow-chat/memory-storage-config.json`。

所有配置步骤都可以直接回车跳过。跳过后可以继续在 Web 页面配置：

```text
/settings/services
```

## 启动服务

API:

```powershell
.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Web:

```powershell
cd apps/web
npm run dev
```

## PostgreSQL 说明

PostgreSQL 可以跳过。不配置 PostgreSQL 时，长期记忆会写入本地 Markdown：

```text
.workflow-chat/memories
```

配置 PostgreSQL 后，系统会同时写入 PostgreSQL 和 Markdown。
