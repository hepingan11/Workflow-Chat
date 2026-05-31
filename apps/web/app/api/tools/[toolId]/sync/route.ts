const API_BASE_URL = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";

type RouteContext = {
  params: Promise<{ toolId: string }>;
};

export async function POST(_: Request, context: RouteContext) {
  const { toolId } = await context.params;
  const response = await fetch(`${API_BASE_URL}/tools/${toolId}/sync`, {
    method: "POST",
  });
  return Response.json(await response.json(), { status: response.status });
}
