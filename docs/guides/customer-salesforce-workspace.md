# Using Pricekeel with Salesforce

Status: customer guide, 2026-08-01.

Pricekeel is a pricing decision layer on top of your Salesforce data. It reads
the Opportunities your authorized user can see, explains historical discount
patterns, flags open deals above a disclosed guardrail, and records the human
decision. It does not replace Salesforce, CPQ, or your approval policy.

## Before you start

Ask your Salesforce admin to install/approve the Pricekeel External Client App
and grant you its permission set. You also need a Pricekeel access code from
your Pricekeel contact.

For useful analysis, your Salesforce history should have:

- at least 30 closed won/lost Opportunities with usable booked and list value;
- one currency per Pricekeel workspace in V1;
- reliable `Amount` or an annualized booked-value field;
- Opportunity Products with list prices, or an annualized list-value field;
- at least one open Opportunity for Deal desk testing.

Thirty closed outcomes is the minimum for a directional view. Pricekeel labels
500+ closed outcomes per year as the target for stable operating guidance.

## Connect your Salesforce org

1. Go to `https://www.pricekeel.com/login` and enter your Pricekeel access code.
2. Open `https://www.pricekeel.com/crm`.
3. Select **Connect Salesforce**.
4. Sign in to the Salesforce org you intend to analyze. If your browser shows
   more than one org, verify the org name before continuing.
5. Review the requested access: API access and refresh/offline access.
6. Select **Allow**. Pricekeel returns you to the CRM workspace.
7. Confirm that the page says **Connected** and shows the expected Salesforce
   org.

You are connecting your own company's Salesforce org. You do not create a new
Salesforce account for Pricekeel, and you do not share your password with
Pricekeel.

## Map the fields

Open **Field mapping** and set the following in this order:

| Pricekeel field | What to select |
|---|---|
| Booked/quoted value | `Amount` or your annualized quoted/contracted value |
| Annualized list value | Your pre-discount annualized value, or leave blank only when Opportunity Products have reliable list prices |
| Segment | Your customer segment field; blank falls back to Account Type, then `Unknown` |
| Product | Your product/plan field; blank falls back to the first Opportunity Product family |
| Value metric | Seats, consumption, or hybrid field; otherwise choose the workspace default |
| Competitor | An optional boolean/indicator field |
| Approver | Optional approval-owner field |
| Term | Optional numeric term in months |

Set the policy threshold to your documented escalation threshold, then select
**Save mapping**. Mapping a field does not repair missing Salesforce data; the
readiness panel reports what was usable and what was excluded.

## Refresh and read the workspace

Select **Refresh analysis** whenever you want current results. Pricekeel queries
Salesforce again and analyzes the rows in memory.

### Executive

- **Price realization** is booked value divided by list value for won deals.
- **Win rate** is won divided by usable closed outcomes.
- **Open exceptions** counts open deals above the disclosed reference.
- **Price to retain** estimates booked value retained if flagged deals move to
  the displayed guardrail. It is a scenario, not a guaranteed outcome.

### Pricing / RevOps

Use this view to inspect realization by segment, historical discount bands,
the number of observations behind a recommendation, mapping quality, and deals
that deserve review. A historical relationship between discount and win rate
is correlational. Pricekeel does not claim the discount caused the outcome.

### Deal desk

Select an open Opportunity to see:

- the current requested discount;
- the recommended discount and reference basis;
- the estimated value retained at the recommendation;
- the historical evidence count and caveat;
- a link back to the Salesforce Opportunity.

If a competitor is recorded, Pricekeel shows it as context. Competitor evidence
does not change the numerical guardrail in V1.

## Run a pricing decision

### Accept the recommendation

1. Select the Opportunity.
2. Enter your name in **Actor**.
3. Optionally enable Salesforce Task writeback.
4. Select **Accept recommendation**.

### Request an override

1. Select the Opportunity.
2. Enter the rep/requester in **Actor**.
3. Enter the requested discount between 0% and 40%.
4. Explain the commercial reason in **Justification**.
5. Optionally enable Salesforce Task writeback.
6. Select **Request override**.

The requested percentage, requester, justification, recommendation, reference
basis, and evidence are recorded as an append-only event.

### Approve or reject

1. Change **Actor** to the approver. The requester cannot approve their own
   request under the V1 self-approval guard.
2. Select **Approve** or **Reject**.
3. If the Opportunity closed or left the open list before the decision, use
   **Overrides awaiting a decision, no longer in the open set**. The approver
   decides the terms that were originally requested; they do not re-enter or
   overwrite them.

Names are operator-entered in V1, not asserted by single sign-on. Use the
workflow for a controlled pilot, not as a substitute for a legally required
segregation-of-duties control.

## Salesforce Task writeback

When the checkbox is enabled, Pricekeel attempts to create a completed Task on
the Opportunity with the event, actor, requested and recommended discounts,
guardrail, reference basis, and justification. The Pricekeel decision can
succeed even when Salesforce writeback fails; the page reports the two results
separately so it never claims a Task was written when it was not.

## What Pricekeel stores

Pricekeel stores encrypted OAuth tokens, connection/sync metadata, your field
mapping and policy threshold, and the append-only decision evidence. Raw
Salesforce Opportunity rows are fetched server-to-server, analyzed in memory,
and not copied into a Pricekeel CRM table. Your Salesforce permissions and
sharing rules control which records Pricekeel can read.

## Common problems

| Message | What it means | What to do |
|---|---|---|
| Access code required | Your Pricekeel session is missing or expired | Sign in again at `/login` |
| Reconnect Salesforce | Salesforce revoked or expired the authorization | Select Connect Salesforce and authorize again |
| Under 30 usable closed | The evidence floor is not met | Fix list/booked data or mapping; do not treat it as a software error |
| Multiple currencies | V1 will not combine unlike currencies | Contact Pricekeel to scope separate currency analysis |
| Missing list value | No mapped list field and no usable Opportunity Product list price | Map the correct annualized list field or fix product data |
| Task writeback failed | The decision is logged, but Salesforce rejected the Task | Ask the admin to check Task create permission and retry explicitly |

## Disconnect

In `/crm`, select **Disconnect Salesforce**. Pricekeel attempts to revoke the
Salesforce token, then removes the stored connection and mapping. Contact your
Salesforce admin if you also want the installed package or user assignment
removed.
