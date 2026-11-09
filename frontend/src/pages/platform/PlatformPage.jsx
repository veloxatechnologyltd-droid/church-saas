import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Activity, Banknote, Building2, Eye, LogOut, MessageSquare, Search, Users } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import Alert from '../../components/shared/Alert';
import Badge from '../../components/shared/Badge';
import Drawer from '../../components/shared/Drawer';
import Field from '../../components/shared/Field';
import LoadingSpinner, { SkeletonRows } from '../../components/shared/LoadingSpinner';
import ProductMark from '../../components/shared/ProductMark';
import StatCard from '../../components/shared/StatCard';
import Tabs from '../../components/shared/Tabs';
import { usePlans } from '../../hooks/usePlans';
import { platformService } from '../../services/churchService';
import { useAuthStore } from '../../store/authStore';
import { errorMessage, formatCurrency, formatDate, formatDateTime } from '../../utils/formatters';
import { applyBrandTheme } from '../../utils/theme';

const STATUS_VARIANT = { active: 'active', trialing: 'visitor', suspended: 'followup', closed: 'inactive' };

function ChurchDrawer({ churchId, onClose }) {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const startImpersonation = useAuthStore((s) => s.startImpersonation);
  const plansQuery = usePlans();
  const detailQuery = useQuery({ queryKey: ['platform-church', churchId], queryFn: () => platformService.church(churchId).then((r) => r.data.data), enabled: Boolean(churchId) });
  const [reason, setReason] = useState('');
  const [plan, setPlan] = useState('');
  const [planStatus, setPlanStatus] = useState('active');
  const [credits, setCredits] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  useEffect(() => {
    setReason(''); setCredits(''); setError(''); setNotice('');
    if (detailQuery.data?.church) setPlan(detailQuery.data.church.plan);
  }, [churchId, detailQuery.data?.church?.plan]); // eslint-disable-line react-hooks/exhaustive-deps

  const done = (message) => () => {
    setError('');
    setNotice(message);
    queryClient.invalidateQueries({ queryKey: ['platform-church', churchId] });
    queryClient.invalidateQueries({ queryKey: ['platform-churches'] });
    queryClient.invalidateQueries({ queryKey: ['platform-stats'] });
    queryClient.invalidateQueries({ queryKey: ['platform-events'] });
  };
  const onError = (err) => { setNotice(''); setError(errorMessage(err)); };
  const suspend = useMutation({ mutationFn: () => platformService.suspend(churchId, reason), onSuccess: done('Church suspended.'), onError });
  const reactivate = useMutation({ mutationFn: () => platformService.reactivate(churchId), onSuccess: done('Church reactivated.'), onError });
  const changePlan = useMutation({ mutationFn: () => platformService.changePlan(churchId, { plan_code: plan, status: planStatus }), onSuccess: done('Plan updated.'), onError });
  const grant = useMutation({ mutationFn: () => platformService.grantSms(churchId, { credits: Number(credits), reason: 'grant' }), onSuccess: done('SMS credits updated.'), onError });
  const impersonate = useMutation({
    mutationFn: () => platformService.impersonate(churchId).then((r) => r.data.data),
    onSuccess: (data) => {
      startImpersonation(data);
      applyBrandTheme(data.active_church);
      queryClient.clear();
      navigate('/dashboard');
    },
    onError,
  });

  const d = detailQuery.data;
  const church = d?.church;
  return (
    <Drawer open={Boolean(churchId)} onClose={onClose} title={church?.name ?? 'Church'} subtitle={church ? `/${church.slug} · created ${formatDate(church.created_at)}` : ''} width="max-w-xl">
      {detailQuery.isLoading ? <LoadingSpinner /> : !d ? null : (
        <div className="space-y-6">
          <div className="flex flex-wrap gap-2">
            <Badge variant={STATUS_VARIANT[church.status]}>{church.status}</Badge>
            <Badge variant="visitor">{d.plan?.name ?? church.plan}</Badge>
            {church.trial_ends_at ? <Badge>trial ends {formatDate(church.trial_ends_at)}</Badge> : null}
          </div>
          <Alert tone="success">{notice}</Alert>
          <Alert tone="error">{error}</Alert>
          <div className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
            {[['Members', d.usage?.members], ['Branches', d.usage?.branches], ['Users', d.usage?.users], ['SMS credits', church.sms_credits]].map(([label, value]) => (
              <div key={label} className="rounded-xl bg-slate-50 p-3"><p className="text-xs text-slate-500">{label}</p><p className="text-lg font-extrabold text-slate-900">{value ?? 0}</p></div>
            ))}
          </div>
          <div className="text-sm text-slate-600">
            <p><span className="font-semibold">Admins:</span> {(d.admins ?? []).join(', ') || '—'}</p>
            {church.phone ? <p><span className="font-semibold">Phone:</span> {church.phone}</p> : null}
            {church.email ? <p><span className="font-semibold">Email:</span> {church.email}</p> : null}
          </div>

          <section className="space-y-3 rounded-2xl border border-slate-200 p-4">
            <p className="font-bold text-slate-900">Support access</p>
            <p className="text-xs text-slate-500">Opens the church as its admin for 30 minutes. Logged in the church's audit trail and the platform log.</p>
            <button type="button" className="btn-outline" disabled={impersonate.isPending || church.status === 'closed'} onClick={() => impersonate.mutate()}><Eye size={15} /> {impersonate.isPending ? 'Opening…' : 'Impersonate church admin'}</button>
          </section>

          <section className="space-y-3 rounded-2xl border border-slate-200 p-4">
            <p className="font-bold text-slate-900">Plan</p>
            <div className="grid gap-3 sm:grid-cols-[1fr_1fr_auto]">
              <select className="field" value={plan} onChange={(e) => setPlan(e.target.value)} aria-label="Plan">{(plansQuery.data ?? []).map((p) => <option key={p.code} value={p.code}>{p.name}</option>)}</select>
              <select className="field" value={planStatus} onChange={(e) => setPlanStatus(e.target.value)} aria-label="Status"><option value="active">Active (paid)</option><option value="trialing">Trialing</option></select>
              <button type="button" className="btn-primary justify-center" disabled={changePlan.isPending} onClick={() => changePlan.mutate()}>Apply</button>
            </div>
          </section>

          <section className="space-y-3 rounded-2xl border border-slate-200 p-4">
            <p className="font-bold text-slate-900">SMS credits</p>
            <div className="flex gap-3">
              <input className="field" type="number" placeholder="e.g. 500 (negative to deduct)" value={credits} onChange={(e) => setCredits(e.target.value)} aria-label="Credits" />
              <button type="button" className="btn-primary" disabled={!credits || grant.isPending} onClick={() => grant.mutate()}>Grant</button>
            </div>
          </section>

          <section className="space-y-3 rounded-2xl border border-accent-100 bg-accent-50/40 p-4">
            <p className="font-bold text-slate-900">Account status</p>
            {church.status === 'suspended' ? (
              <>
                {church.suspended_reason ? <p className="text-sm text-slate-600">Reason: {church.suspended_reason}</p> : null}
                <button type="button" className="btn-primary" disabled={reactivate.isPending} onClick={() => reactivate.mutate()}>Reactivate church</button>
              </>
            ) : (
              <>
                <Field label="Reason for suspension"><input className="field" value={reason} onChange={(e) => setReason(e.target.value)} placeholder="e.g. Unpaid invoice / abuse report" /></Field>
                <button type="button" className="btn-danger" disabled={reason.trim().length < 3 || suspend.isPending || church.status === 'closed'} onClick={() => suspend.mutate()}>Suspend church</button>
              </>
            )}
          </section>

          {(d.invoices ?? []).length > 0 && (
            <section>
              <p className="label-caps mb-2">Invoices</p>
              <div className="space-y-1 text-sm">{d.invoices.map((inv) => <p key={inv.id} className="flex justify-between"><span>{inv.number} · {inv.description}</span><span className="font-semibold">{formatCurrency(inv.amount, inv.currency)} · {inv.status}</span></p>)}</div>
            </section>
          )}
          <section>
            <p className="label-caps mb-2">Recent operator actions</p>
            <div className="space-y-1 text-sm text-slate-600">
              {(d.events ?? []).map((e, i) => <p key={i}><span className="font-semibold">{e.action}</span> · {formatDateTime(e.created_at)}</p>)}
              {!(d.events ?? []).length ? <p>None.</p> : null}
            </div>
          </section>
        </div>
      )}
    </Drawer>
  );
}

export default function PlatformPage() {
  const { user, token, churches, logout } = useAuthStore();
  const navigate = useNavigate();
  const [tab, setTab] = useState('churches');
  const [search, setSearch] = useState('');
  const [debounced, setDebounced] = useState('');
  const [status, setStatus] = useState('');
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    applyBrandTheme(null);
    const t = setTimeout(() => setDebounced(search.trim()), 300);
    return () => clearTimeout(t);
  }, [search]);

  const statsQuery = useQuery({ queryKey: ['platform-stats'], queryFn: () => platformService.stats().then((r) => r.data.data), enabled: Boolean(user?.is_platform_admin) });
  const churchesQuery = useQuery({
    queryKey: ['platform-churches', debounced, status],
    queryFn: () => platformService.churches({ search: debounced || undefined, status: status || undefined, limit: 100 }).then((r) => r.data),
    placeholderData: keepPreviousData,
    enabled: Boolean(user?.is_platform_admin),
  });
  const eventsQuery = useQuery({ queryKey: ['platform-events'], queryFn: () => platformService.events({ limit: 100 }).then((r) => r.data.data), enabled: tab === 'events' });

  if (!token) return <Navigate to="/login" replace />;
  if (!user?.is_platform_admin) return <Navigate to="/dashboard" replace />;

  const s = statsQuery.data;
  return (
    <div className="min-h-screen bg-slate-100">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-3 px-4">
          <div className="flex items-center gap-3"><ProductMark /><span className="hidden rounded-full bg-slate-900 px-2.5 py-0.5 text-xs font-bold text-white sm:inline">Platform</span></div>
          <div className="flex items-center gap-2">
            {churches.length > 0 && <Link to="/select-church" className="btn-outline px-3 py-1.5 text-sm">My churches</Link>}
            <button type="button" className="btn-ghost" onClick={() => { logout(); navigate('/login'); }}><LogOut size={15} /> Sign out</button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl space-y-6 px-4 py-8">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900">Platform console</h1>
          <p className="text-sm text-slate-500">Tenants, revenue and support tools. Signed in as {user.email}.</p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
          <StatCard label="Churches" value={s?.churches_total ?? '–'} helper={s ? `${s.by_status?.active ?? 0} paying · ${s.by_status?.trialing ?? 0} trialing` : ''} icon={Building2} />
          <StatCard label="Signups (30d)" value={s?.signups_last_30_days ?? '–'} icon={Activity} tone="good" />
          <StatCard label="MRR" value={s ? formatCurrency(s.mrr, 'GHS') : '–'} helper={s ? `${formatCurrency(s.revenue_last_30_days ?? 0, 'GHS')} collected (30d)` : ''} icon={Banknote} tone="warn" />
          <StatCard label="Members managed" value={s?.members_total?.toLocaleString() ?? '–'} helper={s ? `${s.users_total} staff users` : ''} icon={Users} />
          <StatCard label="SMS sent (30d)" value={s?.sms_sent_30d?.toLocaleString() ?? '–'} icon={MessageSquare} />
        </div>

        <Tabs items={[{ id: 'churches', label: 'Churches' }, { id: 'events', label: 'Operator log' }]} value={tab} onChange={setTab} />

        {tab === 'churches' ? (
          <div className="panel overflow-hidden">
            <div className="flex flex-col gap-3 border-b border-slate-100 p-4 sm:flex-row">
              <div className="relative flex-1">
                <Search size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                <input className="field pl-9" placeholder="Search by name, slug or email" value={search} onChange={(e) => setSearch(e.target.value)} />
              </div>
              <select className="field sm:w-48" value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Filter by status">
                <option value="">All statuses</option>{['trialing', 'active', 'suspended', 'closed'].map((v) => <option key={v} value={v}>{v}</option>)}
              </select>
            </div>
            {churchesQuery.isLoading ? <div className="p-4"><SkeletonRows /></div> : (
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead className="bg-slate-50 text-left text-xs font-bold uppercase tracking-wider text-slate-500">
                    <tr><th className="px-4 py-3">Church</th><th className="px-4 py-3">Status</th><th className="px-4 py-3">Plan</th><th className="px-4 py-3 text-right">Members</th><th className="px-4 py-3 text-right">Users</th><th className="px-4 py-3 text-right">SMS</th><th className="px-4 py-3">Last active</th></tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {(churchesQuery.data?.data ?? []).map((c) => (
                      <tr key={c.id} className="cursor-pointer hover:bg-brand-50/40" onClick={() => setSelected(c.id)}>
                        <td className="px-4 py-3"><p className="font-semibold text-slate-900">{c.name}</p><p className="text-xs text-slate-500">/{c.slug}{c.country ? ` · ${c.country}` : ''}</p></td>
                        <td className="px-4 py-3"><Badge variant={STATUS_VARIANT[c.status]}>{c.status}</Badge>{c.status === 'trialing' && c.trial_ends_at ? <p className="mt-0.5 text-xs text-slate-400">ends {formatDate(c.trial_ends_at)}</p> : null}</td>
                        <td className="px-4 py-3 capitalize">{c.plan}</td>
                        <td className="px-4 py-3 text-right">{c.member_count}</td>
                        <td className="px-4 py-3 text-right">{c.user_count}</td>
                        <td className="px-4 py-3 text-right">{c.sms_credits}</td>
                        <td className="px-4 py-3 text-slate-500">{c.last_activity_at ? formatDate(c.last_activity_at) : '—'}</td>
                      </tr>
                    ))}
                    {!(churchesQuery.data?.data ?? []).length && <tr><td colSpan={7} className="px-4 py-10 text-center text-slate-500">No churches match.</td></tr>}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        ) : (
          <div className="panel divide-y divide-slate-100">
            {eventsQuery.isLoading ? <div className="p-4"><SkeletonRows /></div> : (eventsQuery.data ?? []).map((e) => (
              <div key={e.id} className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 text-sm">
                <div><span className="font-semibold text-slate-900">{e.action}</span>{e.church_name ? <span className="text-slate-500"> · {e.church_name}</span> : null}
                  {e.details && Object.keys(e.details).length ? <p className="font-mono text-xs text-slate-400">{JSON.stringify(e.details)}</p> : null}</div>
                <span className="text-xs text-slate-500">{formatDateTime(e.created_at)}</span>
              </div>
            ))}
            {!eventsQuery.isLoading && !(eventsQuery.data ?? []).length ? <p className="p-6 text-center text-sm text-slate-500">No operator actions yet.</p> : null}
          </div>
        )}
      </main>
      <ChurchDrawer churchId={selected} onClose={() => setSelected(null)} />
    </div>
  );
}
