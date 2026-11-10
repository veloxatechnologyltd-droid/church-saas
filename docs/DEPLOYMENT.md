# DEPLOYMENT.md — Production setup

Production runs as three pieces:

| Piece | Where | Root dir | Notes |
|---|---|---|---|
| Frontend (React/Vite) | Vercel project `ekklesia-church` | `frontend/` | https://ekklesia-church.vercel.app |
| API (FastAPI, gunicorn + uvicorn workers) | **Render** web service `ekklesia-api` | `backend/` | defined in `render.yaml` (Blueprint) |
| Scheduled jobs | Render cron jobs `ekklesia-reminders` (every 10 min), `ekklesia-purge-closed` (daily) | `backend/` | same Blueprint |
| Database | Neon Postgres (region eu-central-1) | – | `DATABASE_URL`, shared by the three Render services |

The Vercel project `ekklesia-api` (the earlier serverless deployment) is retired once Render is
verified; see "Cutover from the Vercel API" below.

## Backend on Render (first time)

1. Merge `saas-conversion` into `main` (or keep the branch and leave `branch: saas-conversion` in
   `render.yaml`; Render deploys whatever branch the services name).
2. Render dashboard -> **New -> Blueprint** -> connect `veloxatechnologyltd-droid/church-saas`.
   Render reads `render.yaml` and creates the web service, both cron jobs and the `ekklesia-shared`
   environment group. It generates `SECRET_KEY` and `CRON_SECRET` itself.
3. Fill the values it asks for (every `sync: false` in the file):
   * `DATABASE_URL`: the Neon connection string (the **new** password, after rotation).
   * `CORS_ORIGINS` and `FRONTEND_BASE_URL`: `https://ekklesia-church.vercel.app` (+ custom domain).
   * `SENDGRID_API_KEY`, `FROM_EMAIL` (a sender verified in SendGrid).
   * `ARKESEL_API_KEY`, `CLOUDINARY_*`.
   * Optional: `SEEVPLUS_API_KEY`, `BILLING_WEBHOOK_SECRET` (leave `BILLING_PROVIDER=manual` until then),
     `SENTRY_DSN`.
4. The first deploy runs `alembic upgrade head` (preDeployCommand) before traffic switches, then
   Render health-checks `/health/db`. Note the service URL, e.g. `https://ekklesia-api.onrender.com`.
5. In the **frontend** Vercel project set `VITE_API_BASE_URL=https://<render url>/api/v1` and
   `VITE_SUPPORT_EMAIL`, then redeploy it (`cd frontend && vercel deploy --prod --yes`).
6. Sign in to the frontend as the platform admin and open `GET <render url>/api/v1/platform/readiness`:
   every required check must be OK.
7. If you use Seevplus: register `<render url>/api/v1/billing/webhooks/seevplus` for `payment.succeeded`
   and `payment.failed`.

Render specifics worth knowing:
* `plan: starter` never sleeps; the free plan spins down when idle (slow first request, missed reminders).
* The disk is ephemeral: uploads (logos, member photos) require Cloudinary.
* Render's load balancer appends the client address to `X-Forwarded-For`; the API reads it counted from
  the right (`TRUSTED_PROXY_HOPS=1`), so a client cannot spoof its IP to dodge rate limits.
* Reminders run from the cron job `scripts/run_reminders.py` every 10 minutes (Africa/Accra aware);
  the daily purge runs `scripts/purge_closed.py`. The `/internal/cron/*` HTTP endpoints stay available
  (protected by `CRON_SECRET`) for any external scheduler.

## Cutover from the Vercel API

Only after the Render API passes the readiness check and a sign-in test from the frontend:
point the frontend at Render (step 5 above), move the Seevplus webhook URL, then remove the
`ekklesia-api` Vercel project (or just stop using it). Both share the same Neon database, so no data moves.
`backend/vercel.json` and `backend/api/index.py` can then be deleted from the repo.

## Environment variables

API (Render service `ekklesia-api` + group `ekklesia-shared`; the same names apply on Vercel):

| Variable | Value |
|---|---|
| `DATABASE_URL` | Neon connection string (pooled is fine; the app uses transaction-local settings only) |
| `SECRET_KEY` | long random string (set) |
| `ENVIRONMENT` | `production` (hides `/docs`, refuses default secret and the fake billing provider) |
| `CORS_ORIGINS`, `FRONTEND_BASE_URL` | `https://ekklesia-church.vercel.app` (+ custom domain later) |
| `BILLING_PROVIDER` | `manual` until live Seevplus keys exist (operator confirms payments in `/platform`); then `seevplus` with `SEEVPLUS_API_KEY` and `BILLING_WEBHOOK_SECRET` |
| `SMS_PROVIDER`, `ARKESEL_API_KEY` | `arkesel` + **new** key (blank = sending fails with a clear 503) |
| `EMAIL_BACKEND`, `SENDGRID_API_KEY`, `FROM_EMAIL`, `FROM_NAME` | `sendgrid` + key + a sender verified in SendGrid. `console` only logs emails (invites and password resets are NOT delivered) |
| `RATE_LIMIT_ENABLED`, `RATE_LIMIT_BACKEND` | `true`, `database` (counters in Postgres, shared by all serverless instances) |
| `CLOSURE_RETENTION_DAYS` | `30` (default): how long a closed church's data is kept before permanent deletion |
| `FINANCIAL_RETENTION_YEARS` | `7` (default): years paid invoices stay in the anonymised archive after a church is purged |
| `LEGAL_VERSION` | version stamp stored with each signup's acceptance of the Terms/Privacy text |
| `CRON_SECRET` | random (set) |
| `LOG_JSON` | `true` |
| `SENTRY_DSN` | optional; enables Sentry error reports (no request bodies, cookies, auth headers or user details are sent; events are tagged with opaque `church_id` and `request_id`) |
| `CLOUDINARY_*` | required for uploads |

Frontend (`ekklesia-church`): `VITE_API_BASE_URL=https://<render url>/api/v1` and `VITE_SUPPORT_EMAIL` (the contact address printed on the Terms and Privacy pages).

Once signed in as the platform admin, `GET /api/v1/platform/readiness` lists every integration that is still unconfigured (no secrets), and the API logs `NOT READY FOR PRODUCTION` lines at startup for each required one.

## Release procedure

Backend: Render auto-deploys the configured branch on every push; the pre-deploy step runs
`alembic upgrade head` first, and a failed migration aborts the release (the old version keeps serving).
Take a dump before risky migrations (see Backups below).

```bash
# Frontend (Vercel)
cd frontend && vercel deploy --prod --yes

# Smoke test
curl https://<render url>/health/db
```

First time only: create the platform admin with
`PLATFORM_ADMIN_EMAIL=... PLATFORM_ADMIN_PASSWORD=... DATABASE_URL=... python scripts/bootstrap_platform_admin.py`.

## Database role and row-level security

RLS policies are a backstop that only applies to roles that are **not** superusers and do not have
`BYPASSRLS`. Neon's default owner role is not a superuser, and the tables are created with
`FORCE ROW LEVEL SECURITY`, so the policies apply to the app. Never connect the app as a superuser.

## Backups

Neon keeps point-in-time history (7 days on the free plan, longer on paid plans). Before each risky
migration also take a logical dump: `pg_dump "$DATABASE_URL" -Fc -f ekklesia-$(date +%F).dump`, and
test restoring it into a scratch database (`pg_restore -d <scratch url> ekklesia-....dump`).
Per-church export is available to church admins in Settings → Data export.

## Scheduled jobs

Render cron jobs (see `render.yaml`) run `scripts/run_reminders.py` every 10 minutes and
`scripts/purge_closed.py` daily at 03:30 UTC. They share the `ekklesia-shared` environment group, so they
see the same database and SMS settings as the API. (On the old Vercel deployment the same work was
triggered through `/api/v1/internal/cron/*` with `Authorization: Bearer $CRON_SECRET`; those endpoints
still work with any external scheduler.)

## Account closure and data deletion

A church admin closes the account in Settings (password and church URL name required). Access stops
immediately; data is kept `CLOSURE_RETENTION_DAYS` days, during which a platform admin can reopen it
(`POST /platform/churches/{id}/reopen`). Afterwards the purge job deletes every row owned by the
church, its Cloudinary folder (`church_<id>/`) and users who belong to no other church. Two records
survive, neither with personal data: a `church_purged` entry (name, slug, row counts) in
`platform_events`, and one `financial_archive` row per **paid** invoice (church name, invoice number,
amount, payments, dates) for accounting and tax record-keeping. The archive is deleted by the same
job after `FINANCIAL_RETENTION_YEARS` (default 7; confirm the period your accountant needs).

## Staging

See `docs/STAGING.md`: a separate Render service, Vercel frontend project and Neon branch, `ENVIRONMENT=staging`.
