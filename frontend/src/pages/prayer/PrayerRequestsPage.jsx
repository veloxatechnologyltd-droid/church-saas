import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { HandHeart, Lock, Plus, Trash2 } from 'lucide-react';
import { useState } from 'react';
import Alert from '../../components/shared/Alert';
import Badge from '../../components/shared/Badge';
import Drawer from '../../components/shared/Drawer';
import EmptyState from '../../components/shared/EmptyState';
import Field from '../../components/shared/Field';
import { SkeletonRows } from '../../components/shared/LoadingSpinner';
import MemberPicker from '../../components/shared/MemberPicker';
import PageHeader from '../../components/shared/PageHeader';
import Tabs from '../../components/shared/Tabs';
import { prayerService } from '../../services/outreachService';
import { useRole } from '../../store/authStore';
import { PRAYER_CATEGORIES, PRAYER_STATUSES } from '../../utils/constants';
import { errorMessage, formatDateTime } from '../../utils/formatters';

const STATUS_VARIANT = { new: 'visitor', praying: 'excused', answered: 'active', closed: 'inactive' };
const NEW_FORM = { member: null, name: '', phone: '', request: '', category: '', is_confidential: false };

export default function PrayerRequestsPage() {
  const queryClient = useQueryClient();
  const role = useRole();
  const [status, setStatus] = useState('open');
  const [adding, setAdding] = useState(false);
  const [form, setForm] = useState(NEW_FORM);
  const [selected, setSelected] = useState(null);
  const [notes, setNotes] = useState('');
  const [error, setError] = useState('');

  const listQuery = useQuery({
    queryKey: ['prayer-requests', status],
    queryFn: () => prayerService.list({ status: status === 'open' || status === 'all' ? undefined : status, limit: 100 }).then((r) => r.data),
  });
  const refresh = () => queryClient.invalidateQueries({ queryKey: ['prayer-requests'] });
  const create = useMutation({
    mutationFn: () => prayerService.create({
      member_id: form.member?.id ?? null,
      name: form.member ? form.member.name : form.name || null,
      phone: form.phone || null,
      request: form.request,
      category: form.category || null,
      is_confidential: form.is_confidential,
    }),
    onSuccess: () => { setAdding(false); setForm(NEW_FORM); refresh(); },
    onError: (err) => setError(errorMessage(err)),
  });
  const update = useMutation({
    mutationFn: ({ id, ...payload }) => prayerService.update(id, payload).then((r) => r.data.data),
    onSuccess: (data) => { setSelected(data); refresh(); },
    onError: (err) => setError(errorMessage(err)),
  });
  const prayed = useMutation({ mutationFn: (id) => prayerService.prayed(id).then((r) => r.data.data), onSuccess: (data) => { if (selected?.id === data?.id) setSelected(data); refresh(); } });
  const remove = useMutation({ mutationFn: (id) => prayerService.remove(id), onSuccess: () => { setSelected(null); refresh(); } });

  let rows = listQuery.data?.data ?? [];
  if (status === 'open') rows = rows.filter((r) => ['new', 'praying'].includes(r.status));
  const tabs = [{ id: 'open', label: 'Open' }, ...PRAYER_STATUSES.map((s) => ({ id: s.value, label: s.label })), { id: 'all', label: 'All' }];

  return (
    <section className="space-y-5">
      <PageHeader
        title="Prayer Requests"
        subtitle="Requests from the welcome card, the public prayer page and your team. Confidential ones are marked."
        action={<button type="button" className="btn-primary" onClick={() => { setError(''); setAdding(true); }}><Plus size={16} /> Add request</button>}
      />
      <Tabs items={tabs} value={status} onChange={setStatus} />

      {listQuery.isLoading ? <SkeletonRows /> : rows.length === 0 ? (
        <div className="panel"><EmptyState icon={HandHeart} label="No prayer requests here" sublabel="Share your prayer link from Settings › Public links." /></div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {rows.map((r) => (
            <article key={r.id} className="panel flex flex-col p-5">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="truncate font-bold text-slate-900">{r.name || 'Anonymous'}</p>
                  <p className="text-xs text-slate-500">{formatDateTime(r.created_at)}{r.source === 'form' ? ' · online' : ''}</p>
                </div>
                <div className="flex flex-shrink-0 items-center gap-1">
                  {r.is_confidential ? <Lock size={14} className="text-accent-700" aria-label="Confidential" /> : null}
                  <Badge variant={STATUS_VARIANT[r.status]}>{r.status}</Badge>
                </div>
              </div>
              {r.category ? <p className="mt-2 text-xs font-semibold uppercase tracking-wide text-church-700">{r.category}</p> : null}
              <p className="mt-2 line-clamp-4 flex-1 whitespace-pre-wrap text-sm text-slate-700">{r.request}</p>
              <div className="mt-4 flex items-center justify-between gap-2 border-t border-slate-100 pt-3">
                <button type="button" className="btn-ghost" onClick={() => prayed.mutate(r.id)}><HandHeart size={14} /> Prayed{r.prayed_count ? ` · ${r.prayed_count}` : ''}</button>
                <button type="button" className="btn-ghost" onClick={() => { setError(''); setSelected(r); setNotes(r.response_notes || ''); }}>Open</button>
              </div>
            </article>
          ))}
        </div>
      )}

      <Drawer open={adding} onClose={() => setAdding(false)} title="Add prayer request" footer={<button type="submit" form="prayer-form" className="btn-primary" disabled={create.isPending}>{create.isPending ? 'Saving…' : 'Save request'}</button>}>
        <form id="prayer-form" className="space-y-4" onSubmit={(e) => { e.preventDefault(); create.mutate(); }}>
          <Field label="Member (optional)"><MemberPicker value={form.member} onChange={(member) => setForm((p) => ({ ...p, member }))} /></Field>
          {!form.member && <Field label="Name (if not a member)"><input className="field" value={form.name} onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))} /></Field>}
          <Field label="Phone"><input className="field" value={form.phone} onChange={(e) => setForm((p) => ({ ...p, phone: e.target.value }))} /></Field>
          <Field label="Request" required><textarea className="field min-h-[120px]" required minLength={3} value={form.request} onChange={(e) => setForm((p) => ({ ...p, request: e.target.value }))} /></Field>
          <Field label="Category"><select className="field capitalize" value={form.category} onChange={(e) => setForm((p) => ({ ...p, category: e.target.value }))}><option value="">—</option>{PRAYER_CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}</select></Field>
          <label className="flex items-center gap-2 text-sm text-slate-700"><input type="checkbox" checked={form.is_confidential} onChange={(e) => setForm((p) => ({ ...p, is_confidential: e.target.checked }))} /> Confidential (pastors only)</label>
          <Alert tone="error">{error}</Alert>
        </form>
      </Drawer>

      <Drawer open={Boolean(selected)} onClose={() => setSelected(null)} title={selected?.name || 'Anonymous request'} subtitle={selected ? formatDateTime(selected.created_at) : ''}
        footer={selected ? (
          <div className="flex flex-wrap justify-between gap-2">
            {role === 'church_admin' ? <button type="button" className="btn-ghost text-accent-700" onClick={() => remove.mutate(selected.id)}><Trash2 size={14} /> Delete</button> : <span />}
            <button type="button" className="btn-primary" disabled={update.isPending} onClick={() => update.mutate({ id: selected.id, response_notes: notes })}>Save notes</button>
          </div>
        ) : null}
      >
        {selected && (
          <div className="space-y-5">
            {selected.is_confidential ? <Alert tone="warn">Confidential: share only with the pastoral team.</Alert> : null}
            <p className="whitespace-pre-wrap rounded-2xl bg-slate-50 p-4 text-sm text-slate-800">{selected.request}</p>
            <div className="text-sm text-slate-600">
              {selected.phone ? <p>Phone: <a className="font-semibold text-brand-700" href={`tel:${selected.phone}`}>{selected.phone}</a></p> : null}
              {selected.email ? <p>Email: {selected.email}</p> : null}
              <p>Prayed for {selected.prayed_count} time{selected.prayed_count === 1 ? '' : 's'}</p>
            </div>
            <div>
              <p className="mb-2 text-sm font-semibold text-slate-700">Status</p>
              <div className="flex flex-wrap gap-2">
                {PRAYER_STATUSES.map((s) => (
                  <button key={s.value} type="button" onClick={() => update.mutate({ id: selected.id, status: s.value })} className={`rounded-xl px-3 py-1.5 text-sm font-semibold ring-1 ${selected.status === s.value ? 'bg-brand-700 text-white ring-brand-700' : 'bg-white text-slate-600 ring-slate-200'}`}>{s.label}</button>
                ))}
              </div>
            </div>
            <Field label="Pastoral notes / testimony"><textarea className="field min-h-[110px]" value={notes} onChange={(e) => setNotes(e.target.value)} /></Field>
            <Alert tone="error">{error}</Alert>
          </div>
        )}
      </Drawer>
    </section>
  );
}
