// Persistence for captured leads and access codes. Uses Neon/Postgres when
// DATABASE_URL is set (production); otherwise a dev fallback (in-memory leads,
// env-list access codes) so local build/verify is not blocked. See
// neon/schema.sql for the schema.
import { neon, type NeonQueryFunction } from "@neondatabase/serverless";
import { notifyLeadCaptured } from "@/lib/notify";

export type Lead = {
  name: string;
  company: string;
  email: string;
  role_title: string;
  role_function: string;
  // Phase: launch-readiness — qualifying + attribution fields.
  revenue_range: string;
  pricing_model: string;
  utm_source: string;
  utm_medium: string;
  utm_campaign: string;
  consent: boolean;
};

const DATABASE_URL = process.env.DATABASE_URL;

let _sql: NeonQueryFunction<false, false> | null = null;
function db(): NeonQueryFunction<false, false> | null {
  if (!DATABASE_URL) {
    // Fail-fast in production: without a database, leads would silently land
    // in lambda memory (lost on every cold start) while the visitor sees a
    // success message. Local dev keeps the in-memory fallback.
    if (process.env.VERCEL_ENV === "production") {
      throw new Error(
        "DATABASE_URL is not set. Refusing the in-memory lead store in production. Set the Neon pooled connection string in the Vercel environment.",
      );
    }
    return null;
  }
  // neon() is the HTTP (one-shot) driver — no connection pool to exhaust
  // across serverless invocations, which is exactly our access pattern here.
  if (!_sql) _sql = neon(DATABASE_URL);
  return _sql;
}

export function storeBackend(): "neon" | "memory" {
  return db() ? "neon" : "memory";
}

// Dev fallback store (process memory; lost on restart — fine for local).
const memLeads: Lead[] = [];

export async function saveLead(lead: Lead): Promise<void> {
  const sql = db();
  let dbError: unknown = null;
  if (!sql) {
    memLeads.push(lead);
  } else {
    try {
      await sql`
        insert into leads
          (name, company, email, role_title, role_function,
           revenue_range, pricing_model, utm_source, utm_medium, utm_campaign,
           consent)
        values
          (${lead.name}, ${lead.company}, ${lead.email}, ${lead.role_title},
           ${lead.role_function}, ${lead.revenue_range}, ${lead.pricing_model},
           ${lead.utm_source}, ${lead.utm_medium}, ${lead.utm_campaign},
           ${lead.consent})
      `;
    } catch (err) {
      dbError = err;
    }
  }
  // Best-effort alert (Resend email or Slack/Zapier webhook, set by env). It
  // is fired even when the DB write failed, so a database outage degrades to
  // "the lead still lands in your inbox" instead of a lead lost entirely.
  // notifyLeadCaptured never throws (it logs and swallows), so it cannot mask
  // the DB error below.
  await notifyLeadCaptured(lead);
  // Surface the DB failure to the caller only after the alert has gone out.
  // The visitor still sees the retry message and the cookie is not set, but
  // you have the lead in your inbox to recover by hand.
  if (dbError) {
    throw new Error(dbError instanceof Error ? dbError.message : String(dbError));
  }
}

/** Best-effort lookup. Returns true if we have ever captured this email.
 *  Used by the magic-link recovery flow so returning leads do not have to
 *  refill the form on a new device or after their cookie expired. */
export async function leadExists(email: string): Promise<boolean> {
  const e = email.trim().toLowerCase();
  if (!e) return false;
  const sql = db();
  if (!sql) return memLeads.some((l) => l.email.trim().toLowerCase() === e);
  // Escape LIKE wildcards so an input like "%@corp.com" matches literally
  // instead of acting as a pattern. The value is bound as a parameter, so this
  // is purely about ILIKE's wildcard semantics, not injection.
  const pattern = e.replace(/[\\%_]/g, "\\$&");
  try {
    const rows = await sql`
      select email from leads where email ilike ${pattern} limit 1
    `;
    return rows.length > 0;
  } catch (err) {
    console.error("[leadExists] neon error:", err instanceof Error ? err.message : err);
    return false;
  }
}

export async function isValidAccessCode(code: string): Promise<boolean> {
  const sql = db();
  if (!sql) {
    // Dev: a comma-separated PRICEKEEL_ACCESS_CODES env list.
    const list = (process.env.PRICEKEEL_ACCESS_CODES ?? "")
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    return list.includes(code);
  }
  try {
    const rows = await sql`
      select code, expires_at, revoked, used_at
      from access_codes where code = ${code} limit 1
    `;
    const data = rows[0];
    if (!data || data.revoked) return false;
    if (data.expires_at && new Date(data.expires_at as string) < new Date()) {
      return false;
    }
    // Record first use (best-effort; ignore errors).
    if (!data.used_at) {
      try {
        await sql`
          update access_codes set used_at = ${new Date().toISOString()}
          where code = ${code}
        `;
      } catch {
        /* first-use stamp is best-effort */
      }
    }
    return true;
  } catch (err) {
    // Fail closed: a DB error denies access rather than granting it.
    console.error("[isValidAccessCode] neon error:", err instanceof Error ? err.message : err);
    return false;
  }
}
