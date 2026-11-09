# API_SAAS.md — SaaS and outreach endpoints (contract)

All responses use the envelope `{"status": "success", "data": ..., ["total", "page", "limit"]}`.
Errors: `{"detail": "..."}` or, for account-state errors, `{"detail": {"code": "...", "message": "..."}}`.
Authenticated endpoints take `Authorization: Bearer <token>`. The active church always comes
from the token; never send `church_id` in a body.

## Auth (Phase 2, extended)

- `POST /api/v1/auth/login` `{email, password}` -> `{access_token, token_type, user, churches[], active_church}`.
  `churches[]`/`active_church` items: `{id, name, slug, logo_url, primary_color, secondary_color, status, plan,
  currency, role, branch_id}`. If `active_church` is null and `churches.length > 1`, show the church picker and call
  `switch-church`. A platform admin with no church gets `churches: []` and should go to `/platform`.
- `POST /api/v1/auth/switch-church` `{church_id}` -> same shape as login.
- `GET /api/v1/auth/me` -> `{user, active_church, churches}`.
- `POST /api/v1/auth/forgot-password` `{email}`, `POST /api/v1/auth/reset-password` `{token, new_password}`,
  `POST /api/v1/auth/change-password` `{current_password, new_password}`.
- `POST /api/v1/invitations/accept` `{token, password?}` (frontend route `/accept-invite?token=`).

## Signup (public)

- `POST /api/v1/signup` `{church_name, slug?, first_name, last_name, email, password, phone?, country?, timezone?,
  currency?, denomination?}` -> same shape as login (signed in to the new church, 14-day trial on Growth limits).
- `GET /api/v1/signup/slug-available?slug=x` -> `{slug, available, suggestion}`.

## Account-state errors (any authenticated church endpoint)

- `402 {"detail": {"code": "subscription_required", "message"}}` on a write when the trial has ended or the
  subscription lapsed (reads still work: read-only mode). Frontend shows an upgrade banner -> `/settings/billing`.
- `403 {"detail": {"code": "church_suspended", "message"}}` on any request when a platform admin suspended the church.
- `402 {"detail": {"code": "plan_limit", "message", "limit": "members|branches|users|sms"}}` when a plan limit is hit.

## Church settings (church_admin writes; any member reads)

- `GET /api/v1/church` -> `{id, name, slug, logo_url, primary_color, secondary_color, timezone, currency, country,
  denomination, phone, email, address, website, sms_sender_id, email_from, email_from_name, status, plan,
  trial_ends_at, sms_credits, onboarding_completed_at, public_urls: {welcome, prayer}}`
- `PUT /api/v1/church` partial update of the editable fields above (not slug/status/plan/sms_credits).
- `POST /api/v1/church/logo` multipart `file` -> church.
- `POST /api/v1/church/onboarding/complete` -> church.
- `GET /api/v1/church/usage` -> `{plan: {...}, usage: {members, branches, users, sms_sent_this_month}, limits:
  {max_members, max_branches, max_users, monthly_sms_credits}, sms_credits}`
- `GET /api/v1/church/export/{members|donations|attendance|visitors}?format=csv|xlsx` -> file download.

## Branches

- `GET /api/v1/branches` -> list `{id, name, address, is_main, is_active, member_count}`.
- `POST /api/v1/branches` `{name, address?}` (church_admin), `PUT /api/v1/branches/{id}` `{name?, address?, is_active?}`,
  `POST /api/v1/branches/{id}/make-main`, `DELETE /api/v1/branches/{id}` (deactivates; the main branch cannot be).

## Team (church_admin)

- `GET /api/v1/team` -> list `{membership_id, user_id, email, role, branch_id, branch_name, member_id, member_name,
  is_active, created_at}` plus `GET /api/v1/invitations` for pending ones.
- `PUT /api/v1/team/{membership_id}` `{role?, branch_id?, is_active?}` (cannot demote/deactivate the last church_admin).
- Invite: `POST /api/v1/invitations` `{email, role, branch_id?, member_id?}`.

## Billing and SMS credits (church_admin)

- `GET /api/v1/billing/plans` (also public, no auth) -> list plans `{code, name, description, price_monthly,
  price_yearly, currency, max_members, max_branches, max_users, monthly_sms_credits, features[]}`.
- `GET /api/v1/billing/subscription` -> `{plan, status, billing_cycle, current_period_end, trial_ends_at,
  church_status, provider}`.
- `POST /api/v1/billing/checkout` `{plan_code, billing_cycle: "monthly"|"yearly"}` -> `{invoice, checkout_url}`.
  With the fake provider, `checkout_url` points to the frontend `/billing/fake-checkout?invoice=<id>`, whose
  "Pay" button calls `POST /api/v1/billing/fake/complete/{invoice_id}` (only enabled when `BILLING_PROVIDER=fake`).
- `GET /api/v1/billing/invoices` -> list `{id, number, kind, description, amount, currency, status, created_at,
  paid_at, checkout_url}`.
- `POST /api/v1/billing/cancel`.
- `GET /api/v1/sms-credits` -> `{balance, ledger: [{delta, balance_after, reason, reference, created_at}]}`.
- `GET /api/v1/sms-credits/packs` -> `[{code, credits, price, currency}]`;
  `POST /api/v1/sms-credits/purchase` `{pack_code}` -> `{invoice, checkout_url}`.
- `POST /api/v1/billing/webhooks/{provider}` provider webhook (signature verified, idempotent).

## Platform admin (users.is_platform_admin; token may have no church)

- `GET /api/v1/platform/stats` -> `{churches_total, by_status, members_total, signups_last_30_days, mrr, sms_sent_30d}`.
- `GET /api/v1/platform/churches?search=&status=&skip=&limit=` -> list `{id, name, slug, status, plan, created_at,
  trial_ends_at, member_count, user_count, sms_credits, last_activity_at}`.
- `GET /api/v1/platform/churches/{id}` -> detail + usage + recent platform events.
- `POST /api/v1/platform/churches/{id}/suspend` `{reason}`, `POST .../reactivate`,
  `PUT .../plan` `{plan_code, status?, trial_ends_at?}`, `POST .../sms-credits` `{credits, reason}`,
  `POST .../impersonate` -> login-shaped payload (token for that church as church_admin, 30 min, audited).
- `GET /api/v1/platform/events?limit=` operator audit trail.

## Outreach features

### Visitors (first-timers) — roles church_admin, secretary (+ group_leader read)
- `GET /api/v1/visitors?status=&search=&skip=&limit=` -> list (`assignee_email`, `converted_member_id`).
- `POST /api/v1/visitors` `{first_name, last_name?, phone?, email?, gender?, age_group?, address?, visit_date?,
  how_heard?, invited_by?, prayer_request?, wants_visit?, interested_in_membership?, notes?}`.
- `GET/PUT/DELETE /api/v1/visitors/{id}` (PUT also `status`, `assigned_to`, `notes`).
- `POST /api/v1/visitors/{id}/contacted` `{notes?}` -> marks contacted, sets last_contacted_at.
- `POST /api/v1/visitors/{id}/convert` -> creates a Member from the visitor, status converted -> `{visitor, member}`.
- `GET /api/v1/visitors/summary` -> `{new, contacted, returning, converted, this_month, conversion_rate,
  by_source: {form, manual}, follow_up_overdue}`.

### Prayer requests — roles church_admin, secretary (pastoral team)
- `GET /api/v1/prayer-requests?status=&skip=&limit=`, `POST /api/v1/prayer-requests`,
  `PUT /api/v1/prayer-requests/{id}` `{status?, response_notes?, category?}`,
  `POST /api/v1/prayer-requests/{id}/prayed` (increments prayed_count), `DELETE /api/v1/prayer-requests/{id}`.

### Pledge campaigns — roles church_admin, finance
- `GET /api/v1/pledges/campaigns` -> list with `{pledged_total, paid_total, pledge_count, progress_pct}`.
- `POST /api/v1/pledges/campaigns` `{name, description?, fund_id?, target_amount?, start_date, end_date?}`;
  `PUT /api/v1/pledges/campaigns/{id}`; `GET /api/v1/pledges/campaigns/{id}` -> campaign + pledges
  (`member_name`, `paid`, `balance`, `status: fulfilled|partial|unpaid|overdue`).
- `POST /api/v1/pledges/campaigns/{id}/pledges` `{member_id? | pledger_name, phone?, amount, due_date?, notes?}`.
- `POST /api/v1/pledges/{pledge_id}/payments` `{amount, paid_on, payment_method?, reference?}` (also records a
  Donation to the campaign fund when one is linked).
- `DELETE /api/v1/pledges/{pledge_id}`.

### Self check-in (attendance)
- `POST /api/v1/attendance/sessions/{id}/checkin` `{open: true|false}` -> `{checkin_code, checkin_open, checkin_url}`
  (church_admin, secretary, group_leader).

### Public (no auth, rate limited) — resolved by church slug
- `GET /api/v1/public/churches/{slug}` -> `{name, slug, logo_url, primary_color, secondary_color, address, phone,
  website}` (404 if unknown/suspended/closed). Used by public pages and the login page theming.
- `POST /api/v1/public/churches/{slug}/visitors` welcome card -> `{message}`.
- `POST /api/v1/public/churches/{slug}/prayer-requests` `{name?, phone?, email?, request, category?, is_confidential?}`.
- `GET /api/v1/public/checkin/{code}` -> `{church: {...branding}, session: {title, session_date}, open}`;
  `POST /api/v1/public/checkin/{code}` `{phone}` -> `{status: "checked_in"|"already_checked_in"|"not_found",
  first_name?}`. Phone matching is normalised (`024...` == `+23324...`). Not found -> frontend offers the first-timer form.

Frontend public routes: `/welcome/:slug`, `/pray/:slug`, `/checkin/:code`, `/signup`, `/pricing`, `/` (landing when
signed out), `/accept-invite`, `/reset-password`, `/forgot-password`.
