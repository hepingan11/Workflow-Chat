# Workflow Chat

Workflow Chat 是一个开源 Digital Employee OS 原型，Openclaw与Codex、Dify等的结合，多角色协作与LLM节点自动编排---下一代开源数字人系统，让每个人都能当老板。

这个项目最主要的不是开发具体操作，而是**控制操作**：数字员工负责理解目标、整理输入、调用工具/工作流 API、等待人工审批、记录执行过程，而不是绕过控制层直接做高风险动作。

**目前仅是MVP版本，正在完善中**

------

**我们要解决什么样的痛点？**

- 数字员工不再是一次用完就不知道下次该做什么的小白
- 在遇到比较重要的节点操作时，由我们人为选择下一步操作
- 不是单个workflow，执行固定的操作，在这里workflow将和mcp一样
- 可以在一个可视化页面优化员工的提示词和命令
- 集成聊天/沟通软件，随时指挥和监控您的数字员工；目前支持telegram、微信bot
- 与现有热门生态集成，让工作流搭建不再陌生；目前仅支持Dify、Codex；Claude Code、Coze、n8n、openclaw等正在路上
- 您可以自定义您和您员工的角色提示词，让消息不再冷冰冰
- 每个员工有单独的”大脑知识库“，不会忘记我之前干了什么
- 有一个”CEO“的角色才统计每个员工的日志
- 每个数字员工之间能在一个”群”里互相沟通，不再单枪匹马作战，知道每个人能做什么

## 核心定位

- 数字员工不是一次性聊天机器人，而是可持续配置、可追踪、可审批的工作角色。
- Workflow / MCP / Dify / Coze / n8n 都应该是数字员工可调用的工具，而不是平台本体。
- 重要节点必须能由人确认，拒绝后流程可以停止或进入其他分支。
- 每个员工可以有自己的提示词、工具权限、模型配置和后续知识库。
- 未来预留 `CEO` 角色，用于统计员工日志、总结日程和追踪目标健康度。

![](https://img2-hepinan.oss-cn-beijing.aliyuncs.com/picgo/20260531034751.png)

<img src="https://img-hepingan.oss-cn-hangzhou.aliyuncs.com/page1/20260601165536754.png" style="zoom:50%;" />

## Quick Start

未拉取仓库时一条命令部署：

```powershell
$script = iwr https://raw.githubusercontent.com/hepingan11/Workflow-Chat/main/scripts/bootstrap.ps1 -UseBasicParsing
[Text.Encoding]::UTF8.GetString($script.RawContentStream.ToArray()) | iex
```

macOS / Linux:

```bash
curl -fsSL https://raw.githubusercontent.com/hepingan11/Workflow-Chat/main/scripts/bootstrap.sh | bash
```

一条命令安装与基础配置：

```powershell
.\setup.ps1
```

macOS / Linux:

```bash
chmod +x ./setup.sh
./setup.sh
```

脚本支持安装依赖，并可选配置 LLM 接口、消息推送、老板设定和长期记忆配置；所有配置都可以跳过，之后在 `/settings/services` 页面继续配置。详细说明见 [一条命令安装与基础配置](docs/setup-installer.md)。

一键启动前后端：

```powershell
.\start.ps1
```

macOS / Linux:

```bash
chmod +x ./start.sh
./start.sh
```

启动脚本会自动补齐本地依赖，前端后台运行并写入 `.workflow-chat/logs/web-dev.log`，当前终端直接输出后端日志。按 `Ctrl+C` 会停止前后端服务。

重复执行远程 bootstrap 脚本时会自动检测当前安装目录和远端最新版：如果本地落后会提示是否更新，并只使用 `git pull --ff-only` 做安全更新；如果存在本地修改或分支分叉，不会强制覆盖文件。本地 setup 重复执行时会提示已有配置，并默认保留记忆库、skills、playbook、运行日志等数据。

API:

```powershell
cd apps/api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Web:

```powershell
cd apps/web
npm install
npm run dev
```

Weixin Bot:

```powershell
cd integrations/weixinProxy
npm install
npm run login
npm run listen
npm run send -- <user_id> <text>
npm run repl
```

后端会在需要微信登录、发送或监听时自动检测 `integrations/weixinProxy` 的本地依赖；如果未安装，会在该目录执行 `npm install`。`/settings/services` 中提供网页扫码入口，扫码成功后会保存 `userId`。业务消息发送会通过 `integrations/weixinProxy/src/workflow-chat-send-text.js` 读取 UTF-8 文本文件发送，避免多行消息被命令行参数截断。

微信业务推送生效前需要完成：

1. 在 `/settings/services` 选择微信 Bot 并扫码登录。
2. 点击“启动监听”，让 `integrations/weixinProxy` 接收消息。
3. 用接收通知的微信号给 Bot 发一条消息，生成该会话的 `context_token`。
4. 点击“同步目标”，保存真正的推送目标 `target_user_id`。
5. 点击“测试发送”，确认后续 `message_push` 和 `human_approval` 节点可以真正推送到微信。

## MVP后要解决什么？

- 我想通过不断任务节点投递，能让对应角色自己总结经验，即训练一个长期记忆，当前使用 SQLite+Markdown 训练长期记忆（后续可平滑升级到向量检索）
- 优化页面动画

## 当前角色

- `programmer`：程序员
- `operator`：运营
- `customer_support`：客服
- `product_manager`：产品经理
- `ceo`：CEO，预留管理角色

## 已支持能力

### 工具配置

当前支持在 Web 中配置外部工具，v0.1 先以 Dify Workflow 形态接入。

能力包括：

- 创建、查看、编辑、删除工具
- 配置工具名称、描述、服务商、授权角色
- 配置 Dify `base_url` 和 `api_key`
- 同步 Dify 工具元信息
- 测试运行工具
- 为不同职位授权可用工具

相关文档：

- [自然语言编排语义词典](docs/orchestration-semantic-dictionary.md)
- [LLM 输出 Schema](docs/orchestration-output-schema.md)
- [Few-shot 示例](docs/orchestration-few-shot-examples.md)

相关 API：

- `POST /playbooks/parse`：解析自然语言编排
- `GET /playbooks`：查看 Playbook
- `POST /playbooks`：创建 Playbook
- `POST /playbooks/{playbook_id}/trigger`：触发一次运行

### 审批运行

Playbook 运行时会生成 Run，并按步骤推进。

当前支持：

- 创建运行记录
- 推进运行步骤
- 执行工具节点
- 在审批节点暂停
- 查看待审批请求
- 批准或拒绝审批
- 审批通过后继续后续节点
- 审批拒绝后取消或停止流程

### 运营发布控制

运营员工当前有独立管理页面，用于把文案和素材整理成工作流输入，再触发 Dify Workflow。

流程：

```text
copy + materials -> prompt-controlled normalization -> workflow API payload -> Dify workflow
```

相关入口：

- Web：`/employees/operator`
- API：`GET /operator/prompt`
- API：`PUT /operator/prompt`
- API：`POST /operator/publish`

说明文档：

- [运营发布控制链路](docs/operator-publish-control.md)

### 服务配置

当前支持配置全局模型服务，以及按职位覆盖模型配置。

相关入口：

- Web：`/settings/services`
- API：`GET /settings/model-config`
- API：`PUT /settings/model-config`

配置项：

- AI API `base_url`
- AI API `api_key`
- 模型名称
- 按职位覆盖模型配置

通知推送当前支持：

- Telegram Bot API
- 微信 Bot，统一使用 [integrations/weixinProxy](integrations/weixinProxy/README.md)

### 角色长期记忆

每个数字员工拥有独立长期记忆。当前采用 `SQLite + Markdown` 双层设计，无需任何外部数据库服务：

- Markdown 是可读、可人工编辑的长期经验主存（记忆的事实来源）
- SQLite 是本地单文件结构化索引，保存任务记录、记忆类型、来源、标签和重要度，提供按相关度排序的 top-N 检索
- 工具节点执行前会把该角色检索到的相关记忆注入到 `long_term_memory`
- 任务完成、取消或失败后会自动复盘，并提炼为事件经验和避坑点

记忆类型：

- `semantic`：知识类记忆
- `episodic`：事件类记忆
- `procedural`：流程类记忆
- `preference`：偏好类记忆
- `pitfall`：避坑点

相关 API：

- `POST /agents/memory-store/init`：初始化 SQLite 记忆表
- `GET /agents/{agent_key}/memories?q=关键词`：检索角色记忆
- `POST /agents/{agent_key}/memories`：手动写入角色记忆

## Web Console

- `/`：数字员工入口面板
- `/employees/operator`：运营员工管理
- `/employees/product_manager`：产品经理管理
- `/employees/{key}`：其他员工管理占位页
- `/settings/services`：模型服务配置
- `/settings/tools`：工具配置

## 本地配置

运行时配置默认保存在：

```text
.workflow-chat/
```

该目录会被 `.gitignore` 忽略，适合保存本地模型配置、工具配置、Playbook、运行记录和审批记录。

长期记忆配置（均为可选，留空使用默认值）：

```powershell
$env:MEMORY_DB_PATH=".workflow-chat/memory.db"
$env:MEMORY_MARKDOWN_DIR=".workflow-chat/memories"
```

长期记忆默认使用本地 SQLite + Markdown，无需任何外部数据库服务：Markdown 是可读、可人工编辑的记忆主存，SQLite 提供结构化索引与按相关度排序的检索。也可以在 `/settings/services` 页面直接配置 SQLite 路径和 Markdown 目录。
