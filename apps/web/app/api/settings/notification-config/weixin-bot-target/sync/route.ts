const API_BASE_URL = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";

export async function POST() {
  const response = await fetch(`${API_BASE_URL}/settings/notification-config/weixin-bot-target/sync`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  return Response.json(await response.json(), { status: response.status });
}
