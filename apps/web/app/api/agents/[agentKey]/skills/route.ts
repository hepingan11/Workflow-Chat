const API_BASE_URL = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";

type RouteContext = {
  params: Promise<{ agentKey: string }>;
};

export async function GET(request: Request, context: RouteContext) {
  const { agentKey } = await context.params;
  const { searchParams } = new URL(request.url);
  const q = searchParams.get("q") ?? "";
  const limit = searchParams.get("limit") ?? "20";
  const response = await fetch(
    `${API_BASE_URL}/agents/${agentKey}/skills?q=${encodeURIComponent(q)}&limit=${encodeURIComponent(limit)}`,
    { cache: "no-store" },
  );
  return Response.json(await response.json(), { status: response.status });
}

export async function POST(request: Request, context: RouteContext) {
  const { agentKey } = await context.params;
  const body = await request.json();
  const response = await fetch(`${API_BASE_URL}/agents/${agentKey}/skills`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return Response.json(await response.json(), { status: response.status });
}
