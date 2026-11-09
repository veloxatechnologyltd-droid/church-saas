import { Bell, ChevronRight, Menu } from 'lucide-react';
import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { communicationService } from '../../services/communicationService';
import { useAuthStore, useRole } from '../../store/authStore';
import { ROLE_LABELS } from '../../utils/constants';
import ChurchSwitcher from './ChurchSwitcher';

const PAGE_NAMES = {
  dashboard: 'Dashboard',
  members: 'Members',
  attendance: 'Attendance',
  visitors: 'First-timers',
  finance: 'Finance',
  pledges: 'Pledges',
  groups: 'Groups',
  events: 'Events',
  communication: 'Communication',
  prayer: 'Prayer Requests',
  reports: 'Reports',
  pastoral: 'Pastoral Care',
  settings: 'Settings',
  billing: 'Billing',
};

function getInitials(user) {
  if (!user) return '?';
  const parts = (user.email || '').split('@')[0].split(/[._-]/);
  if (parts.length >= 2 && parts[1]) return (parts[0][0] + parts[1][0]).toUpperCase();
  return (user.email || '?').slice(0, 2).toUpperCase();
}

export default function Navbar({ onMenuClick }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, activeChurch, logout } = useAuthStore();
  const role = useRole();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [announcementsOpen, setAnnouncementsOpen] = useState(false);
  const announcementsQuery = useQuery({
    queryKey: ['announcements', activeChurch?.id],
    queryFn: () => communicationService.getAnnouncements().then((response) => response.data.data),
    enabled: Boolean(activeChurch),
  });

  const rootSegment = location.pathname.replace(/^\//, '').split('/').filter(Boolean)[0] || 'dashboard';
  const pageName = PAGE_NAMES[rootSegment] ?? rootSegment.charAt(0).toUpperCase() + rootSegment.slice(1);

  const today = useMemo(
    () => new Intl.DateTimeFormat('en-GH', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' }).format(new Date()),
    []
  );

  function onLogout() {
    logout();
    navigate('/login');
  }

  return (
    <header className="sticky top-0 z-20 flex h-16 items-center justify-between gap-3 border-b border-slate-200 bg-white/95 px-4 backdrop-blur lg:px-6">
      <div className="flex min-w-0 items-center gap-3">
        <button
          type="button"
          onClick={onMenuClick}
          className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg text-slate-500 hover:bg-slate-100 lg:hidden"
          aria-label="Open navigation"
        >
          <Menu size={20} />
        </button>
        <nav className="flex min-w-0 items-center gap-1 text-sm" aria-label="Breadcrumb">
          <span className="hidden truncate text-slate-400 sm:inline">{activeChurch?.name}</span>
          <ChevronRight size={14} className="hidden flex-shrink-0 text-slate-300 sm:inline" />
          <span className="truncate font-semibold text-slate-800">{pageName}</span>
        </nav>
      </div>

      <div className="flex flex-shrink-0 items-center gap-2">
        <span className="hidden text-xs text-slate-400 xl:block">{today}</span>
        <ChurchSwitcher />

        <div className="relative">
          <button
            type="button"
            onClick={() => setAnnouncementsOpen((previous) => !previous)}
            className="relative flex h-9 w-9 items-center justify-center rounded-lg text-slate-500 hover:bg-slate-100"
            aria-label="Announcements"
          >
            <Bell size={18} />
            {(announcementsQuery.data?.length || 0) > 0 && <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-accent-700" />}
          </button>
          {announcementsOpen && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setAnnouncementsOpen(false)} />
              <div className="absolute right-0 top-11 z-20 w-[min(22rem,calc(100vw-2rem))] rounded-2xl bg-white p-4 shadow-lg ring-1 ring-slate-200">
                <div className="flex items-center justify-between border-b border-slate-100 pb-3"><p className="font-semibold text-slate-900">Announcements</p><span className="text-xs text-slate-400">{announcementsQuery.data?.length || 0}</span></div>
                <div className="max-h-80 space-y-3 overflow-y-auto pt-3">{announcementsQuery.data?.map((announcement) => <article key={announcement.id} className="rounded-xl bg-slate-50 p-3"><p className="text-sm font-semibold text-slate-900">{announcement.title}</p><p className="mt-1 whitespace-pre-wrap text-xs leading-5 text-slate-600">{announcement.body}</p></article>)}{!announcementsQuery.data?.length && <p className="py-5 text-center text-sm text-slate-500">No active announcements.</p>}</div>
              </div>
            </>
          )}
        </div>

        <div className="relative">
          <button
            type="button"
            onClick={() => setDropdownOpen((prev) => !prev)}
            className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-100 text-xs font-bold text-brand-800 transition hover:ring-2 hover:ring-brand-300"
            aria-label="User menu"
          >
            {getInitials(user)}
          </button>
          {dropdownOpen && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setDropdownOpen(false)} />
              <div className="absolute right-0 top-11 z-20 min-w-[220px] rounded-2xl bg-white py-2 shadow-lg ring-1 ring-slate-200">
                <div className="border-b border-slate-100 px-4 py-3">
                  <p className="truncate text-sm font-semibold text-slate-900">{user?.email}</p>
                  <p className="mt-0.5 text-xs text-slate-500">{ROLE_LABELS[role] ?? role}</p>
                </div>
                {role === 'church_admin' && (
                  <Link to="/settings" onClick={() => setDropdownOpen(false)} className="block px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50">Church settings</Link>
                )}
                {user?.is_platform_admin && (
                  <Link to="/platform" onClick={() => setDropdownOpen(false)} className="block px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50">Platform console</Link>
                )}
                <button type="button" onClick={onLogout} className="flex w-full items-center gap-2 px-4 py-2.5 text-sm font-medium text-accent-700 transition hover:bg-accent-50">
                  Sign out
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
