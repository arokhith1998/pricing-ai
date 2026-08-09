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
import type { Digest } from "@/lib/api";
import { money, pct100 } from "@/lib/format";

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
      text: `*New Pricekeel lead.* ${lead.company} (${lead.role_title})\n${summary(lead)}`,
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
      // No notification channel configured. Leave a structured stderr line
      // so `vercel logs` still surfaces the new lead in real time.
      console.log("[lead captured]", lead.company, lead.email);
    }
  } catch (err) {
    // Never let a notification failure surface to the user.
    console.error("[lead notify failed]", err instanceof Error ? err.message : err);
  }
}

// ---------------------------------------------------------------------------
// Magic-link delivery. Tight transactional email, no marketing copy.
// Falls back to a stderr log when RESEND_API_KEY is unset so the founder can
// test the flow end-to-end before wiring Resend in Vercel.

const MAGIC_FROM = "Pricekeel <hello@pricekeel.com>";
// Reply-To lands on the real M365 mailbox so any human reply reaches us.
// Sending from hello@ (not yet a real mailbox) is fine because the recipient
// is told to click the link, not reply, and M365 trusts mail more when
// Reply-To resolves to a real inbox under the same org.
const MAGIC_REPLY_TO = process.env.LEAD_NOTIFY_TO || "adhithya@pricekeel.com";

export async function sendMagicLink(email: string, link: string): Promise<void> {
  const resendKey = process.env.RESEND_API_KEY;
  const subject = "Your Pricekeel access link";
  const text = [
    "Click here to open the Pricekeel sample read-out:",
    "",
    link,
    "",
    "This link is valid for 24 hours.",
    "",
    "Pricekeel",
  ].join("\n");

  // Multipart bodies (text + HTML) score better than text-only on M365 and
  // Gmail spam filters. The HTML stays minimal: a single branded paragraph,
  // a styled button, a fallback URL, and a TTL note. No images, no tracking
  // pixels, no marketing chrome (also helps deliverability).
  const html = `<!doctype html>
<html lang="en"><head><meta charset="utf-8"/><title>${escapeHtml(subject)}</title></head>
<body style="margin:0;padding:0;background:#f6f8fb;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;color:#0d1b2e;">
  <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background:#f6f8fb;padding:32px 16px;">
    <tr><td align="center">
      <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="520" style="max-width:520px;background:#ffffff;border:1px solid #dde3ec;border-radius:12px;">
        <tr><td style="padding:28px 32px 8px 32px;">
          <div style="font-size:20px;font-weight:800;letter-spacing:-0.01em;line-height:1;">
            <span style="color:#0d1b2e;">Price</span><span style="color:#0d9488;">keel</span>
          </div>
          <div style="margin-top:4px;color:#6b7891;font-size:11px;">Keep your pricing on an even keel.</div>
        </td></tr>
        <tr><td style="padding:8px 32px 0 32px;">
          <h1 style="margin:16px 0 6px 0;font-size:18px;font-weight:700;color:#0d1b2e;">Your access link</h1>
          <p style="margin:0;font-size:14px;line-height:1.55;color:#1f2a3d;">
            Click the button below to open the Pricekeel sample read-out. This
            link is valid for 24 hours.
          </p>
        </td></tr>
        <tr><td align="center" style="padding:20px 32px 8px 32px;">
          <a href="${escapeAttr(link)}" style="display:inline-block;background:#0d9488;color:#ffffff;font-size:14px;font-weight:600;text-decoration:none;padding:12px 22px;border-radius:8px;">Open Pricekeel</a>
        </td></tr>
        <tr><td style="padding:8px 32px 24px 32px;">
          <p style="margin:12px 0 0 0;font-size:12px;line-height:1.5;color:#6b7891;">
            Button not working? Paste this URL into your browser:<br/>
            <a href="${escapeAttr(link)}" style="color:#0b7d72;word-break:break-all;">${escapeHtml(link)}</a>
          </p>
          <p style="margin:18px 0 0 0;font-size:11px;color:#6b7891;border-top:1px solid #eef2f7;padding-top:14px;">
            You are receiving this because someone using your email asked for an
            access link at pricekeel.com. If that wasn't you, you can ignore
            this message; nothing happens until the link is clicked.
          </p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body></html>`;

  if (!resendKey) {
    // Dev / pre-Resend mode: log to stderr so the founder can copy the URL
    // out of `vercel logs` (or local terminal) and test the redeem path.
    console.log("[magic link]", email, link);
    return;
  }
  try {
    const res = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${resendKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        from: MAGIC_FROM,
        reply_to: MAGIC_REPLY_TO,
        to: email,
        subject,
        text,
        html,
      }),
    });
    if (!res.ok) {
      throw new Error(`resend ${res.status}: ${await res.text().catch(() => "")}`);
    }
  } catch (err) {
    // Same posture as notifyLeadCaptured: log and swallow. The API caller
    // always sees a generic "if you submitted before, check your inbox"
    // response, which makes this safe to fail silently.
    console.error("[magic link send failed]", err instanceof Error ? err.message : err);
  }
}

// ---------------------------------------------------------------------------
// Weekly governance digest. Same minimal-HTML posture as the magic link:
// one branded card, the headline, the lines, a stats strip. No images, no
// tracking. Unlike the lead/magic-link senders this one THROWS on a Resend
// failure: the caller is a cron route that wants to know the send failed,
// not a user-facing form that must never see the error.

const DIGEST_FROM = "Pricekeel Digest <digest@pricekeel.com>";
const DIGEST_REPLY_TO = "adhithya@pricekeel.com";

export async function sendDigest(
  digest: Digest,
): Promise<{ sent_to: string; dry_run: boolean }> {
  const to =
    process.env.DIGEST_RECIPIENT ||
    process.env.LEAD_NOTIFY_TO ||
    "adhithya@pricekeel.com";
  const subject = `Pricekeel digest · ${digest.customer} · last ${digest.window_days} days`;

  const stats = digest.stats;
  // Demo-book disclosure: when the backend flags book_source === "demo" (see
  // CONTRACT B), the realization/leakage figures below come from the sample
  // dataset, not the recipient's own Salesforce book. Say so plainly, up
  // front, in both the text and HTML bodies. Never silently present demo
  // numbers as the customer's own.
  const isDemoBook = digest.book_source === "demo";
  const demoDisclosure =
    "Note: the realization and leakage figures in this digest are from Pricekeel's demonstration book, not your own Salesforce data.";

  // realization_pct / excess can be null when no book is loaded; skip those
  // rows rather than rendering NaN into a customer-facing email.
  const statRows: [string, string][] = [
    ["Exceptions priced", String(stats.exceptions_total)],
    ["Below the floor", String(stats.exceptions_below_floor)],
    ["Copilot decisions", String(stats.copilot_decisions)],
    ...(stats.realization_pct != null
      ? ([["Price realization", pct100(stats.realization_pct)]] as [string, string][])
      : []),
    ...(stats.excess_vs_segment_reference != null
      ? ([["Excess vs segment reference", money(stats.excess_vs_segment_reference)]] as [
          string,
          string,
        ][])
      : []),
  ];

  const text = [
    digest.headline,
    "",
    ...(isDemoBook ? [demoDisclosure, ""] : []),
    ...digest.lines.map((l) => `- ${l}`),
    "",
    ...statRows.map(([k, v]) => `${k}: ${v}`),
    "",
    `Pricekeel · ${digest.customer} · generated ${digest.generated_at}`,
  ].join("\n");

  const html = `<!doctype html>
<html lang="en"><head><meta charset="utf-8"/><title>${escapeHtml(subject)}</title></head>
<body style="margin:0;padding:0;background:#f6f8fb;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;color:#0d1b2e;">
  <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background:#f6f8fb;padding:32px 16px;">
    <tr><td align="center">
      <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="560" style="max-width:560px;background:#ffffff;border:1px solid #dde3ec;border-radius:12px;">
        <tr><td style="padding:28px 32px 8px 32px;">
          <div style="font-size:20px;font-weight:800;letter-spacing:-0.01em;line-height:1;">
            <span style="color:#0d1b2e;">Price</span><span style="color:#0d9488;">keel</span>
          </div>
          <div style="margin-top:4px;color:#6b7891;font-size:11px;">Weekly digest · ${escapeHtml(digest.customer)} · last ${digest.window_days} days</div>
        </td></tr>
        <tr><td style="padding:8px 32px 0 32px;">
          <h1 style="margin:16px 0 6px 0;font-size:18px;font-weight:700;color:#0d1b2e;">${escapeHtml(digest.headline)}</h1>
        </td></tr>
        ${
          isDemoBook
            ? `<tr><td style="padding:4px 32px 0 32px;">
          <p style="margin:0 0 4px 0;padding:10px 12px;background:#FDF3E1;border:1px solid #E8A33D;border-radius:8px;font-size:12px;line-height:1.5;color:#0B1727;">
            <strong>Demo data.</strong> ${escapeHtml(demoDisclosure)}
          </p>
        </td></tr>`
            : ""
        }
        <tr><td style="padding:4px 32px 0 32px;">
          <ul style="margin:8px 0 0 0;padding:0 0 0 18px;font-size:14px;line-height:1.6;color:#1f2a3d;">
            ${digest.lines.map((l) => `<li style="margin:0 0 6px 0;">${escapeHtml(l)}</li>`).join("\n            ")}
          </ul>
        </td></tr>
        <tr><td style="padding:16px 32px 24px 32px;">
          <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="border-top:1px solid #eef2f7;">
            ${statRows
              .map(
                ([k, v]) => `<tr>
              <td style="padding:7px 0 0 0;font-size:12px;color:#6b7891;">${escapeHtml(k)}</td>
              <td align="right" style="padding:7px 0 0 0;font-size:12px;font-weight:600;color:#0d1b2e;">${escapeHtml(v)}</td>
            </tr>`,
              )
              .join("\n            ")}
          </table>
          <p style="margin:18px 0 0 0;font-size:11px;color:#6b7891;border-top:1px solid #eef2f7;padding-top:14px;">
            Every figure above traces back to an entry in your decision log.
            Generated ${escapeHtml(digest.generated_at)}. Reply to this email to reach us.
          </p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body></html>`;

  const resendKey = process.env.RESEND_API_KEY;
  if (!resendKey) {
    // Dev / pre-Resend mode: log the rendered text so the founder can read
    // the digest out of the terminal (or vercel logs) end to end.
    console.log("[digest dry run]", `to: ${to}`, `subject: ${subject}\n${text}`);
    return { sent_to: to, dry_run: true };
  }

  const res = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${resendKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      from: DIGEST_FROM,
      reply_to: DIGEST_REPLY_TO,
      to,
      subject,
      text,
      html,
    }),
  });
  if (!res.ok) {
    throw new Error(`resend ${res.status}: ${await res.text().catch(() => "")}`);
  }
  return { sent_to: to, dry_run: false };
}

// Minimal HTML escaping for the values we interpolate into the template.
// The link is built server-side from our own HMAC + base64url, so it can
// only contain URL-safe chars; the only realistic risk is a future change
// adding user-supplied text. This keeps us safe by default.
function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}
function escapeAttr(s: string): string {
  return escapeHtml(s).replace(/"/g, "&quot;");
}
