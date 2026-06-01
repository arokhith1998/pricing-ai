// POST /api/lead/magic-link
// Body: { email: string, next?: string }
//
// If we have a lead with this email in Supabase, generate a 24-hour signed
// link and email it. If we do not, behave identically (return ok: true) so
// the response cannot be used to enumerate which emails are in our database.
//
// This is the recovery path for visitors who already filled the lead form
// but lost the pk_lead cookie (new device, cleared cookies, expired).

import { isCompanyEmail } from "@/lib/auth";
import { leadExists } from "@/lib/store";
import { makeMagicToken, magicRedeemUrl } from "@/lib/magic";
import { sendMagicLink } from "@/lib/notify";

// Whitelist of routes we will redirect to after redeem. Mirrors proxy.ts.
const ALLOWED_NEXT = new Set([
  "/sample",
  "/diagnostic",
  "/guidance",
  "/competitor-watch",
]);

export async function POST(req: Request) {
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
      const origin = new URL(req.url).origin;
      const link = magicRedeemUrl(origin, token, next);
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
