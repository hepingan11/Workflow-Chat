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

## 重复执行与版本更新

远程 bootstrap 脚本可以重复执行。再次运行时会先检测安装目录：

- 如果目录不存在，会 clone 仓库。
- 如果目录已经是 Git 仓库，会先 `git fetch` 并比较本地版本和 `origin/main`。
- 如果本地版本低于远端最新版，会提示是否先更新，再使用 `git pull --ff-only` 执行安全更新。
- 如果本地已经是最新版，会直接继续执行本地 setup。
- 如果本地有未提交修改，会提示风险；脚本不会执行 `git reset`，也不会强制覆盖你的文件。
- 如果本地分支和远端已经分叉，会跳过自动更新，提示你先手动处理 Git 状态。

想在自动化部署里跳过确认提示，可以设置：

```powershell
$env:WORKFLOW_CHAT_YES="1"
```

```bash
WORKFLOW_CHAT_YES=1
```

本地 setup 也可以重复执行。它会提示已有 `.env`、`.venv`、`node_modules` 和 `.workflow-chat` 配置；默认不会删除记忆库、skills、playbook、运行日志等本地数据。只有你选择重新进行基础配置时，相关服务配置 JSON 才会被重写。

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
