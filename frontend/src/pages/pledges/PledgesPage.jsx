import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { HandCoins, Plus } from 'lucide-react';
import { useState } from 'react';
import { Link } from 'react-router-dom';
import Alert from '../../components/shared/Alert';
import Drawer from '../../components/shared/Drawer';
import EmptyState from '../../components/shared/EmptyState';
import Field from '../../components/shared/Field';
import { SkeletonCards } from '../../components/shared/LoadingSpinner';
import PageHeader from '../../components/shared/PageHeader';
import ProgressBar from '../../components/shared/ProgressBar';
import { useCurrency } from '../../hooks/useChurch';
import { useDonationFunds } from '../../hooks/useDonations';
import { pledgeService } from '../../services/outreachService';
import { errorMessage, formatCurrency, formatDate, todayISO } from '../../utils/formatters';

const EMPTY = { name: '', description: '', fund_id: '', target_amount: '', start_date: todayISO(), end_date: '' };

export default function PledgesPage() {
  const queryClient = useQueryClient();
  const currency = useCurrency();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(EMPTY);
  const [error, setError] = useState('');
  const campaignsQuery = useQuery({ queryKey: ['pledge-campaigns'], queryFn: () => pledgeService.campaigns().then((r) => r.data.data) });
  const fundsQuery = useDonationFunds();
  const funds = fundsQuery.data?.data ?? fundsQuery.data ?? [];

  const create = useMutation({
    mutationFn: () => pledgeService.createCampaign({
      name: form.name,
      description: form.description || null,
      fund_id: form.fund_id || null,
      target_amount: form.target_amount ? Number(form.target_amount) : null,
      start_date: form.start_date,
      end_date: form.end_date || null,
    }),
    onSuccess: () => { setOpen(false); setForm(EMPTY); queryClient.invalidateQueries({ queryKey: ['pledge-campaigns'] }); },
    onError: (err) => setError(errorMessage(err)),
  });
  const set = (key) => (e) => setForm((p) => ({ ...p, [key]: e.target.value }));
  const campaigns = campaignsQuery.data ?? [];

  return (
    <section className="space-y-5">
      <PageHeader
        title="Pledges"
        subtitle="Building projects, harvest and mission drives: track what was promised against what has come in."
        action={<button type="button" className="btn-primary" onClick={() => { setError(''); setOpen(true); }}><Plus size={16} /> New campaign</button>}
      />
      {campaignsQuery.isLoading ? <SkeletonCards cards={3} /> : campaigns.length === 0 ? (
        <div className="panel"><EmptyState icon={HandCoins} label="No pledge campaigns yet" sublabel="Start one for your next building project or harvest." /></div>
      ) : (
        <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
          {campaigns.map((c) => (
            <Link key={c.id} to={`/pledges/${c.id}`} className="panel block p-5 transition hover:ring-2 hover:ring-brand-200">
              <div className="flex items-start justify-between gap-2">
                <h3 className="font-extrabold text-slate-900">{c.name}</h3>
                {!c.is_active ? <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-500">Closed</span> : null}
              </div>
              <p className="mt-1 text-xs text-slate-500">{formatDate(c.start_date)}{c.end_date ? ` – ${formatDate(c.end_date)}` : ''}{c.fund_name ? ` · ${c.fund_name}` : ''}</p>
              <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
                <div><p className="text-xs text-slate-500">Pledged</p><p className="font-extrabold text-slate-900">{formatCurrency(c.pledged_total, currency)}</p></div>
                <div><p className="text-xs text-slate-500">Received</p><p className="font-extrabold text-success-700">{formatCurrency(c.paid_total, currency)}</p></div>
              </div>
              <div className="mt-4">
                <ProgressBar
                  tone="success"
                  value={c.paid_total}
                  max={c.target_amount || c.pledged_total || 0}
                  label={c.target_amount ? `Target ${formatCurrency(c.target_amount, currency)}` : 'Of pledged'}
                  helper={`${Math.round(c.progress_pct ?? 0)}% · ${c.pledge_count} pledges`}
                />
              </div>
            </Link>
          ))}
        </div>
      )}

      <Drawer open={open} onClose={() => setOpen(false)} title="New pledge campaign" footer={<button type="submit" form="campaign-form" className="btn-primary" disabled={create.isPending}>{create.isPending ? 'Saving…' : 'Create campaign'}</button>}>
        <form id="campaign-form" className="space-y-4" onSubmit={(e) => { e.preventDefault(); create.mutate(); }}>
          <Field label="Campaign name" required><input className="field" required minLength={2} value={form.name} onChange={set('name')} placeholder="New Auditorium Project" /></Field>
          <Field label="Description"><textarea className="field min-h-[80px]" value={form.description} onChange={set('description')} /></Field>
          <Field label="Target amount"><input className="field" type="number" min="0" step="0.01" value={form.target_amount} onChange={set('target_amount')} /></Field>
          <Field label="Giving fund" hint="Payments on pledges are also recorded as donations to this fund, so finance reports stay complete.">
            <select className="field" value={form.fund_id} onChange={set('fund_id')}><option value="">No fund (track pledges only)</option>{(Array.isArray(funds) ? funds : []).map((f) => <option key={f.id} value={f.id}>{f.name}</option>)}</select>
          </Field>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Starts" required><input className="field" type="date" required value={form.start_date} onChange={set('start_date')} /></Field>
            <Field label="Ends"><input className="field" type="date" value={form.end_date} onChange={set('end_date')} /></Field>
          </div>
          <Alert tone="error">{error}</Alert>
        </form>
      </Drawer>
    </section>
  );
}
