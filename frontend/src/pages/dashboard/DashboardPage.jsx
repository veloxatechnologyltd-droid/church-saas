import {
  AlertTriangle,
  ArrowRight,
  BarChart2,
  Banknote,
  CalendarDays,
  CheckSquare,
  MessageSquare,
  TrendingDown,
  TrendingUp,
  UserPlus,
  Users,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import LoadingSpinner from '../../components/shared/LoadingSpinner';
import StatCard from '../../components/shared/StatCard';
import TrendBars from '../../components/shared/TrendBars';
import {
  useAttendanceMonthlyReport,
  useDashboardReport,
  useDonationsMonthlyReport,
  useExpensesMonthlyReport,
  useMembersGrowthReport,
} from '../../hooks/useReports';
import { useAuthStore, useRole } from '../../store/authStore';
import { formatCurrency } from '../../utils/formatters';
import OutreachSnapshot from './OutreachSnapshot';

const quickActions = [
  {
    title: 'Members Directory',
    detail: 'Review member records and register new people.',
    to: '/members',
    cta: 'Open Members',
    iconBg: 'bg-brand-50',
    icon: Users,
    iconColor: 'text-brand-700',
  },
  {
    title: 'Attendance Desk',
    detail: 'Run quick service check-in and session tracking.',
    to: '/attendance',
    cta: 'Open Attendance',
    iconBg: 'bg-success-50',
    icon: CheckSquare,
    iconColor: 'text-success-700',
  },
  {
    title: 'Finance Center',
    detail: 'Record giving, expenses, and review fund totals.',
    to: '/finance',
    cta: 'Open Finance',
    iconBg: 'bg-church-50',
    icon: Banknote,
    iconColor: 'text-church-700',
  },
];

function getGreeting() {
  const hour = new Date().getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 17) return 'Good afternoon';
  return 'Good evening';
}

function ProgressBar({ label, value, max, color = 'bg-brand-700' }) {
  const pct = max > 0 ? Math.min(100, Math.round((value / max) * 100)) : 0;
  return (
    <div>
      <div className="mb-1.5 flex items-center justify-between text-sm">
        <span className="font-medium text-slate-700">{label}</span>
        <span className="font-bold text-slate-900">{pct}%</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-slate-100">
        <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

// Mirrors the server: finance trends for admin/finance/secretary, people trends for staff roles.
const REPORT_ROLES = ['church_admin', 'finance', 'secretary'];

/** A plain church member only gets a welcome and the upcoming events (the server withholds the rest). */
function MemberHome() {
  const { activeChurch } = useAuthStore();
  const dashboardQuery = useDashboardReport();
  const events = dashboardQuery.data?.data?.upcoming_event_list ?? [];
  return (
    <section className="space-y-6">
      <div>
        <h1 className="text-2xl font-extrabold text-slate-900">{getGreeting()}</h1>
        <p className="mt-1 text-sm text-slate-500">Welcome to {activeChurch?.name ?? 'your church'}.</p>
      </div>
      <div className="panel p-5">
        <p className="font-bold text-slate-900">Upcoming events</p>
        {dashboardQuery.isLoading ? <LoadingSpinner label="Loading…" /> : null}
        {events.slice(0, 5).map((event) => (
          <p key={event.id} className="mt-2 text-sm text-slate-700">
            <span className="font-semibold">{event.title}</span>
            {event.location ? <span className="text-slate-500"> · {event.location}</span> : null}
          </p>
        ))}
        {!dashboardQuery.isLoading && !events.length && <p className="mt-2 text-sm text-slate-500">No upcoming events scheduled.</p>}
        <Link to="/events" className="mt-3 inline-block text-sm font-semibold text-brand-700 underline">See all events</Link>
      </div>
    </section>
  );
}

export default function DashboardPage() {
  const role = useRole();
  return role === 'member' ? <MemberHome /> : <StaffDashboard role={role} />;
}

function StaffDashboard({ role }) {
  const { user, activeChurch } = useAuthStore();
  const canSeeReports = REPORT_ROLES.includes(role);
  const dashboardQuery = useDashboardReport();
  const attendanceTrendQuery = useAttendanceMonthlyReport();
  const donationsTrendQuery = useDonationsMonthlyReport(canSeeReports);
  const expensesTrendQuery = useExpensesMonthlyReport(canSeeReports);
  const membersTrendQuery = useMembersGrowthReport();

  const today = new Intl.DateTimeFormat('en-GH', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' }).format(new Date());

  if (dashboardQuery.isLoading) {
    return <LoadingSpinner label="Loading dashboard metrics..." />;
  }

  const metrics = dashboardQuery.data?.data ?? {};
  const attendanceTrend = attendanceTrendQuery.data?.data ?? [];
  const donationsTrend = donationsTrendQuery.data?.data ?? [];
  const expensesTrend = expensesTrendQuery.data?.data ?? [];
  const membersTrend = membersTrendQuery.data?.data ?? [];

  const netFlow = (metrics.donations_this_month ?? 0) - (metrics.expenses_this_month ?? 0);

  return (
    <section className="space-y-6">

      {/* Greeting header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900">
            {getGreeting()}{user?.email ? ` 👋` : ''}
          </h1>
          <p className="mt-1 text-sm text-slate-500">{today} — Here's what's happening at {activeChurch?.name ?? 'your church'}.</p>
        </div>
      </div>

      <OutreachSnapshot />

      {/* Stat cards row */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <StatCard
          label="Total Members"
          value={metrics.total_members ?? 0}
          helper="All registered records"
          icon={Users}
        />
        <StatCard
          label="New This Month"
          value={metrics.new_members_this_month ?? 0}
          helper="Joined this month"
          tone="good"
          icon={UserPlus}
        />
        <StatCard
          label="Last Service"
          value={metrics.attendance_last_sunday ?? 0}
          helper={`${metrics.attendance_percentage ?? 0}% attendance rate`}
          icon={BarChart2}
        />
        {canSeeReports && <StatCard
          label="Income (MTD)"
          value={formatCurrency(metrics.donations_this_month ?? 0)}
          helper="Month to date giving"
          tone="good"
          icon={TrendingUp}
        />}
        {canSeeReports && <StatCard
          label="Expenses (MTD)"
          value={formatCurrency(metrics.expenses_this_month ?? 0)}
          helper="Month to date spending"
          tone="warn"
          icon={TrendingDown}
        />}
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
        <div className="panel p-6">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="label-caps mb-1">Pastor’s Overview</p>
              <h2 className="text-lg font-bold text-slate-900">Church activity at a glance</h2>
            </div>
            <Link to="/reports" className="btn-ghost">Full reports <ArrowRight size={14} /></Link>
          </div>
          <div className="mt-5 grid gap-3 sm:grid-cols-3">
            {[
              { label: 'Active Members', value: metrics.active_members ?? metrics.total_members ?? 0 },
              { label: 'Departments', value: metrics.department_count ?? 0 },
              { label: 'Open Follow-Ups', value: metrics.open_pastoral_followups ?? metrics.low_attendance_members ?? 0 },
            ].map((item) => (
              <div key={item.label} className="rounded-2xl bg-slate-50 p-4">
                <p className="text-xs font-semibold text-slate-500">{item.label}</p>
                <p className="mt-1 text-2xl font-extrabold text-slate-900">{item.value}</p>
              </div>
            ))}
          </div>
          <div className="mt-4 grid gap-2 sm:grid-cols-2">
            {(metrics.departments ?? []).slice(0, 6).map((department) => (
              <div key={department.id} className="flex items-center justify-between rounded-xl border border-slate-100 px-3 py-2 text-sm">
                <span className="truncate font-semibold text-slate-700">{department.name}</span>
                <span className="ml-3 text-slate-500">{department.member_count}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="panel p-6">
          <p className="label-caps mb-1">Communications & Events</p>
          <div className="mt-4 space-y-4">
            <div className="flex items-center justify-between gap-3">
              <span className="flex items-center gap-2 text-sm text-slate-600"><MessageSquare size={16} className="text-brand-700" /> SMS sent this month</span>
              <span className="font-bold text-slate-900">{metrics.sms_sent_this_month ?? 0}</span>
            </div>
            <div className="flex items-center justify-between gap-3">
              <span className="flex items-center gap-2 text-sm text-slate-600"><CalendarDays size={16} className="text-church-700" /> Upcoming events</span>
              <span className="font-bold text-slate-900">{metrics.upcoming_events ?? 0}</span>
            </div>
            <div className="border-t border-slate-100 pt-3">
              {(metrics.upcoming_event_list ?? []).slice(0, 3).map((event) => (
                <div key={event.id} className="mb-2 text-sm"><p className="font-semibold text-slate-800">{event.title}</p><p className="text-xs text-slate-500">{new Date(event.start_datetime).toLocaleString('en-GH')}</p></div>
              ))}
              {!(metrics.upcoming_event_list ?? []).length && <p className="text-sm text-slate-500">No upcoming events scheduled.</p>}
            </div>
          </div>
        </div>
      </div>

      {/* Live snapshot + progress bars */}
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="panel p-6">
          <p className="label-caps mb-1">Live Snapshot</p>
          <h2 className="text-lg font-bold text-slate-900">Church operations at a glance</h2>
          <div className="mt-5 space-y-4">
            <ProgressBar
              label="Attendance Rate"
              value={metrics.attendance_percentage ?? 0}
              max={100}
              color="bg-brand-700"
            />
            <ProgressBar
              label="New Members This Month"
              value={metrics.new_members_this_month ?? 0}
              max={Math.max(metrics.new_members_this_month ?? 0, 20)}
              color="bg-success-700"
            />
            <ProgressBar
              label="Follow-Up Members"
              value={metrics.low_attendance_members ?? 0}
              max={Math.max(metrics.total_members ?? 1, 1)}
              color="bg-church-700"
            />
          </div>
        </div>

        {/* Net flow hero card (money: admin, finance and secretary only) */}
        {canSeeReports && <div className="panel overflow-hidden p-6">
          <p className="label-caps mb-1">Monthly Finance Position</p>
          <h2 className="text-lg font-bold text-slate-900">Net cash flow for this month</h2>
          <div className="mt-5 grid grid-cols-2 gap-4">
            <div className="rounded-2xl bg-success-50 p-4">
              <p className="text-xs font-semibold text-success-700">Income</p>
              <p className="mt-1 text-xl font-extrabold text-success-700">
                {formatCurrency(metrics.donations_this_month ?? 0)}
              </p>
            </div>
            <div className="rounded-2xl bg-accent-50 p-4">
              <p className="text-xs font-semibold text-accent-700">Expenses</p>
              <p className="mt-1 text-xl font-extrabold text-accent-700">
                {formatCurrency(metrics.expenses_this_month ?? 0)}
              </p>
            </div>
          </div>
          <div className={`mt-4 rounded-2xl p-4 ${netFlow >= 0 ? 'bg-brand-50' : 'bg-accent-50'}`}>
            <p className={`text-xs font-semibold ${netFlow >= 0 ? 'text-brand-700' : 'text-accent-700'}`}>Net Flow</p>
            <p className={`mt-1 text-3xl font-extrabold ${netFlow >= 0 ? 'text-brand-700' : 'text-accent-700'}`}>
              {formatCurrency(netFlow)}
            </p>
          </div>
        </div>}
      </div>

      {/* Trend charts row */}
      <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-4">
        <TrendBars title="Monthly Attendance" data={attendanceTrend} color="bg-brand-700" />
        {canSeeReports && <TrendBars title="Monthly Income" data={donationsTrend} color="bg-success-700" />}
        {canSeeReports && <TrendBars title="Monthly Expenses" data={expensesTrend} color="bg-accent-700" />}
        <TrendBars title="Member Growth" data={membersTrend} color="bg-church-700" />
      </div>

      {/* Pastoral alert */}
      {['church_admin', 'secretary', 'group_leader'].includes(user?.role)
        && ((metrics.overdue_pastoral_followups ?? 0) > 0 || (metrics.pastoral_followups_due_today ?? 0) > 0) && (
        <div className="panel flex items-start gap-4 border-l-4 border-accent-700 p-5">
          <AlertTriangle size={20} className="mt-0.5 flex-shrink-0 text-accent-700" />
          <div className="flex-1">
            <p className="font-semibold text-slate-900">
              {metrics.overdue_pastoral_followups ?? 0} overdue · {metrics.pastoral_followups_due_today ?? 0} due today
            </p>
            <p className="mt-0.5 text-sm text-slate-500">
              Pastoral care actions need attention from their assigned owners.
            </p>
          </div>
          <Link to="/pastoral" className="flex-shrink-0 text-sm font-semibold text-brand-700 hover:text-brand-800">
            Review care →
          </Link>
        </div>
      )}

      {['church_admin', 'secretary'].includes(user?.role) && (metrics.low_attendance_members ?? 0) > 0 && (
        <div className="panel flex items-start gap-4 border-l-4 border-church-700 p-5">
          <AlertTriangle size={20} className="mt-0.5 flex-shrink-0 text-church-700" />
          <div className="flex-1">
            <p className="font-semibold text-slate-900">
              {metrics.low_attendance_members} member{metrics.low_attendance_members !== 1 ? 's' : ''} need pastoral follow-up
            </p>
            <p className="mt-0.5 text-sm text-slate-500">
              These members haven't been seen in 30+ days. Consider reaching out.
            </p>
          </div>
          <Link to="/pastoral" className="flex-shrink-0 text-sm font-semibold text-brand-700 hover:text-brand-800">
            Start follow-up →
          </Link>
        </div>
      )}

      {/* Quick actions */}
      <div className="grid gap-4 lg:grid-cols-3">
        {quickActions.map((action) => (
          <article key={action.title} className="panel group p-5 transition hover:shadow-md">
            <div className={`mb-4 inline-flex h-11 w-11 items-center justify-center rounded-2xl ${action.iconBg}`}>
              <action.icon size={22} className={action.iconColor} />
            </div>
            <h3 className="text-base font-bold text-slate-900">{action.title}</h3>
            <p className="mt-1.5 text-sm text-slate-500">{action.detail}</p>
            <Link
              to={action.to}
              className="mt-4 inline-flex items-center gap-1.5 text-sm font-semibold text-brand-700 hover:text-brand-800"
            >
              {action.cta}
              <ArrowRight size={14} className="transition-transform group-hover:translate-x-0.5" />
            </Link>
          </article>
        ))}
      </div>
    </section>
  );
}
