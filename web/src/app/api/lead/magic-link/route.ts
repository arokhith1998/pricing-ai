// POST /api/lead/magic-link
// Body: { email: string, next?: string }
//
// If we have a lead with this email in the database, generate a 24-hour signed
// link and email it. If we do not, behave identically (return ok: true) so
// the response cannot be used to enumerate which emails are in our database.
//
// This is the recovery path for visitors who already filled the lead form
// but lost the pk_lead cookie (new device, cleared cookies, expired).

import { isCompanyEmail } from "@/lib/auth";
import { leadExists } from "@/lib/store";
import { makeMagicToken, magicRedeemUrl } from "@/lib/magic";
import { sendMagicLink } from "@/lib/notify";
import { rateLimit } from "@/lib/ratelimit";

// Pin the origin the emailed link points at. Building it from req.url would
// let a Host-header-spoofed request mail out a link to an attacker-controlled
// domain carrying a valid token.
const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://www.pricekeel.com";

// Whitelist of routes we will redirect to after redeem. Mirrors proxy.ts.
const ALLOWED_NEXT = new Set([
  "/sample",
  "/diagnostic",
  "/guidance",
  "/competitor-watch",
]);

export async function POST(req: Request) {
  // Tighter than the lead form: each request can trigger an email send.
  const limited = rateLimit(req, "magic-link", { max: 3, windowMs: 5 * 60_000 });
  if (limited) return limited;

  let body: { email?: unknown; next?: unknown };
  try {
    body = (await req.json()) as typeof body;
  } catch {
    return Response.json({ error: "Bad request" }, { status: 400 });
  }

  const email = typeof body.email === "string" ? body.email.trim().toLowerCase() : "";
  if (!email) {
    return Response.json({ error: "Email required." }, { status: 400 });
  }
  // Same company-email gate the lead form uses: a personal address could not
  // have a lead row in the first place, so reject early with the same wording
  // the form shows.
  if (!isCompanyEmail(email)) {
    return Response.json(
      { error: "Please use your company email address (not a personal one)." },
      { status: 400 },
    );
  }

  const nextRaw = typeof body.next === "string" ? body.next : "";
  const next = ALLOWED_NEXT.has(nextRaw) ? nextRaw : undefined;

  // We deliberately do not surface whether the email was found to prevent
  // address enumeration; the user always sees the same {ok:true} response.
  //
  // The work is awaited (not fire-and-forget) because Vercel's serverless
  // runtime can terminate the function context the moment Response.json()
  // returns, which would silently drop the Resend send call. The cost is a
  // ~1-2s response time, which is fine for this UX.
  try {
    const found = await leadExists(email);
    if (found) {
      const token = await makeMagicToken(email);
      const link = magicRedeemUrl(SITE_URL, token, next);
      await sendMagicLink(email, link);
      console.log("[magic-link] sent to", email);
    } else {
      console.log("[magic-link] no lead found for", email, "(silent)");
    }
  } catch (err) {
    console.error("[magic-link route]", err instanceof Error ? err.message : err);
  }

  return Response.json({ ok: true });
}
