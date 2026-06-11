import type { NextConfig } from "next";

// Pragmatic CSP: locks down the dangerous primitives (plugin content, <base>
// rewrites, clickjacking via framing) without allow-listing scripts/styles,
// so Next.js inline runtime scripts and Vercel Analytics keep working. A
// full script-src policy needs nonce plumbing; revisit when there is a real
// app surface behind auth.
const CSP = "object-src 'none'; base-uri 'self'; frame-ancestors 'none'";

const SECURITY_HEADERS = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  // Redundant with frame-ancestors for modern browsers; kept for older ones.
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
  { key: "Content-Security-Policy", value: CSP },
];

const nextConfig: NextConfig = {
  // The blog routes read content/blog/*.md at request time; make sure those
  // files are traced into the serverless bundle on Vercel.
  outputFileTracingIncludes: {
    "/blog": ["./content/blog/**/*"],
    "/blog/[slug]": ["./content/blog/**/*"],
  },
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: SECURITY_HEADERS,
      },
    ];
  },
};

export default nextConfig;
