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

```jsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from './store/authStore';

function ProtectedRoute({ children, allowedRoles }) {
  const { user, token } = useAuthStore();
  if (!token) return <Navigate to="/login" />;
  if (allowedRoles && !allowedRoles.includes(user?.role)) return <Navigate to="/dashboard" />;
  return children;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
          <Route index element={<Navigate to="/dashboard" />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="members" element={<MembersPage />} />
          <Route path="members/:id" element={<MemberProfilePage />} />
          <Route path="attendance" element={<AttendancePage />} />
          <Route path="finance" element={<FinanceLayout />}>       // Finance workspace
            <Route index element={<DonationsPage view="overview" />} />
            <Route path="giving" element={<DonationsPage view="giving" />} />
            <Route path="expenses" element={<DonationsPage view="expenses" />} />
            <Route path="batches" element={<DonationsPage view="batches" />} />
            <Route path="funds" element={<DonationsPage view="funds" />} />
            <Route path="reports" element={<DonationsPage view="reports" />} />
          </Route>
          <Route path="donations" element={<Navigate to="/finance" replace />} />
          <Route path="groups" element={<GroupsPage />} />
          <Route path="events" element={<EventsPage />} />
          <Route path="communication" element={<CommunicationPage />} />
          <Route path="reports" element={<ReportsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
```

---

## Zustand Auth Store

```javascript
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export const useAuthStore = create(
  persist(
    (set) => ({
      user: null,
      token: null,
      setAuth: (user, token) => set({ user, token }),
      logout: () => set({ user: null, token: null }),
    }),
    { name: 'church-cms-auth' }
  )
);
```

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
