import { getExceptions, postException, type ExceptionInput } from "@/lib/api";
import { requireLead } from "@/lib/gate";

// Same-origin proxy for the governance loop:
//   POST → FastAPI /exceptions  (price + log an approval or exception request)
//   GET  → FastAPI /exceptions  (the decision log, newest first)
// Keeps the API base URL and shared secret server-side. Demo-gated like the
// other /guidance endpoints (recommend, copilot).

export async function POST(req: Request) {
  const denied = await requireLead();
  if (denied) return denied;

  let body: Partial<ExceptionInput>;
  try {
    body = (await req.json()) as Partial<ExceptionInput>;
  } catch {
    return Response.json({ error: "Bad request" }, { status: 400 });
  }

  const deal_id = typeof body.deal_id === "string" ? body.deal_id.trim() : "";
  const requested_discount_pct = body.requested_discount_pct;
  const justification =
    typeof body.justification === "string" ? body.justification.trim() : "";
  const requested_by =
    typeof body.requested_by === "string" ? body.requested_by.trim() : "";

  if (!deal_id) {
    return Response.json({ error: "deal_id required" }, { status: 400 });
  }
  // Contract note: discount values on this endpoint are percent 0-100 (not
  // the 0-1 fractions the diagnostic endpoints use), and the engine's scoring
  // grid caps requests at 40 percent. Mirror the cap here so the user gets a
  // clear message instead of an upstream 422.
  if (
    typeof requested_discount_pct !== "number" ||
    !Number.isFinite(requested_discount_pct) ||
    requested_discount_pct < 0 ||
    requested_discount_pct > 40
  ) {
    return Response.json(
      { error: "requested_discount_pct must be a percentage between 0 and 40" },
      { status: 400 },
    );
  }
  if (!justification) {
    return Response.json({ error: "justification required" }, { status: 400 });
  }
  if (!requested_by) {
    return Response.json({ error: "requested_by required" }, { status: 400 });
  }

  try {
    const result = await postException({
      deal_id,
      requested_discount_pct,
      justification,
      requested_by,
    });
    return Response.json(result);
  } catch {
    return Response.json(
      { error: "Could not log this decision. Is the API running?" },
      { status: 502 },
    );
  }
}

export async function GET(req: Request) {
  const denied = await requireLead();
  if (denied) return denied;

  const raw = parseInt(new URL(req.url).searchParams.get("limit") ?? "50", 10);
  const limit = Math.min(Math.max(Number.isFinite(raw) ? raw : 50, 1), 200);

  try {
    return Response.json(await getExceptions(limit));
  } catch {
    return Response.json(
      { error: "Decision log is unavailable. Is the API running?" },
      { status: 502 },
    );
  }
}
