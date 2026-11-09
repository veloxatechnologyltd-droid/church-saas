# FRONTEND.md — React + Tailwind Frontend Conventions

## Setup

```bash
cd frontend
npm create vite@latest . -- --template react
npm install
npm install axios @tanstack/react-query zustand react-router-dom
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
npx shadcn-ui@latest init
```

---

## Folder Structure

```
frontend/src/
├── components/
│   ├── ui/               # ShadCN components (auto-generated)
│   ├── layout/
│   │   ├── Sidebar.jsx
│   │   ├── Navbar.jsx
│   │   └── Layout.jsx
│   └── shared/
│       ├── DataTable.jsx
│       ├── StatCard.jsx
│       ├── PageHeader.jsx
│       └── LoadingSpinner.jsx
├── pages/
│   ├── auth/LoginPage.jsx
│   ├── dashboard/DashboardPage.jsx
│   ├── members/MembersPage.jsx
│   ├── members/MemberProfilePage.jsx
│   ├── attendance/AttendancePage.jsx
│   ├── donations/DonationsPage.jsx   # Finance section views (legacy folder retained)
│   ├── finance/FinanceLayout.jsx     # Finance navigation shell
│   ├── groups/GroupsPage.jsx
│   ├── events/EventsPage.jsx
│   ├── communication/CommunicationPage.jsx
│   └── reports/ReportsPage.jsx
├── hooks/
│   ├── useMembers.js
│   ├── useAttendance.js
│   ├── useDonations.js
│   └── useReports.js
├── services/
│   ├── api.js
│   ├── memberService.js
│   ├── attendanceService.js
│   ├── donationsService.js
│   └── reportsService.js
├── store/
│   └── authStore.js
├── utils/
│   ├── formatters.js
│   └── constants.js
└── App.jsx
```

---

## Routing (App.jsx)

Routes are lazy-loaded (`React.lazy` + one `Suspense`). Three groups:

| Group | Routes | Guard |
|---|---|---|
| Public | `/` (landing), `/pricing`, `/signup`, `/login`, `/forgot-password`, `/reset-password?token=`, `/accept-invite?token=`, `/welcome/:slug`, `/pray/:slug`, `/checkin/:code` | none |
| Signed in, no church shell | `/select-church`, `/platform` (platform admins), `/onboarding`, `/billing/fake-checkout?invoice=` | token (+ church for the last two) |
| Church app (inside `<Layout />`) | `/dashboard`, `/members…`, `/attendance`, `/visitors`, `/finance/*`, `/pledges`, `/pledges/:id`, `/groups…`, `/events`, `/communication`, `/prayer`, `/pastoral`, `/reports`, `/settings[/:tab]` | `ChurchRoute` |

`ChurchRoute` requires a token **and** an active church. A church-less session goes to
`/select-church` (several churches) or `/platform` (platform admin with no church). A
suspended church renders `SuspendedPage`. Role access per route comes from
`components/layout/navConfig.js` (`ROUTE_ROLES`), the same table that builds the sidebar,
so the menu and the guard never disagree. `Layout` sends a `church_admin` whose church has
no `onboarding_completed_at` to `/onboarding`.

Tenant resolution: **slug on login is not needed**. Users sign in with email; the API returns
their churches. The church slug is used only in public URLs (`/welcome/:slug`, `/pray/:slug`).
Subdomains/custom domains are a later phase.

---

## Zustand Auth Store (`store/authStore.js`, persisted as `ekklesia-auth`)

State: `token`, `user`, `churches[]`, `activeChurch` (null until chosen), `impersonation`
(the platform admin's saved session while impersonating), plus non-persisted
`billingNotice` and `suspension`.

- `setSession(loginPayload)` after login, signup, switch-church.
- `setMe(mePayload)` after `GET /auth/me` on app load.
- `updateActiveChurch(partial)` keeps name/colours/logo in sync after settings changes.
- `startImpersonation(payload)` / `stopImpersonation()`.
- `useRole()` returns the role in the active church. Use it instead of `user.role`.
- `utils/session.js#startSession(payload)` sets the session, applies the theme and returns
  the landing path.

The axios client (`services/api.js`) handles account states: 401 logs out; 402
`subscription_required` sets `billingNotice` (red banner, the app stays usable read-only);
403 `church_suspended` sets `suspension`. `downloadFile(url, name, params)` saves protected
CSV/XLSX exports.

## Theming

Church colours come from the API (`primary_color`, `secondary_color`). `utils/theme.js`
turns each into a 50-900 palette of `"R G B"` CSS variables (`--brand-*`, `--church-*`);
Tailwind's `brand`/`primary` and `church`/`secondary` colours read them, so every existing
`bg-brand-700`, `text-church-700/50` class is themed. Defaults live in `index.css`. Never
hardcode a church's name, logo or colours. The product name is `utils/brand.js#PRODUCT`.

---

## API Service Pattern

```javascript
// services/memberService.js
import api from './api';

export const memberService = {
  getAll: (params) => api.get('/members', { params }),
  getById: (id) => api.get(`/members/${id}`),
  create: (data) => api.post('/members', data),
  update: (id, data) => api.put(`/members/${id}`, data),
  delete: (id) => api.delete(`/members/${id}`),
};
```

---

## React Query Hook Pattern

```javascript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { memberService } from '../services/memberService';

export function useMembers(params) {
  return useQuery({
    queryKey: ['members', params],
    queryFn: () => memberService.getAll(params).then(r => r.data),
  });
}

export function useCreateMember() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data) => memberService.create(data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['members'] }),
  });
}
```

---

## Tailwind Rules

- Use Tailwind utility classes only — no separate CSS files
- Use ShadCN components for all UI elements
- Primary actions: bg-blue-700
- Danger/delete: bg-red-600
- Cards: rounded-lg, shadow-sm
- Always wrap tables in overflow-x-auto for mobile

---

## Utility Helpers

```javascript
// utils/formatters.js
export const formatCurrency = (amount, currency = 'GHS') =>
  new Intl.NumberFormat('en-GH', { style: 'currency', currency }).format(amount);

export const formatDate = (date) =>
  new Intl.DateTimeFormat('en-GH', { dateStyle: 'medium' }).format(new Date(date));

export const getMemberInitials = (first, last) =>
  `${first?.[0] ?? ''}${last?.[0] ?? ''}`.toUpperCase();
```

---

## Constants

```javascript
// utils/constants.js
export const ROLES = ['superadmin', 'secretary', 'finance', 'group_leader', 'member'];
export const MEMBERSHIP_STATUS = ['active', 'inactive', 'visitor', 'new_convert'];
export const MARITAL_STATUS = ['single', 'married', 'divorced', 'widowed'];
export const DONATION_METHODS = ['cash', 'mobile_money', 'cheque', 'online'];
export const CHURCH_SERVICE_TYPES = [
  { value: 'sunday_service', label: 'Sunday Service' },
  { value: 'bible_clinic', label: 'Tuesday Bible Clinic' },
  { value: 'prayer_team', label: 'Wednesday Prayer Team' },
  { value: 'prayer_into_business', label: 'Friday Prayer Into Business' },
];
```

Finance UI should follow church workflow:
- record tithe per member
- record offering/harvest/thanksgiving without forcing a member
- group service-day collections into finance batches
- record expenses and show both inflow and outflow on dashboard

Member profile UI should behave like an activity page:
- profile details
- attendance history and percentage
- punctuality metrics
- giving history and tithe totals
