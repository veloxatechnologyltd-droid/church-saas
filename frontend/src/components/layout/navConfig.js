import {
  BarChart3, Banknote, CalendarDays, CheckSquare, HandCoins, HandHeart, HeartPulse, LayoutDashboard,
  MessageSquare, Settings, Sparkles, Users, UsersRound,
} from 'lucide-react';

// Role-aware navigation. `roles` omitted = everyone in the church.
const ADMIN = 'church_admin';
export const NAV_SECTIONS = [
  {
    title: 'Core',
    items: [
      { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
      { to: '/members', label: 'Members', icon: Users, roles: [ADMIN, 'secretary', 'group_leader', 'finance'] },
      { to: '/attendance', label: 'Attendance', icon: CheckSquare, roles: [ADMIN, 'secretary', 'group_leader'] },
      { to: '/visitors', label: 'First-timers', icon: Sparkles, roles: [ADMIN, 'secretary', 'group_leader'] },
    ],
  },
  {
    title: 'Ministry',
    items: [
      { to: '/finance', label: 'Finance', icon: Banknote, roles: [ADMIN, 'finance'] },
      { to: '/pledges', label: 'Pledges', icon: HandCoins, roles: [ADMIN, 'finance'] },
      { to: '/groups', label: 'Groups', icon: UsersRound, roles: [ADMIN, 'secretary', 'group_leader'] },
      { to: '/events', label: 'Events', icon: CalendarDays },
      { to: '/communication', label: 'Communication', icon: MessageSquare, roles: [ADMIN, 'secretary'] },
      { to: '/prayer', label: 'Prayer Requests', icon: HandHeart, roles: [ADMIN, 'secretary'] },
      { to: '/pastoral', label: 'Pastoral Care', icon: HeartPulse, roles: [ADMIN, 'secretary', 'group_leader'] },
      { to: '/reports', label: 'Reports', icon: BarChart3, roles: [ADMIN, 'finance', 'secretary'] },
    ],
  },
  {
    title: 'Admin',
    items: [{ to: '/settings', label: 'Settings', icon: Settings, roles: [ADMIN] }],
  },
];

export const MOBILE_ITEMS = ['/dashboard', '/members', '/attendance', '/visitors', '/finance', '/events'];

export function navItemsFor(role) {
  return NAV_SECTIONS.map((section) => ({
    ...section,
    items: section.items.filter((item) => !item.roles || item.roles.includes(role)),
  })).filter((section) => section.items.length);
}

// Route -> roles, used by ProtectedRoute so a typed URL is guarded like the menu.
export const ROUTE_ROLES = Object.fromEntries(
  NAV_SECTIONS.flatMap((section) => section.items).filter((item) => item.roles).map((item) => [item.to, item.roles])
);
