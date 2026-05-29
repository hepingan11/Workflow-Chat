import {
  BriefcaseBusiness,
  CalendarDays,
  Code2,
  Headphones,
  Megaphone,
  type LucideIcon,
} from "lucide-react";

export type Employee = {
  name: string;
  key: string;
  status: "active" | "reserved";
  icon: LucideIcon;
  work: string;
  route: string;
  mission: string;
};

export const employees: Employee[] = [
  {
    name: "程序员",
    key: "programmer",
    status: "active",
    icon: Code2,
    work: "代码阅读、实现、测试、技术汇报",
    route: "/employees/programmer",
    mission: "负责把工程目标拆成可执行代码任务，并通过工具 API 控制开发动作。",
  },
  {
    name: "客服",
    key: "customer_support",
    status: "active",
    icon: Headphones,
    work: "问题分类、回复草稿、风险升级",
    route: "/employees/customer_support",
    mission: "负责把用户问题整理成可审批、可追踪、可复用的服务动作。",
  },
  {
    name: "产品经理",
    key: "product_manager",
    status: "active",
    icon: BriefcaseBusiness,
    work: "目标澄清、需求拆解、验收标准",
    route: "/employees/product_manager",
    mission: "负责把业务目标转换成任务图、验收标准和跨角色协作计划。",
  },
  {
    name: "运营",
    key: "operator",
    status: "active",
    icon: Megaphone,
    work: "活动执行、内容触达、增长分析、运营复盘",
    route: "/employees/operator",
    mission: "负责接收文案和素材，整理成标准工作流输入，再通过 API 触发媒体发布流程。",
  },
  {
    name: "CEO",
    key: "ceo",
    status: "reserved",
    icon: CalendarDays,
    work: "日志统计、日程总结、目标健康度汇报",
    route: "/employees/ceo",
    mission: "预留为管理角色，后续汇总数字员工日志、日程和目标健康度。",
  },
];

export function getEmployee(key: string) {
  return employees.find((employee) => employee.key === key);
}
