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
| `EMAIL_BACKEND` | `console` (invites/resets are only logged until a mail provider is added) |
| `CRON_SECRET` | random (set) |
| `LOG_JSON` | `true` |
| `CLOUDINARY_*` | required for uploads |

Frontend (`ekklesia-church`): `VITE_API_BASE_URL=https://ekklesia-api.vercel.app/api/v1`.

## Release procedure

```bash
# 1. Migrations (from your machine, against production)
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
