"""Build the Pricekeel pre-seed fundraising deck.

  decks/Pricekeel-Pre-Seed-Deck.pdf   (A4 landscape, 15 slides)

This replaces the 30 May 2026 design-partner-recruitment deck for fundraising
use. That deck asked for intros; this one asks for capital, and it is written
against the evidence boundary in gtm/llama-ventures/pitch-base.md. See
gtm/llama-ventures/deck-audit.md for what changed and why.

Reuses the house style, the A4 landscape slide frame, and the live-engine
numbers from tools/build_deck.py, so sample figures can never go stale: they
are recomputed from pricing/diagnostic.py on every build.

  python tools/build_investor_deck.py

Style rules enforced here:
  * Light theme, one idea per slide, headline states the point.
  * No em dashes or en dashes anywhere in copy. Ranges read "20 to 100".
  * Every ACV, SAM, NRR and payback figure carries an "assumed" label.
  * Product screenshots embed as base64 so the PDF is self-contained.
"""
from __future__ import annotations

import base64
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.build_deck import (  # noqa: E402
    INVESTOR_CSS,
    N,
    TODAY,
    WORDMARK,
    _m,
    _p,
    render_pdf,
    render_slide_png,
)

OUT_DIR = ROOT / "decks"
ASSETS = OUT_DIR / "assets"
OUT_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Images embed as data URIs: render_pdf uses set_content, so a relative src
# would never resolve and the slide would print an empty box.
def _img(name: str) -> str:
    """Embed an asset as a data URI. Screenshots ship as JPEG: the same panel as
    PNG roughly tripled the PDF, and the intake upload endpoint is size
    sensitive."""
    path = ASSETS / name
    if not path.exists():
        print(f"  WARNING: missing asset {path.name}, slide will render without it")
        return ""
    mime = "image/jpeg" if path.suffix.lower() in (".jpg", ".jpeg") else "image/png"
    b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{b64}"


DECK_CSS = INVESTOR_CSS + """
.shot {
  width: 100%; border-radius: 10px; border: 1px solid var(--line-strong);
  display: block;
}
/* Screenshots are sized by width, never clipped by a max-height: a cropped
   chart axis reads as a broken asset. Narrow the wrap instead. */
.shot-wrap { margin: 3mm auto 0 auto; }
.shot-wrap.narrow { width: 92%; }
.shot-wrap.short { width: 78%; }
.caption { color: var(--slate); font-size: 11px; margin-top: 5px; line-height: 1.45; }
.tier {
  display: inline-block; font-size: 9.5px; font-weight: 700; letter-spacing: .07em;
  text-transform: uppercase; padding: 2px 7px; border-radius: 999px; margin-left: 6px;
  vertical-align: middle;
}
.tier.verified { background: var(--teal-soft); color: var(--teal-strong); }
.tier.assumed { background: var(--surface-2); color: var(--muted); }
.funnel { display: grid; gap: 3mm; margin-top: 3mm; }
.funnel .row {
  display: grid; grid-template-columns: 1fr auto; gap: 10mm; align-items: baseline;
  border-bottom: 1px solid var(--line); padding-bottom: 5px;
}
.funnel .row .lab { color: var(--ink); font-size: 13px; }
.funnel .row .val { color: var(--fg); font-size: 15px; font-weight: 700; white-space: nowrap; }
.funnel .row.last .val { color: var(--teal); }
.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 9mm; align-items: start; }
.lead-in { color: var(--muted); font-size: 13.5px; line-height: 1.5; margin: 0 0 4mm 0; }
.body {
  flex: 1; display: flex; flex-direction: column; justify-content: center;
  padding-bottom: 6mm;  /* keeps content clear of the absolutely placed footer */
}
"""


# The live site's tagline changed after the May deck was built. Overridden here
# rather than in build_deck.py so the retired deck keeps rendering as it was.
DECK_WORDMARK = WORDMARK.replace(
    "Keep your pricing on an even keel.", "Pricing decisions, kept on course."
)


def _slide(num: int, total: int, eyebrow: str, body_html: str) -> str:
    """Slide frame. Drops the 'Confidential' stamp the old deck carried: it is
    unenforceable on a deck you email to investors and it reads as inexperience.

    Body is centered in the remaining height so a light slide does not leave a
    dead lower half."""
    return f"""
    <section class="slide">
      <header>{DECK_WORDMARK}<span class="tag">{eyebrow}</span></header>
      <div class="body">{body_html}</div>
      <footer>
        <span>Pricekeel · Pre-seed · {TODAY}</span>
        <span>{num} of {total}</span>
      </footer>
    </section>
    """


def deck_html() -> str:
    slides: list[tuple[str, str]] = []

    # ---------------------------------------------------------------- 1. Title
    slides.append(("Slide 01", f"""
      <div style="flex:1; display:flex; flex-direction:column; justify-content:center;">
        <h1 class="title">The decision record for<br/>every <span class="teal">discount exception</span>.</h1>
        <p class="lede dim" style="margin-top:16px; font-size:19px; max-width:215mm;">
          Pricekeel reads the live Salesforce Opportunity, recommends a guardrail built from
          that company's own closed won and lost history, and records the decision with
          evidence Finance can audit.
        </p>
        <div style="margin-top:22px; display:flex; gap:9mm; flex-wrap:wrap;">
          <div><div class="card" style="border-color:var(--teal);">
            <div class="k">Raising</div>
            <div class="v">$500K to $1M</div>
            <div class="sub">Pre-seed. Buys down demand risk, not feasibility risk.</div>
          </div></div>
          <div><div class="card">
            <div class="k">Status</div>
            <div class="v small">Product live and installable.<br/>Zero paying customers.</div>
            <div class="sub">Two design-partner conversations, intro-call stage.</div>
          </div></div>
        </div>
        <div style="margin-top:26px; color:var(--slate); font-size:13px;">
          Adhithya Bhaskar, Founder &nbsp;&middot;&nbsp;
          <span class="teal">adhithya@pricekeel.com</span> &nbsp;&middot;&nbsp;
          <span class="teal">pricekeel.com</span>
        </div>
      </div>
    """))

    # -------------------------------------------------------------- 2. Problem
    slides.append(("The problem", """
      <h2 class="section">A discount gets approved. <span class="slate" style="font-weight:600;">Nobody can say why.</span></h2>
      <p class="lead-in">
        The buyer is a CFO or Head of Pricing at a B2B SaaS company on usage-based or hybrid
        pricing. The moment that hurts is a deal desk approval with a number on it and no
        defensible basis underneath.
      </p>
      <div class="split">
        <div>
          <ul class="bullets">
            <li><b>There is no reference price to argue against.</b> <span class="why">Discipline lives in a spreadsheet and in whoever has been there longest.</span></li>
            <li><b>The approver field is optional.</b> <span class="why">Off-policy deals close with it blank, and the audit trail still says approved.</span></li>
            <li><b>Reasons are free text.</b> <span class="why">Unsearchable, unaggregatable, gone when the rep leaves.</span></li>
            <li><b>The warehouse reports, it does not reason.</b> <span class="why">Snowflake shows totals. It does not tell you which discount to defend.</span></li>
            <li><b>So the decision is never recorded.</b> <span class="why">Not in the CRM, not in the BI tool, not anywhere. That record is the product.</span></li>
          </ul>
        </div>
        <div>
          <div class="card coral">
            <div class="k">What it costs the buyer</div>
            <div class="v small">They cannot defend a discount<br/>in committee with math.</div>
            <div class="sub">
              So the rep who wants the quarter closed wins the argument, every quarter.
              Price realization erodes one deal at a time, and no single deal ever looks
              like the problem.
            </div>
          </div>
          <div class="flag good" style="margin-top:5mm;">
            <b>Why this is a system-of-record problem, not a dashboard problem.</b>
            A dashboard tells you discounting rose. It cannot tell you which approvals were
            right, because nobody wrote down what was recommended, what was decided, or what
            happened next.
          </div>
        </div>
      </div>
    """))

    # ------------------------------------------------------------- 3. Why now
    slides.append(("Why now", """
      <h2 class="section">The usage data is being locked up. <span class="slate" style="font-weight:600;">The decision layer on top is still open.</span></h2>
      <p class="lead-in">
        The standalone metering and billing category was absorbed into payments and CRM
        platforms in a single seven-month window.
      </p>
      <div class="cards cols-4">
        <div class="card"><div class="k">Dec 2025</div><div class="v small">Stripe acquires Metronome</div><div class="sub">About $1B. Completed Jan 2026.</div></div>
        <div class="card"><div class="k">Dec 2025</div><div class="v small">Thoma Bravo closes PROS</div><div class="sub">About $1.4B. Combined with Conga.</div></div>
        <div class="card"><div class="k">Jun 2026</div><div class="v small">Adyen agrees to acquire Orb</div><div class="sub">About $335M.</div></div>
        <div class="card coral"><div class="k">Jun 2026</div><div class="v small">Salesforce agrees to acquire m3ter</div><div class="sub">Into Agentforce Revenue Management.</div></div>
      </div>
      <div class="two-col" style="margin-top:6mm;">
        <div class="flag good">
          <b>The thesis.</b> Whoever owns the usage data ships the discount panel next.
          The race is to establish the decision-integrity wedge and accumulate the
          cross-customer corpus before that happens. Estimated window: <b>12 to 18 months</b>
          from mid-2026.
        </div>
        <div class="flag">
          <b>The Salesforce double-edge, stated before you ask.</b> It validates usage-based
          pricing on Salesforce as the battlefield and pulls usage data into the exact CRM we
          already read. It also signals appetite to own more of the revenue lifecycle, and
          Revenue Cloud already ships discount matrices and approval routing.
        </div>
      </div>
      <div class="caption">Figures verified 9 Aug 2026 and stale-fast. Re-verified before each send.</div>
    """))

    # ------------------------------------------------------------- 4. The wedge
    slides.append(("The wedge", """
      <h2 class="section">Four verbs, inside the workflow the team already runs.</h2>
      <div class="pipeline" style="grid-template-columns: repeat(4, 1fr);">
        <div class="step"><div class="num">01</div><div class="name">Read</div>
          <div class="sub">The live Salesforce Opportunity, plus two years of that org's closed won and lost deals.</div></div>
        <div class="step"><div class="num">02</div><div class="name">Recommend</div>
          <div class="sub">An explainable guardrail from the org's own history. Named factors, comparable deals, the win point.</div></div>
        <div class="step"><div class="num">03</div><div class="name">Record</div>
          <div class="sub">The human decision, append-only, with the supporting math. Accept, override, approve, reject.</div></div>
        <div class="step"><div class="num">04</div><div class="name">Reconcile</div>
          <div class="sub">The outcome when the deal closes, back against what was recommended and what was decided.</div></div>
      </div>
      <div class="two-col" style="margin-top:7mm;">
        <div>
          <div class="card accent">
            <div class="k">The category noun</div>
            <div class="v small">The decision record.</div>
            <div class="sub">
              Leakage is the pain. Guidance is the verb. The durable asset is the record of
              what was recommended, what a human decided, and what happened.
            </div>
          </div>
        </div>
        <div>
          <div class="card">
            <div class="k">What Pricekeel is not</div>
            <div class="v small">Not a CRM. Not a CPQ.<br/>Not an autonomous price setter.</div>
            <div class="sub">
              A human decision is the thing being recorded, so removing the human removes the
              product. Not a billing or metering platform, not a consultancy, and not a retail
              price optimizer: shelf pricing has no deal to record.
            </div>
          </div>
        </div>
      </div>
    """))

    # ------------------------------------------------- 5. Product, the recommendation
    slides.append(("Product, live", f"""
      <h2 class="section">This is the product, running. <span class="slate" style="font-weight:600;">Not a mockup.</span></h2>
      <div class="shot-wrap narrow">
        <img class="shot" src="{_img('product-recommendation.jpg')}" alt="Pricekeel guidance surface"/>
      </div>
      <div class="caption">
        The guidance surface on the bundled synthetic book. The recommendation names the deal,
        the change, and what it is worth. The expected-value curve shows where extra win
        probability stops covering the price given away. The right panel names the factors that
        move this specific deal. Every figure is a deterministic Python calculation.
      </div>
    """))

    # ------------------------------------------------- 6. Product, the evidence
    slides.append(("Explainability", f"""
      <h2 class="section">The explanation is the deliverable. <span class="slate" style="font-weight:600;">Accuracy is not the moat.</span></h2>
      <div class="shot-wrap short">
        <img class="shot" src="{_img('product-evidence.jpg')}" alt="Comparable deals and win rate by discount band"/>
      </div>
      <div class="two-col" style="margin-top:5mm;">
        <div class="flag good">
          <b>Why a modest model is the right model.</b> 0.64 AUC on held-out deals, calibrated
          to 61.6% predicted versus 60.8% actual. An enterprise buyer will not accept an opaque
          score from an unknown vendor. The model only has to be good enough to be defensible.
          The explanation chain is what gets bought.
        </div>
        <div class="flag">
          <b>The honesty is built in, not promised.</b> The product says these patterns are
          correlational, not causal, on the surface itself. It calls the headline figure a
          gap to reference that a pilot tests, never recoverable revenue. And a CRM proxy is
          never called margin: that boundary is enforced in the schema.
        </div>
      </div>
    """))

    # ------------------------------------------------------------ 7. Pipeline
    slides.append(("How it works", """
      <h2 class="section">The LLM writes the sentence. <span class="slate" style="font-weight:600;">It never writes the number.</span></h2>
      <div class="pipeline">
        <div class="step"><div class="num">01</div><div class="name">Ingest</div>
          <div class="sub">Salesforce OAuth, or CSV and XLSX. Four-layer column mapper: exact, fuzzy, embedding, LLM fallback.</div></div>
        <div class="step"><div class="num">02</div><div class="name">Clean</div>
          <div class="sub">Account resolution, schema validation, derived list value, discount, quarter-end flags.</div></div>
        <div class="step"><div class="num">03</div><div class="name">Diagnose</div>
          <div class="sub">Overview, reference threshold, segment realization, governance gaps.</div></div>
        <div class="step"><div class="num">04</div><div class="name">Model</div>
          <div class="sub">LightGBM win probability, isotonic calibration, per-deal factors, expected-value curve.</div></div>
        <div class="step"><div class="num">05</div><div class="name">Narrate</div>
          <div class="sub">Deterministic extractors build the object. The model writes prose around it.</div></div>
      </div>
      <div class="two-col" style="margin-top:7mm;">
        <div class="card accent">
          <div class="k">Where the LLM is not used</div>
          <div class="v small">Steps 1 through 3.</div>
          <div class="sub">
            Mapping, metrics and reference math are pure pandas and numpy. Reproducible to the
            cent on the same input.
          </div>
        </div>
        <div class="card">
          <div class="k">Refusal as a feature</div>
          <div class="v small">The engine declines<br/>rather than guess.</div>
          <div class="sub">
            Under 30 usable outcomes, it blocks guidance. With no mapped list field and a book
            that collapses to near-zero discount, onboarding blocks with a remedy instead of
            reporting a confident zero. Every verdict is labeled with the engine that produced it.
          </div>
        </div>
      </div>
    """))

    # ---------------------------------------------------------- 8. Methodology
    slides.append(("Methodology", """
      <h2 class="section">Every figure traces to a named function and a named framework.</h2>
      <table class="code">
        <tr><th>Function</th><th>What it answers</th><th>Grounding</th></tr>
        <tr><td class="k">overview(df)</td><td>Booked value, win rate, price realization, average discount.</td><td>Standard SaaS finance.</td></tr>
        <tr><td class="k">reference_discount(df)</td><td>The smallest discount band whose win rate is statistically indistinguishable from the peak band.</td><td>Bootstrap CI on band-level win rate.</td></tr>
        <tr><td class="k">leakage(df, policy)</td><td>Off-policy discount dollars, and excess versus the reference.</td><td>Nagle, Strategy and Tactics of Pricing.</td></tr>
        <tr><td class="k">governance_gaps(df)</td><td>Off-policy deals with no recorded approver. The audit-trail gap.</td><td>Simon-Kucher discount governance.</td></tr>
        <tr><td class="k">value_metric_reference_table(df)</td><td>A separate win point for seats, consumption and hybrid, because a discount point is not the same lever across value metrics.</td><td>Campbell, the value metric.</td></tr>
        <tr><td class="k">quarter_end_effect(df)</td><td>Discount lift in the last 14 days of the quarter versus the rest.</td><td>Sales-discipline analysis.</td></tr>
      </table>
      <div class="flag good">
        <b>This table is the founder-market-fit slide.</b> The buyer defends decisions in
        committee using exactly these frameworks. The product reasons in the same language,
        because the founder does.
      </div>
    """))

    # -------------------------------------------------------- 9. Live numbers
    slides.append(("Live engine", f"""
      <h2 class="section">What the engine reports on the bundled sample.</h2>
      <p class="lead-in">
        A synthetic 2,000-deal book ships with the product so a prospect sees the shape of a
        read-out before sending real data. These numbers are recomputed by
        <span style="font-family:ui-monospace,monospace; color:var(--teal);">pricing/diagnostic.py</span>
        on every build of this deck and on every page load at pricekeel.com/sample. They are
        never hardcoded.
      </p>
      <div class="cards cols-4">
        <div class="card"><div class="k">Booked value, annual</div><div class="v">{_m(N['booked'])}</div>
          <div class="sub">{N['won']:,} won of {N['opps']:,} opportunities</div></div>
        <div class="card"><div class="k">Price realization</div><div class="v">{_p(N['realization'])}</div>
          <div class="sub">Average discount {_p(N['avg_discount'])}</div></div>
        <div class="card coral"><div class="k">Gap to reference win point</div><div class="v">{_m(N['upside'])}</div>
          <div class="sub">{_p(N['upside_pct'])} of booked. A pilot tests actual recovery.</div></div>
        <div class="card"><div class="k">Win rate</div><div class="v">{_p(N['winrate'])}</div>
          <div class="sub">Peak {_p(N['peak_win_rate'])} at the {N['reference_band']} band</div></div>
      </div>
      <div class="two-col" style="margin-top:6mm;">
        <div class="card accent">
          <div class="k">The tightest, most actionable finding</div>
          <div class="v">{_m(N['unapproved_dollars'])}</div>
          <div class="sub">
            Discounted above the policy threshold with the approver field blank. The
            lowest-friction guardrail on the whole book, and the one a CFO can act on in a week.
          </div>
        </div>
        <div class="flag">
          <b>What this is not.</b> It is synthetic, so it is a demonstration of the method, not
          a market statistic. Excess versus reference is correlational: bigger and more
          competitive deals attract bigger discounts, so some of the gap is justified. The
          product says so on the surface, and we call it a gap to investigate, never recovered
          revenue.
        </div>
      </div>
    """))

    # -------------------------------------------------------------- 10. Market
    slides.append(("Market", """
      <h2 class="section">Bottoms-up, post-funnel. <span class="slate" style="font-weight:600;">The wedge is very small, and I will show you why.</span></h2>
      <p class="lead-in">
        Most decks stop at the band and the value metric. That layer gives roughly 3,000 to
        3,600 US accounts and a $120M to $215M SAM. Applying the operational gates that
        actually decide whether we can serve an account collapses it four to six times, so
        the honest wedge is the bottom row, not the top one.
      </p>
      <div class="funnel">
        <div class="row"><span class="lab">US B2B SaaS companies</span><span class="val">~17,000</span></div>
        <div class="row"><span class="lab">In the $10M to $100M ARR band, 15 to 20%, on usage-based or hybrid pricing</span><span class="val">~3,000 to 3,600</span></div>
        <div class="row"><span class="lab">Tier A, after 500+ closed outcomes a year, data readiness, a policy owner, a champion and a CFO buyer. CSV path, any CRM</span><span class="val">~350 to 480</span></div>
        <div class="row last"><span class="lab">Tier B, after the Salesforce gate. What the live workflow serves today</span><span class="val">~130 to 190</span></div>
      </div>
      <div class="cards cols-3" style="margin-top:5mm;">
        <div class="card"><div class="k">Pre-funnel, shown for depth only</div><div class="v small">$120M to $215M</div>
          <div class="sub">Band and value metric alone. Never our headline.</div></div>
        <div class="card accent"><div class="k">Tier A wedge SAM <span class="tier assumed">Assumed ACV</span></div><div class="v small">$11M to $29M</div>
          <div class="sub">Any CRM, via the CSV path. At a $30K to $60K ACV, pre-pilot.</div></div>
        <div class="card accent"><div class="k">Tier B, today <span class="tier assumed">Assumed ACV</span></div><div class="v small">$4M to $11M</div>
          <div class="sub">Salesforce-native. Salesforce is only ~40% of the qualified pool.</div></div>
      </div>
      <div class="flag">
        <b>So the wedge alone is not a venture case, and I am not going to pretend it is.</b>
        The case is the expansion stack on the next slide. The gate that binds is deal volume,
        not ARR: a high-velocity $12M ARR company with 600 closed opportunities is servable and
        a $30M ARR company closing twelve enterprise deals a year is not. The $5.5B to $6B
        price-optimization and CPQ TAM is gravity, not our market.
      </div>
    """))

    # ------------------------------------------------------------ 11. Expansion
    slides.append(("Expansion", """
      <h2 class="section">Where the venture case actually lives.</h2>
      <p class="lead-in">
        A multiplier stack on the $11M to $29M Tier A wedge, roughly 15 to 40 times, reaching
        $300M to $1B+. Every multiplier is a labeled assumption and none of them are merged
        into the wedge number on the previous slide.
      </p>
      <div class="cards cols-5" style="grid-template-columns:repeat(5,1fr);">
        <div class="card"><div class="k">Usage-only gate</div><div class="v small">~2x</div>
          <div class="sub">Serve seat-based books too.</div></div>
        <div class="card"><div class="k">ARR band</div><div class="v small">~1.5 to 2x</div>
          <div class="sub">Relax to $10M to $250M.</div></div>
        <div class="card"><div class="k">ACV</div><div class="v small">2 to 3x</div>
          <div class="sub">Pillars two through six.</div></div>
        <div class="card"><div class="k">Geography</div><div class="v small">~2 to 3x</div>
          <div class="sub">Beyond US and India.</div></div>
        <div class="card accent"><div class="k">Adjacency</div><div class="v small">Largest</div>
          <div class="sub">Negotiated pricing below.</div></div>
      </div>
      <h2 class="section" style="font-size:22px; margin-top:6mm;">The largest lever: negotiated pricing outside SaaS.</h2>
      <div class="two-col">
        <div>
          <div class="card accent">
            <div class="k">Why this segment</div>
            <div class="v small">Thousands of SKUs. Hundreds of<br/>product lines. Large account books.</div>
            <div class="sub">
              Component suppliers and industrial manufacturers price the same part differently
              across hundreds of negotiated accounts. SKUs times product lines times accounts is
              a decision volume no committee can hold in its head, which is where a decision
              record compounds rather than merely reports. Hypothesis $350M to $850M US SAM at
              a $60K to $120K ACV.
            </div>
          </div>
        </div>
        <div>
          <div class="card coral">
            <div class="k">Why not now, stated plainly</div>
            <div class="sub" style="color:var(--ink);">
              <b>A second engine, not a second segment.</b> The objective flips from win
              probability to pocket margin, the grain drops from the deal to the SKU line, and
              it needs true cost data and ERP connectors we deliberately do not have.<br/><br/>
              <b>Incumbent home turf.</b> Vendavo, PROS and Zilliant have twenty-year head
              starts there. Our wedge exists because they ignore mid-market SaaS usage-based
              pricing. Entering early trades the market where we are uniquely positioned for the
              one where we are weakest.
            </div>
          </div>
        </div>
      </div>
      <div class="flag good">
        <b>The gate is explicit.</b> No cost, SKU or cost-plus capability gets built until a
        SaaS pilot is paying. A proven-engine port with prerequisites, not a second bet running
        in parallel.
      </div>
    """))

    # ------------------------------------------------------- 12. Business model
    slides.append(("Business model", """
      <h2 class="section">Land on a paid pilot. Expand on the pillars.</h2>
      <div class="cards cols-3">
        <div class="card"><div class="k">Entry <span class="tier assumed">Assumed</span></div><div class="v">$15K</div>
          <div class="sub">90-day paid pilot, 50% credited to the annual contract.</div></div>
        <div class="card accent"><div class="k">Wedge ACV <span class="tier assumed">Assumed</span></div><div class="v">$30K to $60K</div>
          <div class="sub">Annual, after a successful pilot.</div></div>
        <div class="card"><div class="k">Cycle <span class="tier assumed">Assumed</span></div><div class="v">3 to 6 months</div>
          <div class="sub">CFO or Head of Pricing buyer, RevOps or Deal Desk champion.</div></div>
      </div>
      <div class="two-col" style="margin-top:6mm;">
        <div class="flag">
          <b>Every number on this slide is assumed.</b> Zero customers means zero observed ACV,
          zero observed retention, and therefore no honest NRR, LTV/CAC or payback figure. We
          would rather show you the hypothesis and what would kill it than a projection.
        </div>
        <div class="card">
          <div class="k">The margin risk, named</div>
          <div class="v small">LLM inference and onboarding<br/>are real gross-margin drag.</div>
          <div class="sub">
            Implementation is priced separately or automated, targeting blended gross margin
            above roughly 60%. The six-pillar expansion is the financial model and it is
            NRR-driven, which is why the wedge being small is survivable.
          </div>
        </div>
      </div>
    """))

    # ------------------------------------------------------ 13. Defensibility
    slides.append(("Defensibility", """
      <h2 class="section">Concede the feature. <span class="slate" style="font-weight:600;">Then the argument that survives.</span></h2>
      <div class="flag">
        <b>Copyable, and we will say so first.</b> The scorecard, the recommended number, and
        the leakage dashboard are all copyable. Salesforce Revenue Cloud already ships discount
        matrices and approval routing. Metronome, Orb and m3ter own the usage substrate and are
        one release from a discount panel. If the pitch is that our interface is nicer, we lose.
      </div>
      <div class="cards cols-3" style="margin-top:5mm;">
        <div class="card accent"><div class="k">1. Neutrality</div>
          <div class="v small">Structural, not a toggle.</div>
          <div class="sub">
            A billing platform that benchmarks your prices profits from higher usage and higher
            prices, and can only see its own billed base. A CRM benchmarks nothing. Stripe cannot
            flip this without cannibalizing its own incentive. This is the Bloomberg argument.
          </div></div>
        <div class="card accent"><div class="k">2. Accumulation</div>
          <div class="v small">The corpus compounds per customer.</div>
          <div class="sub">
            Recommendation, evidence, human decision, reconciled outcome, then the cross-customer
            benchmark on top. A billing player is disinclined to build it and a CRM is
            uninterested: different buyer, different muscle.
          </div></div>
        <div class="card accent"><div class="k">3. Explainability</div>
          <div class="v small">The category, not a feature.</div>
          <div class="sub">
            The product exists so a Head of Pricing wins a committee argument. Billing platforms
            optimize for billing correctness, which is a different muscle from a defensible
            narrative.
          </div></div>
      </div>
      <div class="flag good" style="margin-top:5mm;">
        <b>The honest synthesis.</b> That moat is a thesis today, not an asset, because we have
        zero customers. Defensibility over the next 12 to 18 months is speed, explainability and
        usage-native depth. The compounding moat turns on only once N consenting customers exist.
        So the whole game is the race to accumulation, and the clock is the window on slide 3.
      </div>
    """))

    # ---------------------------------------------------------- 14. Traction
    slides.append(("Where we are", f"""
      <h2 class="section">Feasibility is retired. <span class="slate" style="font-weight:600;">Demand is not.</span></h2>
      <div class="two-col">
        <div>
          <div class="card accent">
            <div class="k">Verified <span class="tier verified">Provable today</span></div>
            <div class="sub" style="color:var(--ink);">
              <b>Live and installable.</b> pricekeel.com is a working product. The Salesforce
              External Client App passed live-org acceptance in a dedicated org: production OAuth
              consent and callback, expected org identity, encrypted token storage, Opportunity
              metadata discovery, mapping persistence, bounded sync.<br/><br/>
              <b>The guardrail fired correctly.</b> That org returned 18 closed and 13 open
              Opportunities, and the 30-usable-outcome bar refused to produce guidance on a book
              that thin.<br/><br/>
              <b>195 Python tests</b> plus TypeScript connector tests, CI green on main and
              gating every push and pull request.
            </div>
          </div>
        </div>
        <div>
          <div class="card">
            <div class="k">Traction, stated without dressing</div>
            <div class="v small">Two design-partner conversations.<br/>Intro calls only.</div>
            <div class="sub">
              No NDA, no data received, no commitment, no revenue.
            </div>
          </div>
          <div class="flag good" style="margin-top:4mm;">
            <b>What is worth more than the meeting count.</b> Those conversations already moved
            the roadmap twice. Ingestion went CRM-agnostic, and a HubSpot export now maps
            cleanly through the CSV path, though a native HubSpot connector is scoped and not
            built. And margin recovery moved forward: the schema already carries the optional
            cost field that anticipates it, while the margin layer itself is scoped, not built.
            First contact with real buyers produced direction changes, not validation theater.
          </div>
        </div>
      </div>
    """))

    # ------------------------------------------------------------- 15. Risks
    slides.append(("Risks", """
      <h2 class="section">The five things most likely to kill this.</h2>
      <div class="cards cols-2">
        <div class="card coral"><div class="k">1. Demand, the whole risk</div>
          <div class="v small">The product is built and nobody has paid.</div>
          <div class="sub">This is the honest headline and it is what the round buys down.</div></div>
        <div class="card"><div class="k">2. Data access</div>
          <div class="v small">Will a mid-market CFO grant CRM access to a pre-seed vendor?</div>
          <div class="sub">Genuinely unknown. Our own guardrails make it harder: a book thinner than 500 closed outcomes cannot be served at all.</div></div>
        <div class="card"><div class="k">3. Platform</div>
          <div class="v small">Salesforce and m3ter.</div>
          <div class="sub">Answered on slides 3 and 13. It is a real risk and we do not treat it as only a tailwind.</div></div>
        <div class="card"><div class="k">4. Cold start</div>
          <div class="v small">Customer one gets no benchmark.</div>
          <div class="sub">Which is why the wedge is the org's own closed won and lost history, so a single customer is useful with no network behind them.</div></div>
      </div>
      <div class="flag" style="margin-top:5mm;">
        <b>5. An open product gap we will not hide.</b> The approver today is operator-typed free
        text and a tenant shares one access code, so approval separation rests on a self-approval
        check and the audit payload records the actor as self-asserted. Real governance evidence
        needs per-user identity, WorkOS or SSO. It is filed, and until it ships we do not describe
        the audit trail as identity-bound.
      </div>
    """))

    # ------------------------------------------------------ 16. Team and ask
    slides.append(("Team and ask", """
      <h2 class="section">A pricing specialist building a pricing product.</h2>
      <div class="two-col">
        <div>
          <div class="card accent">
            <div class="k">Founder-market fit</div>
            <div class="v small">Adhithya Bhaskar<br/>M.S. in Pricing, Simon Business School</div>
            <div class="sub">
              The buyer defends decisions using Nagle on reference price, Simon-Kucher on
              discount governance, and Campbell on the value metric. The product reasons in
              those frameworks because the founder does. That is the explainability thesis in
              human form, and it is why the methodology table on slide 8 exists at all.
            </div>
          </div>
          <div class="flag" style="margin-top:4mm;">
            <b>The gaps, before you ask.</b> No operator scar story from inside a mid-market
            RevOps org, which is what every design-partner conversation is also buying. And solo,
            which is how feasibility got retired single-handed but is not how demand will be.
          </div>
        </div>
        <div>
          <div class="card" style="border-color:var(--teal);">
            <div class="k">The ask</div>
            <div class="v">$500K to $1M pre-seed</div>
            <div class="sub" style="color:var(--ink);">
              12 to 18 months to retire demand risk and turn the moat from thesis into asset.
            </div>
          </div>
          <div class="card" style="margin-top:4mm;">
            <div class="k">What the round buys</div>
            <div class="sub" style="color:var(--ink);">
              15 problem interviews and 5 data-readiness reviews completed.<br/>
              2 paid 90-day pilots converted.<br/>
              The first validated ACV, rather than an assumed one.<br/>
              The first cross-customer benchmark, with consent.<br/>
              Commit, ramp and overage depth, so the engine is usage-native rather than
              usage-adjacent.<br/>
              Per-user identity, closing the governance gap on slide 15.
            </div>
          </div>
        </div>
      </div>
      <div style="margin-top:7mm; display:flex; gap:22px; align-items:baseline; flex-wrap:wrap;">
        <span style="font-size:16px; color:var(--fg); font-weight:700;">Adhithya Bhaskar, Founder</span>
        <span class="teal" style="font-size:16px;">adhithya@pricekeel.com</span>
        <span class="teal" style="font-size:16px;">pricekeel.com</span>
      </div>
    """))

    total = len(slides)
    body = "".join(
        _slide(i + 1, total, eyebrow, html) for i, (eyebrow, html) in enumerate(slides)
    )
    return f"""<!doctype html><html><head>
    <meta charset="utf-8"/>
    <title>Pricekeel, Pre-Seed Deck</title>
    <style>{DECK_CSS}</style>
    </head><body>{body}</body></html>"""


def main() -> int:
    out = OUT_DIR / "Pricekeel-Pre-Seed-Deck.pdf"
    html = deck_html()
    print(f"Rendering {out.name} ...")
    render_pdf(html, out, landscape=True)
    print(f"  -> {out}  ({out.stat().st_size//1024} KB)")

    # Snapshot the image-heavy and number-heavy slides so layout overflow is
    # caught without opening a PDF viewer.
    for idx, name in ((4, "05-product"), (8, "09-live-engine"), (13, "14-traction")):
        png = OUT_DIR / f"_check-{name}.png"
        render_slide_png(html, idx, png)
        print(f"  check -> {png.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
