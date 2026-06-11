// Best-effort per-IP rate limiting for the public POST routes.
//
// In-memory sliding window. On Vercel serverless this is per-lambda-instance,
// so it is not a hard guarantee — a burst that fans out across instances can
// exceed the limit. That is fine: the goal is to blunt casual abuse (form
// spam, credential stuffing on /api/auth, magic-link email bombing), not to
// survive a determined DDoS.
//
// Usage in a route handler:
//
//   const limited = rateLimit(req, "lead", { max: 5, windowMs: 60_000 });
//   if (limited) return limited;

type Bucket = { stamps: number[] };

const buckets = new Map<string, Bucket>();

// Cap total tracked keys so a spoofed-IP flood cannot grow memory unbounded.
const MAX_KEYS = 5_000;

function clientIp(req: Request): string {
  // Vercel sets x-forwarded-for; the first hop is the client.
  const fwd = req.headers.get("x-forwarded-for");
  if (fwd) return fwd.split(",")[0].trim();
  return req.headers.get("x-real-ip") ?? "unknown";
}

export type RateLimitRule = { max: number; windowMs: number };

/** Returns a 429 Response when the caller is over the limit, else null. */
export function rateLimit(
  req: Request,
  scope: string,
  rule: RateLimitRule,
): Response | null {
  const now = Date.now();
  const key = `${scope}:${clientIp(req)}`;

  let bucket = buckets.get(key);
  if (!bucket) {
    if (buckets.size >= MAX_KEYS) buckets.clear(); // crude but bounded
    bucket = { stamps: [] };
    buckets.set(key, bucket);
  }

  bucket.stamps = bucket.stamps.filter((t) => now - t < rule.windowMs);
  if (bucket.stamps.length >= rule.max) {
    const retryAfterSec = Math.max(
      1,
      Math.ceil((bucket.stamps[0] + rule.windowMs - now) / 1000),
    );
    return Response.json(
      { error: "Too many requests. Please wait a moment and try again." },
      { status: 429, headers: { "Retry-After": String(retryAfterSec) } },
    );
  }

  bucket.stamps.push(now);
  return null;
}
