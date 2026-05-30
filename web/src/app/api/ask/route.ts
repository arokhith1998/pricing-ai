// Same-origin proxy: forward an Ask-your-Pricekeel question to FastAPI /ask.
import { requireLead } from "@/lib/gate";

const API = process.env.PRICEKEEL_API ?? "http://127.0.0.1:8000";

export async function POST(req: Request) {
  // Chat answers are demo-gated. (For Phase-3 docs/RAG calls the upstream
  // /ask handler itself can re-check ACCESS_COOKIE; the cookie is forwarded.)
  const denied = await requireLead();
  if (denied) return denied;

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
