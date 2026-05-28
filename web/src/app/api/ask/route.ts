// Same-origin proxy: forward an Ask-the-Analyst question to FastAPI /ask.
const API = process.env.PRICEKEEL_API ?? "http://127.0.0.1:8000";

export async function POST(req: Request) {
  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return Response.json({ error: "Bad request" }, { status: 400 });
  }
  try {
    const upstream = await fetch(`${API}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!upstream.ok) {
      const text = await upstream.text().catch(() => "");
      return Response.json({ error: text || "Could not answer." }, { status: 502 });
    }
    return Response.json(await upstream.json());
  } catch {
    return Response.json({ error: "Assistant is unavailable." }, { status: 502 });
  }
}
