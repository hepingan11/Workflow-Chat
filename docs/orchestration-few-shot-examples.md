# 自然语言编排 Few-shot 示例模板 v0.1

这份文档用于给 LLM 提供项目内的高质量解析样本。

使用建议：

- 每次 prompt 至少挑选 3 到 5 条最接近当前输入的样本
- 按“输入 -> 输出”成对喂给 LLM
- 后续把真实失败案例持续加入这里

---

## 示例 01：立即执行一次

输入：

```text
@operator 马上使用#{Ai最新新闻获取}获取最新AI新闻并整理成摘要。
```

关键语义：

- `马上` = 立即执行
- 只执行一次

输出要点：

- `trigger.type = immediate`
- 生成 1 个 `tool` 节点

---

## 示例 02：稍后执行一次

输入：

```text
@operator 等下使用#{Ai最新新闻获取}抓取今天的AI热点。
```

关键语义：

- `等下` = immediate_once with delay

输出要点：

- `trigger.type = immediate`
- 可加 `delay_seconds`

---

## 示例 03：每天固定时间执行

输入：

```text
@operator 每天早上8点使用#{Ai最新新闻获取}整理AI新闻。
```

输出要点：

- `trigger.type = daily`
- `trigger.time = 08:00`

---

## 示例 04：工作日执行

输入：

```text
@operator 每周一到周五早上8点使用#{Ai最新新闻获取}生成日报。
```

输出要点：

- `trigger.type = recurring`
- `trigger.rule = weekdays`

---

## 示例 05：工具串联

输入：

```text
@operator 每天早上8点使用#{Ai最新新闻获取}整理AI热点，再使用#{视频生成}生成短视频。
```

输出要点：

- 两个 `tool` 节点
- 第二个节点 `depends_on` 第一个节点
- 使用 `context_reads/context_writes`

---

## 示例 06：审批后再发布

输入：

```text
@operator 每天早上8点使用#{Ai最新新闻获取}整理AI热点，使用#{视频生成}生成视频，然后发给我确认，确认后再使用#{抖音、小红书发布}发布。
```

输出要点：

- `tool -> tool -> human_approval -> tool`
- 审批节点有 `on_approved_step_ids`

---

## 示例 07：审批拒绝则停止

输入：

```text
@operator 使用#{视频生成}生成视频，发给我确认，有问题则不发布。
```

输出要点：

- `on_rejected_step_ids = []`
- 可视为终止分支

---

## 示例 08：固定时间二段执行

输入：

```text
@operator 早上8点使用#{Ai最新新闻获取}整理新闻，下午2点使用#{抖音、小红书发布}发布。
```

输出要点：

- 两个 `tool` 节点
- 第二个节点 `run_at = 14:00`

---

## 示例 09：跨角色移交

输入：

```text
@customer_support 每天18点汇总用户高频问题，交给@product_manager 生成产品改进建议。
```

输出要点：

- 第一个节点归属 `customer_support`
- 生成 `handoff` 节点
- 后续节点归属 `product_manager`

---

## 示例 10：产品经理交给程序员

输入：

```text
@product_manager 每周一梳理需求优先级，交给@programmer 输出本周开发计划。
```

输出要点：

- `multi_role`
- 包含 `participant_role_keys`

---

## 示例 11：只记录日志

输入：

```text
@ceo 每天晚上9点汇总所有员工日志并记录即可，不需要执行其它操作。
```

输出要点：

- `tool` 或 `noop`
- 终点节点无后续

---

## 示例 12：发给另一个角色继续

输入：

```text
@operator 使用#{Ai最新新闻获取}整理热点后发给@customer_support，让@customer_support 根据内容生成用户解释稿。
```

输出要点：

- `tool -> handoff -> role2 step`

---

## 示例 13：连续三角色协作

输入：

```text
@product_manager 先制定选题，交给@operator 生成内容，再交给@customer_support 整理FAQ。
```

输出要点：

- 至少 3 个节点
- 至少 2 个 handoff

---

## 示例 14：先工具后人工确认

输入：

```text
@programmer 先使用#{代码扫描}检查仓库问题，然后发给我确认是否修复。
```

输出要点：

- `tool -> human_approval`

---

## 示例 15：立即交接

输入：

```text
@product_manager 马上整理本周需求重点并交给@programmer。
```

输出要点：

- `trigger.type = immediate`
- `handoff` 节点

---

## 示例 16：带条件继续

输入：

```text
@operator 使用#{视频生成}生成视频，如果效果没问题就用#{抖音、小红书发布}发布。
```

输出要点：

- 应视为隐式审批或条件节点
- 第一版可降级为 `human_approval`

---

## 示例 17：多工具但同角色

输入：

```text
@operator 先用#{Ai最新新闻获取}整理新闻，再用#{视频生成}做视频，再用#{抖音、小红书发布}发布。
```

输出要点：

- 单角色多工具链

---

## 示例 18：审批通过后定时执行

输入：

```text
@operator 先生成视频发给我确认，我确认没问题后下午2点再用#{抖音、小红书发布}发布。
```

输出要点：

- 审批节点
- 后续发布节点 `run_at = 14:00`

---

## 示例 19：失败不继续

输入：

```text
@operator 如果#{Ai最新新闻获取}失败，就记录日志并停止。
```

输出要点：

- 第一版可先标注为失败策略
- 后续扩展成 error branch

---

## 示例 20：典型完整样例

输入：

```text
@operator 每天早上8点使用#{Ai最新新闻获取}工具获取最新的Ai新闻并整理成视频文案，使用#{视频生成}工具剪辑成视频，然后把消息发给我，我确认没问题后下午2点再使用#{抖音、小红书发布}工具发布到自媒体平台，有问题则不发布。
```

输出要点：

- `daily 08:00`
- `tool(fetch)`
- `tool(generate)`
- `human_approval`
- `tool(publish at 14:00)`
- `reject => stop`

---

## 使用建议

### Prompt 中优先挑选的样本

- 时间词相近
- 角色结构相近
- 审批模式相近
- 工具链长度相近

### 不建议

- 一次性把 20 条全喂给模型
- 不加 schema 直接让模型自由生成
- 不做 validator 直接执行

### 后续维护

- 每次解析失败都记录到这份文档
- 每次新增关键语义词都补一个最小样本
- 每次扩展新节点类型都补 3 条以上样本
