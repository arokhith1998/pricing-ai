// Raw HTML response: serves ONLY the LinkedIn cover canvas, no global
// Nav / Footer / fonts-from-layout. Used as the screencap target so the
// resulting PNG is the cover and nothing else.
//
// Visit http://localhost:3000/brand/cover/raw → take a screenshot of the
// element id="cover-canvas" at its native 1128 x 191. The page is also
// noindex'd via X-Robots-Tag.

export function GET() {
  // Keep the HTML inline — no React, no imports — so this is literally a
  // page with one element on it. Inter is loaded from Google Fonts since
  // we are not inside the root layout that ordinarily injects it.
  const html = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>Pricekeel brand cover (raw)</title>
<meta name="robots" content="noindex,nofollow" />
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link
  href="https://fonts.googleapis.com/css2?family=Inter:wght@500;600;700;800&display=swap"
  rel="stylesheet"
/>
<style>
  html, body { margin: 0; padding: 0; background: #000; }
  body {
    display: flex; align-items: center; justify-content: center;
    min-height: 100vh;
    font-family: Inter, ui-sans-serif, system-ui, sans-serif;
    color: #e9f0f8;
  }
  #cover-canvas {
    width: 1128px; height: 191px;
    background:
      radial-gradient(140% 220% at 100% 100%,
        rgba(45,212,191,0.18) 0%, rgba(45,212,191,0) 45%),
      linear-gradient(135deg, #0a0f1a 0%, #0d1422 60%, #111a2b 100%);
    position: relative; overflow: hidden;
  }
  .waterline {
    position: absolute; left: 0; right: 0; top: 62%; height: 1px;
    background: linear-gradient(to right,
      rgba(233,240,248,0) 0%,
      rgba(233,240,248,0.22) 18%,
      rgba(233,240,248,0.22) 82%,
      rgba(233,240,248,0) 100%);
  }
  .grid {
    position: absolute; inset: 0;
    display: grid;
    grid-template-columns: 260px 1fr 220px;
    align-items: center;
    padding: 0 36px; gap: 28px;
  }
  .markwrap { display: flex; align-items: center; gap: 14px; }
  .wordmark {
    font-weight: 800; font-size: 32px;
    letter-spacing: -0.6px; line-height: 1;
  }
  .wordmark .keel { color: #2dd4bf; }
  .tag {
    margin-top: 6px; font-size: 11px; font-weight: 500;
    color: #8ea3bd; letter-spacing: 0.04em;
  }
  .moat {
    font-weight: 700; font-size: 22px;
    line-height: 1.18; letter-spacing: -0.3px;
    color: #e9f0f8;
  }
  .moat .accent { color: #2dd4bf; }
  .sub {
    margin-top: 8px; font-size: 12px;
    color: #8ea3bd; letter-spacing: 0.01em;
  }
  .right { text-align: right; }
  .eyebrow {
    font-size: 11px; color: #8ea3bd;
    letter-spacing: 0.1em; text-transform: uppercase;
    font-weight: 600;
  }
  .url {
    margin-top: 4px; font-weight: 700; font-size: 18px;
    color: #e9f0f8; letter-spacing: -0.2px;
  }
</style>
</head>
<body>
  <div id="cover-canvas">
    <div class="waterline" aria-hidden="true"></div>
    <div class="grid">
      <div class="markwrap">
        <svg width="56" height="56" viewBox="0 0 64 64" aria-label="Pricekeel">
          <line x1="10" y1="26" x2="54" y2="26"
                stroke="#e9f0f8" stroke-width="3"
                stroke-linecap="round" opacity="0.88" />
          <path d="M 14 26 Q 34 60 50 26"
                fill="none" stroke="#2dd4bf"
                stroke-width="5"
                stroke-linecap="round" stroke-linejoin="round" />
        </svg>
        <div>
          <div class="wordmark">Price<span class="keel">keel</span></div>
          <div class="tag">Keep your pricing on an even keel.</div>
        </div>
      </div>
      <div style="padding-left:12px;">
        <div class="moat">
          Decisions logged with their math.<br />
          <span class="accent">Defensible to finance.</span>
        </div>
        <div class="sub">For VP Pricing teams at $10–100M ARR usage-based B2B SaaS.</div>
      </div>
      <div class="right">
        <div class="eyebrow">See it in product</div>
        <div class="url">pricekeel.com</div>
      </div>
    </div>
  </div>
</body>
</html>`;

  return new Response(html, {
    headers: {
      "Content-Type": "text/html; charset=utf-8",
      "X-Robots-Tag": "noindex, nofollow",
      "Cache-Control": "no-store",
    },
  });
}
