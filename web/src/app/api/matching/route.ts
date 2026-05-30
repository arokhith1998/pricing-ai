// Same-origin proxy: forwards product-matching calls to FastAPI /matching/*.
// One method on this route:
//   POST {action:"compare", my_url, competitor_urls[]}  -> Comparison
//   POST {action:"competitor", url}                     -> single-URL Plan list
import { requireLead } from "@/lib/gate";

const API = process.env.PRICEKEEL_API ?? "http://127.0.0.1:8000";
// Plan extraction is LLM-bound and pricing pages can be slow to fetch;
// give the upstream more headroom than the default Vercel route limit.
export const maxDuration = 60;

async function forwardJson(url: string, init: RequestInit) {
  try {
    const upstream = await fetch(url, init);
    if (!upstream.ok) {
      const text = await upstream.text().catch(() => "");
      return Response.json({ error: text || "Matching upstream error." }, { status: 502 });
    }
    return Response.json(await upstream.json());
  } catch {
    return Response.json({ error: "Matching is unavailable." }, { status: 502 });
  }
}

export async function POST(req: Request) {
  // Competitor-watch is demo-gated. Plus matching fetches outbound URLs,
  // so we want a real cookie before we let anyone trigger that path.
  const denied = await requireLead();
  if (denied) return denied;

  let body: { action?: string } & Record<string, unknown>;
  try {
    body = (await req.json()) as typeof body;
  } catch {
    return Response.json({ error: "Bad request" }, { status: 400 });
  }
  const action = body.action ?? "compare";
  delete body.action;
  if (action === "competitor") {
    return forwardJson(`${API}/matching/competitor`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  }
  return forwardJson(`${API}/matching/compare`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}
