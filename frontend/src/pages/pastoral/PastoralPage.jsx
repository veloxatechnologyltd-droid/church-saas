import {
  AlertTriangle,
  CalendarClock,
  CheckCircle2,
  HeartPulse,
  Pencil,
  Plus,
  RotateCcw,
  Search,
  UserRoundCheck,
  X,
} from 'lucide-react';
import { useMemo, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import EmptyState from '../../components/shared/EmptyState';
import PageHeader from '../../components/shared/PageHeader';
import { useMembers } from '../../hooks/useMembers';
import { pastoralService } from '../../services/pastoralService';
import { useAuthStore } from '../../store/authStore';

const LOG_TYPES = [
  { value: 'visit', label: 'Visit' },
  { value: 'call', label: 'Call' },
  { value: 'counselling', label: 'Counselling' },
  { value: 'prayer', label: 'Prayer' },
  { value: 'welfare', label: 'Welfare' },
];

const PRIORITIES = [
  { value: 'low', label: 'Low' },
  { value: 'normal', label: 'Normal' },
  { value: 'high', label: 'High' },
  { value: 'urgent', label: 'Urgent' },
];

const PRIORITY_STYLES = {
  low: 'bg-slate-100 text-slate-600',
  normal: 'bg-brand-50 text-brand-700',
  high: 'bg-amber-50 text-amber-700',
  urgent: 'bg-accent-50 text-accent-700',
};

const DUE_STYLES = {
  overdue: 'bg-accent-50 text-accent-700',
  due_today: 'bg-amber-50 text-amber-700',
  upcoming: 'bg-brand-50 text-brand-700',
  unscheduled: 'bg-slate-100 text-slate-500',
  completed: 'bg-success-50 text-success-700',
};

const DUE_LABELS = {
  overdue: 'Overdue',
  due_today: 'Due today',
  upcoming: 'Upcoming',
  unscheduled: 'No due date',
  completed: 'Completed',
};

function today() {
  return new Date().toISOString().slice(0, 10);
}

function initialForm(ownerId = '') {
  return {
    member_id: '',
    log_type: 'call',
    notes: '',
    log_date: today(),
    follow_up_date: '',
    priority: 'normal',
    assigned_to: ownerId || '',
    source: 'manual',
  };
}

function readableStatus(status) {
  return status?.replace('_', ' ') || 'Unknown';
}

function errorMessage(error) {
  return error?.response?.data?.detail || 'Unable to save this follow-up. Please try again.';
}

export default function PastoralPage() {
  const queryClient = useQueryClient();
  const formRef = useRef(null);
  const { user } = useAuthStore();
  const canCreate = ['church_admin', 'secretary'].includes(user?.role);
  const [form, setForm] = useState(() => initialForm(user?.id));
  const [editingId, setEditingId] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [view, setView] = useState('open');
  const [search, setSearch] = useState('');
  const [memberSearch, setMemberSearch] = useState('');
  const [feedback, setFeedback] = useState(null);

  const logsQuery = useQuery({
    queryKey: ['pastoral-logs'],
    queryFn: () => pastoralService.getAll().then((response) => response.data.data),
  });
  const summaryQuery = useQuery({
    queryKey: ['pastoral-summary'],
    queryFn: () => pastoralService.getSummary().then((response) => response.data.data),
  });
  const risksQuery = useQuery({
    queryKey: ['pastoral-attendance-risks'],
    queryFn: () => pastoralService.getAttendanceRisks({ limit: 25 }).then((response) => response.data.data),
    enabled: canCreate,
  });
  const assigneesQuery = useQuery({
    queryKey: ['pastoral-assignees'],
    queryFn: () => pastoralService.getAssignees().then((response) => response.data.data),
    enabled: canCreate,
  });
  const membersQuery = useMembers({ limit: 100, search: memberSearch || undefined });

  function refreshPastoralData() {
    queryClient.invalidateQueries({ queryKey: ['pastoral-logs'] });
    queryClient.invalidateQueries({ queryKey: ['pastoral-summary'] });
    queryClient.invalidateQueries({ queryKey: ['pastoral-attendance-risks'] });
    queryClient.invalidateQueries({ queryKey: ['reports-dashboard'] });
  }

  function closeForm() {
    setShowForm(false);
    setEditingId(null);
    setForm(initialForm(user?.id));
    setMemberSearch('');
  }

  const saveMutation = useMutation({
    mutationFn: ({ id, payload }) => (
      id ? pastoralService.update(id, payload) : pastoralService.create(payload)
    ),
    onSuccess: (_, { id }) => {
      refreshPastoralData();
      closeForm();
      setFeedback({
        type: 'success',
        text: id ? 'Pastoral follow-up updated.' : 'Pastoral follow-up created and assigned.',
      });
    },
    onError: (error) => setFeedback({ type: 'error', text: errorMessage(error) }),
  });
  const statusMutation = useMutation({
    mutationFn: ({ id, status }) => pastoralService.update(id, { status }),
    onSuccess: (_, { status }) => {
      refreshPastoralData();
      setFeedback({
        type: 'success',
        text: status === 'completed' ? 'Follow-up marked completed.' : 'Follow-up reopened.',
      });
    },
    onError: (error) => setFeedback({ type: 'error', text: errorMessage(error) }),
  });

  const logs = logsQuery.data || [];
  const summary = summaryQuery.data || {};
  const risks = risksQuery.data || [];
  const assignees = assigneesQuery.data || [];
  const members = membersQuery.data?.data || [];

  const visibleLogs = useMemo(() => {
    const keyword = search.trim().toLowerCase();
    return logs.filter((log) => {
      const matchesView = (
        view === 'all'
        || (view === 'open' && log.status === 'open')
        || (view === 'overdue' && log.due_state === 'overdue')
        || (view === 'completed' && log.status === 'completed')
      );
      const matchesSearch = !keyword || [
        log.member_name,
        log.notes,
        log.assignee_name,
        log.log_type,
      ].some((value) => value?.toLowerCase().includes(keyword));
      return matchesView && matchesSearch;
    });
  }, [logs, search, view]);

  function revealForm() {
    setTimeout(() => formRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 0);
  }

  function startNewFollowUp() {
    setEditingId(null);
    setForm(initialForm(user?.id));
    setMemberSearch('');
    setShowForm(true);
    setFeedback(null);
    revealForm();
  }

  function startRiskFollowUp(risk) {
    setEditingId(null);
    setMemberSearch(risk.member_name);
    setForm({
      ...initialForm(user?.id),
      member_id: risk.member_id,
      priority: risk.membership_status === 'inactive' ? 'high' : 'normal',
      source: 'attendance',
      notes: `Member care follow-up: ${risk.reason}.`,
      follow_up_date: today(),
    });
    setShowForm(true);
    setFeedback(null);
    revealForm();
  }

  function editFollowUp(log) {
    setEditingId(log.id);
    setMemberSearch(log.member_name || '');
    setForm({
      member_id: log.member_id,
      log_type: log.log_type,
      notes: log.notes,
      log_date: log.log_date,
      follow_up_date: log.follow_up_date || '',
      priority: log.priority,
      assigned_to: log.assigned_to || '',
      source: log.source,
    });
    setShowForm(true);
    setFeedback(null);
    revealForm();
  }

  function submit(event) {
    event.preventDefault();
    setFeedback(null);
    const payload = {
      log_type: form.log_type,
      notes: form.notes,
      follow_up_date: form.follow_up_date || null,
      priority: form.priority,
      assigned_to: form.assigned_to || null,
      ...(editingId ? {} : {
        member_id: form.member_id,
        log_date: form.log_date,
        source: form.source,
      }),
    };
    saveMutation.mutate({ id: editingId, payload });
  }

  return (
    <section className="space-y-5">
      <PageHeader
        title="Pastoral Follow-Up"
        subtitle="Turn attendance concerns and member care needs into assigned, trackable actions."
        action={canCreate ? (
          <button type="button" className="btn-primary" onClick={startNewFollowUp}>
            <Plus size={15} /> Record Follow-Up
          </button>
        ) : null}
      />

      {feedback && (
        <p className={`rounded-xl px-4 py-3 text-sm font-medium ring-1 ${
          feedback.type === 'error'
            ? 'bg-accent-50 text-accent-700 ring-accent-100'
            : 'bg-success-50 text-success-700 ring-success-100'
        }`}>
          {feedback.text}
        </p>
      )}

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {[
          { label: 'Open Care', value: summary.open || 0, icon: HeartPulse, tone: 'text-brand-700 bg-brand-50' },
          { label: 'Overdue', value: summary.overdue || 0, icon: AlertTriangle, tone: 'text-accent-700 bg-accent-50' },
          { label: 'Due Today', value: summary.due_today || 0, icon: CalendarClock, tone: 'text-amber-700 bg-amber-50' },
          { label: 'Completed', value: summary.completed || 0, icon: CheckCircle2, tone: 'text-success-700 bg-success-50' },
        ].map(({ label, value, icon: Icon, tone }) => (
          <div key={label} className="panel flex items-center gap-4 p-4">
            <div className={`rounded-xl p-3 ${tone}`}><Icon size={20} /></div>
            <div><p className="text-2xl font-extrabold text-slate-900">{value}</p><p className="text-xs font-semibold text-slate-500">{label}</p></div>
          </div>
        ))}
      </div>

      {canCreate && (
        <div className="panel p-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="label-caps">Needs attention</p>
              <h2 className="mt-1 text-lg font-bold text-slate-900">Attendance and membership concerns</h2>
              <p className="mt-1 text-sm text-slate-500">Members with an open follow-up are removed from this list automatically.</p>
            </div>
            <span className="rounded-full bg-amber-50 px-3 py-1 text-xs font-bold text-amber-700">{risks.length} suggested</span>
          </div>
          {risksQuery.isLoading && <p className="mt-4 text-sm text-slate-500">Checking member care risks…</p>}
          {!risksQuery.isLoading && !risks.length && <p className="mt-4 rounded-xl bg-success-50 p-4 text-sm font-medium text-success-700">No unassigned attendance or inactive-member concerns.</p>}
          <div className="mt-4 grid gap-3 lg:grid-cols-2">
            {risks.slice(0, 6).map((risk) => (
              <div key={risk.member_id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 p-4">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-semibold text-slate-900">{risk.member_name}</p>
                    <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-semibold capitalize text-slate-600">{readableStatus(risk.membership_status)}</span>
                  </div>
                  <p className="mt-1 text-xs text-slate-500">{risk.reason}</p>
                </div>
                <button type="button" className="btn-outline" onClick={() => startRiskFollowUp(risk)}>
                  <Plus size={14} /> Start follow-up
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {showForm && (
        <form ref={formRef} onSubmit={submit} className="panel scroll-mt-20 space-y-5 p-6">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="text-lg font-bold text-slate-900">{editingId ? 'Update care plan' : 'Create care plan'}</h2>
              <p className="mt-1 text-sm text-slate-500">Record the concern, assign an owner, and set the next action date.</p>
            </div>
            <button type="button" className="btn-ghost" onClick={closeForm}><X size={16} /> Close</button>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="md:col-span-2">
              <label className="mb-1.5 block text-sm font-semibold text-slate-700">Find member</label>
              <div className="relative">
                <Search size={16} className="absolute left-4 top-3.5 text-slate-400" />
                <input
                  className="field pl-10"
                  value={memberSearch}
                  onChange={(event) => setMemberSearch(event.target.value)}
                  placeholder="Search by name, phone, or email"
                  disabled={Boolean(editingId)}
                />
              </div>
            </div>
            <div className="md:col-span-2">
              <label className="mb-1.5 block text-sm font-semibold text-slate-700">Member *</label>
              <select
                required
                className="field"
                value={form.member_id}
                onChange={(event) => setForm({ ...form, member_id: event.target.value })}
                disabled={Boolean(editingId)}
              >
                <option value="">Select member</option>
                {members.map((member) => (
                  <option key={member.id} value={member.id}>
                    {member.first_name} {member.last_name} — {readableStatus(member.membership_status)}
                  </option>
                ))}
              </select>
              <p className="mt-1 text-xs text-slate-400">Active, inactive, visitor, and new-convert records are available.</p>
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-semibold text-slate-700">Care action</label>
              <select className="field" value={form.log_type} onChange={(event) => setForm({ ...form, log_type: event.target.value })}>
                {LOG_TYPES.map((type) => <option key={type.value} value={type.value}>{type.label}</option>)}
              </select>
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-semibold text-slate-700">Priority</label>
              <select className="field" value={form.priority} onChange={(event) => setForm({ ...form, priority: event.target.value })}>
                {PRIORITIES.map((priority) => <option key={priority.value} value={priority.value}>{priority.label}</option>)}
              </select>
            </div>
            {!editingId && (
              <div>
                <label className="mb-1.5 block text-sm font-semibold text-slate-700">Date recorded</label>
                <input type="date" className="field" value={form.log_date} onChange={(event) => setForm({ ...form, log_date: event.target.value })} />
              </div>
            )}
            <div>
              <label className="mb-1.5 block text-sm font-semibold text-slate-700">Next follow-up date</label>
              <input type="date" className="field" value={form.follow_up_date} onChange={(event) => setForm({ ...form, follow_up_date: event.target.value })} />
            </div>
            {canCreate ? (
              <div className={editingId ? '' : 'md:col-span-2'}>
                <label className="mb-1.5 block text-sm font-semibold text-slate-700">Care owner *</label>
                <select required className="field" value={form.assigned_to} onChange={(event) => setForm({ ...form, assigned_to: event.target.value })}>
                  <option value="">Select responsible staff member</option>
                  {assignees.map((assignee) => (
                    <option key={assignee.id} value={assignee.id}>{assignee.email} — {readableStatus(assignee.role)}</option>
                  ))}
                </select>
              </div>
            ) : (
              <div>
                <label className="mb-1.5 block text-sm font-semibold text-slate-700">Care owner</label>
                <div className="field bg-slate-50">{user?.email}</div>
              </div>
            )}
            <div className="md:col-span-2">
              <label className="mb-1.5 block text-sm font-semibold text-slate-700">Care notes *</label>
              <textarea
                required
                className="field min-h-32 resize-y"
                value={form.notes}
                onChange={(event) => setForm({ ...form, notes: event.target.value })}
                placeholder="Record the concern, conversation, agreed action, and anything the next person should know."
              />
            </div>
          </div>
          <button type="submit" className="btn-primary justify-center" disabled={saveMutation.isPending}>
            <UserRoundCheck size={16} /> {saveMutation.isPending ? 'Saving…' : editingId ? 'Save changes' : 'Create follow-up'}
          </button>
        </form>
      )}

      <div className="panel p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap gap-2">
            {[
              { id: 'open', label: 'Open', count: summary.open || 0 },
              { id: 'overdue', label: 'Overdue', count: summary.overdue || 0 },
              { id: 'completed', label: 'Completed', count: summary.completed || 0 },
              { id: 'all', label: 'All', count: logs.length },
            ].map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => setView(item.id)}
                className={`rounded-xl px-3 py-2 text-sm font-semibold transition ${
                  view === item.id ? 'bg-brand-700 text-white' : 'bg-slate-50 text-slate-600 hover:bg-slate-100'
                }`}
              >
                {item.label} <span className="ml-1 opacity-75">{item.count}</span>
              </button>
            ))}
          </div>
          <div className="relative w-full sm:w-72">
            <Search size={15} className="absolute left-3 top-3 text-slate-400" />
            <input className="field py-2 pl-9" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search follow-ups" />
          </div>
        </div>
      </div>

      {logsQuery.isLoading && <div className="panel p-8 text-sm text-slate-500">Loading pastoral care work…</div>}
      {logsQuery.isError && <div className="panel p-8 text-sm text-accent-700">Unable to load pastoral follow-ups.</div>}
      {!logsQuery.isLoading && !visibleLogs.length && (
        <div className="panel p-8">
          <EmptyState icon={HeartPulse} label={`No ${view === 'all' ? '' : `${view} `}follow-ups`} sublabel="Change the view or create a new care plan." />
        </div>
      )}

      <div className="space-y-3">
        {visibleLogs.map((log) => (
          <article key={log.id} className={`panel border-l-4 p-5 ${
            log.due_state === 'overdue' ? 'border-l-accent-700' : log.priority === 'urgent' ? 'border-l-amber-700' : 'border-l-brand-700'
          }`}>
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="font-bold text-slate-900">{log.member_name}</h3>
                  <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold capitalize text-slate-600">{readableStatus(log.member_status)}</span>
                  <span className={`rounded-full px-2.5 py-1 text-xs font-semibold capitalize ${PRIORITY_STYLES[log.priority]}`}>{log.priority} priority</span>
                  <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${DUE_STYLES[log.due_state]}`}>{DUE_LABELS[log.due_state]}</span>
                </div>
                <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-slate-700">{log.notes}</p>
                <div className="mt-3 flex flex-wrap gap-x-5 gap-y-2 text-xs text-slate-500">
                  <span className="capitalize">{LOG_TYPES.find((type) => type.value === log.log_type)?.label || log.log_type}</span>
                  <span>Recorded {log.log_date}</span>
                  <span>{log.follow_up_date ? `Next action ${log.follow_up_date}` : 'No next action date'}</span>
                  <span>Owner: {log.assignee_name || 'Unassigned'}</span>
                  {log.source === 'attendance' && <span className="font-semibold text-amber-700">Attendance-generated</span>}
                  {log.completed_at && <span>Completed {new Date(log.completed_at).toLocaleDateString('en-GH')}</span>}
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                <button type="button" className="btn-outline" onClick={() => editFollowUp(log)}>
                  <Pencil size={14} /> Edit
                </button>
                {log.status === 'open' ? (
                  <button
                    type="button"
                    className="btn-primary"
                    disabled={statusMutation.isPending}
                    onClick={() => statusMutation.mutate({ id: log.id, status: 'completed' })}
                  >
                    <CheckCircle2 size={15} /> Complete
                  </button>
                ) : (
                  <button
                    type="button"
                    className="btn-outline"
                    disabled={statusMutation.isPending}
                    onClick={() => statusMutation.mutate({ id: log.id, status: 'open' })}
                  >
                    <RotateCcw size={14} /> Reopen
                  </button>
                )}
              </div>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
