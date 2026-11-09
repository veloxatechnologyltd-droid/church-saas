# SAAS.md — Multi-Tenant Architecture

This repo is the multi-tenant SaaS fork of the Living Spring Church Management
System. The original Living Spring repo and deployment are separate and are never
touched from here. **Nothing in this repo may use the Living Spring database,
credentials, or API keys.**

`SAAS_CHECKLIST.md` is the master plan and records the decisions below. This file
describes the resulting architecture and conventions; update it whenever one changes.

> Status: Phase 0 (safe setup) is done. Sections marked **(planned)** describe the
> target design for later phases and are not implemented yet.

---

## Tenancy model

- **One shared Postgres database.** Every tenant-owned table carries `church_id`
  (NOT NULL, indexed, FK to `churches`). **(planned: Phase 1)**
- **A church is the tenant.** All church data (members, attendance, finance,
  groups, events, communication, pastoral care, audit) belongs to exactly one church.
- **Isolation is enforced in layers (Phase 3):**
  1. The active church comes from the verified JWT, never from a request body,
     query string, or path.
  2. A central scoping helper applies `church_id` on every read, create, update
     and delete, so a CRUD function cannot forget the filter.
  3. Postgres Row-Level Security (`app.current_church` set per request) is the
     backstop if application code is wrong.
  4. An isolation test suite proves a user in church A gets 404/403 on church B's
     data on every endpoint.
- Cross-tenant lookups return **404**, not 403, so existence is not leaked.

## Users, memberships and branches (planned: Phases 1–2)

- `users` is a **global identity**: email, password hash, active flag. One person
  has one login regardless of how many churches they belong to.
- `memberships` links a user to a church: `(user_id, church_id, role, branch_id
  nullable, is_active)`, unique on `(user_id, church_id)`. The role lives here,
  not on the user.
- **Branches:** hierarchy is `church -> branches`. `branch_id` is nullable on
  tenant data. A membership is either **church-wide** (`branch_id` NULL) or
  **limited to one branch**. Each church gets a main branch at signup.
- The JWT carries `sub` (user), `church_id` (active church), `role`, and
  `branch_id` when scoped. `POST /auth/switch-church` issues a new token for
  another church the user belongs to.

### Roles

| Level | Role | Scope |
|---|---|---|
| Platform | `platform_admin` | Product owner only. Operates the platform; never a church role. |
| Church | `church_admin` | Everything inside one church (replaces the old `superadmin`). |
| Church | `secretary`, `finance`, `group_leader`, `member` | Unchanged capabilities, now per church. |

Church roles can be church-wide or branch-scoped. The full matrix is written into
`docs/AUTH.md` in Phase 2.

## Open decisions for Phase 1

These were left open by the checklist and are settled in the Phase 1 plan:

- Whether `member_id` (link from a login to a member profile) lives on
  `memberships` (a member profile is per church) or on `users`.
- Exactly which tables get `branch_id` (attendance, events, donations, pastoral,
  groups) and which stay church-wide.

## Tenant configuration (planned: Phase 4)

Per-church settings live on the `churches` record, not in environment variables:
name, slug, logo, brand colors, timezone, currency, SMS sender ID, email
from-address, and a `settings` JSON. Environment variables remain only as
**platform defaults**. Uploads use a per-church Cloudinary folder
(`church_{id}/...`). SMS is prepaid per church with a credit ledger.

## Theming (planned: Phase 6)

The frontend loads the church name, logo and colors from the API and applies them
as CSS variables that Tailwind reads. No church's branding is hardcoded.
Tenant resolution (subdomain vs. slug on login) is decided and documented in
Phase 6; custom domains come later.

## Billing (planned: Phase 7)

Billing provider is **Seevplus** (a Seevcash product), behind a
provider-agnostic `BillingProvider` interface (create checkout/payment link,
verify webhook, cancel, status). A `FakeProvider` is used for tests. The real
`SeevplusProvider` is **blocked until the owner supplies the Seevplus API
documentation** — do not guess endpoints. Webhooks must verify signatures and be
idempotent.

---

## Local development

The dev database is an isolated Postgres container defined in
`docker-compose.dev.yml` (host port **55440**, user/db `church_saas`). It must stay
separate from any other project's database.

```bash
# 1. Database
docker compose -f docker-compose.dev.yml up -d

# 2. Backend (Python 3.11)
cd backend
python3.11 -m venv venv && source venv/bin/activate   # or: uv venv --python 3.11 venv
pip install -r requirements.txt
cp .env.example .env        # then set a NEW SECRET_KEY; keep third-party keys blank
alembic upgrade head
uvicorn app.main:app --reload

# 3. Tests
python -m unittest discover -s tests -t .
```

Reset the database from scratch (destroys all local data):
`docker compose -f docker-compose.dev.yml down -v`.

### Conventions

- `backend/.env` is gitignored. Never copy values from the Living Spring `.env` or
  production `DATABASE_URL`.
- Third-party keys (Cloudinary, SendGrid, Arkesel, Moolre) must be new dev keys,
  or blank. Blank means the feature is disabled locally.
- `DATABASE_URL` may be written as `postgresql://...`; `config.py` normalises it to
  the `psycopg2` driver (SQLAlchemy 2.1 would otherwise pick the uninstalled
  `psycopg` v3).
- The `alembic upgrade head` chain must always apply cleanly to an **empty**
  database.
