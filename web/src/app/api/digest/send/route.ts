import { getDigest } from "@/lib/api";
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
// The digest itself comes from the FastAPI GET /digest (server-side via
// apiFetch, which adds X-Pricekeel-Key and the timeout) and goes out through
// sendDigest in notify.ts. With RESEND_API_KEY unset, sendDigest logs the
// rendered text and reports a dry run.

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

  let digest;
  try {
    digest = await getDigest();
  } catch {
    return Response.json(
      { error: "Could not fetch the digest. Is the API running?" },
      { status: 502 },
    );
  }

  try {
    const { sent_to, dry_run } = await sendDigest(digest);
    if (dry_run) {
      return Response.json({ ok: true, dry_run: true });
    }
    return Response.json({ ok: true, sent_to, headline: digest.headline });
  } catch {
    return Response.json(
      { error: "Digest rendered but the email send failed." },
      { status: 502 },
    );
  }
}
