请解析用户输入中的时间表达。

当前时间：{now_iso}
默认时区：{timezone}

规则：
- cron 使用 5 段格式：minute hour day month weekday。
- 如果是相对时间，必须基于当前时间计算 run_at。
- 如果用户说“待会儿”、“马上”、“等下”、“稍后”但没有具体时间，默认当前时间后 {default_relative_minutes} 分钟。
- 如果是一次性未来时间，trigger_type 使用 scheduled，run_at 必须有值。
- 如果是每天、每日这类周期任务，trigger_type 使用 daily，run_at 为 null。
- 不要编造用户没说的业务动作。

Few-shot 示例：
{examples}

用户输入：
{text}
