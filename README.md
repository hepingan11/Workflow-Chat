# Workflow Chat

这个项目最主要的不是开发具体的操作，而是控制操作
An open-source Digital Employee OS prototype.

**我们要解决什么样的痛点？**

- 数字员工不再是一次用完就不知道下次该做什么的小白

- 在遇到比较重要的节点操作时，由我们人为选择下一步操作
- 不是单个workflow，执行固定的操作，在这里workflow将和mcp一样
- 可以在一个可视化页面优化员工的提示词和命令
- 集成聊天/沟通软件，随时指挥和监控您的数字员工
- 与现有热门生态集成，让搭建不再陌生；目前支持Dify、Coze等
- 每个员工有单独的"大脑知识库“，不会忘记我之前干了什么
- 有一个”CEO“的角色才统计每个员工的日志


## Quick Start

API:

```powershell
cd apps/api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
uvicorn app.main:app --reload
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

## Current Status

The repository currently contains the scaffold, role definitions, and the first operator publish control API.

Operator control flow:

```text
copy + materials -> prompt-controlled normalization -> workflow API payload -> Dify workflow
```

See [docs/operator-publish-control.md](docs/operator-publish-control.md).

Web console:

- `/`: employee entry dashboard
- `/employees/operator`: operator workflow control
- `/settings/services`: global and per-role AI model configuration
