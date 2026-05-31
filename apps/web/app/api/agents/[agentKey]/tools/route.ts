const API_BASE_URL = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";

type RouteContext = {
  params: Promise<{ agentKey: string }>;
};

export async function GET(_: Request, context: RouteContext) {
  const { agentKey } = await context.params;
  const response = await fetch(`${API_BASE_URL}/agents/${agentKey}/tools`, {
    cache: "no-store",
  });
  return Response.json(await response.json(), { status: response.status });
}
