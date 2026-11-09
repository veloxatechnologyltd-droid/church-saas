import { useMutation } from '@tanstack/react-query';
import { CreditCard, ShieldCheck } from 'lucide-react';
import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import Alert from '../../components/shared/Alert';
import ProductMark from '../../components/shared/ProductMark';
import { billingService } from '../../services/churchService';
import { errorMessage } from '../../utils/formatters';

// Stand-in for the payment provider's hosted checkout while BILLING_PROVIDER=fake.
export default function FakeCheckoutPage() {
  const [params] = useSearchParams();
  const invoiceId = params.get('invoice');
  const navigate = useNavigate();
  const [method, setMethod] = useState('momo');
  const pay = useMutation({
    mutationFn: () => billingService.fakeComplete(invoiceId).then((r) => r.data.data),
    onSuccess: (data) => navigate(data?.kind === 'sms_credits' || data?.invoice?.kind === 'sms_credits' ? '/settings/sms' : '/settings/billing', { replace: true }),
  });

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-100 px-4">
      <div className="panel w-full max-w-md p-6">
        <ProductMark />
        <h1 className="mt-6 text-xl font-extrabold text-slate-900">Test checkout</h1>
        <p className="mt-1 text-sm text-slate-500">This environment uses a simulated payment provider. No money moves.</p>
        <div className="mt-5 space-y-2">
          {[['momo', 'Mobile money (MTN, Telecel, AirtelTigo)'], ['card', 'Debit / credit card']].map(([value, label]) => (
            <label key={value} className={`flex cursor-pointer items-center gap-3 rounded-xl border p-3 text-sm ${method === value ? 'border-brand-700 bg-brand-50' : 'border-slate-200'}`}>
              <input type="radio" name="method" checked={method === value} onChange={() => setMethod(value)} />
              <CreditCard size={16} className="text-slate-400" /> {label}
            </label>
          ))}
        </div>
        {!invoiceId ? <div className="mt-4"><Alert tone="error">No invoice was given.</Alert></div> : null}
        {pay.isError ? <div className="mt-4"><Alert tone="error">{errorMessage(pay.error, 'Payment failed.')}</Alert></div> : null}
        <button type="button" className="btn-primary mt-6 w-full justify-center py-3" disabled={!invoiceId || pay.isPending} onClick={() => pay.mutate()}>
          <ShieldCheck size={16} /> {pay.isPending ? 'Processing…' : 'Pay now'}
        </button>
        <Link to="/settings/billing" className="mt-3 block text-center text-sm font-semibold text-slate-500 hover:text-slate-800">Cancel</Link>
      </div>
    </main>
  );
}
