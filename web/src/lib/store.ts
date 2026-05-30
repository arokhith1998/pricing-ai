// Persistence for captured leads and access codes. Uses Supabase/Postgres when
// SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY are set (production); otherwise a dev
// fallback (in-memory leads, env-list access codes) so local build/verify is
// not blocked. See docs/design/buyer-funnel.md for the schema.
import { createClient, type SupabaseClient } from "@supabase/supabase-js";
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

const URL = process.env.SUPABASE_URL;
const KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;

let _client: SupabaseClient | null = null;
function client(): SupabaseClient | null {
  if (!URL || !KEY) return null;
  if (!_client) _client = createClient(URL, KEY, { auth: { persistSession: false } });
  return _client;
}

export function storeBackend(): "supabase" | "memory" {
  return client() ? "supabase" : "memory";
}

// Dev fallback store (process memory; lost on restart — fine for local).
const memLeads: Lead[] = [];

export async function saveLead(lead: Lead): Promise<void> {
  const c = client();
  if (!c) {
    memLeads.push(lead);
  } else {
    const { error } = await c.from("leads").insert(lead);
    if (error) throw new Error(error.message);
  }
  // Best-effort alert (Resend email or Slack/Zapier webhook, set by env).
  // Failure here never blocks the lead capture.
  await notifyLeadCaptured(lead);
}

export async function isValidAccessCode(code: string): Promise<boolean> {
  const c = client();
  if (!c) {
    // Dev: a comma-separated PRICEKEEL_ACCESS_CODES env list.
    const list = (process.env.PRICEKEEL_ACCESS_CODES ?? "")
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    return list.includes(code);
  }
  const { data, error } = await c
    .from("access_codes")
    .select("code, expires_at, revoked, used_at")
    .eq("code", code)
    .maybeSingle();
  if (error || !data || data.revoked) return false;
  if (data.expires_at && new Date(data.expires_at) < new Date()) return false;
  // Record first use (best-effort; ignore errors).
  if (!data.used_at) {
    await c.from("access_codes").update({ used_at: new Date().toISOString() }).eq("code", code);
  }
  return true;
}
