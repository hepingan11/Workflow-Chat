import Link from "next/link";
import { ArrowRight, Settings, ShieldCheck } from "lucide-react";

import { employees } from "./employees";

export default function Home() {
  return (
    <main className="shell">
      <section className="masthead">
        <div>
          <p className="eyebrow">Digital Employee OS</p>
          <h1>选择一个数字员工</h1>
          <p className="lede">
            每个职业都有独立的管理页面。平台负责控制操作、整理输入、触发工作流 API 和保留审计边界。
          </p>
        </div>
        <div className="statusPanel">
          <ShieldCheck aria-hidden="true" />
          <span>Control layer first</span>
        </div>
      </section>

      <section className="quickActions" aria-label="服务配置">
        <Link className="serviceConfigButton" href="/settings/services">
          <Settings aria-hidden="true" />
          服务配置
          <ArrowRight aria-hidden="true" />
        </Link>
      </section>

      <section className="employeeGrid" aria-label="数字员工角色">
        {employees.map((employee) => {
          const Icon = employee.icon;
          return (
            <Link className="employeeCard" href={employee.route} key={employee.key}>
              <div className="cardTop">
                <Icon aria-hidden="true" />
                <span data-status={employee.status}>{employee.status}</span>
              </div>
              <h2>{employee.name}</h2>
              <p>{employee.work}</p>
              <div className="cardAction">
                <code>{employee.key}</code>
                <ArrowRight aria-hidden="true" />
              </div>
            </Link>
          );
        })}
      </section>
    </main>
  );
}
