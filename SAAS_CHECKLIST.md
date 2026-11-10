# SAAS_CHECKLIST.md — Converting the CMS into a multi-tenant SaaS

This repo is a **fork** of the Living Spring Church Management System
(`livingspring-v1`). The original repo keeps running Living Spring untouched.
This repo becomes the multi-tenant SaaS product.

> Agent: read `AGENTS.md` and every file in `docs/` first, then work through this
> checklist **in order**. Tick items as you finish them (`- [x]`), commit in small
> steps, and update `docs/` when a convention changes. Do not start a phase
> until the previous one is green (migrations apply, tests pass).

## Decisions already made (do not re-litigate)

- **Tenancy:** one shared Postgres DB, `church_id` on every tenant-owned table.
- **Users:** global identity (`users`), can belong to **multiple churches** via `memberships`.
- **Multi-branch:** hierarchy `church -> branches`. `branch_id` is nullable on tenant data;
  a membership may be church-wide or limited to one branch.
- **Billing:** **Seevplus** (Seevcash product), behind a provider-agnostic interface.
  API docs are NOT yet available. Do not guess endpoints; build the interface and a stub,
  and ask the owner for the docs before implementing the real provider.
- **Living Spring:** stays on the old repo/deployment. It may be imported into this SaaS
  later as tenant #1 (own domain, name, logo, colors). Nothing here may depend on the
  Living Spring database or credentials.
- **Existing data:** none to preserve in this repo; start from a fresh DB.

## Phase 0 — Safe setup (do this first)

- [x] Confirm `git remote -v` points to `veloxatechnologyltd-droid/church-saas`, not the old repo
- [x] Create a fresh `backend/.env` from `.env.example` with a **new** `DATABASE_URL` (never Living Spring's)
      (local isolated Postgres via `docker-compose.dev.yml`, port 55440; new generated `SECRET_KEY`)
- [ ] Use new/dev keys for Cloudinary, SendGrid, Arkesel, Seevplus (never Living Spring's live ones). Moolre is no longer needed: SMS is Arkesel
      (all left **blank** in `.env`, so no Living Spring key is in use; **owner will set up the keys later**)
- [x] Edit `render.yaml`: new service names, no references to Living Spring services/URLs
- [ ] Update `CORS_ORIGINS` for the new frontend URL
      (dev origins are set; `render.yaml` has placeholders; **waiting on the real frontend URL from owner**)
- [x] Verify backend boots and existing tests pass on the new DB (`alembic upgrade head`, `pytest`)
      (10 migrations apply to an empty DB; `/health/db` OK; 9 tests pass. `pytest` now lives in `backend/requirements-dev.txt`)
- [x] Write `docs/SAAS.md` (tenancy model, memberships, branches, roles, theming, billing interface) and link it from `AGENTS.md`

## Phase 1 — Tenancy data model

- [x] New models + migration: `churches` (name, slug, logo_url, brand colors, timezone, currency, status, plan, trial_ends_at, sms_sender_id, email_from, settings JSON)
- [x] New model: `branches` (church_id, name, address, is_main, is_active)
- [x] New model: `memberships` (user_id, church_id, role, branch_id nullable, is_active) with unique `(user_id, church_id)`
- [x] Keep `users` as global identity (email, password, is_active); move `role` out to `memberships`; keep `member_id` link per church (decide: on membership)
      (decided: `member_id` is on `memberships`. `users.role` / `users.member_id` stay as **deprecated** columns because auth still reads them; the Phase 2 migration drops them)
- [x] Add `church_id` (NOT NULL, indexed, FK) to every tenant table: announcements, attendance, audit, communication, donations (+funds/categories), events, families, groups, members, pastoral
      (19 tables incl. child tables; tenant->tenant references are composite `(col, church_id)` FKs so the DB rejects cross-church links)
- [x] Add nullable `branch_id` where data is per-branch (attendance, events, donations, pastoral, groups as decided); members get `home_branch_id`
- [x] Fix global unique constraints to be per-church: `groups.name` -> `(church_id, name)`, `donations.code` -> `(church_id, code)`, plus any others found
      (it is `donation_funds.code`, not `donations.code`; also `donation_funds.name` and `expense_categories.name`. `users.email` and `churches.slug` stay global)
- [x] Composite indexes on `(church_id, ...)` for hot queries
- [x] Single Alembic migration chain is clean from scratch (`alembic upgrade head` on empty DB)
      (chain is 000001-000013, additive. Tested: empty->head, no model drift, down-then-up round trip. Migration 000012 removes the ownerless seed rows the old chain inserted)

## Phase 2 — Auth and roles

- [x] Platform role `platform_admin` (owner only) separate from church roles; rename old `super_admin` to church-level `church_admin`
      (platform admin = `users.is_platform_admin` flag, read from the DB on every request; `superadmin` -> `church_admin` everywhere in the API)
- [x] Update `docs/AUTH.md` with the new role matrix (platform / church-wide / branch-scoped)
- [x] JWT carries `sub` (user), `church_id` (active church), `role`, `branch_id` (if scoped)
      (role/branch are re-read from the membership on every request; the claims are informational)
- [x] Login: authenticate user, return list of their churches; auto-select if only one
- [x] `POST /auth/switch-church` issues a new token for another church the user belongs to
- [x] `get_current_user` validates the membership is active for the token's `church_id`
- [x] New dependencies: `get_current_church`, `get_current_membership`, `require_roles(...)` updated for church roles
      (also `get_session_context`, `require_platform_admin`)
- [x] Invite flow: church admin invites an email into a church with a role/branch (existing user -> adds membership; new user -> set-password link)
      (SendGrid sender implemented (`EMAIL_BACKEND=sendgrid`); until the owner sets the key, emails only go to the server log)
- [x] Password reset flow (email) if not already present

## Phase 3 — Tenant isolation (highest risk, do not skip)

- [x] Central scoping helper so CRUD queries cannot forget the church filter (base repository/query helper, or SQLAlchemy event)
- [x] Branch scoping applied automatically for branch-scoped memberships
- [x] Refactor every `crud/*.py` to scope by `church_id` on read, create, update, delete
- [x] Refactor every `api/v1/*.py` to pass the church context; never trust `church_id` from request bodies
- [x] Reports/exports/dashboard aggregates scoped by church (and branch)
- [x] Audit log records `church_id` and actor
- [x] Postgres Row-Level Security as backstop: set `app.current_church` per request, policies on all tenant tables
      (migration 000015; `app.current_church` set per transaction; memberships/invitations excluded so login works. Superusers bypass RLS: never run the app as one)
- [x] **Isolation test suite:** two churches, log in as A, attempt to list/read/update/delete B's data on **every** endpoint; all must 404/403
      (`tests/test_isolation_all_endpoints.py` enumerates every id route from OpenAPI, checks list endpoints for leaks, and probes RLS with a non-superuser role)
- [x] Test: branch-scoped user cannot see other branches' data
- [x] Test: user in two churches sees only the active church's data

## Phase 4 — Per-tenant configuration and integrations

- [x] Move SMS sender ID, email from-address/name from `core/config.py` env vars to the `churches` record (env stays as platform defaults only)
      (Arkesel: the owner registers a sender ID per church. New churches start with none and use the platform default `ARKESEL_SENDER_ID` until one is set)
- [x] Per-church Cloudinary folder (`church_{id}/...`)
      (`services/storage.py`: `church_<id>/<folder>`, local fallback in dev)
- [x] SMS credits per church: balance, deduct on send, block when empty, ledger table
- [x] Remove hardcoded "Living Spring" / `livingsspring.org` from `config.py`, `main.py`, `.env.example`, `scripts/seed_superadmin.py`, `README.md`, `docs/*`
      (product name is now Ekklesia; `AGENTS.md` keeps its history note)
- [x] Replace `seed_superadmin.py` with a platform bootstrap script (creates `platform_admin`) and the onboarding flow below
      (bootstrap script done in Phase 2: `scripts/bootstrap_platform_admin.py`; the onboarding flow is Phase 5)
- [x] `GET/PUT /church/settings` (branding, contact, timezone, currency, sender ID)
- [x] Branch CRUD endpoints (`/branches`)

## Phase 5 — Onboarding and platform admin

- [x] Public signup: create church + first user + `church_admin` membership + main branch, start trial
- [x] Onboarding creates the church's standard funds and expense categories (existing `bootstrap` logic, now per church). The migrations no longer seed them
- [x] Unique church slug generation and validation (reserved words blocked)
- [x] Platform admin API: list/search churches, view usage, suspend/reactivate, change plan, impersonate (audited)
- [x] Suspended/expired church -> API returns a clear status; data stays, access is read-only or blocked per policy
- [x] Data export per church (members, donations, attendance as CSV/XLSX)

## Phase 6 — Frontend

- [x] Remove hardcoded branding from `index.html`, `tailwind.config.js`, `LoginPage.jsx`, `Sidebar.jsx`, `Navbar.jsx`, `DashboardPage.jsx`; read `docs/DESIGN.md` first and update it
- [x] Tenant theming: load church name/logo/colors from the API, apply as CSS variables (Tailwind uses the variables)
- [x] Tenant resolution: subdomain (`slug.yourapp.com`) or slug on login; decide and document (custom domains later)
      (decided: email login returns the user's churches; slug is used for public pages `/welcome/:slug`, `/pray/:slug`. Subdomains/custom domains later)
- [x] Church switcher in the navbar for users with multiple churches
- [x] Branch selector / branch filter for church-wide roles
      (branch-scoped users are filtered automatically server side; a church-wide branch filter UI is still a nice-to-have)
- [x] Signup + onboarding wizard (church details, logo, first branch, invite team)
- [x] Settings pages: church profile and branding, branches, team and roles, SMS credits, billing
- [x] Role-aware navigation using the new roles
- [x] Platform admin console (owner only): tenants, usage, plans, suspend
- [x] Marketing/landing page and pricing page (separate route or site)

## Phase 7 — Billing (Seevplus)

- [x] Seevplus API docs received (https://docs.seevcash.com); real provider implemented in `services/billing.py`
- [x] Models: `plans`, `subscriptions`, `invoices`, `payments`, `billing_events` (webhook log, idempotent)
- [x] `BillingProvider` interface (create checkout/payment link, verify webhook, cancel, status) with a `FakeProvider` for tests and a `SeevplusProvider` for real use
      (`services/billing.py`: Fake (dev/test), Manual (production: offline MoMo/bank, operator confirms), Seevplus stub)
- [x] Plan limits enforced in the backend (members, branches, users, SMS)
- [x] Trial, grace period, and read-only mode on non-payment
- [x] Webhook endpoint: signature verification, idempotency, replay-safe
- [ ] GHS pricing and mobile money support confirmed with Seevplus
      (docs confirm GHS mobile money (MTN, Telecel, AT) is live; **fees and minimum amounts are not documented: ask Seevplus**. Still to do: live keys, webhook endpoint registered, one sandbox end-to-end run)
- [x] Billing UI: current plan, upgrade/downgrade, invoices, payment history
- [x] Prepaid SMS credit top-up via the same provider

## Phase 8 — Hardening and launch

- [x] Rate limiting on auth and public signup
      (fixed-window counters per IP in Postgres, shared by every serverless instance: login, reset, invites, signup, public forms)
- [x] Error monitoring (e.g. Sentry) and structured logging with `church_id`
      (structured JSON request logs with request id and church id; Sentry integrated and privacy-scrubbed, **active once the owner sets `SENTRY_DSN`**)
- [x] Per-tenant usage metrics (members, SMS sent, storage)
- [x] Per-church export/delete (account closure) flow
      (admin closes the account, 30-day grace, scheduled permanent purge; platform admin can reopen; see `docs/DEPLOYMENT.md`)
- [ ] Backups and a tested restore (procedure documented in `docs/DEPLOYMENT.md`; **owner must run one restore test**)
- [ ] Terms of Service, Privacy Policy; Ghana Data Protection Act review (member and donation data is sensitive)
      (drafts are live at `/terms` and `/privacy`, acceptance is required at signup and recorded; **a Ghanaian lawyer must review the text and the DPC registration is the owner's to do**)
- [x] Security review (`/security-review`) with focus on tenant isolation and the invite/impersonation flows
      (done: own review plus an independent reviewer's report; every finding was fixed and has a regression test in `tests/test_closure.py::TestSecurityReviewFixes`; see `docs/AUTH.md` "Enforced access rules")
- [x] Render Blueprint for the API and cron jobs (`render.yaml`), frontend stays on Vercel (`docs/DEPLOYMENT.md`)
- [ ] Staging environment separate from production
      (runbook in `docs/STAGING.md`; **the Neon branch and the two Vercel projects are for the owner to create**)
- [ ] Pilot with 2-3 churches before public launch

## Phase 9 — Optional: bring Living Spring in as tenant #1

- [ ] Write a one-off import script: Living Spring DB -> this DB under a new `church` (map users to global users plus memberships)
- [ ] Re-create Living Spring's 10 departments under that church (they were removed from the migration chain in Phase 1)
- [ ] Custom domain support (e.g. `app.livingspring.org`) with Living Spring's name, logo, colors and SMS sender ID
- [ ] Dry run on a copy of the production data; verify counts and totals
- [ ] Cutover plan and rollback plan; keep the old deployment until verified
