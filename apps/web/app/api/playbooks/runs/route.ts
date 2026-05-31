const API_BASE_URL = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const playbookId = url.searchParams.get("playbook_id");
  const target = playbookId
    ? `${API_BASE_URL}/playbooks/runs?playbook_id=${encodeURIComponent(playbookId)}`
    : `${API_BASE_URL}/playbooks/runs`;
  const response = await fetch(target, {
    cache: "no-store",
  });
  return Response.json(await response.json(), { status: response.status });
}
