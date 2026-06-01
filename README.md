# Workflow Chat

Workflow Chat 是一个开源 Digital Employee OS 原型。

这个项目最主要的不是开发具体操作，而是**控制操作**：数字员工负责理解目标、整理输入、调用工具/工作流 API、等待人工审批、记录执行过程，而不是绕过控制层直接做高风险动作。

**我们要解决什么样的痛点？**

- 数字员工不再是一次用完就不知道下次该做什么的小白
- 在遇到比较重要的节点操作时，由我们人为选择下一步操作
- 不是单个workflow，执行固定的操作，在这里workflow将和mcp一样
- 可以在一个可视化页面优化员工的提示词和命令
- 集成聊天/沟通软件，随时指挥和监控您的数字员工；目前先拿telegram下手
- 与现有热门生态集成，让工作流搭建不再陌生；目前仅支持Dify；Codex、Claude Code、Coze、n8n、openclaw、herms agent等正在路上
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

![](https://img-hepingan.oss-cn-hangzhou.aliyuncs.com/page1/20260601165536754.png)

## 正在解决

- 我想通过不断任务节点投递，能让对应角色自己总结经验，即训练一个长期记忆

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

## Web Console

- `/`：数字员工入口面板
- `/employees/operator`：运营员工管理
- `/employees/{key}`：其他员工管理占位页
- `/settings/services`：模型服务配置
- `/settings/tools`：工具配置

## Quick Start

API:

```powershell
cd apps/api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Worker:

```powershell
cd apps/worker
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
python -m worker.main
```

Web:

```powershell
cd apps/web
npm install
npm run dev
```

## 本地配置

运行时配置默认保存在：

```text
.workflow-chat/
```

该目录会被 `.gitignore` 忽略，适合保存本地模型配置、工具配置、Playbook、运行记录和审批记录。
