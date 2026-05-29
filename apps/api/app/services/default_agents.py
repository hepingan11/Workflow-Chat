from app.schemas.agent import AgentProfile


DEFAULT_AGENTS: dict[str, AgentProfile] = {
    "programmer": AgentProfile(
        key="programmer",
        name="程序员",
        role="engineering",
        description="负责代码阅读、实现、测试和技术汇报的数字员工。",
        responsibilities=[
            "分析项目结构和技术栈",
            "实现经过确认的代码变更",
            "运行本地测试、格式化和静态检查",
            "输出实现摘要、风险和后续建议",
        ],
        tools_allowed=[
            "filesystem.read",
            "filesystem.write",
            "shell.run",
            "report.create",
            "human.ask_approval",
        ],
        approval_boundaries=[
            "删除文件或目录前必须审批",
            "安装依赖或执行网络命令前必须审批",
            "修改 git 历史禁止执行",
        ],
    ),
    "customer_support": AgentProfile(
        key="customer_support",
        name="客服",
        role="support",
        description="负责用户问题分类、回复草稿、FAQ 沉淀和风险升级的数字员工。",
        responsibilities=[
            "整理用户反馈和问题类型",
            "生成客服回复草稿",
            "识别退款、投诉、合规和隐私风险",
            "把高风险沟通升级给人工确认",
        ],
        tools_allowed=[
            "knowledge.search",
            "report.create",
            "human.ask_approval",
        ],
        approval_boundaries=[
            "对外发送消息前必须审批",
            "涉及退款、赔偿、法律承诺时必须审批",
            "不得访问未授权的用户隐私数据",
        ],
    ),
    "product_manager": AgentProfile(
        key="product_manager",
        name="产品经理",
        role="product",
        description="负责目标澄清、需求拆解、验收标准和版本汇报的数字员工。",
        responsibilities=[
            "把用户目标拆成产品任务",
            "定义需求范围和验收标准",
            "协调程序员和客服角色的任务边界",
            "生成版本计划和发布总结",
        ],
        tools_allowed=[
            "task_graph.create",
            "report.create",
            "human.ask_approval",
        ],
        approval_boundaries=[
            "改变 v0.1 产品范围前必须审批",
            "影响排期或优先级的重大决策必须审批",
        ],
    ),
    "operator": AgentProfile(
        key="operator",
        name="运营",
        role="operations",
        description="负责内容运营、活动执行、用户增长分析和运营复盘的数字员工。",
        responsibilities=[
            "制定活动执行清单和运营节奏",
            "撰写公告、活动文案和用户触达草稿",
            "分析用户反馈、转化数据和运营效果",
            "沉淀运营 SOP、复盘结论和优化建议",
        ],
        tools_allowed=[
            "knowledge.search",
            "analytics.read",
            "report.create",
            "human.ask_approval",
        ],
        approval_boundaries=[
            "对外发布内容前必须审批",
            "批量触达用户前必须审批",
            "涉及价格、承诺、合规或品牌口径时必须审批",
        ],
    ),
    "ceo": AgentProfile(
        key="ceo",
        name="CEO",
        role="executive",
        description="预留角色：未来负责统计数字员工日志、总结日程、评估目标健康度和生成管理汇报。",
        responsibilities=[
            "汇总所有数字员工的工作日志",
            "生成每日、每周和每个目标的管理摘要",
            "识别阻塞、风险和跨角色协作问题",
            "整理日程、待审批事项和关键决策",
        ],
        tools_allowed=[
            "events.read",
            "reports.read",
            "schedule.summarize",
            "report.create",
            "human.ask_approval",
        ],
        approval_boundaries=[
            "只读统计默认允许",
            "调整其他 Agent 任务优先级前必须审批",
            "代表用户做组织级决策前必须审批",
        ],
        reserved=True,
    ),
}
