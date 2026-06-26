# Neon cutover runbook

Migrating Pricekeel's database from Supabase (paused/dead) to Neon, preserving
existing rows. The code on branch `neon-migration` already targets Neon via a
single `DATABASE_URL`; this is the operational sequence to flip prod over.

One `DATABASE_URL` (the **pooled** connection string) serves both tiers: the web
app (Vercel, `@neondatabase/serverless`) and the API (Render, `psycopg`).

## 0. Order matters

Do steps 1-5 (schema + data + env) BEFORE merging the branch. The new code fails
fast in production when `DATABASE_URL` is unset, so the env var must exist first.

## 1. Restore Supabase (temporary, to export)

You chose to preserve existing rows, so the paused project has to come back just
long enough to dump it. Supabase dashboard -> project `jzhnjxlsmdghcipzvjke` ->
Restore. Wait until `https://jzhnjxlsmdghcipzvjke.supabase.co` resolves again.

Grab its **direct** connection URI: Project Settings -> Database -> Connection
string -> URI (session mode). Call it `$SUPABASE_DB_URL`.

## 2. Create the Neon project

At neon.com, create a project (region: US East to match the rest of the stack).
Copy TWO connection strings from the dashboard:

- **Pooled** (host contains `-pooler`): this becomes `DATABASE_URL` in the app.
- **Direct** (no `-pooler`): use this for schema load + data restore. Call it
  `$NEON_DIRECT_URL`. (Restores can misbehave through the pooler.)

## 3. Create the schema in Neon

```bash
psql "$NEON_DIRECT_URL" -f neon/schema.sql
```

(Or paste `neon/schema.sql` into the Neon SQL editor.)

## 4. Copy the data (Supabase -> Neon)

Needs Postgres client tools (`pg_dump`/`psql`) >= the server version. If you do
not have them on Windows, use Docker: prefix each command with
`docker run --rm postgres:17 ` and pass the URLs as arguments.

Dump the three tables data-only, in dependency order (leads before access_codes,
which references it):

```bash
pg_dump "$SUPABASE_DB_URL" --data-only --no-owner --no-privileges \
  --table=public.leads --table=public.access_codes --table=public.decision_log \
  > pricekeel_data.sql

psql "$NEON_DIRECT_URL" --single-transaction -f pricekeel_data.sql
```

If an FK error appears, load `leads` first on its own, then the other two.

## 5. Verify the copy

```bash
psql "$NEON_DIRECT_URL" -c \
  "select 'leads' t, count(*) from leads
   union all select 'access_codes', count(*) from access_codes
   union all select 'decision_log', count(*) from decision_log;"
```

Compare to the same query against `$SUPABASE_DB_URL`. Counts must match.

## 6. Set env, remove Supabase vars

Set `DATABASE_URL` = the **pooled** Neon string in BOTH:

- Vercel (web project) -> Settings -> Environment Variables. Delete
  `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`.
- Render (API service) -> Environment. Delete the same two if present.

## 7. Ship the code

Merge `neon-migration` -> `main` (PR). Vercel and Render redeploy on merge. If
Render does not pick up the new env automatically, redeploy it manually.

## 8. Verify live (Claude does this)

After deploy, the live checks: `POST /api/lead` returns 200 (was 500), magic-link
recovery works, and a `POST /exceptions` returns `persisted: true` (decision_log
write reached Neon).

## 9. Decommission Supabase

Once Neon is verified live: pause or delete the Supabase project, and remove the
`SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` GitHub Actions secrets (the
keep-alive workflow that used them is already deleted).

## Follow-up worth doing

The original outage went unnoticed for weeks because nothing watched the lead
path end to end. Consider a small synthetic uptime check (a scheduled GET on a
new DB-connectivity health route) that alerts on failure. This catches a dead
database regardless of provider, which a keep-alive ping never did.
