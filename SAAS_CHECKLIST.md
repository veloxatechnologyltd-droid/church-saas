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
- [ ] Use new/dev keys for Cloudinary, SendGrid, Arkesel, Moolre (never Living Spring's live ones)
      (all left **blank** in `.env`, so no Living Spring key is in use; **waiting on owner to provision new dev keys**)
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
      (emails go to the server log only: no real mail provider yet, waiting on a dev key)
- [x] Password reset flow (email) if not already present

## Phase 3 — Tenant isolation (highest risk, do not skip)

- [ ] Central scoping helper so CRUD queries cannot forget the church filter (base repository/query helper, or SQLAlchemy event)
- [ ] Branch scoping applied automatically for branch-scoped memberships
- [ ] Refactor every `crud/*.py` to scope by `church_id` on read, create, update, delete
- [ ] Refactor every `api/v1/*.py` to pass the church context; never trust `church_id` from request bodies
- [ ] Reports/exports/dashboard aggregates scoped by church (and branch)
- [ ] Audit log records `church_id` and actor
- [ ] Postgres Row-Level Security as backstop: set `app.current_church` per request, policies on all tenant tables
- [ ] **Isolation test suite:** two churches, log in as A, attempt to list/read/update/delete B's data on **every** endpoint; all must 404/403
- [ ] Test: branch-scoped user cannot see other branches' data
- [ ] Test: user in two churches sees only the active church's data

## Phase 4 — Per-tenant configuration and integrations

- [ ] Move SMS sender ID, email from-address/name from `core/config.py` env vars to the `churches` record (env stays as platform defaults only)
- [ ] Per-church Cloudinary folder (`church_{id}/...`)
- [ ] SMS credits per church: balance, deduct on send, block when empty, ledger table
- [ ] Remove hardcoded "Living Spring" / `livingsspring.org` from `config.py`, `main.py`, `.env.example`, `scripts/seed_superadmin.py`, `README.md`, `docs/*`
- [ ] Replace `seed_superadmin.py` with a platform bootstrap script (creates `platform_admin`) and the onboarding flow below
      (bootstrap script done in Phase 2: `scripts/bootstrap_platform_admin.py`; the onboarding flow is Phase 5)
- [ ] `GET/PUT /church/settings` (branding, contact, timezone, currency, sender ID)
- [ ] Branch CRUD endpoints (`/branches`)

## Phase 5 — Onboarding and platform admin

- [ ] Public signup: create church + first user + `church_admin` membership + main branch, start trial
- [ ] Onboarding creates the church's standard funds and expense categories (existing `bootstrap` logic, now per church). The migrations no longer seed them
- [ ] Unique church slug generation and validation (reserved words blocked)
- [ ] Platform admin API: list/search churches, view usage, suspend/reactivate, change plan, impersonate (audited)
- [ ] Suspended/expired church -> API returns a clear status; data stays, access is read-only or blocked per policy
- [ ] Data export per church (members, donations, attendance as CSV/XLSX)

## Phase 6 — Frontend

- [ ] Remove hardcoded branding from `index.html`, `tailwind.config.js`, `LoginPage.jsx`, `Sidebar.jsx`, `Navbar.jsx`, `DashboardPage.jsx`; read `docs/DESIGN.md` first and update it
- [ ] Tenant theming: load church name/logo/colors from the API, apply as CSS variables (Tailwind uses the variables)
- [ ] Tenant resolution: subdomain (`slug.yourapp.com`) or slug on login; decide and document (custom domains later)
- [ ] Church switcher in the navbar for users with multiple churches
- [ ] Branch selector / branch filter for church-wide roles
- [ ] Signup + onboarding wizard (church details, logo, first branch, invite team)
- [ ] Settings pages: church profile and branding, branches, team and roles, SMS credits, billing
- [ ] Role-aware navigation using the new roles
- [ ] Platform admin console (owner only): tenants, usage, plans, suspend
- [ ] Marketing/landing page and pricing page (separate route or site)

## Phase 7 — Billing (Seevplus)

- [ ] **Blocked until the owner provides Seevplus API docs.** Ask before implementing the provider
- [ ] Models: `plans`, `subscriptions`, `invoices`, `payments`, `billing_events` (webhook log, idempotent)
- [ ] `BillingProvider` interface (create checkout/payment link, verify webhook, cancel, status) with a `FakeProvider` for tests and a `SeevplusProvider` for real use
- [ ] Plan limits enforced in the backend (members, branches, users, SMS)
- [ ] Trial, grace period, and read-only mode on non-payment
- [ ] Webhook endpoint: signature verification, idempotency, replay-safe
- [ ] GHS pricing and mobile money support confirmed with Seevplus
- [ ] Billing UI: current plan, upgrade/downgrade, invoices, payment history
- [ ] Prepaid SMS credit top-up via the same provider

## Phase 8 — Hardening and launch

- [ ] Rate limiting on auth and public signup
- [ ] Error monitoring (e.g. Sentry) and structured logging with `church_id`
- [ ] Per-tenant usage metrics (members, SMS sent, storage)
- [ ] Backups and a tested restore; per-church export/delete (account closure) flow
- [ ] Terms of Service, Privacy Policy; Ghana Data Protection Act review (member and donation data is sensitive)
- [ ] Security review (`/security-review`) with focus on tenant isolation and the invite/impersonation flows
- [ ] Staging environment separate from production
- [ ] Pilot with 2-3 churches before public launch

## Phase 9 — Optional: bring Living Spring in as tenant #1

- [ ] Write a one-off import script: Living Spring DB -> this DB under a new `church` (map users to global users plus memberships)
- [ ] Re-create Living Spring's 10 departments under that church (they were removed from the migration chain in Phase 1)
- [ ] Custom domain support (e.g. `app.livingspring.org`) with Living Spring's name, logo, colors and SMS sender ID
- [ ] Dry run on a copy of the production data; verify counts and totals
- [ ] Cutover plan and rollback plan; keep the old deployment until verified
