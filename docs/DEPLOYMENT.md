# DEPLOYMENT.md — Production setup

Production runs on Vercel as two projects plus a managed Postgres:

| Piece | Vercel project | Root dir | URL |
|---|---|---|---|
| Frontend (React/Vite) | `ekklesia-church` | `frontend/` | https://ekklesia-church.vercel.app |
| API (FastAPI, Python 3.12 serverless) | `ekklesia-api` | `backend/` | https://ekklesia-api.vercel.app |
| Database | Neon Postgres (Vercel Marketplace, linked to `ekklesia-api`) | – | `DATABASE_URL` env var |

`render.yaml` is kept as an alternative (long-running server + cron job) if you prefer Render.

## How the API runs on Vercel

- `backend/api/index.py` exposes the FastAPI `app`; `backend/vercel.json` rewrites every path to it.
- `backend/.python-version` pins Python 3.12 (Vercel cannot use the `runtime.txt` patch version).
- The filesystem is read-only: uploads (logos, member photos) **require Cloudinary** (`CLOUDINARY_*`).
- Vercel Cron calls `GET /api/v1/internal/cron/reminders` daily (Hobby plan limit) with
  `Authorization: Bearer $CRON_SECRET`. For on-time weekly SMS reminders, also point an external
  scheduler (e.g. cron-job.org, every 10 minutes) at that URL with the same header. Reminders up to
  `REMINDER_CATCHUP_MINUTES` (180) late are still sent, once.

## Environment variables

API (`ekklesia-api`, Production):

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

Frontend (`ekklesia-church`): `VITE_API_BASE_URL=https://ekklesia-api.vercel.app/api/v1` and `VITE_SUPPORT_EMAIL` (the contact address printed on the Terms and Privacy pages).

Once signed in as the platform admin, `GET /api/v1/platform/readiness` lists every integration that is still unconfigured (no secrets), and the API logs `NOT READY FOR PRODUCTION` lines at startup for each required one.

## Release procedure

```bash
# 0. Back up first (see Backups below)
# 1. Migrations (from your machine, against production). ALWAYS before deploying the API:
#    the models read columns added by the newest migrations.
cd backend && DATABASE_URL='<prod url>' alembic upgrade head

# 2. Deploy
cd backend  && vercel deploy --prod
cd frontend && vercel deploy --prod

# 3. Smoke test
curl https://ekklesia-api.vercel.app/health/db
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

Vercel Cron (see `backend/vercel.json`) calls, with `Authorization: Bearer $CRON_SECRET`:

* `/api/v1/internal/cron/reminders`: daily 06:00 UTC (Hobby plan limit; add an external scheduler such as cron-job.org every 10 minutes for on-time weekly reminders).
* `/api/v1/internal/cron/purge-closed`: daily 03:30 UTC; permanently deletes churches whose closure retention period has ended.

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

See `docs/STAGING.md`: a separate Vercel project pair and Neon branch, `ENVIRONMENT=staging`.
