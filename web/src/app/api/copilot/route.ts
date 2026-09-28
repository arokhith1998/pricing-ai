// Same-origin proxy: forwards canonical-copilot calls to FastAPI /copilot/*.
// Two methods on this route:
//   GET  ?action=canonical            → list the six canonical questions
//   GET  ?action=decisions&session_id → list logged decisions for the session
//   POST {action:"canonical", ...}    → ask a canonical question; returns
//                                       narrative + structured opportunities
//   POST {action:"log", ...}          → record accept / reject on opportunities
import { customerRef, requireLead } from "@/lib/gate";

const API = process.env.PRICEKEEL_API ?? "http://127.0.0.1:8000";

async function apiHeaders(): Promise<Record<string, string>> {
  return {
    "Content-Type": "application/json",
    "X-Pricekeel-Key": process.env.PRICEKEEL_API_KEY ?? "",
    "X-Pricekeel-Customer": await customerRef(),
  };
}

async function forwardJson(url: string, init: RequestInit) {
  let upstream: Response;
  try {
    upstream = await fetch(url, init);
  } catch {
    return Response.json({ error: "Copilot is unavailable." }, { status: 502 });
  }
  if (!upstream.ok) {
    // Parse the upstream's own detail (FastAPI's HTTPException shape is
    // {detail}, this app's own routes use {error}) and forward its status
    // for a 4xx instead of collapsing every non-2xx into a 502 body-as-error.
    // A 4xx means the backend understood the request and rejected it (a
    // pydantic validation error, e.g. one echoing the posted analysis back,
    // an unknown session_id, ...): the fix is in the request, and the raw
    // upstream body used to be dumped straight into `error` with the status
    // always flattened to 502, so ChatPanel could not tell "the LLM is down"
    // from "you sent a bad request" (silent-failure-hunter finding 4). 401/403
    // stay a 502: those mean the shared X-Pricekeel-Key itself is wrong, an
    // infra problem, not something the caller's input can fix.
    const body = (await upstream.json().catch(() => null)) as
      | { detail?: unknown; error?: unknown }
      | null;
    const detail =
      body && typeof body.detail === "string"
        ? body.detail
        : body && typeof body.error === "string"
          ? body.error
          : undefined;
    const status =
      upstream.status >= 400 && upstream.status < 500 && ![401, 403].includes(upstream.status)
        ? upstream.status
        : 502;
    return Response.json({ error: detail || "Copilot upstream error." }, { status });
  }
  return Response.json(await upstream.json());
}

export async function GET(req: Request) {
  // Copilot reads (canonical questions, decision log) are demo-gated.
  const denied = await requireLead();
  if (denied) return denied;

  const url = new URL(req.url);
  const action = url.searchParams.get("action") || "canonical";
  const headers = await apiHeaders();
  if (action === "decisions") {
    const sid = url.searchParams.get("session_id") || "";
    return forwardJson(`${API}/copilot/decisions?session_id=${encodeURIComponent(sid)}`,
                       { method: "GET", headers });
  }
  return forwardJson(`${API}/copilot/canonical`, { method: "GET", headers });
}

export async function POST(req: Request) {
  // Copilot question + decision-log writes are demo-gated.
  const denied = await requireLead();
  if (denied) return denied;

  let body: { action?: string } & Record<string, unknown>;
  try {
    body = (await req.json()) as typeof body;
  } catch {
    return Response.json({ error: "Bad request" }, { status: 400 });
  }
  const action = body.action ?? "canonical";
  delete body.action;
  const headers = await apiHeaders();
  if (action === "log") {
    return forwardJson(`${API}/copilot/log`, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
    });
  }
  return forwardJson(`${API}/copilot/canonical`, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });
}
