# Pricekeel packaging runbook (unlocked package)

Status: active operator manual. Corrected 2026-08-22. Owner: Pricekeel founder/admin.

> **STEPS 1 THROUGH 4 ARE ALREADY DONE. Do not re-run them.**
>
> Commit `f04b86a` (2026-08-08) created the package and its first version:
>
> | | |
> |---|---|
> | Package | `Pricekeel` (**Unlocked**), `0Hoak0000004szVCAQ` |
> | Version | `0.1.0-1`, subscriber id `04tak000000aPeDAAU` |
>
> Both ids are recorded in `salesforce/sfdx-project.json` under `packageAliases`.
> Re-running `sf package create` produces a **second** package and orphans that
> alias. The live work starts at **step 5 (install and test in a clean org)**,
> which has never been run.
>
> This doc previously described a **managed** package requiring a registered
> namespace. That was wrong: the package that exists is unlocked and
> `sfdx-project.json` carries `"namespace": ""`. Corrected 2026-08-22.

This is the concrete build for the release gate named in
`salesforce-integration-runbook.md` section 3 ("Package for customer orgs").
It turns the Pricekeel External Client App (ECA) into a distributable
**unlocked** package with an install URL a customer admin can use.
The DX project lives in `salesforce/`.

Complete this once before connecting the first external customer org. The
2026-08-01 Developer Edition connection proves the OAuth flow; it does not make
the app installable elsewhere.

## 0. Prerequisites (one time)

- Salesforce CLI installed: `sf --version`.
- A durable source org (never delete it while subscribers exist) with **Dev Hub
  enabled** (Setup -> Dev Hub -> Enable).
- **No namespace is required.** Unlocked packages do not need one, and
  `salesforce/sfdx-project.json` correctly carries `"namespace": ""`. Do not
  register a namespace org; it is work with no payoff here. A namespace would
  only be needed if this became a managed package for AppExchange listing,
  which is explicitly not the distribution model (see the integration runbook).
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
  --package-type Unlocked \
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

> **THIS IS THE NEXT ACTION AND IT HAS NEVER BEEN RUN.**
>
> `salesforce/config/project-scratch-def.json` was added on 2026-08-08 "for
> package install testing" and no result has been recorded in git or in
> `docs/`. Until this passes, the distribution model is unproven: we do not
> know whether `orgScopedExternalApp = 00Dak000016fI9t:Pricekeel` in the ECA
> metadata pins the app to its source org at runtime. Commit the outcome here
> when it is run, pass or fail.

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

> Check first whether this already happened:
> `sf package version list --target-dev-hub devhub` and read `IsReleased`.
> An unpromoted beta version **cannot** be installed into a customer
> production org, only scratch, sandbox, or Developer Edition orgs. No promote
> is recorded in git, so assume beta until confirmed.

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
