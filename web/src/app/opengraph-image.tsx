// Default 1200x630 Open Graph image for shared links (LinkedIn, Slack,
// iMessage, X). Generated at build time via the opengraph-image file
// convention; brand style mirrors /brand/cover (dark navy canvas, keel
// mark, teal accent).
import { ImageResponse } from "next/og";

export const alt =
  "Pricekeel: we stop AI companies from losing money on heavy users";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function Image() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: "64px 72px",
          backgroundColor: "#0a0f1a",
          backgroundImage:
            "radial-gradient(900px 700px at 100% 100%, rgba(45,212,191,0.16), rgba(45,212,191,0)), linear-gradient(135deg, #0a0f1a 0%, #0d1422 60%, #111a2b 100%)",
          color: "#e9f0f8",
          fontFamily: "sans-serif",
        }}
      >
        {/* Mark + wordmark */}
        <div style={{ display: "flex", alignItems: "center", gap: 24 }}>
          <svg width="88" height="88" viewBox="0 0 64 64">
            <line
              x1="10"
              y1="26"
              x2="54"
              y2="26"
              stroke="#e9f0f8"
              strokeWidth="3"
              strokeLinecap="round"
              opacity="0.88"
            />
            <path
              d="M 14 26 Q 34 60 50 26"
              fill="none"
              stroke="#2dd4bf"
              strokeWidth="5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          <div style={{ display: "flex", fontSize: 64, fontWeight: 800, letterSpacing: -1.5 }}>
            <span>Price</span>
            <span style={{ color: "#2dd4bf" }}>keel</span>
          </div>
        </div>

        {/* Headline */}
        <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              fontSize: 52,
              fontWeight: 700,
              lineHeight: 1.15,
              letterSpacing: -1,
            }}
          >
            <span>We stop AI companies from losing</span>
            <span style={{ display: "flex" }}>money on heavy users.</span>
          </div>
          <div style={{ display: "flex", fontSize: 26, color: "#8ea3bd" }}>
            For B2B and AI software companies moving from flat or per-seat to usage or outcome pricing.
          </div>
        </div>

        {/* Footer row: the site only. No revenue band on the card (F14). */}
        <div style={{ display: "flex", justifyContent: "flex-end", fontSize: 24 }}>
          <div style={{ display: "flex", fontWeight: 700, color: "#2dd4bf" }}>
            pricekeel.com
          </div>
        </div>
      </div>
    ),
    { ...size },
  );
}
