import { useMutation, useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import Alert from '../../components/shared/Alert';
import Badge from '../../components/shared/Badge';
import LoadingSpinner from '../../components/shared/LoadingSpinner';
import PlanCard from '../../components/shared/PlanCard';
import ProgressBar from '../../components/shared/ProgressBar';
import { usePlans } from '../../hooks/usePlans';
import { billingService, churchService } from '../../services/churchService';
import { errorMessage, formatCurrency, formatDate } from '../../utils/formatters';

const STATUS_BADGE = { active: 'active', trialing: 'visitor', past_due: 'followup', canceled: 'inactive', expired: 'inactive', paid: 'active', open: 'excused', void: 'inactive', failed: 'followup' };

function goTo(url) {
  if (!url) return;
  if (url.startsWith(window.location.origin)) window.location.assign(url.slice(window.location.origin.length) || '/');
  else window.location.assign(url);
}

export default function BillingPanel() {
  const plansQuery = usePlans();
  const subQuery = useQuery({ queryKey: ['subscription'], queryFn: () => billingService.subscription().then((r) => r.data.data) });
  const usageQuery = useQuery({ queryKey: ['church-usage'], queryFn: () => churchService.usage().then((r) => r.data.data) });
  const invoicesQuery = useQuery({ queryKey: ['invoices'], queryFn: () => billingService.invoices().then((r) => r.data.data) });
  const [cycle, setCycle] = useState('monthly');

  const checkout = useMutation({
    mutationFn: (planCode) => billingService.checkout({ plan_code: planCode, billing_cycle: cycle }).then((r) => r.data.data),
    onSuccess: (data) => goTo(data.checkout_url),
  });

  const sub = subQuery.data;
  const usage = usageQuery.data;
  const currentPlan = sub?.plan?.code ?? sub?.plan;

  return (
    <div className="space-y-8">
      <section className="grid gap-5 lg:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 p-5">
          <p className="label-caps">Current plan</p>
          {subQuery.isLoading ? <LoadingSpinner /> : sub ? (
            <>
              <p className="mt-2 flex items-center gap-2 text-2xl font-extrabold text-slate-900">
                {sub.plan?.name ?? currentPlan} <Badge variant={STATUS_BADGE[sub.status] ?? 'default'}>{sub.status?.replace('_', ' ')}</Badge>
              </p>
              <p className="mt-2 text-sm text-slate-600">
                {sub.status === 'trialing' && sub.trial_ends_at ? `Free trial until ${formatDate(sub.trial_ends_at)}.` : null}
                {sub.status === 'active' && sub.current_period_end ? `Renews ${formatDate(sub.current_period_end)} (${sub.billing_cycle}).` : null}
                {['expired', 'past_due', 'canceled'].includes(sub.status) ? 'Your church is read-only until you choose a plan below.' : null}
              </p>
            </>
          ) : <p className="mt-2 text-sm text-slate-500">No subscription found.</p>}
        </div>
        <div className="space-y-4 rounded-2xl border border-slate-200 p-5">
          <p className="label-caps">Usage</p>
          {usageQuery.isLoading ? <LoadingSpinner /> : usage ? (
            <>
              <ProgressBar label="Members" value={usage.usage?.members ?? 0} max={usage.limits?.max_members} />
              <ProgressBar label="Branches" value={usage.usage?.branches ?? 0} max={usage.limits?.max_branches} />
              <ProgressBar label="Staff logins" value={usage.usage?.users ?? 0} max={usage.limits?.max_users} />
              <p className="text-xs text-slate-500">SMS this month: {usage.usage?.sms_sent_this_month ?? 0} · Credit balance: {usage.sms_credits ?? 0}</p>
            </>
          ) : null}
        </div>
      </section>

      <section>
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <h3 className="text-lg font-extrabold text-slate-900">Plans</h3>
          <div className="inline-flex rounded-xl bg-slate-100 p-1">
            {['monthly', 'yearly'].map((value) => (
              <button key={value} type="button" onClick={() => setCycle(value)} className={`rounded-lg px-3 py-1.5 text-sm font-semibold capitalize ${cycle === value ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500'}`}>{value}</button>
            ))}
          </div>
        </div>
        {checkout.isError ? <div className="mb-4"><Alert tone="error">{errorMessage(checkout.error, 'Could not start checkout.')}</Alert></div> : null}
        {plansQuery.isLoading ? <LoadingSpinner /> : (
          <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-4">
            {(plansQuery.data ?? []).map((plan) => {
              const isCurrent = plan.code === currentPlan && sub?.status === 'active';
              return (
                <PlanCard
                  key={plan.code}
                  plan={plan}
                  cycle={cycle}
                  current={isCurrent}
                  highlighted={plan.code === 'growth' && !isCurrent}
                  action={
                    plan.code === 'enterprise' ? (
                      <a href="mailto:sales@ekklesia.app" className="btn-outline w-full justify-center">Contact sales</a>
                    ) : Number(plan.price_monthly) === 0 ? (
                      <button type="button" className="btn-outline w-full justify-center" disabled={isCurrent || checkout.isPending} onClick={() => checkout.mutate(plan.code)}>{isCurrent ? 'Current plan' : 'Switch to Free'}</button>
                    ) : (
                      <button type="button" className="btn-primary w-full justify-center" disabled={isCurrent || checkout.isPending} onClick={() => checkout.mutate(plan.code)}>
                        {isCurrent ? 'Current plan' : checkout.isPending && checkout.variables === plan.code ? 'Opening checkout…' : `Choose ${plan.name}`}
                      </button>
                    )
                  }
                />
              );
            })}
          </div>
        )}
        <p className="mt-3 text-xs text-slate-500">Payments by mobile money or card through our payment partner. Prices include all features listed.</p>
      </section>

      <section>
        <h3 className="mb-3 text-lg font-extrabold text-slate-900">Invoices</h3>
        <div className="overflow-x-auto rounded-2xl border border-slate-200">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs font-bold uppercase tracking-wider text-slate-500">
              <tr><th className="px-4 py-3">Invoice</th><th className="px-4 py-3">Description</th><th className="px-4 py-3">Amount</th><th className="px-4 py-3">Status</th><th className="px-4 py-3">Date</th><th className="px-4 py-3" /></tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {(invoicesQuery.data ?? []).map((inv) => (
                <tr key={inv.id}>
                  <td className="px-4 py-3 font-mono text-xs">{inv.number}</td>
                  <td className="px-4 py-3">{inv.description}</td>
                  <td className="px-4 py-3 font-semibold">{formatCurrency(inv.amount, inv.currency)}</td>
                  <td className="px-4 py-3"><Badge variant={STATUS_BADGE[inv.status] ?? 'default'}>{inv.status}</Badge></td>
                  <td className="px-4 py-3 text-slate-500">{formatDate(inv.paid_at || inv.created_at)}</td>
                  <td className="px-4 py-3 text-right">{inv.status === 'open' && inv.checkout_url ? <button type="button" className="btn-ghost" onClick={() => goTo(inv.checkout_url)}>Pay now</button> : null}</td>
                </tr>
              ))}
              {!invoicesQuery.isLoading && !(invoicesQuery.data ?? []).length && (
                <tr><td colSpan={6} className="px-4 py-8 text-center text-slate-500">No invoices yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

export { goTo };
