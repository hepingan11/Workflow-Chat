const API_BASE_URL = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";

export async function DELETE(_request: Request, context: { params: Promise<{ playbookId: string }> }) {
  const { playbookId } = await context.params;
  const response = await fetch(`${API_BASE_URL}/playbooks/${playbookId}`, {
    method: "DELETE",
  });
  return Response.json(await response.json(), { status: response.status });
}
