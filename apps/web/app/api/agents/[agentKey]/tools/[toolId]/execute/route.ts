const API_BASE_URL = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";

type RouteContext = {
  params: Promise<{ agentKey: string; toolId: string }>;
};

export async function POST(request: Request, context: RouteContext) {
  const { agentKey, toolId } = await context.params;
  const body = await request.json();
  const response = await fetch(`${API_BASE_URL}/agents/${agentKey}/tools/${toolId}/execute`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return Response.json(await response.json(), { status: response.status });
}
