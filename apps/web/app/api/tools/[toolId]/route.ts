const API_BASE_URL = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";

type RouteContext = {
  params: Promise<{ toolId: string }>;
};

export async function GET(_: Request, context: RouteContext) {
  const { toolId } = await context.params;
  const response = await fetch(`${API_BASE_URL}/tools/${toolId}`, {
    cache: "no-store",
  });
  return Response.json(await response.json(), { status: response.status });
}

export async function PUT(request: Request, context: RouteContext) {
  const { toolId } = await context.params;
  const body = await request.json();
  const response = await fetch(`${API_BASE_URL}/tools/${toolId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return Response.json(await response.json(), { status: response.status });
}

export async function DELETE(_: Request, context: RouteContext) {
  const { toolId } = await context.params;
  const response = await fetch(`${API_BASE_URL}/tools/${toolId}`, {
    method: "DELETE",
  });
  return Response.json(await response.json(), { status: response.status });
}
