"use client";

import Link from "next/link";
import { ArrowLeft, FileText, Megaphone, Play, Save, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";

export default function OperatorPage() {
  const [prompt, setPrompt] = useState("");
  const [title, setTitle] = useState("新品功能上线公告");
  const [copy, setCopy] = useState("我们准备发布一篇介绍数字员工运营控制能力的文章。");
  const [platforms, setPlatforms] = useState("公众号, 小红书, B站");
  const [materialUrl, setMaterialUrl] = useState("");
  const [result, setResult] = useState("等待提交");
  const [isBusy, setIsBusy] = useState(false);

  useEffect(() => {
    fetch("/api/operator/prompt")
      .then((response) => response.json())
      .then((data) => setPrompt(data.prompt ?? ""))
      .catch(() => setResult("无法读取提示词，请确认 API 代理或后端服务已启动。"));
  }, []);

  async function savePrompt() {
    setIsBusy(true);
    try {
      const response = await fetch("/api/operator/prompt", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      });
      if (!response.ok) {
        throw new Error("save failed");
      }
      setResult("提示词已保存");
    } catch {
      setResult("提示词保存失败");
    } finally {
      setIsBusy(false);
    }
  }

  async function submitPublish() {
    setIsBusy(true);
    try {
      const response = await fetch("/api/operator/publish", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title,
          copy,
          platforms: platforms
            .split(",")
            .map((item) => item.trim())
            .filter(Boolean),
          materials: materialUrl
            ? [
                {
                  name: "运营素材",
                  type: "link",
                  url: materialUrl,
                },
              ]
            : [],
          workflow_provider: "dify",
          dry_run: true,
        }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(JSON.stringify(data));
      }
      setResult(JSON.stringify(data, null, 2));
    } catch {
      setResult("发布控制请求失败");
    } finally {
      setIsBusy(false);
    }
  }

  return (
    <main className="shell">
      <section className="employeeHero">
        <Link className="backLink" href="/">
          <ArrowLeft aria-hidden="true" />
          返回员工列表
        </Link>
        <div className="employeeHeroGrid">
          <div>
            <p className="eyebrow">Operator Employee</p>
            <h1>运营员工管理</h1>
            <p className="lede">
              这里管理运营员工的整理提示词和发布工作流输入。数字员工只做控制、整理和触发 API，不绕过工作流直接发布。
            </p>
          </div>
          <div className="statusPanel">
            <ShieldCheck aria-hidden="true" />
            <span>Dify workflow ready</span>
          </div>
        </div>
      </section>

      <section className="operatorConsole" aria-label="运营发布控制台">
        <div className="editorPanel">
          <div className="panelHeader">
            <FileText aria-hidden="true" />
            <h2>整理提示词</h2>
            <button type="button" onClick={savePrompt} disabled={isBusy} title="保存提示词">
              <Save aria-hidden="true" />
              保存
            </button>
          </div>
          <textarea
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            aria-label="运营整理提示词"
          />
        </div>

        <div className="publishPanel">
          <div className="panelHeader">
            <Megaphone aria-hidden="true" />
            <h2>发布工作流输入</h2>
            <button type="button" onClick={submitPublish} disabled={isBusy} title="生成工作流输入">
              <Play aria-hidden="true" />
              Dry Run
            </button>
          </div>
          <label>
            标题
            <input value={title} onChange={(event) => setTitle(event.target.value)} />
          </label>
          <label>
            平台
            <input value={platforms} onChange={(event) => setPlatforms(event.target.value)} />
          </label>
          <label>
            素材链接
            <input value={materialUrl} onChange={(event) => setMaterialUrl(event.target.value)} />
          </label>
          <label>
            文案
            <textarea value={copy} onChange={(event) => setCopy(event.target.value)} />
          </label>
        </div>
      </section>

      <section className="resultPanel" aria-label="执行结果">
        <h2>API 执行结果</h2>
        <pre>{result}</pre>
      </section>
    </main>
  );
}
