# Prototype

1. What the prototype proves and what it does not

The prototype is the calculator page at /margin-audit (F7, F13, PK-111), not a separate mock. Three sections: Input, Diagnostic, Recommendation.

It is the manual audit's first three steps made clickable.

It proves a visitor can reach a checkable result in two minutes. It is not the audit: it never sees billing or cost data, so it cannot find which customers lose money. Margin reads "contribution margin, customer-supplied cost basis" (F1), never gross margin. It sets no price.

2. Screen 1, Input

Blank rule: a blank is never zero and never carried over. A missing required field shows "Not enough to score." and no band or figure.

How you charge: flat, per seat, usage, hybrid. No default.

Fee, seat price or platform fee per month: USD, 0.01 to 1,000,000. Seats: integer 1 to 100,000. Unit price: USD, 0.000001 to 100,000. Included units (hybrid): 0 to 1e12, a typed 0 means none. No defaults.

Unit: "1M tokens" by default, or "Other" with a 1 to 24 character label. Customers: integer 1 to 100,000. Average usage per customer per month: above 0. Heavy customer usage (90th percentile): from the average up to 10 times it.

Model cost per unit, USD: above 0, typed 0 rejected. Blank under "1M tokens" takes the one labelled public-list-price default; under "Other" it is not enough to score.

Storage and other cost per customer per month, USD: 0 to 1,000,000. A typed 0 is accepted and echoed. Blank is not enough to score.

Monthly churn: 0.1% to 50%. A typed 0 is rejected.

Headline line (F9): "Know your cost to serve before you choose a unit."

3. Screen 2, Diagnostic (free)

B fee, p unit price, I included units, c model cost, s other cost, N customers. Rev(u) = B + p x max(0, u - I). M(u) = Rev(u) - c x u - s.

Margin at average usage. Formula: M(u_avg), and M(u_avg) / Rev(u_avg). Screen: "An average customer leaves {amount} a month ({pct}%)." It says "loses" when negative.

Margin at p90. Same formula at u90. Screen: "A customer at the 90th percentile leaves {amount} a month ({pct}%)."

Heavy-user break-even (flat, per seat). Formula: u* = (B - s) / c. Screen: "Margin turns negative above {u} {unit} a month per customer."

Revenue at risk. Formula: 0.1 x N x Rev(u90) / R_tot if M(u90) < 0, else 0. R_tot = N x (0.9 x Rev(u_bulk) + 0.1 x Rev(u90)), u_bulk = (u_avg - 0.1 x u90) / 0.9. Screen: "At least {pct}% of revenue comes from customers who cost more than they pay at the 90th percentile."

Margin Health, first match wins. Negative: M(u_avg) < 0 or blended < 0. At risk: blended < 40% or M(u90) < 0. Watch: blended < 60% or u90 >= 0.5 x u*. Healthy: otherwise. Blended = 1 - N x (c x u_avg + s) / R_tot.

Negative screen: "On your numbers the average customer costs more than it pays." The 40% and 60% lines are Pricekeel review lines, not benchmarks, printed beside the band. Churn over 8.33% a month drops the band one step.

4. Screen 3, Recommendation

Packaging signal, first match wins. Flat or per seat with M(u90) < 0 or u90 >= 0.5 x u*: add a usage component. Hybrid with p < c or u* <= I: fix overage or allowance. Usage with (p - c) / p < 0.40: unit price near cost. Otherwise: structure covers p90.

Free: band, figures, signal, formula block, and the "not scored" list. Behind the work email (F8): margin by customer group, the price-drop table, the 14-day audit request.

Gate copy, exact. Heading: "See the full breakdown". Body: "The headline result above is free and stays on this page. Enter your work email to see margin by customer group, the full price-drop table, and to request the 14-day audit of your real billing and cost data." Label: "Work email". Button: "Show the breakdown".

Honesty line: "Computed in your browser from the numbers you typed. No benchmark, no comparison to other companies, no stored data. Nothing is sent to us unless you submit your email."

5. Demo path under two minutes

Path: pick a model, type, read band and signal, open the gate. Unit 1M tokens, churn 2%.

Healthy. Flat, B 500, N 100, u_avg 2, u90 6, c 10, s 50. M(avg) = 500 - 70 = 430 (86%). M(p90) = 500 - 110 = 390. u* = 450 / 10 = 45, and 6 < 22.5. Blended = 1 - 7,000 / 50,000 = 86%.

Watch. Hybrid, B 300, p 20, I 10, c 10, s 50, N 50, u_avg 12, u90 30. u_bulk = 9 / 0.9 = 10. M(12) = 340 - 170 = 170. M(30) = 700 - 350 = 350. R_tot = 50 x (270 + 70) = 17,000, cost 8,500, blended 50%.

At risk. Flat, B 500, N 100, u_avg 20, u90 100, c 10, s 50, churn 3%. M(avg) = 500 - 250 = 250. M(p90) = 500 - 1,050 = -550. Blended 50%. Revenue at risk = 5,000 / 50,000 = 10%.

Negative. Flat, B 200, N 100, u_avg 20, u90 40, c 10, s 50. M(avg) = 200 - 250 = -50. M(p90) = 200 - 450 = -250. u* = 150 / 10 = 15. Blended = 1 - 25,000 / 20,000 = -25%.

6. What the prototype feeds back

PK-107 builds the formula module and takes these four sets as fixtures. PK-110 ships the page and gate. PK-102, the margin engine, replaces typed averages with per-customer margin from real billing and declared cost.

Open founder question from the design: none. F8 settled the gate: the result is free, the breakdown and audit request sit behind the work email.
