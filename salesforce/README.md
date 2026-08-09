# Pricekeel Salesforce DX project (2GP managed package)

This is the Salesforce DX project that packages the Pricekeel External Client
App (ECA) so customer orgs can install it. It is the release gate the
integration runbook calls out: a Local ECA works only in its source org, and
only a packaged ECA is distributable to arbitrary customer orgs.

- `sfdx-project.json` — package definition (`Pricekeel`, API 67.0). Set the
  `namespace` after registering one against your Dev Hub (see runbook).
- `force-app/main/default/externalClientApps/` — the ECA, retrieved from your
  source org (not hand-authored). See that directory's README.
- `force-app/main/default/permissionsets/Pricekeel_Integration.permissionset-meta.xml`
  — least-privilege access for the integration user (read Opportunity/Account,
  create Task for optional writeback). Field-level security for mapped fields is
  granted per customer, post-install.

## What this does NOT contain
No Apex, no LWC, no consumer secret. Pricekeel is an external OAuth connector:
Salesforce data is read server-side by the Next.js app via the API, and the
only thing installed in the customer org is the ECA (OAuth app) plus this
permission set.

## Build and release
Follow `docs/ops/salesforce-2gp-packaging.md` end to end. In short: retrieve the
ECA, register/set the namespace, `sf package create`, `sf package version
create`, install and test in a scratch/sandbox org, then promote and record the
install URL in the customer onboarding record.

## Prerequisites
- Salesforce CLI (`sf`) installed.
- A durable source org with Dev Hub enabled.
- A registered namespace linked to that Dev Hub (managed packages require one).
