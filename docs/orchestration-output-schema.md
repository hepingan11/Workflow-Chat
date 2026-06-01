# 自然语言编排 LLM 输出 Schema v0.1

这份文档定义 LLM 在解析自然语言编排时，必须输出的结构化数据格式。

目标：

- 可验证
- 可执行
- 可扩展到多角色协作
- 与当前 `playbook` / `run` / `approval` 模型兼容

## 1. 顶层结构

```json
{
  "role_key": "operator",
  "name": "AI 新闻视频日报",
  "trigger": {},
  "collaboration": {},
  "steps": [],
  "referenced_tools": [],
  "unresolved_tools": []
}
```

## 2. 顶层字段定义

### 2.1 `role_key`

- 类型：`string`
- 含义：主责任角色
- 说明：单角色模式下通常等于 owner role；多角色模式下表示入口角色

### 2.2 `name`

- 类型：`string`
- 含义：剧本名称

### 2.3 `trigger`

```json
{
  "type": "scheduled",
  "time": "08:00",
  "timezone": "Asia/Shanghai",
  "cron": "0 8 * * *",
  "run_at": "2026-06-01T08:00:00+08:00",
  "description": "每天 08:00 执行"
}
```

当前推荐枚举：

- `immediate`
- `scheduled`
- `daily`
- `recurring`

时间解析要求：

- `cron` 使用 5 段格式：`minute hour day month weekday`
- 绝对时间如 `每天早上8点` 输出 `cron = "0 8 * * *"`
- 相对时间如 `5分钟后` 需要先获取当前时间，再推算 `run_at`
- `待会儿`、`马上`、`等下`、`稍后` 如果没有明确时间，默认当前时间后 10 分钟
- 无法通过规则解析时，可以调用 LLM 输出本结构，但仍必须返回结构化 JSON

### 2.4 `collaboration`

```json
{
  "mode": "single_role",
  "owner_role_key": "operator",
  "participant_role_keys": [],
  "handoff_strategy": "manual",
  "shared_context_keys": []
}
```

字段说明：

- `mode`: `single_role | multi_role`
- `owner_role_key`: 最终负责人
- `participant_role_keys`: 参与角色列表
- `handoff_strategy`: `manual | auto`
- `shared_context_keys`: 共享上下文键列表

## 3. Step 结构

```json
{
  "id": "step_fetch_source",
  "name": "执行 Ai最新新闻获取",
  "type": "tool",
  "role_key": "operator",
  "assignee_role_key": "operator",
  "participant_role_keys": [],
  "depends_on_step_ids": [],
  "handoff_to_role_key": null,
  "next_step_ids": ["step_generate_asset"],
  "on_approved_step_ids": [],
  "on_rejected_step_ids": [],
  "context_reads": [],
  "context_writes": ["fetched_result"],
  "config": {}
}
```

## 4. Step 字段说明

### 4.1 通用字段

- `id`
- `name`
- `type`
- `role_key`
- `assignee_role_key`
- `participant_role_keys`
- `depends_on_step_ids`
- `handoff_to_role_key`
- `next_step_ids`
- `on_approved_step_ids`
- `on_rejected_step_ids`
- `context_reads`
- `context_writes`
- `config`

### 4.2 `type` 枚举

- `tool`
- `human_approval`
- `handoff`
- `noop`

## 5. `tool` 节点要求

`config` 至少包含：

```json
{
  "tool_id": "tool_xxx",
  "tool_name": "Ai最新新闻获取",
  "run_at": "08:00",
  "input_template": {},
  "needs_previous_output": false
}
```

约束：

- 必须有 `tool_name`
- 解析后建议补全 `tool_id`
- 如果依赖上一步输出，`needs_previous_output = true`

## 6. `human_approval` 节点要求

`config` 至少包含：

```json
{
  "channel": "message",
  "message_template": "请确认今日内容是否可发布",
  "proceed_if": "approved"
}
```

约束：

- 必须有 `on_approved_step_ids`
- 可选 `on_rejected_step_ids`
- 默认审批对象为用户

## 7. `handoff` 节点要求

```json
{
  "id": "step_handoff_to_pm",
  "name": "交接给产品经理",
  "type": "handoff",
  "role_key": "operator",
  "assignee_role_key": "operator",
  "handoff_to_role_key": "product_manager",
  "next_step_ids": ["step_pm_review"],
  "context_reads": ["draft_report"],
  "context_writes": [],
  "config": {
    "message_template": "请产品经理基于现有草稿继续处理"
  }
}
```

约束：

- 必须有 `handoff_to_role_key`
- 必须显式定义交给哪个后续节点

## 8. `noop` 节点要求

用途：

- 只记录日志
- 只终止流程
- 只做状态标记

示例：

```json
{
  "id": "step_stop",
  "name": "终止发布",
  "type": "noop",
  "next_step_ids": [],
  "config": {
    "reason": "approval rejected"
  }
}
```

## 9. Validator 必做校验

### 9.1 基础校验

- `role_key` 是否存在
- `participant_role_keys` 是否存在
- `tool_name` 是否存在于注册表
- `tool_id` 是否与 `tool_name` 匹配

### 9.2 图结构校验

- 所有 `next_step_ids` 必须指向已有节点
- 所有 `depends_on_step_ids` 必须指向已有节点
- 不允许出现悬空审批分支
- 不允许出现无入口节点

### 9.3 权限校验

- 工具是否授权给 `assignee_role_key`
- handoff 目标角色是否存在

### 9.4 语义校验

- `human_approval` 节点必须有 approve 分支或终止规则
- `handoff` 节点必须有目标角色
- `context_reads` 必须能在上游节点找到来源

## 10. 推荐解析流程

1. 规则层抽取：
   - 角色
   - 工具
   - 时间
   - 审批词
   - handoff 词
2. LLM 输出本 schema
3. Validator 校验
4. Normalizer 修正默认值
5. 保存为 playbook

## 10.1 时间解析工程约定

时间解析采用“规则优先，LLM 兜底”的方式：

- 规则层优先处理高频、低歧义表达，例如 `5分钟后`、`待会儿`、`每天早上8点`、`明天上午10点`。
- LLM 只在规则层无法解析时调用，避免每次解析都产生额外延迟和成本。
- LLM 必须返回结构化 JSON，不能返回解释性文本。
- LLM 输出必须通过 `ParsedTime` schema 和 cron 校验后才能进入 playbook。
- LLM 调用失败、超时或输出不合法时，系统回退到默认触发时间。

当前代码位置：

- `apps/api/app/services/time_parser/rules.py`：规则解析。
- `apps/api/app/services/time_parser/llm.py`：LLM 兜底解析。
- `apps/api/app/services/time_parser/validators.py`：结构化输出校验。
- `apps/api/app/services/time_parser/prompts/system.md`：系统提示词模板。
- `apps/api/app/services/time_parser/prompts/user.md`：用户提示词模板。
- `apps/api/app/services/time_parser/prompts/examples.json`：Few-shot 示例。

后续新增时间表达时，优先判断是否能沉淀为规则；只有长尾、模糊、多语言或上下文相关表达才建议加入 Few-shot 或交给 LLM。

## 11. 输出约束建议

给 LLM 的要求：

- 只输出 JSON
- 不输出解释性文本
- 不猜不存在的角色
- 不猜不存在的工具
- 无法确认时放入 `unresolved_tools`

## 12. 当前与代码映射

当前项目内对应文件：

- `apps/api/app/schemas/playbooks.py`
- `apps/api/app/services/playbooks.py`

这份 schema 文档是它们的解释层规范。
