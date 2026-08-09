# Pricekeel 2GP packaging runbook

Status: active operator manual, 2026-08-08. Owner: Pricekeel founder/admin.

This is the concrete build for the release gate named in
`salesforce-integration-runbook.md` section 3 ("Package for customer orgs").
It turns the Pricekeel External Client App (ECA) into a distributable
second-generation managed package with an install URL a customer admin can use.
The DX project lives in `salesforce/`.

Complete this once before connecting the first external customer org. The
2026-08-01 Developer Edition connection proves the OAuth flow; it does not make
the app installable elsewhere.

## 0. Prerequisites (one time)

- Salesforce CLI installed: `sf --version`.
- A durable source org (never delete it while subscribers exist) with **Dev Hub
  enabled** (Setup -> Dev Hub -> Enable).
- A **registered namespace** linked to that Dev Hub. Managed packages require
  one. Create a namespace org, register the namespace, and link it in Dev Hub
  (Setup -> Namespace Registries). Then set `"namespace"` in
  `salesforce/sfdx-project.json`.
- The ECA already created in the source org with distribution state `Packaged`
  and the OAuth settings from the integration runbook (callback
  `https://www.pricekeel.com/api/salesforce/oauth/callback`, scopes `api` and
  `refresh_token`/`offline_access`, PKCE required, no `full`).

## 1. Authenticate the Dev Hub

```bash
sf org login web --alias devhub --set-default-dev-hub
```

## 2. Retrieve the ECA into the project

```bash
cd salesforce
sf project retrieve start \
  --metadata "ExternalClientApplication:Pricekeel" \
  --target-org devhub
```

Review the retrieved files under `force-app/main/default/`. Confirm no consumer
secret was written to source. Commit the ECA metadata and the permission set.

## 3. Create the package (once)

```bash
sf package create \
  --name Pricekeel \
  --package-type Managed \
  --path force-app \
  --target-dev-hub devhub
```

This writes a `packageAliases` entry and a package Id (`0Ho...`) into
`sfdx-project.json`. Commit that change.

## 4. Create a beta version

```bash
sf package version create \
  --package Pricekeel \
  --installation-key-bypass \
  --code-coverage \
  --wait 30 \
  --target-dev-hub devhub
```

Use `--installation-key "<key>"` instead of `--installation-key-bypass` if you
want to gate installs. The command returns a subscriber package version Id
(`04t...`). That Id is what customers install.

## 5. Install and test in a clean org

Use a scratch org or a throwaway sandbox that is NOT the source org.

```bash
sf package install \
  --package 04t... \
  --target-org <test-org-alias> \
  --wait 30 \
  --publish-wait 10
```

Then run the install-side test matrix (mirrors the acceptance checklist in the
integration runbook):

1. Assign the `Pricekeel Integration` permission set to a test integration user.
2. Grant field-level security on that org's mapped fields to the permission set.
3. From Pricekeel `/crm`, Connect Salesforce as that user, verify the org and
   the two scopes, and Allow.
4. Refresh analysis; confirm fetched/usable counts return.
5. If writeback is enabled, confirm a completed Task is created on an
   Opportunity.
6. Force a token refresh (or wait for expiry); confirm reconnect works.
7. Uninstall the package cleanly:
   `sf package uninstall --package 04t... --target-org <test-org-alias> --wait 20`.

Do not promote until install, authorize, refresh, writeback (if used), and
uninstall all pass.

## 6. Promote to released

```bash
sf package version promote --package 04t... --target-dev-hub devhub
```

## 7. Record the install URL

```
https://login.salesforce.com/packaging/installPackage.apexp?p0=04t...
```

Store the install URL and the `04t...` version Id in the customer onboarding
record. Send the install URL plus the requested permission list to the customer
admin per the integration runbook's per-customer onboarding steps.

## Rotation and versioning notes

- Each new release is a new `sf package version create` + promote. Ship fixes as
  new versions; subscribers upgrade in place.
- Rotating the ECA consumer secret is an org/Vercel operation (see the
  integration runbook "Rotation and offboarding"), not a package rebuild.
- Never delete the source org or the package while any subscriber depends on it.
