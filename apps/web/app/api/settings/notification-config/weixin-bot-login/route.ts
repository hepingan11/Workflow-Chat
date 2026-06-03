const API_BASE_URL = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";

export async function POST(request: Request) {
  const body = await request.json();
  const response = await fetch(`${API_BASE_URL}/settings/notification-config/weixin-bot-login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return Response.json(await safeJson(response, "微信 Bot 登录启动失败"), { status: response.status });
}

async function safeJson(response: Response, fallback: string) {
  const text = await response.text();
  if (!text) {
    return { ok: false, message: fallback, detail: { status: response.status, response_preview: "" } };
  }
  try {
    return JSON.parse(text);
  } catch {
    return { ok: false, message: fallback, detail: { status: response.status, response_preview: text.slice(0, 800) } };
  }
}
