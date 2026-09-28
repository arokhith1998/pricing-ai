import { getDigestAll } from "@/lib/api";
import { sendDigest } from "@/lib/notify";

// The weekly digest sender. Hit by a cron (Vercel cron, GitHub Action, or
// curl), never by a browser, so the gate is a shared secret header instead
// of a cookie:
//
//   POST /api/digest/send
//   X-Cron-Key: $CRON_SECRET
//
// Behavior matrix:
//   CRON_SECRET set, header matches      → send
//   CRON_SECRET set, header missing/off  → 401
//   CRON_SECRET unset, production        → 503 (refuse to run an open relay)
//   CRON_SECRET unset, dev               → allow (local testing)
//
// The digests come from the FastAPI GET /digest/all (server-side via
// apiFetch, which adds X-Pricekeel-Key and the timeout): one per real
// customer with decision-log activity in the window, excluding demo:*
// tenants. (2026-09-27 fix: this used to call GET /digest for the "default"
// tenant, which nobody writes to once a visitor is either a verified access
// code or an anonymous demo:<uuid>, so the cron email reported zero activity
// forever.) Each digest goes out through sendDigest in notify.ts; with
// RESEND_API_KEY unset, sendDigest logs the rendered text and reports a dry
// run. One tenant's send failure does not block the others.

export async function POST(req: Request) {
  const secret = process.env.CRON_SECRET;
  if (!secret) {
    if (process.env.NODE_ENV === "production") {
      return Response.json(
        { error: "CRON_SECRET is not configured" },
        { status: 503 },
      );
    }
    // Dev without a secret: allow, so the loop is testable locally.
  } else if (req.headers.get("X-Cron-Key") !== secret) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  let digests, customers;
  try {
    ({ digests, customers } = await getDigestAll());
  } catch {
    return Response.json(
      { error: "Could not fetch the digests. Is the API running?" },
      { status: 502 },
    );
  }

  if (digests.length === 0) {
    return Response.json({ ok: true, dry_run: true, customers: [] });
  }

  const results = await Promise.allSettled(digests.map((d) => sendDigest(d)));
  const sent: { customer: string; sent_to: string; dry_run: boolean }[] = [];
  const failed: string[] = [];
  results.forEach((result, i) => {
    const customer = customers[i];
    if (result.status === "fulfilled") {
      sent.push({ customer, ...result.value });
    } else {
      failed.push(customer);
    }
  });

  return Response.json({
    ok: failed.length === 0,
    sent_count: sent.length,
    sent,
    failed,
  });
}
