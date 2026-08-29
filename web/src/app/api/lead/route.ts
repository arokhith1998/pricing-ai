import { cookies } from "next/headers";
import {
  LEAD_COOKIE,
  isCompanyEmail,
  leadCookieOptions,
  makeLeadCookieValue,
} from "@/lib/auth";
import { saveLead } from "@/lib/store";
import { rateLimit } from "@/lib/ratelimit";

// POST a lead -> store it -> set pk_lead, which unlocks the full sample.
export async function POST(req: Request) {
  const limited = rateLimit(req, "lead", { max: 5, windowMs: 60_000 });
  if (limited) return limited;

  let body: Record<string, unknown>;
  try {
    body = await req.json();
  } catch {
    return Response.json({ error: "Bad request" }, { status: 400 });
  }

  const str = (v: unknown) => (typeof v === "string" ? v.trim() : "");

  // Honeypot: real visitors never see or fill this field. Bots that
  // autofill every input do. Accept and silently drop so the bot cannot
  // tell the submission went nowhere: this response is byte-for-byte the
  // same 200 {ok:true} a real save returns below, on the same status code,
  // with no extra work done first, so there is no body or gross-timing
  // signal to key off. Do not add a distinguishing field or delay here.
  // The client (LeadForm) does not trust this response as proof of an
  // unlock either; it watches whether the follow-up navigation actually
  // leaves the gated page, since that is the only place a real signal
  // exists (the lead cookie set below, which this branch skips).
  if (str(body.website)) {
    return Response.json({ ok: true });
  }

  const name = str(body.name);
  const company = str(body.company);
  const email = str(body.email);
  const role_title = str(body.role_title);
  const role_function = str(body.role_function);
  const revenue_range = str(body.revenue_range);
  const pricing_model = str(body.pricing_model);
  // UTM is optional — only stored if it came in on the URL.
  const utmRaw = (body.utm && typeof body.utm === "object" ? body.utm : {}) as Record<string, unknown>;
  const utm: Record<string, string> = {};
  for (const k of ["utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content"]) {
    const v = str(utmRaw[k]);
    if (v) utm[k] = v;
  }

  if (!name || !company || !email || !role_title || !role_function ||
      !revenue_range || !pricing_model) {
    return Response.json({ error: "Please fill in every field." }, { status: 400 });
  }
  if (!isCompanyEmail(email)) {
    return Response.json(
      { error: "Please use your company email address (not a personal one)." },
      { status: 400 },
    );
  }
  if (body.consent !== true) {
    return Response.json(
      { error: "Please agree to the Privacy Policy to continue." },
      { status: 400 },
    );
  }

  try {
    await saveLead({
      name, company, email, role_title, role_function,
      revenue_range, pricing_model,
      utm_source: utm.utm_source || "",
      utm_medium: utm.utm_medium || "",
      utm_campaign: utm.utm_campaign || "",
      consent: true,
    });
  } catch {
    return Response.json({ error: "Could not save right now. Try again." }, { status: 500 });
  }

  (await cookies()).set(LEAD_COOKIE, await makeLeadCookieValue(), leadCookieOptions());
  return Response.json({ ok: true });
}
