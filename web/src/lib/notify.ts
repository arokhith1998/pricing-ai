// Lead notification — fires off a "new lead" alert after a successful save.
// Strictly best-effort: any failure is logged and swallowed, never re-raised,
// so a flaky Resend / Slack endpoint never blocks the lead-form response.
//
// Two wire formats, picked by env:
//
//   RESEND_API_KEY      → POST https://api.resend.com/emails
//   LEAD_WEBHOOK_URL    → POST <url>  (Slack/Discord/Zapier compatible JSON)
//
// If neither is set, we log to stderr and move on — same as the dev fallback
// behavior `saveLead` had before this module existed.

import type { Lead } from "@/lib/store";

const FROM = "Pricekeel Leads <leads@pricekeel.com>";
const TO = process.env.LEAD_NOTIFY_TO || "adhithya@pricekeel.com";

function summary(lead: Lead): string {
  return [
    `${lead.name} (${lead.role_title}, ${lead.role_function})`,
    `${lead.company} · ${lead.revenue_range} · ${lead.pricing_model}`,
    `${lead.email}`,
    lead.utm_source ? `via ${lead.utm_source}/${lead.utm_medium || "?"}/${lead.utm_campaign || "?"}` : "",
  ].filter(Boolean).join("\n");
}

async function viaResend(lead: Lead, apiKey: string): Promise<void> {
  const res = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      from: FROM,
      to: TO,
      subject: `New lead: ${lead.company} (${lead.role_title})`,
      text: summary(lead),
    }),
  });
  if (!res.ok) {
    throw new Error(`resend ${res.status}: ${await res.text().catch(() => "")}`);
  }
}

async function viaWebhook(lead: Lead, url: string): Promise<void> {
  // Slack/Discord both accept { text } at the top level; Zapier accepts
  // arbitrary JSON. We send a structured payload + a plaintext fallback.
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      text: `*New Pricekeel lead* — ${lead.company} (${lead.role_title})\n${summary(lead)}`,
      lead,
    }),
  });
  if (!res.ok) {
    throw new Error(`webhook ${res.status}`);
  }
}

export async function notifyLeadCaptured(lead: Lead): Promise<void> {
  const resendKey = process.env.RESEND_API_KEY;
  const webhook = process.env.LEAD_WEBHOOK_URL;
  try {
    if (resendKey) {
      await viaResend(lead, resendKey);
    } else if (webhook) {
      await viaWebhook(lead, webhook);
    } else {
      // No notification channel configured — leave a structured stderr line
      // so `vercel logs` still surfaces the new lead in real time.
      console.log("[lead captured]", lead.company, lead.email);
    }
  } catch (err) {
    // Never let a notification failure surface to the user.
    console.error("[lead notify failed]", err instanceof Error ? err.message : err);
  }
}
