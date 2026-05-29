# 运营发布控制链路

本项目当前优先验证的不是“让 Agent 直接执行发布动作”，而是先做一个可控、可审计、可替换的运营操作控制层。

核心目标：

```text
接收文案和素材 -> 整理成标准工作流输入 -> 调用已存在的发布工作流 API -> 返回执行结果
```

## 1. 设计原则

- 所有执行动作都优先 API 化。
- 数字员工负责控制、整理、审批和编排，不直接绕过工作流做真实发布。
- 工作流提供方可替换，v0.1 先支持 Dify Workflow API。
- 整理文案的提示词必须可在 Web 控制台修改。
- 发布到外部媒体平台属于高风险动作，后续必须接审批和审计。

## 2. 当前 API

### 2.1 获取运营整理提示词

```text
GET /operator/prompt
```

返回当前运营整理提示词。

### 2.2 更新运营整理提示词

```text
PUT /operator/prompt
```

请求体：

```json
{
  "prompt": "新的运营整理提示词"
}
```

### 2.3 提交运营发布控制请求

```text
POST /operator/publish
```

请求体示例：

```json
{
  "title": "新品功能上线公告",
  "copy": "这里是原始文案内容",
  "platforms": ["公众号", "小红书", "B站"],
  "materials": [
    {
      "name": "封面图",
      "type": "image",
      "url": "https://example.com/cover.png"
    }
  ],
  "campaign": "v0.1 发布",
  "tone": "专业、克制、可信",
  "workflow_provider": "dify",
  "workflow_inputs": {
    "custom_field": "可透传给工作流的额外字段"
  },
  "dry_run": true
}
```

当前接口会把请求整理成 Dify Workflow 所需的 `inputs`，再调用：

```text
POST {DIFY_API_BASE_URL}/workflows/run
```

如果没有配置 `DIFY_API_KEY`，接口会自动进入 `dry_run`，只返回准备好的工作流请求体。

## 3. Dify Workflow 输入约定

当前会传给 Dify 的核心字段：

| 字段 | 说明 |
| --- | --- |
| `control_prompt` | Web 可编辑的运营整理提示词 |
| `title` | 原始标题 |
| `copy` | 原始文案 |
| `platforms` | 目标媒体平台 |
| `materials` | 素材列表 |
| `campaign` | 活动或项目名称 |
| `tone` | 内容语气 |
| `workflow_inputs` | 额外透传字段 |
| `operator_contract` | 控制层约束，如不得直接发布、外部发布需审批 |

## 4. 后续扩展点

### 4.1 工作流提供方

当前只实现：

```text
dify
```

后续可以扩展：

```text
n8n
zapier
custom_http
mcp_tool
```

只需要新增对应的 Workflow Client，并保持 `POST /operator/publish` 的请求格式稳定。

### 4.2 审批与审计

下一步应补：

- `operation_requests`
- `workflow_runs`
- `approval_requests`
- `events`

所有发布控制请求都应该记录：

- 谁提交的
- 提交了什么文案和素材
- 触发了哪个工作流
- 工作流输入是什么
- 是否真实执行
- 是否需要审批
- 执行结果是什么

### 4.3 提示词版本管理

当前提示词保存到本地 JSON 文件：

```text
.workflow-chat/operator-prompt.json
```

后续可以扩展为：

- 数据库存储
- 多版本提示词
- 按角色/平台/工作流区分提示词
- 提示词变更审计

## 5. 服务配置

Web 控制台首页提供“服务配置”入口：

```text
/settings/services
```

当前支持：

- 全局 AI API `base_url`
- 全局 AI API `api_key`
- 全局模型名称
- 高级选项：按职位覆盖模型配置

配置会保存到本地运行配置目录：

```text
.workflow-chat/model-config.json
```

安全说明：

- API Key 不会在读取接口中明文返回。
- Web 页面保存时如果 API Key 留空，会保留服务端已保存的旧 Key。
- 后续需要补配置变更审计和敏感字段加密。
