import { Check } from 'lucide-react';
import { formatCurrency } from '../../utils/formatters';

const FEATURE_LABELS = {
  members: 'Member & family records',
  attendance: 'Attendance tracking',
  giving: 'Giving & finance',
  events: 'Events & registrations',
  sms: 'Bulk SMS & reminders',
  visitors: 'First-timer follow-up',
  prayer: 'Prayer request inbox',
  pledges: 'Pledge campaigns',
  self_checkin: 'QR self check-in',
  reports: 'Reports & insights',
  multi_branch: 'Multi-branch management',
  exports: 'CSV / Excel exports',
  priority_support: 'Priority support',
  everything: 'Everything in Kingdom',
  custom_domain: 'Custom domain',
  dedicated_support: 'Dedicated success manager',
};

export const featureLabel = (code) => FEATURE_LABELS[code] ?? code.replaceAll('_', ' ');

function limit(value, noun) {
  return value === null || value === undefined ? `Unlimited ${noun}` : `Up to ${Number(value).toLocaleString()} ${noun}`;
}

// A pricing card. `cycle` is 'monthly' | 'yearly'.
export default function PlanCard({ plan, cycle = 'monthly', highlighted, current, action }) {
  const custom = plan.code === 'enterprise';
  const price = cycle === 'yearly' ? plan.price_yearly : plan.price_monthly;
  return (
    <article className={`relative flex flex-col rounded-3xl bg-white p-6 ring-1 ${highlighted ? 'shadow-xl ring-2 ring-brand-700' : 'ring-slate-200'}`}>
      {highlighted ? <span className="absolute -top-3 left-6 rounded-full bg-brand-700 px-3 py-1 text-xs font-bold text-white">Most popular</span> : null}
      {current ? <span className="absolute -top-3 right-6 rounded-full bg-success-700 px-3 py-1 text-xs font-bold text-white">Current plan</span> : null}
      <h3 className="text-lg font-extrabold text-slate-900">{plan.name}</h3>
      <p className="mt-1 min-h-[2.5rem] text-sm text-slate-500">{plan.description}</p>
      <p className="mt-4">
        {custom ? (
          <span className="text-3xl font-extrabold text-slate-900">Let&apos;s talk</span>
        ) : Number(price) === 0 ? (
          <span className="text-3xl font-extrabold text-slate-900">Free</span>
        ) : (
          <>
            <span className="text-3xl font-extrabold text-slate-900">{formatCurrency(price, plan.currency)}</span>
            <span className="text-sm text-slate-500">/{cycle === 'yearly' ? 'year' : 'month'}</span>
          </>
        )}
      </p>
      <ul className="mt-5 space-y-2 text-sm text-slate-700">
        <li className="flex gap-2"><Check size={16} className="mt-0.5 flex-shrink-0 text-success-700" />{limit(plan.max_members, 'members')}</li>
        <li className="flex gap-2"><Check size={16} className="mt-0.5 flex-shrink-0 text-success-700" />{limit(plan.max_branches, plan.max_branches === 1 ? 'branch' : 'branches')}</li>
        <li className="flex gap-2"><Check size={16} className="mt-0.5 flex-shrink-0 text-success-700" />{limit(plan.max_users, 'staff logins')}</li>
        {plan.monthly_sms_credits ? (
          <li className="flex gap-2"><Check size={16} className="mt-0.5 flex-shrink-0 text-success-700" />{Number(plan.monthly_sms_credits).toLocaleString()} SMS credits / month</li>
        ) : null}
        {(plan.features ?? []).map((feature) => (
          <li key={feature} className="flex gap-2"><Check size={16} className="mt-0.5 flex-shrink-0 text-success-700" />{featureLabel(feature)}</li>
        ))}
      </ul>
      {action ? <div className="mt-6 pt-2">{action}</div> : null}
    </article>
  );
}
