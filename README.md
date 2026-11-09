# Ekklesia — multi-church management SaaS

Ekklesia is a multi-tenant church management platform built for growing ministries in Ghana and beyond.
Each church signs up, gets its own branded workspace, and manages its people, services, giving and outreach,
across one or many branches.

## What churches get

| Area | Highlights |
|---|---|
| Members & families | Profiles, families, photo, status, baptism/membership class, birthdays, CSV/XLSX export |
| Attendance | Service sessions per branch, quick marking, **QR self check-in** by phone number, absence risk alerts |
| Giving & finance | Funds, service batches, tithes/offerings, expenses, monthly/annual reports, **member giving statements** |
| Pledge campaigns | Building projects/harvest drives with targets, pledges, instalment payments that flow into finance |
| First-timers | **Public welcome card** (QR), visitor pipeline (new → contacted → returning → converted), one-click convert to member |
| Prayer requests | **Public prayer form**, confidential flag, prayer team workflow |
| Pastoral care | Follow-up logs, assignment, due dates, attendance-driven care alerts |
| Groups & events | Departments with leaders, events with registrations and reminders |
| Communication | Bulk SMS with **prepaid SMS credits** and the church's own sender ID, weekly scheduled reminders, announcements |
| Multi-branch | Church-wide and branch-scoped roles; branch users only see their branch |
| Team & roles | Invitations, `church_admin`, `secretary`, `finance`, `group_leader`, `member` |
| Branding | Church name, logo and colours applied across the app and public pages |

Platform side: self-service signup with a 14-day trial, plans with enforced limits (Free / Growth / Kingdom /
Enterprise, priced in GHS), read-only mode after a lapsed trial or payment, billing behind a provider interface
(Seevplus pending API docs; a fake provider is used for development), signed idempotent webhooks, and a platform
admin console (stats, MRR, suspend/reactivate, plan changes, SMS credit grants, audited impersonation).

## Architecture

- **Backend:** FastAPI, SQLAlchemy 2, Alembic, PostgreSQL — `backend/`
- **Frontend:** React 18, Vite, Tailwind, React Query, Zustand — `frontend/`
- **Tenancy:** one database, `church_id` on every tenant table, enforced in three layers: automatic ORM scoping
  (`backend/app/db/tenancy.py`), composite same-church foreign keys, and Postgres row-level security. An
  endpoint-wide isolation test suite proves church A cannot read or change church B's data.

Read `docs/SAAS.md` for the full architecture and `docs/API_SAAS.md` for the SaaS endpoints.

## Local development

```bash
# 1. Database (isolated Postgres on port 55440)
docker compose -f docker-compose.dev.yml up -d

# 2. Backend
cd backend
python3.11 -m venv venv && source venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env              # set SECRET_KEY; SMS_PROVIDER=console for local
alembic upgrade head
python scripts/seed_demo.py       # synthetic demo churches (use --reset to rebuild)
uvicorn app.main:app --reload     # http://localhost:8000/docs

# 3. Frontend
cd ../frontend
npm install
echo "VITE_API_BASE_URL=http://localhost:8000/api/v1" > .env.local
npm run dev                       # http://localhost:5173

# 4. Tests (real Postgres)
cd ../backend && pytest -q
```

### Demo logins (password `Demo@12345`)

| Email | Role |
|---|---|
| `owner@ekklesia.demo` | Platform admin (console at `/platform`) |
| `pastor@grace.demo` | Church admin, Grace Covenant (also in Living Waters — church picker) |
| `secretary@grace.demo` / `finance@grace.demo` / `youth@grace.demo` | Secretary / Finance / Group leader |
| `tema@grace.demo` | Admin limited to the Tema branch |
| `admin@livingwaters.demo` | Church admin, Living Waters (on trial) |

All demo people, phone numbers and emails are invented.

## Deployment

See `docs/DEPLOYMENT.md`.
