const API_BASE_URL = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const roleKey = url.searchParams.get("role_key");
  const target = roleKey ? `${API_BASE_URL}/playbooks?role_key=${encodeURIComponent(roleKey)}` : `${API_BASE_URL}/playbooks`;
  const response = await fetch(target, {
    cache: "no-store",
  });
  return Response.json(await response.json(), { status: response.status });
}

export async function POST(request: Request) {
  const body = await request.json();
  const response = await fetch(`${API_BASE_URL}/playbooks`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return Response.json(await response.json(), { status: response.status });
}
