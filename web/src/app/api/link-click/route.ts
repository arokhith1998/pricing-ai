import { saveLinkClick } from "@/lib/store";
import { rateLimit } from "@/lib/ratelimit";

// Logs a landing hit for a `?ref=` token appended to a cold-outreach link
// (e.g. pricekeel.com/?ref=temporal-interview), so a click can be attributed
// to the company/campaign it came from without any per-person identifier.
// Fired by LinkClickCapture on the client, gated by
// NEXT_PUBLIC_LINK_TRACKING_ENABLED. See neon/schema.sql for the disclosure
// note on link_clicks.

// Matches the token format we ask the founder to use in outbound links:
// short, URL-safe, no spaces or free text (so nothing a visitor could paste
// into the query string themselves ends up stored as an open text field).
const SAFE_TOKEN = /^[a-zA-Z0-9_-]{1,64}$/;

export async function POST(req: Request) {
  const limited = rateLimit(req, "link-click", { max: 30, windowMs: 60_000 });
  if (limited) return limited;

  let body: Record<string, unknown>;
  try {
    body = await req.json();
  } catch {
    return Response.json({ error: "Bad request" }, { status: 400 });
  }

  const str = (v: unknown) => (typeof v === "string" ? v.trim() : "");

  const ref = str(body.ref);
  if (!ref || !SAFE_TOKEN.test(ref)) {
    // Malformed or missing ref is not worth surfacing as an error to a page
    // load; just no-op so the visitor never sees this.
    return Response.json({ ok: true });
  }

  const landing_path = str(body.landing_path).slice(0, 200) || "/";
  const utmRaw = (body.utm && typeof body.utm === "object" ? body.utm : {}) as Record<
    string,
    unknown
  >;
  const utm_source = str(utmRaw.utm_source).slice(0, 100);
  const utm_medium = str(utmRaw.utm_medium).slice(0, 100);
  const utm_campaign = str(utmRaw.utm_campaign).slice(0, 100);

  try {
    await saveLinkClick({ ref, utm_source, utm_medium, utm_campaign, landing_path });
  } catch (err) {
    // Best-effort logging: never let a DB hiccup surface to the visitor.
    console.error("[link-click] save failed:", err instanceof Error ? err.message : err);
  }

  return Response.json({ ok: true });
}
