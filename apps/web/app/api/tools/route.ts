const API_BASE_URL = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";

export async function GET() {
  const response = await fetch(`${API_BASE_URL}/tools`, {
    cache: "no-store",
  });
  return Response.json(await response.json(), { status: response.status });
}

export async function POST(request: Request) {
  const body = await request.json();
  const response = await fetch(`${API_BASE_URL}/tools`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return Response.json(await response.json(), { status: response.status });
}
