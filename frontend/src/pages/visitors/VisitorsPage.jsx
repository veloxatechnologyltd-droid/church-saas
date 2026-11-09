import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { MessageCircle, Phone, Plus, Search, Sparkles, UserCheck, UserPlus, Users } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import Alert from '../../components/shared/Alert';
import Badge from '../../components/shared/Badge';
import Drawer from '../../components/shared/Drawer';
import EmptyState from '../../components/shared/EmptyState';
import Field from '../../components/shared/Field';
import { SkeletonRows } from '../../components/shared/LoadingSpinner';
import PageHeader from '../../components/shared/PageHeader';
import StatCard from '../../components/shared/StatCard';
import Tabs from '../../components/shared/Tabs';
import api from '../../services/api';
import { visitorService } from '../../services/outreachService';
import { useRole } from '../../store/authStore';
import { AGE_GROUPS, HOW_HEARD, VISITOR_STATUSES } from '../../utils/constants';
import { errorMessage, formatDate, todayISO } from '../../utils/formatters';

const STATUS_VARIANT = { new: 'visitor', contacted: 'excused', returning: 'new_convert', converted: 'active', not_interested: 'inactive' };
const EMPTY = {
  first_name: '', last_name: '', phone: '', email: '', gender: '', age_group: '', address: '', visit_date: todayISO(),
  how_heard: '', invited_by: '', prayer_request: '', wants_visit: false, interested_in_membership: false, notes: '',
  status: 'new', assigned_to: '',
};

function cleanPayload(form, isNew) {
  const payload = {};
  Object.entries(form).forEach(([key, value]) => {
    if (isNew && key === 'status') return;
    payload[key] = value === '' ? null : value;
  });
  if (!payload.visit_date) delete payload.visit_date;
  return payload;
}

export default function VisitorsPage() {
  const role = useRole();
  const canWrite = ['church_admin', 'secretary'].includes(role);
  const queryClient = useQueryClient();
  const [status, setStatus] = useState('all');
  const [search, setSearch] = useState('');
  const [debounced, setDebounced] = useState('');
  const [page, setPage] = useState(0);
  const [editing, setEditing] = useState(null); // null | 'new' | visitor
  const [form, setForm] = useState(EMPTY);
  const [error, setError] = useState('');
  const [flash, setFlash] = useState(null);
  const limit = 20;

  useEffect(() => {
    const t = setTimeout(() => { setDebounced(search.trim()); setPage(0); }, 300);
    return () => clearTimeout(t);
  }, [search]);

  const summaryQuery = useQuery({ queryKey: ['visitor-summary'], queryFn: () => visitorService.summary().then((r) => r.data.data) });
  const listQuery = useQuery({
    queryKey: ['visitors', status, debounced, page],
    queryFn: () => visitorService.list({ status: status === 'all' ? undefined : status, search: debounced || undefined, skip: page * limit, limit }).then((r) => r.data),
    placeholderData: keepPreviousData,
  });
  const assigneesQuery = useQuery({
    queryKey: ['assignees'],
    queryFn: () => api.get('/pastoral/assignees').then((r) => r.data.data),
    enabled: canWrite,
  });

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['visitors'] });
    queryClient.invalidateQueries({ queryKey: ['visitor-summary'] });
  };
  const save = useMutation({
    mutationFn: () => (editing === 'new' ? visitorService.create(cleanPayload(form, true)) : visitorService.update(editing.id, cleanPayload(form, false))),
    onSuccess: () => { setEditing(null); refresh(); },
    onError: (err) => setError(errorMessage(err)),
  });
  const contacted = useMutation({ mutationFn: (v) => visitorService.contacted(v.id), onSuccess: refresh });
  const convert = useMutation({
    mutationFn: (v) => visitorService.convert(v.id).then((r) => r.data.data),
    onSuccess: (data) => {
      setEditing(null);
      setFlash({ text: `${data.member?.first_name ?? 'Visitor'} is now a member.`, memberId: data.member?.id });
      refresh();
      queryClient.invalidateQueries({ queryKey: ['members'] });
    },
    onError: (err) => setError(errorMessage(err)),
  });

  function openForm(visitor) {
    setError('');
    if (visitor === 'new') {
      setForm({ ...EMPTY, visit_date: todayISO() });
    } else {
      setForm(Object.fromEntries(Object.keys(EMPTY).map((key) => [key, visitor[key] ?? EMPTY[key]])));
    }
    setEditing(visitor);
  }
  const set = (key) => (e) => setForm((p) => ({ ...p, [key]: e.target.type === 'checkbox' ? e.target.checked : e.target.value }));

  const summary = summaryQuery.data;
  const rows = listQuery.data?.data ?? [];
  const total = listQuery.data?.total ?? 0;
  const tabs = [{ id: 'all', label: 'All' }, ...VISITOR_STATUSES.map((s) => ({ id: s.value, label: s.label, count: summary?.[s.value] }))];

  return (
    <section className="space-y-5">
      <PageHeader
        title="First-timers"
        subtitle="Every guest gets a welcome and a follow-up. Track them from first visit to membership."
        action={canWrite ? <button type="button" className="btn-primary" onClick={() => openForm('new')}><Plus size={16} /> Add first-timer</button> : null}
      />
      {flash ? (
        <Alert tone="success" action={flash.memberId ? <Link className="btn-ghost" to={`/members/${flash.memberId}`}>Open profile</Link> : null}>{flash.text}</Alert>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="New this month" value={summary?.this_month ?? '–'} icon={Sparkles} />
        <StatCard label="Awaiting contact" value={summary?.new ?? '–'} helper={summary?.follow_up_overdue ? `${summary.follow_up_overdue} waiting over 3 days` : 'All caught up'} tone={summary?.follow_up_overdue ? 'danger' : 'good'} icon={Phone} />
        <StatCard label="Returning" value={summary?.returning ?? '–'} icon={Users} tone="warn" />
        <StatCard label="Conversion rate" value={summary ? `${Math.round(Number(summary.conversion_rate ?? 0))}%` : '–'} helper={`${summary?.converted ?? 0} became members`} tone="good" icon={UserCheck} />
      </div>

      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <Tabs items={tabs} value={status} onChange={(id) => { setStatus(id); setPage(0); }} />
        <div className="relative lg:w-72">
          <Search size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input className="field pl-9" placeholder="Search name, phone or email" value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
      </div>

      <div className="panel overflow-hidden">
        {listQuery.isLoading ? <div className="p-4"><SkeletonRows /></div> : rows.length === 0 ? (
          <EmptyState label="No first-timers here yet" sublabel="Share your welcome card link from Settings › Public links, or add guests by hand." icon={Sparkles} />
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="border-b border-slate-200 bg-slate-50 text-left text-xs font-bold uppercase tracking-wider text-slate-500">
                <tr><th className="px-4 py-3">Guest</th><th className="px-4 py-3">Visited</th><th className="px-4 py-3">Status</th><th className="px-4 py-3">Follow-up</th><th className="px-4 py-3 text-right">Actions</th></tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {rows.map((v) => (
                  <tr key={v.id} className="hover:bg-brand-50/40">
                    <td className="px-4 py-3">
                      <button type="button" className="text-left" onClick={() => openForm(v)}>
                        <p className="font-semibold text-slate-900">{v.first_name} {v.last_name}</p>
                        <p className="text-xs text-slate-500">{v.phone || v.email || 'No contact'}{v.source === 'form' ? ' · welcome card' : ''}</p>
                      </button>
                    </td>
                    <td className="px-4 py-3 text-slate-600">{formatDate(v.visit_date)}{v.visit_count > 1 ? <span className="ml-1 text-xs text-slate-400">({v.visit_count} visits)</span> : null}</td>
                    <td className="px-4 py-3"><Badge variant={STATUS_VARIANT[v.status]}>{VISITOR_STATUSES.find((s) => s.value === v.status)?.label ?? v.status}</Badge>
                      {v.wants_visit ? <span className="ml-1 text-xs font-semibold text-church-700">wants a visit</span> : null}</td>
                    <td className="px-4 py-3 text-xs text-slate-500">{v.assignee_email ? `Assigned: ${v.assignee_email}` : 'Unassigned'}{v.last_contacted_at ? <><br />Contacted {formatDate(v.last_contacted_at)}</> : null}</td>
                    <td className="px-4 py-3">
                      {canWrite && (
                        <div className="flex justify-end gap-1">
                          {v.phone ? <a className="btn-ghost" href={`https://wa.me/${v.phone.replace(/\D/g, '').replace(/^0/, '233')}`} target="_blank" rel="noreferrer" title="WhatsApp"><MessageCircle size={14} /></a> : null}
                          {['new', 'returning'].includes(v.status) && <button type="button" className="btn-ghost" onClick={() => contacted.mutate(v)}><Phone size={14} /> Contacted</button>}
                          {v.status !== 'converted' && <button type="button" className="btn-ghost" onClick={() => convert.mutate(v)}><UserPlus size={14} /> Make member</button>}
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {total > limit && (
          <div className="flex items-center justify-between border-t border-slate-100 px-4 py-3 text-sm">
            <span className="text-slate-500">{page * limit + 1}–{Math.min(total, (page + 1) * limit)} of {total}</span>
            <div className="flex gap-2">
              <button type="button" className="btn-outline px-3 py-1.5" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>Previous</button>
              <button type="button" className="btn-outline px-3 py-1.5" disabled={(page + 1) * limit >= total} onClick={() => setPage((p) => p + 1)}>Next</button>
            </div>
          </div>
        )}
      </div>

      <Drawer
        open={Boolean(editing)}
        onClose={() => setEditing(null)}
        title={editing === 'new' ? 'Add first-timer' : `${form.first_name} ${form.last_name}`.trim() || 'First-timer'}
        subtitle={editing && editing !== 'new' && editing.source === 'form' ? 'Submitted through the welcome card' : undefined}
        footer={canWrite ? (
          <div className="flex flex-wrap justify-between gap-2">
            {editing !== 'new' && editing?.status !== 'converted' ? <button type="button" className="btn-outline" onClick={() => convert.mutate(editing)} disabled={convert.isPending}><UserPlus size={15} /> Convert to member</button> : <span />}
            <button type="submit" form="visitor-form" className="btn-primary" disabled={save.isPending}>{save.isPending ? 'Saving…' : 'Save'}</button>
          </div>
        ) : null}
      >
        <form id="visitor-form" className="space-y-4" onSubmit={(e) => { e.preventDefault(); save.mutate(); }}>
          <fieldset disabled={!canWrite} className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="First name" required><input className="field" required value={form.first_name} onChange={set('first_name')} /></Field>
              <Field label="Last name"><input className="field" value={form.last_name} onChange={set('last_name')} /></Field>
              <Field label="Phone"><input className="field" value={form.phone} onChange={set('phone')} /></Field>
              <Field label="Email"><input className="field" type="email" value={form.email} onChange={set('email')} /></Field>
              <Field label="Gender"><select className="field" value={form.gender} onChange={set('gender')}><option value="">—</option><option value="male">Male</option><option value="female">Female</option></select></Field>
              <Field label="Age group"><select className="field capitalize" value={form.age_group} onChange={set('age_group')}><option value="">—</option>{AGE_GROUPS.map((a) => <option key={a} value={a}>{a}</option>)}</select></Field>
              <Field label="Visit date"><input className="field" type="date" value={form.visit_date || ''} onChange={set('visit_date')} /></Field>
              <Field label="How they heard"><select className="field" value={form.how_heard} onChange={set('how_heard')}><option value="">—</option>{HOW_HEARD.map((h) => <option key={h}>{h}</option>)}{form.how_heard && !HOW_HEARD.includes(form.how_heard) ? <option>{form.how_heard}</option> : null}</select></Field>
            </div>
            <Field label="Invited by"><input className="field" value={form.invited_by} onChange={set('invited_by')} /></Field>
            <Field label="Address"><input className="field" value={form.address} onChange={set('address')} /></Field>
            <Field label="Prayer request"><textarea className="field min-h-[70px]" value={form.prayer_request} onChange={set('prayer_request')} /></Field>
            <div className="flex flex-wrap gap-5 text-sm text-slate-700">
              <label className="flex items-center gap-2"><input type="checkbox" checked={form.wants_visit} onChange={set('wants_visit')} /> Wants a visit / call</label>
              <label className="flex items-center gap-2"><input type="checkbox" checked={form.interested_in_membership} onChange={set('interested_in_membership')} /> Interested in membership</label>
            </div>
            <div className="grid gap-4 rounded-2xl bg-slate-50 p-4 sm:grid-cols-2">
              {editing !== 'new' && (
                <Field label="Follow-up status"><select className="field" value={form.status} onChange={set('status')}>{VISITOR_STATUSES.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}</select></Field>
              )}
              <Field label="Assigned to"><select className="field" value={form.assigned_to || ''} onChange={set('assigned_to')}><option value="">Unassigned</option>{(assigneesQuery.data ?? []).map((u) => <option key={u.id} value={u.id}>{u.email}</option>)}</select></Field>
              <Field label="Follow-up notes" className="sm:col-span-2"><textarea className="field min-h-[80px]" value={form.notes} onChange={set('notes')} /></Field>
            </div>
          </fieldset>
          <Alert tone="error">{error}</Alert>
        </form>
      </Drawer>
    </section>
  );
}
