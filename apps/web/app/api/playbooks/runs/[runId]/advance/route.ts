const API_BASE_URL = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";

type RouteContext = {
  params: Promise<{ runId: string }>;
};

export async function POST(_: Request, context: RouteContext) {
  const { runId } = await context.params;
  const response = await fetch(`${API_BASE_URL}/playbooks/runs/${runId}/advance`, {
    method: "POST",
  });
  return Response.json(await response.json(), { status: response.status });
}
