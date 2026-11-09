import { NavLink } from 'react-router-dom';
import { useRole } from '../../store/authStore';
import { MOBILE_ITEMS, navItemsFor } from './navConfig';

export default function MobileNav() {
  const role = useRole();
  const items = navItemsFor(role)
    .flatMap((section) => section.items)
    .filter((item) => MOBILE_ITEMS.includes(item.to))
    .slice(0, 5);

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-20 flex border-t border-slate-200 bg-white pb-[env(safe-area-inset-bottom)] lg:hidden" aria-label="Quick">
      {items.map(({ to, label, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          className={({ isActive }) =>
            `flex flex-1 flex-col items-center gap-1 py-2.5 text-[10px] font-semibold uppercase tracking-wide transition ${
              isActive ? 'text-brand-700' : 'text-slate-400 hover:text-slate-600'
            }`
          }
        >
          {({ isActive }) => (
            <>
              <Icon size={20} strokeWidth={isActive ? 2.5 : 2} />
              <span className="max-w-full truncate px-1">{label}</span>
            </>
          )}
        </NavLink>
      ))}
    </nav>
  );
}
