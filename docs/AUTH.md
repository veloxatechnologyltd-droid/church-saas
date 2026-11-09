# AUTH.md — Authentication & Role-Based Access Control

> Multi-tenant fork. Read `docs/SAAS.md` for the tenancy model. This file is the source
> of truth for identity, roles, tokens, invitations and password reset.

## Identity model

- A **user** (`users`) is a global login identity: email + bcrypt password hash. One
  person has one login no matter how many churches they belong to.
- A **membership** (`memberships`) gives a user a **role in one church**, either
  church-wide (`branch_id` NULL) or limited to one branch. Unique per `(user, church)`.
- A **platform admin** is a flag on the user (`users.is_platform_admin`), set only by the
  bootstrap script. It is not a church role and grants nothing inside a church. Platform
  operations arrive in Phase 5; impersonation, when added, must be audited.

## Roles

| Level | Role | Meaning |
|---|---|---|
| Platform | `platform_admin` | Product owner's operators. Tenant management only (Phase 5). No access to a church's data unless they also hold a membership there. |
| Church | `church_admin` | Everything in the church: settings, team invitations, audit log, deletes, fund and category setup. (Was `superadmin` in the single-church app.) |
| Church | `secretary` | Members, families, attendance, events, communication, departments, pastoral care. |
| Church | `finance` | Giving, expenses, service batches, statements, finance reports. |
| Church | `group_leader` | Their own department's members, attendance, department SMS, and pastoral care assigned to them. |
| Church | `member` | Their own profile and giving history only. |

Any church role can be **branch-scoped**: the membership names one branch and the user
is limited to it. A branch-scoped `church_admin` is a *branch admin*: they may invite
people only into their own branch, and see and revoke only their branch's invitations.
Church-wide actions such as churches, branches and billing settings are for
church-wide `church_admin`s (those endpoints arrive in Phases 4 and 7).

> **Data-level branch filtering is Phase 3.** Until then a branch-scoped membership is
> carried in the token and enforced for invitations, but list endpoints are not yet
> filtered by branch (and not yet by church: see `docs/SAAS.md`).

## Tokens (JWT, HS256)

Claims: `sub` (user id), `iat` (float seconds), `exp`, and, once a church is selected,
`church_id`, `role` and `branch_id` (only if branch-scoped).

**The server never trusts the role or branch in the token.** On every request it reloads
the user and the membership for the token's `church_id`:

| Situation | Result |
|---|---|
| Bad signature, expired, malformed, bad `sub` / `church_id` | `401` |
| User missing or `is_active = false` | `401` |
| Token issued before the user's `password_changed_at` | `401` "Session expired" |
| `church_id` present but no **active** membership there (never a member, deactivated, or forged claim) | `401` |
| Valid token with **no** `church_id` used on a tenant endpoint | `403` "No church selected" |
| Authenticated but role not allowed | `403` |

So demoting, deactivating or removing someone takes effect on their next request, and a
forged `role` or `is_platform_admin` claim does nothing.

## Dependencies (`app/core/dependencies.py`)

| Dependency | Guarantees | Use for |
|---|---|---|
| `get_token_claims` | validly signed, unexpired JWT | internal |
| `get_session_context` | real active user, token not predating a password change; **church optional** (validated if present) | `/auth/me`, `/auth/churches`, `/auth/switch-church`, `/auth/change-password`, platform endpoints |
| `get_current_user` | as above **and** an active membership in the token's church | every tenant endpoint |
| `get_current_church` / `get_current_membership` | the `Church` / `Membership` of this request | endpoints that need them |
| `require_roles(*roles)` | the user's role **in the active church** is in `roles` | role-gated tenant endpoints |
| `require_platform_admin` | `users.is_platform_admin` read from the database | platform endpoints (Phase 5) |

`get_current_user` returns a `CurrentUser` exposing `id`, `email`, `role`, `member_id`,
`church_id`, `branch_id`, `is_branch_scoped`, `is_platform_admin`, plus `.user`,
`.membership` and `.church`. `role` and `member_id` are those of the **active church's
membership**.

```python
from app.core.dependencies import get_current_user, require_roles

@router.get("/members")                       # any signed-in member of the church
def list_members(current_user=Depends(get_current_user), db=Depends(get_db)):
    church_id = current_user.church_id        # always take the church from here, never from the request body

@router.post("/members")                      # church_admin or secretary of the active church
def create_member(current_user=Depends(require_roles("church_admin", "secretary")), db=Depends(get_db)):
    ...
```

## Endpoints (`/api/v1`)

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/auth/login` | public | Verify credentials. Returns a token, the user's churches, and the active church. One church: signed straight in. Several: a church-less token to list and switch. None: `403` (unless platform admin). |
| GET | `/auth/churches` | any session | Churches the user can sign in to, with their role in each. |
| POST | `/auth/switch-church` | any session | `{church_id}` -> new token for that church. `403` with one identical message if the church does not exist, the user is not in it, the membership is inactive, or the church is closed. |
| GET | `/auth/me` | any session | The user and the active church (or null). |
| POST | `/auth/change-password` | any session | Needs the current password. Ends all older sessions and returns a fresh token. |
| POST | `/auth/forgot-password` | public | Always the same reply, whether or not the email has an account. |
| POST | `/auth/reset-password` | public | `{token, new_password}`. Single use. Ends all sessions. Does not sign in. |
| POST | `/invitations/` | `church_admin` | Invite an email with a role (and optional branch / member profile). |
| GET | `/invitations/` | `church_admin` | Pending invitations of this church (a branch admin sees only their branch's). |
| DELETE | `/invitations/{id}` | `church_admin` | Revoke a pending invitation. `404` for another church's. |
| POST | `/invitations/accept` | public | `{token, password?}`. Redeem an emailed invitation. |

`POST /auth/register` no longer exists: people join a church through an invitation, and
a church plus its first admin are created by public signup (Phase 5).

Passwords: 8-72 characters (bcrypt ignores everything past 72 bytes).

## Invitations

1. A church admin posts an email, role, and optionally `branch_id` / `member_id`. Both must
   belong to the same church (checked by the API **and** by composite foreign keys).
2. The server stores only a SHA-256 hash of a random 256-bit token and emails the link
   `FRONTEND_BASE_URL/accept-invite?token=...`. **The token is never returned by the API.**
3. Re-inviting the same email revokes the earlier pending link. Inviting someone who is
   already an *active* member is `409`; a deactivated member can be re-invited and is
   reactivated with the new role on acceptance.
4. The invitee posts the token. If the email has no account they must also choose a
   password; if it has one, their existing password is left untouched (the emailed
   link proves mailbox control, but must not be able to change a password). No session
   is issued: they sign in normally afterwards.
5. A link works once and expires after `INVITE_EXPIRE_HOURS` (default 168). Unknown,
   expired, revoked and used tokens all return the same `400`. Redeeming is serialised
   with a row lock so two simultaneous redemptions cannot both succeed.
6. Creating, revoking and redeeming are written to `audit_logs` with the church.

## Password reset

`/auth/forgot-password` creates a single-use token (hash stored, 60 minutes by default,
`PASSWORD_RESET_EXPIRE_MINUTES`) and voids any earlier one. `/auth/reset-password` sets the
password and records `users.password_changed_at`, which makes every token issued
earlier invalid. Changing a password does the same, and returns a fresh token so the
caller stays signed in.

## Email

`app/services/email.py` defines `EmailSender`. Only `ConsoleEmailSender` (logs the
message, **including the secret link**, to the server log) and `FakeEmailSender` (tests)
exist. Any `EMAIL_BACKEND` other than `console` raises when the first email is sent,
rather than silently dropping mail. A real provider needs a new dev key first.
Delivery failures never change an API reply (forgot-password) or lose the invitation
(`email_sent: false`).

## Bootstrapping the platform admin

```bash
PLATFORM_ADMIN_EMAIL=you@yourcompany.com PLATFORM_ADMIN_PASSWORD='a long passphrase' \
  python scripts/bootstrap_platform_admin.py
```
Both are required (no defaults; password at least 12 characters for a new account). An
existing user is promoted without touching their password.

## Frontend flow (not yet implemented: Phase 6)

The current frontend still expects the single-church shapes and the old role names.
Target flow: login -> if `active_church` is null show a church picker -> `switch-church`
-> store the token. Send `Authorization: Bearer <token>` on every request, treat `401`
as "sign in again", and read the active role from `data.user.role`. After
`change-password`, store the returned `access_token`. Accept-invite and reset-password
are pages that read `?token=` from the link.
