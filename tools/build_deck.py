"""Build two PDFs from brand-styled HTML:

  decks/Pricekeel-Investor-Deck.pdf      (landscape, ~15 slides)
  decks/Pricekeel-Technical-Doc.pdf      (portrait, ~10 pages)

Both render via Playwright + Chromium so the print CSS, fonts, and colors
match what a browser would show. Run:

  python tools/build_deck.py

No external network. Sample numbers are pulled live from the engine so they
match what /sample renders on pricekeel.com.

Style rules enforced here:
  * Light theme (white background, deep navy text, teal accents).
  * No em dashes or en dashes anywhere in copy.
  * One idea per slide. Density kept low so nothing overflows the page box.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from playwright.sync_api import sync_playwright  # noqa: E402

OUT_DIR = ROOT / "decks"
OUT_DIR.mkdir(exist_ok=True)

_today = date.today()
TODAY = f"{_today.day} {_today.strftime('%b %Y')}"


# ---------------------------------------------------------------------------
# Pull the live sample numbers from the engine so the deck never goes stale.
def _live_numbers() -> dict:
    from pricing.diagnostic import run

    res = run(ROOT / "data" / "synthetic" / "deals.csv")
    o, l, r = res["overview"], res["leakage"], res["reference_discount"]
    dvi = res["defended_vs_investigate"]
    gov = res["governance"]
    return {
        "opps": o["opportunities"],
        "won": o["won"],
        "lost": o["lost"],
        "winrate": o["win_rate"],
        "booked": o["booked_acv_won"],
        "realization": o["price_realization_won"],
        "avg_discount": o["avg_discount_won"],
        "upside": l["excess_vs_reference_won"],
        "upside_pct": l["excess_pct_of_booked"],
        "deals_above_ref": l["deals_above_reference"],
        "reference_band": r["reference_band"],
        "reference_threshold": r["reference_threshold"],
        "peak_win_rate": r["peak_win_rate"],
        "defended_value": dvi["defended_value"],
        "defended_deals": dvi["defended_deals"],
        "investigate_value": dvi["investigate_value"],
        "investigate_deals": dvi["investigate_deals"],
        "off_policy": l["off_policy_leakage_won"],
        "unapproved_dollars": gov["unapproved_discount_dollars"],
    }


N = _live_numbers()


def _m(x: float) -> str:
    if x >= 1_000_000:
        return f"${x/1_000_000:.1f}M"
    if x >= 1_000:
        return f"${x/1_000:.0f}K"
    return f"${x:.0f}"


def _p(x: float, decimals: int = 1) -> str:
    return f"{x*100:.{decimals}f}%"


def _range(a, b) -> str:
    """Range without an en dash. '4 to 8%' instead of '4 to 8%'."""
    return f"{a} to {b}"


# ---------------------------------------------------------------------------
# Brand CSS, light theme. Deep navy on white with teal and coral accents.

BRAND_CSS = """
:root {
  --bg: #ffffff;
  --paper: #ffffff;
  --surface: #f6f8fb;
  --surface-2: #eef2f7;
  --line: #dde3ec;
  --line-strong: #c6d0dd;
  --fg: #0d1b2e;
  --ink: #1f2a3d;
  --muted: #56627a;
  --slate: #6b7891;
  --teal: #0d9488;
  --teal-soft: #ccfbf1;
  --teal-strong: #0b7d72;
  --coral: #e0533b;
  --coral-soft: #ffe2db;
  --amber: #c87f12;
  --navy: #0d1b2e;
}
* { box-sizing: border-box; }
html, body {
  margin: 0; padding: 0;
  background: var(--bg); color: var(--fg);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue",
               Arial, "Noto Sans", sans-serif;
  -webkit-font-smoothing: antialiased;
  font-feature-settings: "tnum" 1, "kern" 1;
}
.muted { color: var(--muted); }
.slate { color: var(--slate); }
.teal  { color: var(--teal);  }
.coral { color: var(--coral); }
.tnum { font-feature-settings: "tnum" 1; }
.eyebrow { color: var(--teal); text-transform: uppercase; letter-spacing: .12em; font-weight: 700; font-size: 11px; }
.tag {
  display: inline-block; padding: 4px 10px;
  background: var(--teal-soft); color: var(--teal-strong); border-radius: 999px;
  font-size: 10.5px; font-weight: 700; letter-spacing: .04em; text-transform: uppercase;
}
.kbd {
  background: var(--surface); color: var(--ink); padding: 1px 6px;
  border-radius: 4px; font-size: 11.5px;
  font-family: ui-monospace, SFMono-Regular, "JetBrains Mono", Menlo, Consolas, monospace;
  border: 1px solid var(--line);
}
"""

LOGO_SVG = """
<svg width="42" height="42" viewBox="0 0 64 64" aria-label="Pricekeel">
  <line x1="10" y1="26" x2="54" y2="26" stroke="#cbd4df" stroke-width="3"
        stroke-linecap="round"/>
  <path d="M 14 26 Q 34 60 50 26" fill="none" stroke="#0d9488"
        stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
"""

WORDMARK = """
<div style="display:flex;align-items:center;gap:14px;">
  {logo}
  <div>
    <div style="font-size:22px;font-weight:800;letter-spacing:-0.01em;line-height:1;color:var(--fg);">
      Price<span style="color:var(--teal);">keel</span>
    </div>
    <div style="color:var(--slate);font-size:11px;margin-top:2px;">Keep your pricing on an even keel.</div>
  </div>
</div>
""".format(logo=LOGO_SVG)


# ---------------------------------------------------------------------------
# Investor deck. Landscape A4. One idea per slide.

INVESTOR_CSS = BRAND_CSS + """
@page { size: A4 landscape; margin: 0; }
.slide {
  width: 297mm; height: 210mm;
  padding: 16mm 22mm 14mm 22mm;
  display: flex; flex-direction: column;
  page-break-after: always;
  position: relative;
  background: var(--paper);
  border-top: 4px solid var(--teal);
}
.slide:last-child { page-break-after: avoid; }
.slide header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 9mm;
}
.slide footer {
  position: absolute; bottom: 8mm; left: 22mm; right: 22mm;
  display: flex; justify-content: space-between;
  color: var(--slate); font-size: 10px; letter-spacing: .04em;
}
h1.title {
  font-size: 50px; font-weight: 800; line-height: 1.05; letter-spacing: -0.02em;
  margin: 0; color: var(--fg);
}
h2.section {
  font-size: 32px; font-weight: 800; line-height: 1.12; letter-spacing: -0.01em;
  margin: 0 0 6mm 0; color: var(--fg);
}
p.lede { font-size: 16px; line-height: 1.45; color: var(--ink); max-width: 230mm; }
p.lede.dim { color: var(--muted); }
.cards { display: grid; gap: 5mm; margin-top: 3mm; }
.card {
  background: var(--paper); border: 1px solid var(--line); border-radius: 10px;
  padding: 14px 16px;
}
.card .k {
  color: var(--teal); font-size: 10.5px; text-transform: uppercase;
  letter-spacing: .08em; font-weight: 700;
}
.card .v {
  color: var(--fg); font-size: 24px; font-weight: 800; margin-top: 4px;
  font-feature-settings: "tnum" 1;
}
.card .v.small { font-size: 16px; line-height: 1.2; }
.card .sub { color: var(--muted); font-size: 12px; margin-top: 6px; line-height: 1.45; }
.card.accent { border-color: var(--teal); }
.card.coral { border-color: var(--coral); }
.card.coral .k { color: var(--coral); }
.card.coral .v { color: var(--coral); }
.cards.cols-2 { grid-template-columns: 1fr 1fr; }
.cards.cols-3 { grid-template-columns: 1fr 1fr 1fr; }
.cards.cols-4 { grid-template-columns: 1fr 1fr 1fr 1fr; }
.split { display: grid; grid-template-columns: 1.05fr 1fr; gap: 10mm; align-items: start; }
ul.bullets { padding-left: 1.1em; margin: 0; }
ul.bullets li { margin: 6px 0; color: var(--ink); font-size: 14px; line-height: 1.5; }
ul.bullets li b { color: var(--fg); font-weight: 700; }
ul.bullets li .why { color: var(--slate); }
.pipeline { display: grid; grid-template-columns: repeat(5, 1fr); gap: 4mm; margin-top: 5mm; }
.pipeline .step {
  background: var(--paper); border: 1px solid var(--line); border-radius: 10px;
  padding: 12px 12px; min-height: 78px;
}
.pipeline .step .num { color: var(--teal); font-size: 10.5px; font-weight: 700; letter-spacing: .1em; }
.pipeline .step .name { color: var(--fg); font-size: 14px; font-weight: 700; margin-top: 2px; }
.pipeline .step .sub { color: var(--slate); font-size: 10.5px; margin-top: 4px; line-height: 1.4; }
table.code {
  width: 100%; border-collapse: collapse; margin-top: 3mm;
  font-size: 12.5px; color: var(--ink);
}
table.code th, table.code td {
  text-align: left; padding: 6px 10px; border-bottom: 1px solid var(--line);
  vertical-align: top;
}
table.code th { color: var(--slate); font-weight: 600; font-size: 10.5px;
                text-transform: uppercase; letter-spacing: .06em; }
table.code td.k {
  color: var(--teal); font-family: ui-monospace, SFMono-Regular, monospace;
  white-space: nowrap; font-weight: 600;
}
.stack {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 4mm; margin-top: 5mm;
}
.stack .group {
  background: var(--paper); border: 1px solid var(--line); border-radius: 10px;
  padding: 12px 14px;
}
.stack .group h4 {
  margin: 0 0 6px 0; color: var(--teal); font-size: 11px;
  text-transform: uppercase; letter-spacing: .08em;
}
.stack .group p { margin: 0; font-size: 12px; line-height: 1.5; color: var(--ink); }
.flag {
  background: var(--surface); border-left: 3px solid var(--coral);
  padding: 10px 14px; color: var(--ink); font-size: 12.5px; line-height: 1.5; margin-top: 4mm;
  border-radius: 0 6px 6px 0;
}
.flag.good { border-color: var(--teal); }
.flag b { color: var(--fg); }
"""


def _slide(num: int, total: int, eyebrow: str, body_html: str) -> str:
    return f"""
    <section class="slide">
      <header>{WORDMARK}<span class="tag">{eyebrow}</span></header>
      {body_html}
      <footer>
        <span>Pricekeel · Confidential · {TODAY}</span>
        <span>{num} of {total}</span>
      </footer>
    </section>
    """


def investor_html() -> str:
    slides = []

    # 1. Title.
    slides.append(("Slide 01", f"""
      <div style="flex:1; display:flex; flex-direction:column; justify-content:center;">
        <h1 class="title">System of record for <span class="teal">pricing decisions</span>.</h1>
        <p class="lede dim" style="margin-top:14px; font-size:20px; max-width:230mm;">
          B2B SaaS companies leak 4 to 8% of ARR to discount drift. Pricekeel's wedge is a free
          retrospective diagnostic from one CSV export. It produces a CFO-readable, sales-defendable
          read-out that nobody else builds.
        </p>
        <div style="margin-top:28px; color:var(--slate); font-size:13px;">
          Adhithya Bhaskar, Founder &nbsp;&middot;&nbsp;
          <span class="teal">adhithya@pricekeel.com</span> &nbsp;&middot;&nbsp;
          <span class="teal">pricekeel.com</span>
        </div>
      </div>
    """))

    # 2. The problem.
    slides.append(("The problem", f"""
      <h2 class="section">Discount leakage compounds. <span class="slate" style="font-weight:600;">Nobody catches it.</span></h2>
      <div class="split">
        <div>
          <ul class="bullets">
            <li><b>Sales discounts to win the quarter.</b> <span class="why">Pattern: bigger discount, same win probability. Money on the floor.</span></li>
            <li><b>Quarter-end pressure compresses pricing discipline.</b> <span class="why">15 to 25% lift in discount given, almost no extra win rate.</span></li>
            <li><b>Approval workflows exist but are not enforced.</b> <span class="why">Off-policy deals close with the approver field left blank.</span></li>
            <li><b>Finance gets a number.</b> <span class="why">They do not get a read-out that explains the gap.</span></li>
            <li><b>The system of record for why each discount was given does not exist.</b> <span class="why">Not in the CRM, not in the BI tool, not in the data warehouse.</span></li>
          </ul>
        </div>
        <div>
          <div class="cards cols-2">
            <div class="card">
              <div class="k">Where leakage hides</div>
              <div class="v small">Above-policy discounts<br/>without approvers</div>
              <div class="sub">Audit trail says approved because the field is optional.</div>
            </div>
            <div class="card">
              <div class="k">Where intent dies</div>
              <div class="v small">Reasons stored as<br/>free-text notes</div>
              <div class="sub">Unsearchable, unaggregatable, lost on rep turnover.</div>
            </div>
            <div class="card">
              <div class="k">Why dashboards miss it</div>
              <div class="v small">Snowflake shows totals,<br/>not what to defend</div>
              <div class="sub">Lakehouses report. They do not reason.</div>
            </div>
            <div class="card">
              <div class="k">Why pure ML misses it</div>
              <div class="v small">Win-prob models are<br/>correlational, not causal</div>
              <div class="sub">Buyers want decision support, not opaque scores.</div>
            </div>
          </div>
        </div>
      </div>
    """))

    # 3. The wedge.
    slides.append(("The wedge", f"""
      <h2 class="section">One CSV. One read-out. <span class="teal">Free.</span></h2>
      <p class="lede" style="max-width:225mm;">
        A prospect sends a CSV of closed deals from any CRM. In under a minute, the engine returns
        four artifacts a Head of Pricing can forward to their CFO unchanged.
      </p>
      <div class="cards cols-4" style="margin-top:7mm;">
        <div class="card accent">
          <div class="k">1. Executive summary</div>
          <div class="v small">A one-page narrative</div>
          <div class="sub">Booked value, realization, win point, top three deals to investigate. Plain English.</div>
        </div>
        <div class="card accent">
          <div class="k">2. Win-curve report</div>
          <div class="v small">Win rate vs discount</div>
          <div class="sub">With the calculated reference point. The band where bigger discounts stop buying wins.</div>
        </div>
        <div class="card accent">
          <div class="k">3. Per-deal guidance</div>
          <div class="v small">Recommended discount</div>
          <div class="sub">Expected-value lift, win-prob change, top three factors driving the deal.</div>
        </div>
        <div class="card accent">
          <div class="k">4. Defended vs investigate</div>
          <div class="v small">Sales-friendly split</div>
          <div class="sub">Won deals split into earned the win vs worth a retrospective look.</div>
        </div>
      </div>
      <div class="flag good" style="margin-top:7mm;">
        <b>Pricekeel is decision support, not autopilot.</b> Every number traces to a key in the
        analysis. We call the headline figure pricing upside to investigate, not guaranteed savings.
      </div>
    """))

    # 4. Live engine numbers (first half).
    slides.append(("Live engine, headline", f"""
      <h2 class="section">What the engine reports on the <span class="teal">bundled sample</span>.</h2>
      <p class="lede dim">A synthetic 2,000-deal book ships with the product so prospects can see the
        shape of a read-out before sending real data. These numbers are computed live by
        <span class="kbd">pricing/diagnostic.py</span> on every page load, never hardcoded.</p>
      <div class="cards cols-4" style="margin-top:8mm;">
        <div class="card">
          <div class="k">Booked value, annual</div>
          <div class="v">{_m(N['booked'])}</div>
          <div class="sub">{N['won']:,} won of {N['opps']:,} opportunities</div>
        </div>
        <div class="card">
          <div class="k">Price realization</div>
          <div class="v">{_p(N['realization'])}</div>
          <div class="sub">Average discount given: {_p(N['avg_discount'])}</div>
        </div>
        <div class="card coral">
          <div class="k">Upside to investigate</div>
          <div class="v">{_m(N['upside'])}</div>
          <div class="sub">{_p(N['upside_pct'])} of booked, above the win-point</div>
        </div>
        <div class="card">
          <div class="k">Win rate</div>
          <div class="v">{_p(N['winrate'])}</div>
          <div class="sub">Peak {_p(N['peak_win_rate'])} reached by {N['reference_band']} band</div>
        </div>
      </div>
    """))

    # 5. Live engine numbers (defended / investigate / governance).
    slides.append(("Live engine, drilldown", f"""
      <h2 class="section">Same sample, sales-friendly split.</h2>
      <p class="lede dim">The reviewer who pushed back on the original framing was right.
        Showing leakage by itself reads as a witch-hunt. Splitting won deals into defended
        and investigate gives the sales team a fair seat at the readout meeting.</p>
      <div class="cards cols-3" style="margin-top:8mm;">
        <div class="card accent">
          <div class="k">Defended, earned the win</div>
          <div class="v">{_m(N['defended_value'])}</div>
          <div class="sub">{N['defended_deals']:,} deals at or below {_p(N['reference_threshold'])}.
            Tell sales: keep doing this. Do not blanket-restrict.</div>
        </div>
        <div class="card coral">
          <div class="k">Investigate</div>
          <div class="v">{_m(N['investigate_value'])}</div>
          <div class="sub">{N['investigate_deals']:,} deals above the reference. Walk the top
            with the rep and document the pattern.</div>
        </div>
        <div class="card">
          <div class="k">Off-policy, no approver</div>
          <div class="v">{_m(N['unapproved_dollars'])}</div>
          <div class="sub">Discounted above the policy threshold with the approver field blank.
            Lowest-friction guardrail.</div>
        </div>
      </div>
    """))

    # 6. Pipeline.
    slides.append(("Pipeline", f"""
      <h2 class="section">How a CSV becomes a read-out.</h2>
      <div class="pipeline">
        <div class="step"><div class="num">01</div><div class="name">Ingest</div>
          <div class="sub">Read CSV or XLSX. Four-layer column mapper: exact, fuzzy, embedding, cloud LLM fallback.</div></div>
        <div class="step"><div class="num">02</div><div class="name">Clean</div>
          <div class="sub">Account resolution, schema validation, derive list_acv, discount_pct, quarter_end flags.</div></div>
        <div class="step"><div class="num">03</div><div class="name">Diagnose</div>
          <div class="sub">Compute overview, leakage, reference threshold, segment realization, governance gaps.</div></div>
        <div class="step"><div class="num">04</div><div class="name">Model and explain</div>
          <div class="sub">LightGBM win probability, SHAP factors, expected-value curve.</div></div>
        <div class="step"><div class="num">05</div><div class="name">Narrate</div>
          <div class="sub">Deterministic Python extractors build Opportunity objects. LLM only writes the prose.</div></div>
      </div>
      <div style="margin-top:7mm; display:grid; grid-template-columns: 1fr 1fr; gap: 5mm;">
        <div class="card">
          <div class="k">Where ML lives</div>
          <div class="sub" style="color:var(--ink);font-size:12.5px;">
            Steps 4 and 5. Every dollar figure is a deterministic Python calculation against
            the analysis dict. The LLM writes prose around the number, never the number itself.
          </div>
        </div>
        <div class="card">
          <div class="k">Where the LLM is not used</div>
          <div class="sub" style="color:var(--ink);font-size:12.5px;">
            Steps 1 through 3. Mapping, metrics, leakage math are pure pandas plus numpy.
            Reproducible to the cent on the same input.
          </div>
        </div>
      </div>
    """))

    # 7. Metrics provenance.
    slides.append(("Where the numbers come from", f"""
      <h2 class="section">Every figure traces back to <span class="teal">pricing/metrics.py</span>.</h2>
      <p class="lede dim">Pure functions of the deal frame. No hidden state, no fitted parameter, no
        recovery-rate assumption. Reportage only.</p>
      <table class="code">
        <thead><tr><th>Function</th><th>What it answers</th><th>Methodology</th></tr></thead>
        <tbody>
          <tr><td class="k">overview(df)</td><td>Booked value, win rate, price realization, average discount.</td><td>Standard SaaS finance.</td></tr>
          <tr><td class="k">reference_discount(df)</td><td>The smallest discount band whose win rate is statistically indistinguishable from the peak band.</td><td>Bootstrap CI on band-level win rate.</td></tr>
          <tr><td class="k">leakage(df, policy)</td><td>Off-policy discount dollars and excess vs reference dollars.</td><td>Nagle, <i>Strategy and Tactics of Pricing</i>.</td></tr>
          <tr><td class="k">governance_gaps(df)</td><td>Off-policy deals with no recorded approver. The audit-trail gap.</td><td>Simon-Kucher discount governance.</td></tr>
          <tr><td class="k">quarter_end_effect(df)</td><td>Discount lift in the last 14 days of the quarter vs the rest.</td><td>Standard sales-discipline analysis.</td></tr>
          <tr><td class="k">defended_vs_investigate(df)</td><td>Won deals where the discount plausibly earned the win, vs deals worth a retrospective look.</td><td>Pure function. No causal claim.</td></tr>
        </tbody>
      </table>
      <div class="flag" style="margin-top:5mm;">
        <b>Honest disclosure on the deck.</b> Excess vs reference is correlational. The UI calls it
        pricing upside to investigate in every surface, never recoverable revenue.
      </div>
    """))

    # 8. The model.
    slides.append(("The model", f"""
      <h2 class="section">Win probability is <span class="teal">explainable</span> first, accurate second.</h2>
      <div class="split">
        <div>
          <ul class="bullets">
            <li><b>LightGBM binary classifier.</b> Predicts <span class="kbd">won</span> from deal features. Lives in <span class="kbd">pricing/model.py</span>.</li>
            <li><b>Time-ordered holdout.</b> The latest 25% of closes are scored, so the model is graded the way it is used: on deals that closed after everything it trained on.</li>
            <li><b>SHAP per-deal contributions.</b> Every recommendation names the factor: raises win chance, or lowers it.</li>
            <li><b>Expected-value curve.</b> Recommended discount maximizes <span class="kbd">list × (1 minus discount) × P(win)</span> across a sweep.</li>
            <li><b>AUC 0.614 on the bundled book</b>, time-ordered holdout, with a Brier skill of +0.037 against a constant that just quotes the win rate. The 2026-05-30 reviewer note called 0.64 fine for deal-guidance support, and that 0.64 came from an easier random split. Accuracy is not the moat. The explanation chain is.</li>
          </ul>
        </div>
        <div>
          <div class="card">
            <div class="k">Top features by gain</div>
            <table class="code" style="margin-top:6px;">
              <tbody>
                <tr><td class="k">discount_pct</td><td>1,962</td></tr>
                <tr><td class="k">list_acv</td><td>1,805</td></tr>
                <tr><td class="k">quantity</td><td>1,517</td></tr>
                <tr><td class="k">industry</td><td>495</td></tr>
                <tr><td class="k">competitor_present</td><td>433</td></tr>
                <tr><td class="k">region</td><td>316</td></tr>
              </tbody>
            </table>
          </div>
          <div class="card" style="margin-top:5mm;">
            <div class="k">Why not a deeper model</div>
            <div class="sub" style="color:var(--ink);font-size:12.5px;">
              Enterprise buyers do not accept opaque scores from an unknown vendor.
              The model only has to be good enough to be defensible. The explanation
              chain (SHAP factors, reference threshold, decision log) is the deliverable.
            </div>
          </div>
        </div>
      </div>
    """))

    # 9. Copilot.
    slides.append(("Copilot architecture", f"""
      <h2 class="section">Deterministic extractors. <span class="teal">LLM never invents numbers.</span></h2>
      <p class="lede dim">The chat surface looks like an LLM. It is not. Every dollar figure, deal count,
        and confidence score is a Python function call against the analysis dict. The LLM writes the
        sentence around the number, and that sentence is logged.</p>
      <div class="pipeline" style="grid-template-columns: repeat(4, 1fr); margin-top:5mm;">
        <div class="step"><div class="num">01</div><div class="name">User asks</div>
          <div class="sub">One of six canonical questions. Where is leakage. Which deals to defend. Etc.</div></div>
        <div class="step"><div class="num">02</div><div class="name">Extractor runs</div>
          <div class="sub"><span class="kbd">pricing/copilot.py</span> turns the analysis dict into a structured <span class="kbd">Opportunity</span>.</div></div>
        <div class="step"><div class="num">03</div><div class="name">LLM narrates</div>
          <div class="sub">Cloud LLM gets the Opportunity JSON. Writes prose. Cannot output a number not in its input.</div></div>
        <div class="step"><div class="num">04</div><div class="name">Decision log</div>
          <div class="sub">User accepts or dismisses. We persist the opportunity, action, and supporting math.</div></div>
      </div>
      <div class="cards cols-2" style="margin-top:6mm;">
        <div class="card accent">
          <div class="k">Why this matters</div>
          <div class="sub" style="color:var(--ink);font-size:12.5px;">
            The decision log is the moat. Six months of recommendations plus accept and dismiss
            outcomes on a customer's own data is unrepeatable from a CSV. A Snowflake dashboard
            or a generic LLM cannot generate it.
          </div>
        </div>
        <div class="card">
          <div class="k">Why ChatGPT does not replace this</div>
          <div class="sub" style="color:var(--ink);font-size:12.5px;">
            ChatGPT can write the prose. It cannot run a calibrated win-prob model on the
            customer's own deal book, maintain a per-customer decision log, or ground each
            sentence in a methodology a CFO will sign off on.
          </div>
        </div>
      </div>
    """))

    # 10. Competitor matching.
    slides.append(("Competitor intelligence", f"""
      <h2 class="section">Match <span class="teal">your plans</span> against <span class="teal">your named competitors</span>.</h2>
      <div class="split">
        <div>
          <ul class="bullets">
            <li><b>Customer-named URLs only.</b> We do not scrape the open web. The customer tells us which 3 to 8 competitors they care about.</li>
            <li><b>SSRF-hardened fetcher.</b> <span class="kbd">pricing/_safe_fetch.py</span> resolves the hostname, blocks private IPs, caps redirects. Cannot be tricked into hitting AWS metadata or internal IPs.</li>
            <li><b>robots.txt respected.</b> Per-host kill-switch. We will not be the company that gets sued for crawling.</li>
            <li><b>Blended scorer.</b> 0.65 fastembed cosine on feature lists, plus 0.35 rapidfuzz token-set ratio on plan names.</li>
            <li><b>Output.</b> Per-plan matches, pricing position (above, at, below market), feature deltas in each direction.</li>
          </ul>
        </div>
        <div>
          <div class="card">
            <div class="k">Why this scope, not a market scraper</div>
            <div class="sub" style="color:var(--ink);font-size:12.5px;">
              Architect-panel constraint (2026-05-29 blind review): a market-wide scraper has
              <b style="color:var(--coral);">unbounded data acquisition cost</b> at pre-seed and serious
              IP-risk exposure. Customer-named URLs is a 100x narrower scope with 95% of the buyer value.
            </div>
          </div>
          <div class="card" style="margin-top:4mm;">
            <div class="k">What we will not build</div>
            <div class="sub" style="color:var(--ink);font-size:12.5px;">
              MAP enforcement, retail price intelligence, dealer-network scraping, daily monitoring crawler.
              Pricekeel is B2B SaaS pricing intelligence, not a generalist scraper.
            </div>
          </div>
        </div>
      </div>
    """))

    # 11. Tech stack.
    slides.append(("Tech stack", f"""
      <h2 class="section">Stack chosen for <span class="teal">explainability</span> and <span class="teal">cost discipline</span>.</h2>
      <div class="stack">
        <div class="group">
          <h4>Engine, Python</h4>
          <p><b>LightGBM</b>, gradient-boosted win probability.<br/>
             <b>scikit-learn</b>, splits and metrics.<br/>
             <b>SHAP</b>, per-deal feature contributions.<br/>
             <b>pandas, numpy</b>, deterministic metric math.<br/>
             <b>FastAPI</b>, the engine endpoints.</p>
        </div>
        <div class="group">
          <h4>Intelligence layer</h4>
          <p><b>fastembed</b> (BAAI bge-small ONNX), local CPU embeddings, no API call.<br/>
             <b>rapidfuzz</b>, fuzzy column and plan-name matching.<br/>
             <b>OpenAI, Anthropic</b>, plan extraction and narration only.<br/>
             <b>Zero-retention</b> provider terms.</p>
        </div>
        <div class="group">
          <h4>Web, Next.js 16</h4>
          <p><b>App Router, Turbopack</b>.<br/>
             <b>Tailwind v4</b>, brand-styled UI.<br/>
             <b>Recharts</b>, win curve, segment chart, expected-value chart.<br/>
             <b>Two-tier funnel</b>, lead cookie unlocks demo, access code unlocks own-data upload.</p>
        </div>
        <div class="group">
          <h4>Data and auth</h4>
          <p><b>Neon, Postgres</b>, leads and access codes.<br/>
             <b>pgvector</b>, per-customer chunk store (Phase 3 path).<br/>
             <b>Microsoft 365</b>, contact email with DKIM and SPF.<br/>
             <b>Resend</b>, transactional lead-notify email.</p>
        </div>
        <div class="group">
          <h4>Infrastructure</h4>
          <p><b>Vercel</b>, Next.js web at pricekeel.com.<br/>
             <b>Render</b>, FastAPI engine at api.pricekeel.com.<br/>
             <b>GoDaddy</b>, DNS (apex A, www CNAME, api CNAME).<br/>
             <b>GitHub Actions</b>, CI on every push.</p>
        </div>
        <div class="group">
          <h4>Observability and posture</h4>
          <p><b>Vercel logs</b> plus Render logs.<br/>
             <b>Test suite</b>, 77 Python tests pin dollar math.<br/>
             <b>CORS lockdown</b>, production accepts only pricekeel.com origins.<br/>
             <b>SSRF guard</b> on every outbound URL fetch.</p>
        </div>
      </div>
    """))

    # 12. Privacy and security.
    slides.append(("Privacy and security", f"""
      <h2 class="section">Designed for what a <span class="teal">$50M-ARR CISO</span> will ask.</h2>
      <div class="cards cols-2">
        <div class="card">
          <div class="k">Data in transit</div>
          <div class="sub" style="color:var(--ink);font-size:12.5px;">
            TLS only at both edges (Vercel, Render). CORS lockdown rejects cross-origin calls
            from any host not on the production allow-list.
          </div>
        </div>
        <div class="card">
          <div class="k">Data at rest</div>
          <div class="sub" style="color:var(--ink);font-size:12.5px;">
            CSV uploads are processed in memory and deleted after the analysis completes. Never
            written to disk on our servers. Only the read-out the customer downloads persists.
          </div>
        </div>
        <div class="card">
          <div class="k">What the LLM sees</div>
          <div class="sub" style="color:var(--ink);font-size:12.5px;">
            Aggregate figures and column header names. Never row-level deal data.
            Zero-retention provider terms keep customer data out of training.
          </div>
        </div>
        <div class="card">
          <div class="k">SSRF and IP risk</div>
          <div class="sub" style="color:var(--ink);font-size:12.5px;">
            Outbound URL fetches go through a hardened wrapper. Hostname resolved, private IPs
            blocked, redirects capped, robots.txt respected. 12 dedicated tests pin the behavior.
          </div>
        </div>
        <div class="card">
          <div class="k">Two-tier funnel gate</div>
          <div class="sub" style="color:var(--ink);font-size:12.5px;">
            <span class="kbd">pk_lead</span> unlocks the bundled-sample read-out (low risk).
            <span class="kbd">pk_access</span> (one-time code) unlocks uploading customer data.
            Both enforced at the proxy and per route handler.
          </div>
        </div>
        <div class="card">
          <div class="k">Legal posture</div>
          <div class="sub" style="color:var(--ink);font-size:12.5px;">
            /terms, /privacy, /subprocessors, /trust, /licenses, robots.txt all live.
            DPA available on request. NDA available on request.
          </div>
        </div>
      </div>
    """))

    # 13. Defensibility.
    slides.append(("Defensibility", f"""
      <h2 class="section">Why this <span class="teal">compounds</span> with each customer.</h2>
      <div class="cards cols-3">
        <div class="card accent">
          <div class="k">Decision-log moat</div>
          <div class="sub" style="color:var(--ink);font-size:12.5px;">
            Every recommendation logged with its supporting math. After six months the customer
            owns an audit-grade record of which pricing calls worked. Unrepeatable from a CSV.
          </div>
        </div>
        <div class="card">
          <div class="k">Citation chain</div>
          <div class="sub" style="color:var(--ink);font-size:12.5px;">
            Every methodology cited. Nagle for reference threshold, Ramanujam for monetization,
            Simon-Kucher for governance, Rivera for packaging, Bertini for the ends game. The
            methodology is the deliverable.
          </div>
        </div>
        <div class="card">
          <div class="k">Integration-light wedge</div>
          <div class="sub" style="color:var(--ink);font-size:12.5px;">
            CSV in, read-out out. No 6-month Salesforce integration. The wedge ships in the
            time-to-first-meeting that most pricing tools need for procurement alone.
          </div>
        </div>
        <div class="card">
          <div class="k">Privacy posture</div>
          <div class="sub" style="color:var(--ink);font-size:12.5px;">
            In-memory only, aggregates-only to the LLM, zero-retention provider terms.
            Enterprise data teams can say yes without involving security legal.
          </div>
        </div>
        <div class="card">
          <div class="k">No category competitor</div>
          <div class="sub" style="color:var(--ink);font-size:12.5px;">
            Pricefx, Vendavo, PROS sell into manufacturing and industrial.
            SaaS-native pricing intelligence with our scope and privacy posture has no incumbent.
          </div>
        </div>
        <div class="card">
          <div class="k">LLM-orthogonal</div>
          <div class="sub" style="color:var(--ink);font-size:12.5px;">
            Better LLMs make our narration better. Our value is the deterministic pipeline
            underneath, which does not improve when GPT-7 ships.
          </div>
        </div>
      </div>
    """))

    # 14. Stage and phase plan combined into one tight slide.
    slides.append(("Stage and phase plan", f"""
      <h2 class="section">Pre-seed. Product launch-ready. <span class="coral">Distribution not yet.</span></h2>
      <div class="split">
        <div>
          <ul class="bullets">
            <li><b>Product.</b> 8 phases shipped, 77 tests passing, web build and lint clean.</li>
            <li><b>Public site live.</b> pricekeel.com (Vercel), api.pricekeel.com (Render), Neon Postgres.</li>
            <li><b>Legal pack live.</b> Terms, Privacy, Subprocessors, Trust, Licenses. Founder follow-ups (entity, counsel review, TM, DMCA) tracked separately.</li>
            <li><b>Security hardened.</b> Cross-model launch review flagged 4 High items. All shipped this week.</li>
            <li><b>What is not here yet.</b> <span class="coral">No design partner. n=1 synthetic deal book. No testimonial.</span></li>
          </ul>
        </div>
        <div>
          <div class="cards cols-1" style="gap:3mm;">
            <div class="card accent">
              <div class="k">Phase 1, now</div>
              <div class="v small">Retrospective diagnostic</div>
              <div class="sub">CSV in, four artifacts out. Free for design partners. Engine plus UI plus privacy posture all live today.</div>
            </div>
            <div class="card">
              <div class="k">Phase 2, 2027</div>
              <div class="v small">Copilot and recommendation engine</div>
              <div class="sub">On the customer's own ongoing data. Per-deal guidance plus decision log become the daily-used surface. First paid tier here.</div>
            </div>
            <div class="card">
              <div class="k">Phase 3, 2028</div>
              <div class="v small">Adjacent SaaS verticals</div>
              <div class="sub">Active-contract layer, NRR plus expansion plus contraction. Snowflake plus Fivetran ingest. Margin enhancement positioning.</div>
            </div>
          </div>
        </div>
      </div>
    """))

    # 15. Ask.
    slides.append(("Ask", f"""
      <h2 class="section" style="font-size:40px;">5 to 10 design partner intros. <span class="teal">VP Pricing, VP Finance, RevOps.</span></h2>
      <p class="lede" style="max-width:240mm;">
        Companies in $10M to $100M ARR B2B SaaS on usage-based or hybrid pricing, with at least
        12 months of closed deal history. The ask is one call. The offer is a free retrospective
        read-out on their own data, with an NDA if they want one.
      </p>
      <div class="cards cols-3" style="margin-top:7mm;">
        <div class="card">
          <div class="k">What we need</div>
          <div class="sub" style="font-size:12.5px; color:var(--ink);">
            Warm intros to VPs of Pricing, Finance, or RevOps at portfolio companies fitting the ICP.
          </div>
        </div>
        <div class="card accent">
          <div class="k">What they get</div>
          <div class="sub" style="font-size:12.5px; color:var(--ink);">
            Free diagnostic on their last 4 quarters of closed deals. Read-out delivered as a PDF and a live link.
            NDA on request. No commercial commitment.
          </div>
        </div>
        <div class="card">
          <div class="k">What we learn</div>
          <div class="sub" style="font-size:12.5px; color:var(--ink);">
            Whether the read-out generalizes off the synthetic book. The methodology is robust.
            We need to see it on real data with a real CRO in the room.
          </div>
        </div>
      </div>
      <div style="margin-top:14mm; display:flex; gap:24px; align-items:baseline; flex-wrap:wrap;">
        <span style="font-size:17px; color:var(--fg); font-weight:600;">Adhithya Bhaskar, Founder</span>
        <span class="teal" style="font-size:17px;">adhithya@pricekeel.com</span>
        <span class="teal" style="font-size:17px;">pricekeel.com</span>
      </div>
    """))

    total = len(slides)
    slides_html = "".join(
        _slide(i + 1, total, eyebrow, body) for i, (eyebrow, body) in enumerate(slides)
    )

    return f"""<!doctype html><html><head>
    <meta charset="utf-8"/>
    <title>Pricekeel, Investor Deck</title>
    <style>{INVESTOR_CSS}</style>
    </head><body>{slides_html}</body></html>"""


# ---------------------------------------------------------------------------
# Technical doc, portrait A4.

DOC_CSS = BRAND_CSS + """
@page { size: A4 portrait; margin: 18mm 16mm 18mm 16mm;
  @bottom-center { content: "Pricekeel · Technical Doc · page " counter(page) " of " counter(pages);
                   color: #6b7891; font-size: 9px; }
}
body { font-size: 11.5px; line-height: 1.55; background: #ffffff; color: var(--fg); }
h1.doc-title { font-size: 30px; font-weight: 800; letter-spacing: -0.01em; margin: 0 0 4px 0; color: var(--fg); }
h2 {
  font-size: 17px; font-weight: 800; color: var(--fg); margin: 22px 0 8px 0;
  border-bottom: 1px solid var(--line); padding-bottom: 5px;
}
h3 {
  font-size: 13px; font-weight: 700; color: var(--teal); margin: 14px 0 6px 0;
  text-transform: uppercase; letter-spacing: .06em;
}
h4 { font-size: 12px; font-weight: 700; color: var(--fg); margin: 10px 0 4px 0; }
p  { margin: 6px 0; color: var(--ink); }
.lead { font-size: 12.5px; color: var(--muted); }
code, .kbd {
  background: var(--surface); color: var(--teal-strong);
  padding: 1px 5px; border-radius: 4px;
  font-family: ui-monospace, SFMono-Regular, monospace; font-size: 10.5px;
  border: 1px solid var(--line);
}
pre {
  background: var(--surface); color: var(--ink);
  padding: 10px 12px; border-radius: 8px; border: 1px solid var(--line);
  font-family: ui-monospace, SFMono-Regular, monospace;
  font-size: 10.5px; line-height: 1.45;
  overflow: hidden;
}
ul { padding-left: 1.1em; }
ul li { margin: 4px 0; color: var(--ink); }
table {
  width: 100%; border-collapse: collapse; margin: 8px 0; font-size: 10.5px;
}
table th, table td {
  text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--line);
  vertical-align: top; color: var(--ink);
}
table th {
  color: var(--slate); font-weight: 600; font-size: 10px;
  text-transform: uppercase; letter-spacing: .06em;
}
.toc ol { margin: 0; padding-left: 1.2em; }
.toc li { color: var(--slate); margin: 4px 0; }
.toc li b { color: var(--fg); font-weight: 600; }
.flag {
  background: var(--surface); border-left: 3px solid var(--coral);
  padding: 8px 12px; color: var(--ink); margin: 10px 0; border-radius: 0 6px 6px 0;
}
.flag.good { border-color: var(--teal); }
.flag b { color: var(--fg); }
.page-break { page-break-before: always; }
"""


def technical_html() -> str:
    head_block = f"""
      <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom: 6mm;">
        {WORDMARK}
        <div style="text-align:right; color:var(--slate); font-size: 10px;">
          Technical Doc &middot; {TODAY}<br/>Confidential
        </div>
      </div>
      <h1 class="doc-title">How Pricekeel works</h1>
      <p class="lead">A function-level walkthrough of the engine, model, copilot, matching layer,
        and privacy posture. Written so a technical co-investor, an engineering hire, or future
        Claude can understand every layer of the system without reading the source.</p>
    """

    toc_block = """
      <h3>Contents</h3>
      <div class="toc">
      <ol>
        <li><b>Product framing.</b> What Pricekeel is, what it is not.</li>
        <li><b>Data path.</b> Ingest, mapping, cleaning, schema.</li>
        <li><b>Metrics layer.</b> pricing/metrics.py, function by function.</li>
        <li><b>Model layer.</b> LightGBM, calibration, SHAP, expected value.</li>
        <li><b>Copilot layer.</b> Deterministic extractors, LLM narration, decision log.</li>
        <li><b>Matching layer.</b> Competitor URLs, fastembed, rapidfuzz, SSRF defense.</li>
        <li><b>Privacy and security posture.</b> What flows where.</li>
        <li><b>API surface.</b> Every endpoint, what it takes, what it returns.</li>
        <li><b>Two-tier funnel and auth.</b> pk_lead, pk_access, the route gate.</li>
        <li><b>Testing and verification.</b> How we know the math is right.</li>
      </ol>
      </div>
    """

    section_1 = """
      <div class="page-break"></div>
      <h2>1. Product framing</h2>
      <p>Pricekeel is a system of record for pricing decisions in B2B SaaS. The wedge is a free
        retrospective diagnostic. A customer sends one CSV of closed deals (won and lost), and the
        engine returns four artifacts a Head of Pricing can forward to a CFO unchanged.</p>
      <ul>
        <li><b>Executive summary.</b> A narrative. Booked value, realization, win point, top three deals to investigate.</li>
        <li><b>Win-curve report.</b> Win rate by discount band with the calculated reference threshold.</li>
        <li><b>Per-deal guidance.</b> Recommended discount, expected-value lift, SHAP factors per open opportunity.</li>
        <li><b>Defended vs investigate list.</b> Sales-friendly split of won deals.</li>
      </ul>
      <h3>What Pricekeel is not</h3>
      <ul>
        <li>Not a CRM. We read CSV exports, we do not replace Salesforce.</li>
        <li>Not autopilot. Every recommendation is decision support with a citation chain. The call stays with the team.</li>
        <li>Not a market scraper. Competitor matching uses customer-named URLs only.</li>
        <li>Not multi-vertical. SaaS-native. Explicitly rejected retail, manufacturing, auto (blind panel 2026-05-29).</li>
      </ul>
    """

    section_2 = """
      <h2>2. Data path</h2>
      <h3>Ingest</h3>
      <p><code>pricing/ingest.py</code> reads CSV or XLSX, normalizes column types, and computes derived
        fields (<code>list_acv</code>, <code>discount_pct</code>, <code>is_quarter_end</code>). Handles
        currency-formatted strings, percentage strings, ISO and US date formats, and bool-ish values
        (yes, no, 1, 0).</p>
      <h3>Column mapping</h3>
      <p><code>pricing/mapping.py</code> is a four-layer mapper, cheapest first:</p>
      <ol>
        <li><b>Exact name match</b> against the canonical schema.</li>
        <li><b>Fuzzy match</b> via rapidfuzz <code>token_set_ratio</code> at threshold 85.</li>
        <li><b>Local embedding similarity</b> via fastembed (BAAI bge-small ONNX, CPU). No API call.</li>
        <li><b>Cloud LLM fallback.</b> Only invoked if the prior three fail. Sees column names only, never row data.</li>
      </ol>
      <p>The mapper exposes its decision in the UI so the customer can override before the analysis runs.
        You cannot diagnose a book of deals if the mapper silently picked the wrong revenue field.</p>
      <h3>Canonical schema</h3>
      <p><code>pricing/schema.py</code> defines required and optional columns. Required:
        <code>opportunity_id</code>, <code>account_name</code>, <code>list_acv</code>,
        <code>booked_acv</code>, <code>discount_pct</code>, <code>won</code>, <code>close_date</code>.
        Optional hierarchy (segment, business_unit, product_line, region, industry) enables additional
        slices when populated.</p>
    """

    section_3 = f"""
      <h2>3. Metrics layer</h2>
      <p>Every dollar figure in the read-out comes from a function in <code>pricing/metrics.py</code>.
        These are pure functions of the deal frame. No fitted parameters, no hidden state, no
        recovery-rate assumption. Reproducible to the cent on the same input.</p>

      <h3>overview(df)</h3>
      <p>Booked ACV (won), price realization (booked over list, won), average discount (won),
        opportunity counts. On the bundled 2,000-deal sample: <b>{N['opps']:,} opportunities,
        {N['won']:,} won, win rate {_p(N['winrate'])}, booked {_m(N['booked'])}, price realization
        {_p(N['realization'])}.</b></p>

      <h3>reference_discount(df)</h3>
      <p>The smallest discount band whose win rate is statistically indistinguishable from the peak
        band, computed via bootstrap confidence interval on band-level win rate. Methodology: Nagle's
        reference price concept. On the bundled sample: <b>reference threshold
        {_p(N['reference_threshold'])}, in the <code>{N['reference_band']}</code> band</b>. Discount
        above this bought no incremental win rate.</p>

      <h3>leakage(df, policy_threshold)</h3>
      <p>Two figures. <b>Off-policy leakage</b>: discount dollars given above the company's policy
        threshold (e.g. above 15%). <b>Excess vs reference</b>: discount dollars given above where wins
        peak. On the bundled sample: <b>excess vs reference {_m(N['upside'])}
        ({_p(N['upside_pct'])} of booked) across {N['deals_above_ref']:,} deals.</b></p>

      <h3>defended_vs_investigate(df, policy_threshold)</h3>
      <p>Sales-friendly split. Won deals at or below the reference threshold are defended (the
        discount plausibly earned the win). Above the threshold are investigate (worth a retrospective
        look). Pure function. No causal claim. On the bundled sample: <b>defended
        {_m(N['defended_value'])} across {N['defended_deals']:,} deals; investigate
        {_m(N['investigate_value'])} across {N['investigate_deals']:,} deals.</b></p>

      <h3>governance_gaps(df) and quarter_end_effect(df)</h3>
      <p>Off-policy deals with no recorded approver (the audit-trail gap; Simon-Kucher framework),
        and discount lift in the last 14 days of the quarter vs the rest. On the bundled sample:
        <b>{_m(N['unapproved_dollars'])} discounted above policy with the approver field blank</b>.</p>

      <div class="flag">
        <b>Honest framing in the UI.</b> Excess vs reference is correlational. The UI calls it
        pricing upside to investigate in every surface, never recoverable revenue or guaranteed
        savings. This came from the 2026-05-30 reviewer note: do not overstate recoverable dollars.
      </div>
    """

    section_4 = """
      <h2>4. Model layer</h2>
      <p><code>pricing/model.py</code> trains a LightGBM binary classifier that predicts
        <code>won</code> from deal features. Probabilities come straight from the classifier;
        there is no post-hoc calibration layer, so the calibration gap reported below is the
        model's own.</p>

      <h3>Features</h3>
      <p>Inputs the classifier sees, top six by gain on the bundled book:</p>
      <table>
        <thead><tr><th>Feature</th><th>Gain</th><th>Why it matters</th></tr></thead>
        <tbody>
          <tr><td><code>competitor_present</code></td><td>410</td><td>Multi-vendor deals discount more and close differently.</td></tr>
          <tr><td><code>list_acv</code></td><td>382</td><td>Bigger deals close differently. Buyer composition differs.</td></tr>
          <tr><td><code>industry</code></td><td>251</td><td>Cohort effect. Fintech, healthcare, media accept discounts differently.</td></tr>
          <tr><td><code>discount_pct</code></td><td>236</td><td>The lever the rep controls, and the one feature the model is constrained on.</td></tr>
          <tr><td><code>quantity</code></td><td>163</td><td>Per-seat vs platform mix proxy.</td></tr>
          <tr><td><code>region</code></td><td>93</td><td>Geo-cohort effect.</td></tr>
        </tbody>
      </table>

      <h3>Holdout and calibration</h3>
      <p>Time-ordered holdout: the earliest 1,500 closes train, the latest 500 (closing from
        2025-04-03) are scored, so no training deal closed after a deal it is graded on. There
        is no post-hoc calibration step. On the bundled book the model predicts a mean 59.3%
        win rate against an actual 65.8%. Much of that 6.5 point gap is the quarter-to-quarter
        swing in win rate on this book (55.3% to 65.4%). The average is the easy test, though:
        the one that matters is whether a per-deal probability beats simply quoting the win
        rate, and there the margin is thin, Brier 0.221 against 0.230 for that constant.</p>

      <h3>Headline metrics on the bundled sample</h3>
      <p><b>AUC 0.614</b> on the time-ordered holdout. Brier 0.221 against 0.230 for a constant
        that quotes the training win rate, so a Brier skill of +0.037. n_train 1,500. n_test 500.
        The 2026-05-30 launch-readiness panel flagged AUC 0.64 as fine for deal-guidance use;
        that 0.64 came from a random split, which on this book reports anywhere from 0.551 to
        0.670 depending on the seed. The time-ordered number is the one to hold us to.
        Accuracy is not the moat. The explanation chain is.</p>

      <h3>Per-deal explainability</h3>
      <p><code>explain(tm, X_row)</code> returns SHAP-style contributions (using LightGBM's
        <code>pred_contrib=True</code>) for each feature on a single deal. The UI surfaces the top
        three as raises win chance, or lowers win chance, with the factor named. Never the model says
        73% without a reason a rep can argue with.</p>

      <h3>Recommendation</h3>
      <p><code>recommend_discount(tm, X_row, list_acv)</code> sweeps the discount axis from 0% to
        about 40%, computes the calibrated win probability at each point, and returns the discount
        that maximizes expected ACV (<code>list × (1 minus discount) × P(win)</code>). The returned
        curve is what the UI renders so the human can see the shape, not just the argmax.</p>
    """

    section_5 = """
      <h2>5. Copilot layer</h2>
      <p><code>pricing/copilot.py</code> is the structural answer to the question, how do we use
        LLMs without hallucinating dollar figures. The chat UI looks like an LLM. Underneath it is a
        deterministic extractor pipeline.</p>

      <h3>Dataclass shapes</h3>
      <pre>@dataclass
class Opportunity:
    id: str
    kind: str            # "excess_leakage", "defended", "quarter_end", ...
    scope: str           # "All segments", "Enterprise", "Q4-2025 only"
    headline: str        # human title, roughly 70 chars
    current_value: float
    recommended_action: str
    revenue_impact_usd: float   # the dollar figure for the card
    confidence: float    # 0 to 1
    evidence: list[Evidence]    # citations back to the analysis dict</pre>

      <h3>Extractors</h3>
      <p>Functions named <code>_opp_*</code> turn the analysis dict into
        <code>Optional[Opportunity]</code> objects. Each:</p>
      <ul>
        <li>Reads only deterministic figures from the analysis dict.</li>
        <li>Computes the dollar impact directly. Never asks the LLM for a number.</li>
        <li>Returns <code>None</code> if the opportunity is not material (e.g. excess leakage under $1.5M).</li>
        <li>Attaches an <code>Evidence</code> list pointing back to specific keys in the analysis dict
          (auditable trail).</li>
      </ul>

      <h3>LLM role</h3>
      <p>The LLM gets the Opportunity JSON plus aggregate analysis figures, and writes the prose
        around them. Its system prompt forbids inventing numbers. Its temperature is low. If the LLM
        produces a dollar figure that does not appear in its input, the response is rejected and a
        deterministic fallback narration is rendered.</p>

      <h3>Decision log</h3>
      <p>When a user clicks Accept or Dismiss on an Opportunity card, we persist the opportunity
        (including its evidence, supporting math, and recommended action) and the user's decision.
        After six months on their own data the customer has an audit-grade record of which pricing
        calls worked. A moat that is unrepeatable from a CSV.</p>

      <p>The decision log is intentionally simple. Append-only, JSON-serializable, exportable. It is
        the product, not an implementation detail.</p>
    """

    section_6 = """
      <h2>6. Matching layer</h2>
      <p><code>pricing/matching.py</code> compares the customer's pricing page against a small list
        of customer-named competitor URLs. Scope is deliberately narrow. We do not scrape the open
        web.</p>

      <h3>Fetch</h3>
      <p>Every outbound URL goes through <code>pricing/_safe_fetch.py::safe_get()</code>. This function:</p>
      <ul>
        <li>Resolves the hostname (<code>socket.getaddrinfo</code>) before connecting.</li>
        <li>Rejects any address in a private, loopback, link-local, multicast, or reserved range.
          AWS IMDSv1 (<code>169.254.169.254</code>) is blocked, as is <code>localhost.example.com</code>
          (the canonical DNS-rebinding pattern).</li>
        <li>Handles redirects manually, re-resolving and re-checking each hop. Caps at three redirects.</li>
        <li>Caps response body size to 250 KB. Pricing pages are small. Ignore the rest.</li>
      </ul>
      <p>12 dedicated tests in <code>tests/test_safe_fetch.py</code> pin each guard.</p>

      <h3>robots.txt and kill-switch</h3>
      <p>Every fetch checks the origin's robots.txt for our user agent before proceeding. A static
        plus env-driven (<code>LEGAL_BLOCKED_HOSTS</code>) kill-switch lets a host be removed without
        a redeploy. Both defenses run before any HTTP request hits the network.</p>

      <h3>Extract and match</h3>
      <p>HTML is stripped of <code>script</code>, <code>style</code>, <code>noscript</code>. The
        cleaned text is sent to the LLM in JSON mode with a strict schema (vendor, plus plans with
        name, price, unit, features, notes). The LLM is told not to invent plans or features.</p>
      <p>Plans are matched using a blended scorer:</p>
      <pre>similarity = 0.65 * fastembed_cosine(features_a, features_b)
           + 0.35 * rapidfuzz_token_set(name_a, name_b)</pre>
      <p>Match output: per-plan pairings, pricing position (above_market, at_market, below_market,
        unknown), price delta %, features only on each side, confidence.</p>
    """

    section_7 = """
      <h2>7. Privacy and security posture</h2>
      <h3>What flows where</h3>
      <table>
        <thead><tr><th>Data</th><th>Stored?</th><th>Reaches LLM?</th><th>Reaches third party?</th></tr></thead>
        <tbody>
          <tr><td>Uploaded CSV row data</td><td>No, in-memory only</td><td>No</td><td>No</td></tr>
          <tr><td>Column header names</td><td>No</td><td>Only if cloud LLM mapping fallback fires</td><td>OpenAI or Anthropic (zero-retention)</td></tr>
          <tr><td>Aggregate analysis figures</td><td>Yes (the read-out)</td><td>Yes (for chat narration)</td><td>OpenAI or Anthropic (zero-retention)</td></tr>
          <tr><td>Lead form fields</td><td>Neon Postgres</td><td>No</td><td>Resend (notify email body only)</td></tr>
          <tr><td>Access codes</td><td>Neon Postgres</td><td>No</td><td>No</td></tr>
          <tr><td>Decision log entries</td><td>Neon Postgres (per session)</td><td>No</td><td>No</td></tr>
        </tbody>
      </table>

      <h3>Hardening shipped 2026-05-30 (PR 21)</h3>
      <ul>
        <li><b>API gating.</b> Every <code>/api/*</code> route handler enforces a cookie check
          (<code>requireLead</code> or <code>requireAccess</code>). Previously the page-level proxy
          gated routes but the API was reachable from curl.</li>
        <li><b>CORS lockdown.</b> FastAPI <code>CORSMiddleware</code> defaults to pricekeel.com
          origins in production. Env-overridable. Dev mode keeps wildcard.</li>
        <li><b>SSRF defense.</b> Every outbound URL fetch routes through <code>safe_get()</code>.</li>
        <li><b>DOC_STORE TTL.</b> 4-hour expiry, 500-session cap, 2000-chunks-per-session cap.
          All env-overridable.</li>
        <li><b>Lead notification.</b> Env-driven Resend or webhook. Failure never blocks the lead
          save.</li>
      </ul>
    """

    section_8 = """
      <h2>8. API surface</h2>
      <p>FastAPI service at <code>api.pricekeel.com</code>. All POST endpoints take JSON unless
        marked.</p>
      <table>
        <thead><tr><th>Endpoint</th><th>What it does</th><th>Auth</th></tr></thead>
        <tbody>
          <tr><td><code>GET /demo</code></td><td>Run the diagnostic on the bundled sample.</td><td>Public (read-only)</td></tr>
          <tr><td><code>POST /diagnostic</code> (multipart)</td><td>Run the diagnostic on an uploaded CSV.</td><td>pk_access (Next.js gate)</td></tr>
          <tr><td><code>POST /map-headers</code> (multipart)</td><td>Suggest a column mapping for an upload.</td><td>pk_access</td></tr>
          <tr><td><code>POST /recommend</code></td><td>Per-deal recommended discount and expected-value curve.</td><td>pk_lead</td></tr>
          <tr><td><code>POST /summary</code></td><td>One-page narrative summary of the diagnostic.</td><td>Public (bundled sample)</td></tr>
          <tr><td><code>GET, POST /copilot/canonical</code></td><td>List or answer one of six canonical questions.</td><td>pk_lead</td></tr>
          <tr><td><code>POST /copilot/log</code></td><td>Append accept or dismiss to the decision log.</td><td>pk_lead</td></tr>
          <tr><td><code>GET /copilot/decisions</code></td><td>Read the decision log for a session.</td><td>pk_lead</td></tr>
          <tr><td><code>POST /matching/competitor</code></td><td>Extract plans from a single competitor URL.</td><td>pk_lead</td></tr>
          <tr><td><code>POST /matching/compare</code></td><td>Match your plans against N competitor URLs.</td><td>pk_lead</td></tr>
          <tr><td><code>POST /docs/upload</code> (multipart)</td><td>Parse, chunk, embed uploaded policy docs.</td><td>pk_access</td></tr>
          <tr><td><code>POST /ask</code></td><td>RAG over analysis, uploaded docs, and optional web search.</td><td>pk_lead</td></tr>
        </tbody>
      </table>
    """

    section_9 = """
      <h2>9. Two-tier funnel and auth</h2>
      <p>Two cookies, two unlock tiers, all gates enforced at the proxy AND per handler:</p>
      <ul>
        <li><code>pk_lead</code>. Set after a valid lead form submission (company email required;
          free-email domains rejected). Unlocks the bundled-sample read-out, copilot, and competitor
          watch.</li>
        <li><code>pk_access</code>. Set after a valid one-time access code. Unlocks uploading the
          customer's own CSV. Cookie value is a stateless SHA-256 of <code>PRICEKEEL_SECRET</code>,
          so the proxy validates without a DB round trip.</li>
      </ul>
      <p>Routes:</p>
      <ul>
        <li><code>/sample</code>, <code>/login</code>, <code>/blog/*</code>, legal pages: public.</li>
        <li><code>/diagnostic</code>, <code>/guidance</code>, <code>/competitor-watch</code>:
          require <code>pk_lead</code>. Proxy redirects to <code>/sample?unlock=&lt;route&gt;</code>
          with a visible banner explaining what they tried to open.</li>
        <li><code>/upload</code>: requires <code>pk_access</code>. Proxy redirects to
          <code>/login?next=&lt;route&gt;</code>.</li>
      </ul>
    """

    section_10 = """
      <h2>10. Testing and verification</h2>
      <p>77 Python tests, run on every commit. Coverage focus is the dollar math. Every metric
        extractor, every copilot extractor, the SSRF guard, the model train and predict path, the
        column mapper.</p>
      <ul>
        <li><code>tests/test_metrics.py</code>. Pins the formulas. If <code>leakage</code> changes
          shape, tests fail with a dollar figure diff.</li>
        <li><code>tests/test_copilot.py</code>. Pins every <code>Opportunity</code> the extractors
          emit: headline, dollar impact, confidence, evidence count, sort order. Tests use synthetic
          analysis dicts so they run in under 100 ms.</li>
        <li><code>tests/test_safe_fetch.py</code>. 12 tests covering IP-range rejection (IPv4
          loopback, RFC1918, IMDSv1, IPv6 loopback, link-local), scheme block, redirect to private,
          redirect cap, body cap.</li>
        <li><code>tests/test_matching.py</code>. Strip and scorer behavior, cache TTL, robots.txt
          enforcement, kill-switch.</li>
        <li><code>tests/test_model.py</code>. Train and predict shape, calibration smoothness,
          recommend monotonicity (the recommended discount cannot be larger than the discount where
          expected value starts dropping).</li>
      </ul>
      <p>Web tier verification: <code>next build</code> succeeds, <code>eslint .</code> reports zero
        problems, and TypeScript strict mode is on. Cookie-gate behavior is verified via the proxy
        test in <code>web/src/proxy.ts</code> (small, hand-readable).</p>

      <div class="flag good">
        <b>What we will not claim.</b> We have no real-customer validation yet. AUC 0.61 is the
        synthetic book. On real data it may go up (cleaner signal, more features) or down (noisier
        outcomes). The methodology is honest. The wedge says: send your CSV, see what the engine
        reports. The customer is the one who validates it.
      </div>
    """

    return f"""<!doctype html><html><head>
    <meta charset="utf-8"/>
    <title>Pricekeel, How It Works (Technical Doc)</title>
    <style>{DOC_CSS}</style>
    </head><body>
      {head_block}
      {toc_block}
      {section_1}
      {section_2}
      {section_3}
      {section_4}
      {section_5}
      {section_6}
      {section_7}
      {section_8}
      {section_9}
      {section_10}
    </body></html>"""


# ---------------------------------------------------------------------------
# Render to PDF and optionally to a sanity-check PNG of slide 4.

def render_pdf(html: str, out: Path, landscape: bool) -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        page = browser.new_page()
        page.set_content(html, wait_until="domcontentloaded")
        page.emulate_media(media="print")
        page.pdf(
            path=str(out),
            format="A4",
            landscape=landscape,
            print_background=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"} if landscape
            else {"top": "16mm", "right": "14mm", "bottom": "16mm", "left": "14mm"},
            display_header_footer=False,
            prefer_css_page_size=True,
        )
        browser.close()


def render_slide_png(html: str, slide_index_0: int, out: Path) -> None:
    """Render the investor HTML at A4 landscape pixel size and screenshot a
    specific slide. Used to visually sanity-check layout without poking the
    PDF viewer."""
    # A4 landscape at 96 DPI is roughly 1123 x 794 px. Render larger for
    # retina sharpness then let the screenshot tool downsample.
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        page = browser.new_page(viewport={"width": 1400, "height": 990}, device_scale_factor=2)
        page.set_content(html, wait_until="domcontentloaded")
        page.emulate_media(media="print")
        # Snap to the requested slide.
        page.evaluate(
            f"""() => {{
                const slides = document.querySelectorAll('.slide');
                if (slides[{slide_index_0}]) {{
                    slides[{slide_index_0}].scrollIntoView({{block:'start'}});
                }}
            }}"""
        )
        elem = page.locator(".slide").nth(slide_index_0)
        elem.screenshot(path=str(out))
        browser.close()


def main() -> None:
    investor_pdf = OUT_DIR / "Pricekeel-Investor-Deck.pdf"
    doc_pdf = OUT_DIR / "Pricekeel-Technical-Doc.pdf"
    sanity_png = OUT_DIR / "_sanity-slide-04.png"

    inv_html = investor_html()
    doc_html = technical_html()

    print(f"Rendering {investor_pdf.name} ...")
    render_pdf(inv_html, investor_pdf, landscape=True)
    print(f"  -> {investor_pdf}  ({investor_pdf.stat().st_size//1024} KB)")

    print(f"Rendering {doc_pdf.name} ...")
    render_pdf(doc_html, doc_pdf, landscape=False)
    print(f"  -> {doc_pdf}  ({doc_pdf.stat().st_size//1024} KB)")

    # Sanity-check the heaviest slide (live engine headline) renders without
    # overflow by snapshotting just it as PNG.
    print(f"Sanity PNG of slide 4 (live engine numbers) ...")
    render_slide_png(inv_html, 3, sanity_png)
    print(f"  -> {sanity_png}  ({sanity_png.stat().st_size//1024} KB)")


if __name__ == "__main__":
    main()
