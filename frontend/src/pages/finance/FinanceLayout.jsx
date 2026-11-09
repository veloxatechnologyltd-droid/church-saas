import { BarChart3, Banknote, ClipboardList, LayoutDashboard, Receipt, Settings2 } from 'lucide-react';
import { NavLink, Outlet } from 'react-router-dom';
import PageHeader from '../../components/shared/PageHeader';

const financeSections = [
  { to: '/finance', label: 'Overview', icon: LayoutDashboard, end: true },
  { to: '/finance/batches', label: 'Service Batches', icon: ClipboardList },
  { to: '/finance/giving', label: 'Giving', icon: Banknote },
  { to: '/finance/expenses', label: 'Expenses', icon: Receipt },
  { to: '/finance/funds', label: 'Funds & Categories', icon: Settings2 },
  { to: '/finance/reports', label: 'Reports', icon: BarChart3 },
];

export default function FinanceLayout() {
  return (
    <section className="space-y-5">
      <PageHeader
        title="Finance"
        subtitle="Manage giving, expenses, service batches, funds, and financial reports."
      />

      <nav className="panel flex gap-1 overflow-x-auto p-2" aria-label="Finance sections">
        {financeSections.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) => `flex shrink-0 items-center gap-2 rounded-xl px-3 py-2.5 text-sm font-semibold transition ${
              isActive
                ? 'bg-brand-700 text-white shadow-sm'
                : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
            }`}
          >
            <Icon size={16} />
            {label}
          </NavLink>
        ))}
      </nav>

      <Outlet />
    </section>
  );
}
