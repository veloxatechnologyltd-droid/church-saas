import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, Plus, Wallet } from 'lucide-react';
import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import Alert from '../../components/shared/Alert';
import Badge from '../../components/shared/Badge';
import Drawer from '../../components/shared/Drawer';
import Field from '../../components/shared/Field';
import LoadingSpinner from '../../components/shared/LoadingSpinner';
import MemberPicker from '../../components/shared/MemberPicker';
import ProgressBar from '../../components/shared/ProgressBar';
import StatCard from '../../components/shared/StatCard';
import { useCurrency } from '../../hooks/useChurch';
import { pledgeService } from '../../services/outreachService';
import { DONATION_METHODS } from '../../utils/constants';
import { errorMessage, formatCurrency, formatDate, todayISO } from '../../utils/formatters';

const STATUS_VARIANT = { fulfilled: 'active', partial: 'excused', unpaid: 'default', overdue: 'followup' };

export default function PledgeCampaignPage() {
  const { id } = useParams();
  const currency = useCurrency();
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState('all');
  const [adding, setAdding] = useState(false);
  const [pledgeForm, setPledgeForm] = useState({ member: null, pledger_name: '', phone: '', amount: '', due_date: '', notes: '' });
  const [paying, setPaying] = useState(null);
  const [payForm, setPayForm] = useState({ amount: '', paid_on: todayISO(), payment_method: 'cash', reference: '' });
  const [error, setError] = useState('');

  const query = useQuery({ queryKey: ['pledge-campaign', id], queryFn: () => pledgeService.campaign(id).then((r) => r.data.data) });
  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['pledge-campaign', id] });
    queryClient.invalidateQueries({ queryKey: ['pledge-campaigns'] });
  };
  const addPledge = useMutation({
    mutationFn: () => pledgeService.addPledge(id, {
      member_id: pledgeForm.member?.id ?? null,
      pledger_name: pledgeForm.member ? null : pledgeForm.pledger_name || null,
      phone: pledgeForm.phone || null,
      amount: Number(pledgeForm.amount),
      due_date: pledgeForm.due_date || null,
      notes: pledgeForm.notes || null,
    }),
    onSuccess: () => { setAdding(false); setPledgeForm({ member: null, pledger_name: '', phone: '', amount: '', due_date: '', notes: '' }); refresh(); },
    onError: (err) => setError(errorMessage(err)),
  });
  const pay = useMutation({
    mutationFn: () => pledgeService.recordPayment(paying.id, { ...payForm, amount: Number(payForm.amount), reference: payForm.reference || null }),
    onSuccess: () => { setPaying(null); refresh(); queryClient.invalidateQueries({ queryKey: ['donations'] }); },
    onError: (err) => setError(errorMessage(err)),
  });
  const toggleActive = useMutation({ mutationFn: (active) => pledgeService.updateCampaign(id, { is_active: active }), onSuccess: refresh });

  if (query.isLoading) return <LoadingSpinner />;
  if (query.isError) return <Alert tone="error">{errorMessage(query.error, 'Campaign not found.')}</Alert>;
  const c = query.data;
  const pledges = (c.pledges ?? []).filter((p) => filter === 'all' || p.status === filter);
  const outstanding = Math.max(0, Number(c.pledged_total) - Number(c.paid_total));

  return (
    <section className="space-y-5">
      <Link to="/pledges" className="btn-ghost -ml-2"><ArrowLeft size={15} /> All campaigns</Link>
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900">{c.name}</h1>
          <p className="mt-1 text-sm text-slate-500">{formatDate(c.start_date)}{c.end_date ? ` – ${formatDate(c.end_date)}` : ''}{c.fund_name ? ` · payments go to ${c.fund_name}` : ''}</p>
          {c.description ? <p className="mt-2 max-w-2xl text-sm text-slate-600">{c.description}</p> : null}
        </div>
        <div className="flex gap-2">
          <button type="button" className="btn-outline" onClick={() => toggleActive.mutate(!c.is_active)}>{c.is_active ? 'Close campaign' : 'Reopen'}</button>
          <button type="button" className="btn-primary" onClick={() => { setError(''); setAdding(true); }}><Plus size={16} /> Add pledge</button>
        </div>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Target" value={c.target_amount ? formatCurrency(c.target_amount, currency) : '—'} />
        <StatCard label="Pledged" value={formatCurrency(c.pledged_total, currency)} helper={`${c.pledge_count} pledges`} />
        <StatCard label="Received" value={formatCurrency(c.paid_total, currency)} tone="good" />
        <StatCard label="Outstanding" value={formatCurrency(outstanding, currency)} tone={outstanding ? 'warn' : 'good'} />
      </div>
      <div className="panel p-5"><ProgressBar tone="success" value={c.paid_total} max={c.target_amount || c.pledged_total || 0} label="Progress" helper={`${Math.round(c.progress_pct ?? 0)}%`} /></div>

      <div className="flex flex-wrap gap-2">
        {['all', 'unpaid', 'partial', 'overdue', 'fulfilled'].map((f) => (
          <button key={f} type="button" onClick={() => setFilter(f)} className={`rounded-xl px-3 py-1.5 text-sm font-semibold capitalize ring-1 ${filter === f ? 'bg-brand-700 text-white ring-brand-700' : 'bg-white text-slate-600 ring-slate-200'}`}>{f}</button>
        ))}
      </div>
      <div className="panel overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead className="border-b border-slate-200 bg-slate-50 text-left text-xs font-bold uppercase tracking-wider text-slate-500">
            <tr><th className="px-4 py-3">Pledger</th><th className="px-4 py-3">Pledged</th><th className="px-4 py-3">Paid</th><th className="px-4 py-3">Balance</th><th className="px-4 py-3">Status</th><th className="px-4 py-3" /></tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {pledges.map((p) => (
              <tr key={p.id}>
                <td className="px-4 py-3">
                  {p.member_id ? <Link to={`/members/${p.member_id}`} className="font-semibold text-slate-900 hover:text-brand-700">{p.display_name}</Link> : <span className="font-semibold text-slate-900">{p.display_name}</span>}
                  <p className="text-xs text-slate-500">{p.phone || ''}{p.due_date ? ` · due ${formatDate(p.due_date)}` : ''}</p>
                </td>
                <td className="px-4 py-3 font-semibold">{formatCurrency(p.amount, currency)}</td>
                <td className="px-4 py-3 text-success-700">{formatCurrency(p.paid, currency)}</td>
                <td className="px-4 py-3">{formatCurrency(p.balance, currency)}</td>
                <td className="px-4 py-3"><Badge variant={STATUS_VARIANT[p.status]}>{p.status}</Badge></td>
                <td className="px-4 py-3 text-right">{p.balance > 0 && <button type="button" className="btn-ghost" onClick={() => { setError(''); setPayForm({ amount: String(p.balance), paid_on: todayISO(), payment_method: 'cash', reference: '' }); setPaying(p); }}><Wallet size={14} /> Record payment</button>}</td>
              </tr>
            ))}
            {!pledges.length && <tr><td colSpan={6} className="px-4 py-10 text-center text-slate-500">No pledges {filter === 'all' ? 'yet' : `marked ${filter}`}.</td></tr>}
          </tbody>
        </table>
      </div>

      <Drawer open={adding} onClose={() => setAdding(false)} title="Add pledge" footer={<button type="submit" form="pledge-form" className="btn-primary" disabled={addPledge.isPending}>{addPledge.isPending ? 'Saving…' : 'Save pledge'}</button>}>
        <form id="pledge-form" className="space-y-4" onSubmit={(e) => { e.preventDefault(); addPledge.mutate(); }}>
          <Field label="Member"><MemberPicker value={pledgeForm.member} onChange={(member) => setPledgeForm((p) => ({ ...p, member }))} /></Field>
          {!pledgeForm.member && <Field label="Or name (non-member)"><input className="field" value={pledgeForm.pledger_name} onChange={(e) => setPledgeForm((p) => ({ ...p, pledger_name: e.target.value }))} /></Field>}
          <Field label="Phone"><input className="field" value={pledgeForm.phone} onChange={(e) => setPledgeForm((p) => ({ ...p, phone: e.target.value }))} /></Field>
          <Field label={`Amount (${currency})`} required><input className="field" type="number" required min="0.01" step="0.01" value={pledgeForm.amount} onChange={(e) => setPledgeForm((p) => ({ ...p, amount: e.target.value }))} /></Field>
          <Field label="Due by"><input className="field" type="date" value={pledgeForm.due_date} onChange={(e) => setPledgeForm((p) => ({ ...p, due_date: e.target.value }))} /></Field>
          <Field label="Notes"><textarea className="field" value={pledgeForm.notes} onChange={(e) => setPledgeForm((p) => ({ ...p, notes: e.target.value }))} /></Field>
          <Alert tone="error">{error}</Alert>
        </form>
      </Drawer>

      <Drawer open={Boolean(paying)} onClose={() => setPaying(null)} title="Record pledge payment" subtitle={paying ? `${paying.display_name} · balance ${formatCurrency(paying.balance, currency)}` : ''} footer={<button type="submit" form="pay-form" className="btn-primary" disabled={pay.isPending}>{pay.isPending ? 'Saving…' : 'Record payment'}</button>}>
        <form id="pay-form" className="space-y-4" onSubmit={(e) => { e.preventDefault(); pay.mutate(); }}>
          <Field label={`Amount (${currency})`} required><input className="field" type="number" required min="0.01" step="0.01" value={payForm.amount} onChange={(e) => setPayForm((p) => ({ ...p, amount: e.target.value }))} /></Field>
          <Field label="Date" required><input className="field" type="date" required value={payForm.paid_on} onChange={(e) => setPayForm((p) => ({ ...p, paid_on: e.target.value }))} /></Field>
          <Field label="Method"><select className="field capitalize" value={payForm.payment_method} onChange={(e) => setPayForm((p) => ({ ...p, payment_method: e.target.value }))}>{DONATION_METHODS.map((m) => <option key={m} value={m}>{m.replace('_', ' ')}</option>)}</select></Field>
          <Field label="Reference"><input className="field" value={payForm.reference} onChange={(e) => setPayForm((p) => ({ ...p, reference: e.target.value }))} placeholder="MoMo transaction ID, receipt no." /></Field>
          {c.fund_name ? <p className="text-xs text-slate-500">This payment will also appear in Finance as a donation to {c.fund_name}.</p> : null}
          <Alert tone="error">{error}</Alert>
        </form>
      </Drawer>
    </section>
  );
}
