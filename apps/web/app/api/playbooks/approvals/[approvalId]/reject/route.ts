const API_BASE_URL = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";

type RouteContext = {
  params: Promise<{ approvalId: string }>;
};

export async function POST(_: Request, context: RouteContext) {
  const { approvalId } = await context.params;
  const response = await fetch(`${API_BASE_URL}/playbooks/approvals/${approvalId}/reject`, {
    method: "POST",
  });
  return Response.json(await response.json(), { status: response.status });
}
