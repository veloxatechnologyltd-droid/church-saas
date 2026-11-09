import { useMutation, useQuery } from '@tanstack/react-query';
import { MessageSquare } from 'lucide-react';
import Alert from '../../components/shared/Alert';
import LoadingSpinner from '../../components/shared/LoadingSpinner';
import { billingService } from '../../services/churchService';
import { errorMessage, formatCurrency, formatDateTime } from '../../utils/formatters';
import { goTo } from './BillingPanel';

const REASONS = { purchase: 'Top-up', monthly_allowance: 'Monthly plan allowance', send: 'SMS sent', refund: 'Refund (failed SMS)', grant: 'Granted by support' };

export default function SmsCreditsPanel() {
  const creditsQuery = useQuery({ queryKey: ['sms-credits'], queryFn: () => billingService.smsCredits().then((r) => r.data.data) });
  const packsQuery = useQuery({ queryKey: ['sms-packs'], queryFn: () => billingService.smsPacks().then((r) => r.data.data) });
  const purchase = useMutation({
    mutationFn: (code) => billingService.purchaseSms(code).then((r) => r.data.data),
    onSuccess: (data) => goTo(data.checkout_url),
  });

  const balance = creditsQuery.data?.balance ?? 0;
  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-center gap-4 rounded-2xl bg-brand-50 p-5">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-white text-brand-700"><MessageSquare size={22} /></div>
        <div className="flex-1">
          <p className="text-sm font-semibold text-brand-800">SMS credit balance</p>
          <p className="text-3xl font-extrabold text-slate-900">{creditsQuery.isLoading ? '…' : balance.toLocaleString()}</p>
        </div>
        <p className="max-w-sm text-xs text-slate-600">One credit sends one SMS page (160 characters) to one person. Failed messages are refunded automatically.</p>
      </div>
      {balance < 50 && !creditsQuery.isLoading ? <Alert tone="warn">Your balance is low. Messages will stop sending when it reaches zero.</Alert> : null}

      <section>
        <h3 className="mb-3 text-lg font-extrabold text-slate-900">Top up</h3>
        {purchase.isError ? <div className="mb-3"><Alert tone="error">{errorMessage(purchase.error)}</Alert></div> : null}
        {packsQuery.isLoading ? <LoadingSpinner /> : (
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {(packsQuery.data ?? []).map((pack) => (
              <div key={pack.code} className="rounded-2xl border border-slate-200 p-5">
                <p className="text-2xl font-extrabold text-slate-900">{Number(pack.credits).toLocaleString()}</p>
                <p className="text-sm text-slate-500">SMS credits</p>
                <p className="mt-3 font-semibold text-slate-800">{formatCurrency(pack.price, pack.currency)}</p>
                <button type="button" className="btn-primary mt-4 w-full justify-center" disabled={purchase.isPending} onClick={() => purchase.mutate(pack.code)}>Buy</button>
              </div>
            ))}
          </div>
        )}
      </section>

      <section>
        <h3 className="mb-3 text-lg font-extrabold text-slate-900">Credit history</h3>
        <div className="overflow-x-auto rounded-2xl border border-slate-200">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs font-bold uppercase tracking-wider text-slate-500">
              <tr><th className="px-4 py-3">When</th><th className="px-4 py-3">What</th><th className="px-4 py-3 text-right">Change</th><th className="px-4 py-3 text-right">Balance</th></tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {(creditsQuery.data?.ledger ?? []).map((row, i) => (
                <tr key={row.id ?? i}>
                  <td className="px-4 py-3 text-slate-500">{formatDateTime(row.created_at)}</td>
                  <td className="px-4 py-3">{REASONS[row.reason] ?? row.reason}{row.reference ? <span className="ml-1 text-xs text-slate-400">· {row.reference}</span> : null}</td>
                  <td className={`px-4 py-3 text-right font-semibold ${row.delta >= 0 ? 'text-success-700' : 'text-slate-700'}`}>{row.delta > 0 ? `+${row.delta}` : row.delta}</td>
                  <td className="px-4 py-3 text-right">{row.balance_after}</td>
                </tr>
              ))}
              {!creditsQuery.isLoading && !(creditsQuery.data?.ledger ?? []).length && <tr><td colSpan={4} className="px-4 py-8 text-center text-slate-500">No credit activity yet.</td></tr>}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
