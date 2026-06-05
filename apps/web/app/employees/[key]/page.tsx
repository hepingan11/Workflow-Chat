import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft, Construction, ShieldCheck } from "lucide-react";

import { getEmployee } from "../../employees";

type PageProps = {
  params: Promise<{
    key: string;
  }>;
};

export default async function EmployeePage({ params }: PageProps) {
  const { key } = await params;
  const employee = getEmployee(key);

  if (!employee || ["operator", "programmer", "customer_support", "product_manager"].includes(employee.key)) {
    notFound();
  }

  const Icon = employee.icon;

  return (
    <main className="shell">
      <section className="employeeHero">
        <Link className="backLink" href="/">
          <ArrowLeft aria-hidden="true" />
          返回员工列表
        </Link>
        <div className="employeeHeroGrid">
          <div>
            <p className="eyebrow">{employee.key}</p>
            <h1>{employee.name}管理</h1>
            <p className="lede">{employee.mission}</p>
          </div>
          <div className="statusPanel">
            <Icon aria-hidden="true" />
            <span>{employee.status}</span>
          </div>
        </div>
      </section>

      <section className="emptyWorkbench">
        <Construction aria-hidden="true" />
        <h2>管理页面待接入</h2>
        <p>
          这个职业的控制 API、提示词配置、审批策略和执行记录会放在这里。当前先完成运营员工的发布工作流控制链路。
        </p>
        <div className="emptyFacts">
          <span>{employee.work}</span>
          <span>API-first</span>
          <span>Auditable</span>
        </div>
      </section>
    </main>
  );
}
