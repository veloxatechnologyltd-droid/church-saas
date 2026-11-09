import { LogOut } from 'lucide-react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuthStore, useRole } from '../../store/authStore';
import { PRODUCT } from '../../utils/brand';
import { ROLE_LABELS } from '../../utils/constants';
import ChurchMark from '../shared/ChurchMark';
import { navItemsFor } from './navConfig';

function getInitials(user) {
  if (!user) return '?';
  const parts = (user.email || '').split('@')[0].split(/[._-]/);
  if (parts.length >= 2 && parts[1]) return (parts[0][0] + parts[1][0]).toUpperCase();
  return (user.email || '?').slice(0, 2).toUpperCase();
}

export default function Sidebar({ onNavigate }) {
  const { user, activeChurch, logout } = useAuthStore();
  const role = useRole();
  const navigate = useNavigate();

  function onLogout() {
    logout();
    navigate('/login');
  }

  return (
    <aside className="flex h-screen w-60 flex-col border-r border-slate-200 bg-white">
      <div className="flex items-center gap-3 border-b border-slate-100 px-5 py-4">
        <ChurchMark church={activeChurch} />
        <div className="min-w-0">
          <p className="truncate text-sm font-bold leading-tight text-slate-900" title={activeChurch?.name}>{activeChurch?.name ?? PRODUCT.name}</p>
          <p className="truncate text-[11px] text-slate-500">Powered by {PRODUCT.name}</p>
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 py-4" aria-label="Main">
        {navItemsFor(role).map((section) => (
          <div key={section.title} className="mb-5">
            <p className="label-caps mb-2 px-2">{section.title}</p>
            <div className="space-y-0.5">
              {section.items.map(({ to, label, icon: Icon }) => (
                <NavLink
                  key={to}
                  to={to}
                  onClick={onNavigate}
                  className={({ isActive }) =>
                    `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors ${
                      isActive ? 'bg-brand-700 text-white' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                    }`
                  }
                >
                  {({ isActive }) => (
                    <>
                      <Icon size={17} className={isActive ? 'text-white' : 'text-slate-400'} strokeWidth={isActive ? 2.5 : 2} />
                      {label}
                    </>
                  )}
                </NavLink>
              ))}
            </div>
          </div>
        ))}
      </nav>

      <div className="border-t border-slate-100 px-3 py-3">
        <div className="mb-2 flex items-center gap-3 rounded-xl px-2 py-2">
          <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full bg-brand-100 text-xs font-bold text-brand-800">
            {getInitials(user)}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-semibold text-slate-900">{user?.email ?? 'User'}</p>
            <p className="truncate text-[11px] text-slate-500">{ROLE_LABELS[role] ?? role ?? 'Staff'}</p>
          </div>
        </div>
        <button
          type="button"
          onClick={onLogout}
          className="flex w-full items-center gap-2.5 rounded-xl px-3 py-2.5 text-sm font-medium text-slate-600 transition hover:bg-accent-50 hover:text-accent-700"
        >
          <LogOut size={16} className="text-slate-400" />
          Sign out
        </button>
      </div>
    </aside>
  );
}
