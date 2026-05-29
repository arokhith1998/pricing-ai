// Same-origin proxy: forwards canonical-copilot calls to FastAPI /copilot/*.
// Two methods on this route:
//   GET  ?action=canonical            → list the six canonical questions
//   GET  ?action=decisions&session_id → list logged decisions for the session
//   POST {action:"canonical", ...}    → ask a canonical question; returns
//                                       narrative + structured opportunities
//   POST {action:"log", ...}          → record accept / reject on opportunities
const API = process.env.PRICEKEEL_API ?? "http://127.0.0.1:8000";

async function forwardJson(url: string, init: RequestInit) {
  try {
    const upstream = await fetch(url, init);
    if (!upstream.ok) {
      const text = await upstream.text().catch(() => "");
      return Response.json({ error: text || "Copilot upstream error." }, { status: 502 });
    }
    return Response.json(await upstream.json());
  } catch {
    return Response.json({ error: "Copilot is unavailable." }, { status: 502 });
  }
}

export async function GET(req: Request) {
  const url = new URL(req.url);
  const action = url.searchParams.get("action") || "canonical";
  if (action === "decisions") {
    const sid = url.searchParams.get("session_id") || "";
    return forwardJson(`${API}/copilot/decisions?session_id=${encodeURIComponent(sid)}`,
                       { method: "GET" });
  }
  return forwardJson(`${API}/copilot/canonical`, { method: "GET" });
}

export async function POST(req: Request) {
  let body: { action?: string } & Record<string, unknown>;
  try {
    body = (await req.json()) as typeof body;
  } catch {
    return Response.json({ error: "Bad request" }, { status: 400 });
  }
  const action = body.action ?? "canonical";
  delete body.action;
  if (action === "log") {
    return forwardJson(`${API}/copilot/log`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  }
  return forwardJson(`${API}/copilot/canonical`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}
