// /brand/cover — designed to render at exactly 1128 x 191 px so we can
// screencap a pixel-perfect LinkedIn company-page cover image. Open the
// page in a 1128x191 viewport, capture it, save as PNG, upload to LinkedIn.
//
// This page is intentionally OUTSIDE the global layout (no nav, no footer)
// so the capture is the cover and nothing else.

import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Brand cover · Pricekeel",
  // Don't index — this is an internal brand surface, not a marketing page.
  robots: { index: false, follow: false },
};

export default function CoverPage() {
  return (
    // Outer wrapper exists so the capture surface (the inner div) is exactly
    // 1128 x 191 even when the browser viewport is slightly different.
    <main className="flex min-h-screen items-center justify-center bg-black p-0">
      <div
        id="cover-canvas"
        style={{
          width: "1128px",
          height: "191px",
          background:
            // Two-stop dark navy with a faint teal aurora pulled to the
            // lower right — matches the site's .pk-horizon treatment.
            "radial-gradient(140% 220% at 100% 100%, rgba(45,212,191,0.18) 0%, rgba(45,212,191,0) 45%), linear-gradient(135deg, #0a0f1a 0%, #0d1422 60%, #111a2b 100%)",
          color: "#e9f0f8",
          fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif",
          position: "relative",
          overflow: "hidden",
        }}
      >
        {/* Quiet "waterline" running across the full width, ~62% of the
            height down — echoes the keel waterline; gives the type a
            visual hook to sit above. */}
        <div
          aria-hidden
          style={{
            position: "absolute",
            left: 0,
            right: 0,
            top: "62%",
            height: "1px",
            background:
              "linear-gradient(to right, rgba(233,240,248,0) 0%, rgba(233,240,248,0.22) 18%, rgba(233,240,248,0.22) 82%, rgba(233,240,248,0) 100%)",
          }}
        />

        {/* Three-column grid: mark | tagline | url */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "grid",
            gridTemplateColumns: "260px 1fr 220px",
            alignItems: "center",
            padding: "0 36px",
            gap: "28px",
          }}
        >
          {/* COL 1 — mark + wordmark, stacked */}
          <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
            <svg width="56" height="56" viewBox="0 0 64 64" aria-label="Pricekeel">
              <line
                x1="10" y1="26" x2="54" y2="26"
                stroke="#e9f0f8" strokeWidth="3"
                strokeLinecap="round" opacity="0.88"
              />
              <path
                d="M 14 26 Q 34 60 50 26"
                fill="none" stroke="#2dd4bf"
                strokeWidth="5"
                strokeLinecap="round" strokeLinejoin="round"
              />
            </svg>
            <div>
              <div
                style={{
                  fontWeight: 800,
                  fontSize: "32px",
                  letterSpacing: "-0.6px",
                  lineHeight: 1,
                }}
              >
                <span>Price</span>
                <span style={{ color: "#2dd4bf" }}>keel</span>
              </div>
              <div
                style={{
                  marginTop: "6px",
                  fontSize: "11px",
                  fontWeight: 500,
                  color: "#8ea3bd",
                  letterSpacing: "0.04em",
                }}
              >
                Keep your pricing on an even keel.
              </div>
            </div>
          </div>

          {/* COL 2 — moat statement */}
          <div style={{ textAlign: "left", paddingLeft: "12px" }}>
            <div
              style={{
                fontWeight: 700,
                fontSize: "22px",
                lineHeight: 1.18,
                letterSpacing: "-0.3px",
                color: "#e9f0f8",
              }}
            >
              Decisions logged with their math.
              <br />
              <span style={{ color: "#2dd4bf" }}>Defensible to finance.</span>
            </div>
            <div
              style={{
                marginTop: "8px",
                fontSize: "12px",
                color: "#8ea3bd",
                letterSpacing: "0.01em",
              }}
            >
              For VP Pricing teams at $10 to 100M ARR usage-based B2B SaaS.
            </div>
          </div>

          {/* COL 3 — quiet brand close */}
          <div style={{ textAlign: "right" }}>
            <div
              style={{
                fontSize: "11px",
                color: "#8ea3bd",
                letterSpacing: "0.1em",
                textTransform: "uppercase",
                fontWeight: 600,
              }}
            >
              See it in product
            </div>
            <div
              style={{
                marginTop: "4px",
                fontWeight: 700,
                fontSize: "18px",
                color: "#e9f0f8",
                letterSpacing: "-0.2px",
              }}
            >
              pricekeel.com
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
