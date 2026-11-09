import { Clock3, History, Megaphone, Pencil, Send, Smartphone, Trash2, Users, X } from 'lucide-react';
import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import PageHeader from '../../components/shared/PageHeader';
import { communicationService } from '../../services/communicationService';
import { groupsService } from '../../services/groupsService';
import { useAuthStore } from '../../store/authStore';

const DAYS = [
  { value: 0, label: 'Monday' }, { value: 1, label: 'Tuesday' }, { value: 2, label: 'Wednesday' },
  { value: 3, label: 'Thursday' }, { value: 4, label: 'Friday' }, { value: 5, label: 'Saturday' },
  { value: 6, label: 'Sunday' },
];

const AUDIENCE_OPTIONS = [
  { value: 'all_members', label: 'All members' },
  { value: 'active_members', label: 'Active members' },
  { value: 'inactive_members', label: 'Inactive members' },
  { value: 'department', label: 'One department' },
];

const initialSchedule = {
  name: 'Sunday Service Reminder',
  message_template: 'Dear member, this is a reminder that our Sunday church service is tomorrow. We look forward to worshipping with you.',
  weekday: 6,
  send_time: '',
  audience_type: 'all_members',
  group_id: '',
};

function errorMessage(error) {
  return error?.response?.data?.detail || 'Something went wrong. Please try again.';
}

function formatDate(value) {
  if (!value) return '—';
  return new Intl.DateTimeFormat('en-GH', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value));
}

function formatReminderTime(value) {
  if (!value) return 'Time not set';
  const [hours, minutes] = value.split(':').map(Number);
  const date = new Date(2000, 0, 1, hours, minutes);
  return new Intl.DateTimeFormat('en-GH', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  }).format(date);
}

function formatAudience(audienceType, groupName) {
  if (audienceType === 'department') return groupName || 'Department';
  return AUDIENCE_OPTIONS.find((option) => option.value === audienceType)?.label || 'Members';
}

export default function CommunicationPage() {
  const queryClient = useQueryClient();
  const [tab, setTab] = useState('send');
  const [audienceType, setAudienceType] = useState('all_members');
  const [groupId, setGroupId] = useState('');
  const [message, setMessage] = useState('');
  const [schedule, setSchedule] = useState(initialSchedule);
  const [editingReminderId, setEditingReminderId] = useState(null);
  const [announcement, setAnnouncement] = useState({ title: '', body: '', expires_at: '' });
  const [feedback, setFeedback] = useState(null);
  const { user } = useAuthStore();

  const groupsQuery = useQuery({
    queryKey: ['groups'],
    queryFn: () => groupsService.getAll().then((response) => response.data.data),
  });
  const healthQuery = useQuery({
    queryKey: ['communication-health'],
    queryFn: () => communicationService.getHealth().then((response) => response.data.data),
  });
  const historyQuery = useQuery({
    queryKey: ['communication-history'],
    queryFn: () => communicationService.getHistory().then((response) => response.data.data),
    enabled: tab === 'history',
  });
  const remindersQuery = useQuery({
    queryKey: ['reminders'],
    queryFn: () => communicationService.getReminders({ include_inactive: true }).then((response) => response.data.data),
    enabled: tab === 'reminders',
  });
  const announcementsQuery = useQuery({
    queryKey: ['announcements', 'admin'],
    queryFn: () => communicationService.getAnnouncements({ include_inactive: true }).then((response) => response.data.data),
    enabled: tab === 'announcements' && ['church_admin', 'secretary'].includes(user?.role),
  });

  const sendMutation = useMutation({
    mutationFn: () => communicationService.sendSms({
      message,
      audience_type: audienceType,
      group_id: audienceType === 'department' ? groupId : undefined,
    }),
    onSuccess: (response) => {
      const item = response.data.data;
      setMessage('');
      setFeedback({ type: 'success', text: `${item.successful_count || item.recipient_count} SMS message(s) queued successfully.` });
      queryClient.invalidateQueries({ queryKey: ['communication-history'] });
    },
    onError: (error) => setFeedback({ type: 'error', text: errorMessage(error) }),
  });
  const saveReminderMutation = useMutation({
    mutationFn: ({ id, payload }) => (
      id
        ? communicationService.updateReminder(id, payload)
        : communicationService.createReminder(payload)
    ),
    onSuccess: (_, { id }) => {
      setSchedule({ ...initialSchedule });
      setEditingReminderId(null);
      setFeedback({ type: 'success', text: id ? 'Automatic SMS reminder updated.' : 'Automatic SMS reminder saved.' });
      queryClient.invalidateQueries({ queryKey: ['reminders'] });
    },
    onError: (error) => setFeedback({ type: 'error', text: errorMessage(error) }),
  });
  const removeReminderMutation = useMutation({
    mutationFn: (id) => communicationService.removeReminder(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['reminders'] }),
    onError: (error) => setFeedback({ type: 'error', text: errorMessage(error) }),
  });
  const createAnnouncementMutation = useMutation({
    mutationFn: () => communicationService.createAnnouncement({
      title: announcement.title,
      body: announcement.body,
      expires_at: announcement.expires_at ? new Date(announcement.expires_at).toISOString() : undefined,
    }),
    onSuccess: () => {
      setAnnouncement({ title: '', body: '', expires_at: '' });
      setFeedback({ type: 'success', text: 'Announcement published.' });
      queryClient.invalidateQueries({ queryKey: ['announcements'] });
    },
    onError: (error) => setFeedback({ type: 'error', text: errorMessage(error) }),
  });
  const removeAnnouncementMutation = useMutation({
    mutationFn: (id) => communicationService.removeAnnouncement(id),
    onSuccess: () => {
      setFeedback({ type: 'success', text: 'Announcement archived.' });
      queryClient.invalidateQueries({ queryKey: ['announcements'] });
    },
    onError: (error) => setFeedback({ type: 'error', text: errorMessage(error) }),
  });

  function submitSms(event) {
    event.preventDefault();
    setFeedback(null);
    sendMutation.mutate();
  }

  function submitReminder(event) {
    event.preventDefault();
    setFeedback(null);
    saveReminderMutation.mutate({
      id: editingReminderId,
      payload: {
        ...schedule,
        weekday: Number(schedule.weekday),
        group_id: schedule.audience_type === 'department' ? schedule.group_id : undefined,
      },
    });
  }

  function editReminder(reminder) {
    setEditingReminderId(reminder.id);
    setSchedule({
      name: reminder.name,
      message_template: reminder.message_template,
      weekday: reminder.weekday,
      send_time: reminder.send_time?.slice(0, 5) || '',
      audience_type: reminder.audience_type,
      group_id: reminder.group_id || '',
    });
    setFeedback(null);
  }

  function cancelReminderEdit() {
    setEditingReminderId(null);
    setSchedule({ ...initialSchedule });
    setFeedback(null);
  }

  function submitAnnouncement(event) {
    event.preventDefault();
    setFeedback(null);
    createAnnouncementMutation.mutate();
  }

  const groups = groupsQuery.data || [];
  const reminders = remindersQuery.data || [];
  const history = historyQuery.data || [];
  const announcements = announcementsQuery.data || [];

  return (
    <section className="space-y-5">
      <PageHeader title="Communication" subtitle="Send church-wide or department-specific SMS messages and reminders." />

      <div className="flex flex-wrap gap-2">
        {[
          { id: 'send', label: 'Send SMS', icon: Send },
          { id: 'reminders', label: 'Automatic Reminders', icon: Clock3 },
          { id: 'history', label: 'History', icon: History },
          ...(['church_admin', 'secretary'].includes(user?.role) ? [{ id: 'announcements', label: 'Announcements', icon: Megaphone }] : []),
        ].map(({ id, label, icon: Icon }) => (
          <button key={id} type="button" onClick={() => { setTab(id); setFeedback(null); }} className={`btn-outline ${tab === id ? 'border-brand-700 bg-brand-50 text-brand-700' : ''}`}>
            <Icon size={15} /> {label}
          </button>
        ))}
      </div>

      {feedback && <p className={`rounded-xl px-4 py-3 text-sm font-medium ring-1 ${feedback.type === 'error' ? 'bg-accent-50 text-accent-700 ring-accent-100' : 'bg-success-50 text-success-700 ring-success-100'}`}>{feedback.text}</p>}

      {healthQuery.data && <div className={`flex flex-wrap items-center justify-between gap-2 rounded-xl px-4 py-3 text-sm ring-1 ${healthQuery.data.sms_provider_configured && healthQuery.data.sms_provider_supported ? 'bg-success-50 text-success-700 ring-success-100' : 'bg-amber-50 text-amber-700 ring-amber-100'}`}><span><span className="font-semibold">SMS service:</span> {healthQuery.data.sms_provider}</span><span className="font-semibold">{healthQuery.data.sms_provider_configured && healthQuery.data.sms_provider_supported ? 'Ready to send' : 'Provider configuration required'}</span></div>}

      {tab === 'send' && (
        <div className="grid gap-5 lg:grid-cols-[1.1fr_0.9fr]">
          <form onSubmit={submitSms} className="panel space-y-5 p-6">
            <div className="flex items-center gap-3"><div className="rounded-xl bg-brand-50 p-3 text-brand-700"><Smartphone size={20} /></div><div><h2 className="text-lg font-bold text-slate-900">Send an SMS</h2><p className="text-sm text-slate-500">Choose all members, active members, inactive members, or one department.</p></div></div>
            <div>
              <label className="mb-2 block text-sm font-semibold text-slate-700">Audience</label>
              <div className="grid gap-2 sm:grid-cols-2">
                {AUDIENCE_OPTIONS.map(({ value, label }) => (
                  <label key={value} className={`flex cursor-pointer items-center gap-2 rounded-xl border p-3 text-sm font-semibold ${audienceType === value ? 'border-brand-700 bg-brand-50 text-brand-700' : 'border-slate-200 text-slate-700'}`}>
                    <input type="radio" name="audience" value={value} checked={audienceType === value} onChange={() => { setAudienceType(value); setGroupId(''); }} className="accent-brand-700" /> {label}
                  </label>
                ))}
              </div>
            </div>
            {audienceType === 'department' && <select required className="field" value={groupId} onChange={(event) => setGroupId(event.target.value)}><option value="">Select department</option>{groups.map((group) => <option key={group.id} value={group.id}>{group.name} ({group.member_count})</option>)}</select>}
            <div>
              <label className="mb-1.5 block text-sm font-semibold text-slate-700">Message *</label>
              <textarea required className="field min-h-32 resize-y" maxLength={918} value={message} onChange={(event) => setMessage(event.target.value)} placeholder="Write your church message here…" />
              <p className={`mt-1 text-xs ${message.length > 160 ? 'text-church-700' : 'text-slate-400'}`}>{message.length} / 918 characters</p>
            </div>
            <button type="submit" className="btn-primary w-full justify-center" disabled={sendMutation.isPending}><Send size={15} /> {sendMutation.isPending ? 'Sending…' : 'Send SMS'}</button>
          </form>
          <div className="panel p-6"><p className="label-caps">Useful audiences</p><div className="mt-4 space-y-3 text-sm text-slate-600"><p className="flex gap-2"><Users size={16} className="mt-0.5 text-brand-700" /> All members includes active, inactive, visitor, and new-convert records.</p><p className="flex gap-2"><Users size={16} className="mt-0.5 text-success-700" /> Active members is useful for regular church-wide notices.</p><p className="flex gap-2"><Users size={16} className="mt-0.5 text-accent-700" /> Inactive members can receive follow-up and reconnection messages.</p><p className="flex gap-2"><Users size={16} className="mt-0.5 text-church-700" /> A department is available for ministry-specific communication.</p><p className="rounded-xl bg-slate-50 p-3 text-xs text-slate-500">Only members with a phone number can receive SMS. Every send is recorded in History.</p></div></div>
        </div>
      )}

      {tab === 'reminders' && (
        <div className="grid gap-5 lg:grid-cols-[1.1fr_0.9fr]">
          <form onSubmit={submitReminder} className="panel space-y-4 p-6">
            <div><h2 className="text-lg font-bold text-slate-900">{editingReminderId ? 'Edit automatic reminder' : 'Create automatic reminder'}</h2><p className="mt-1 text-sm text-slate-500">Choose the weekly day and time. The schedule uses Africa/Accra time.</p></div>
            <input required className="field" placeholder="Reminder name" value={schedule.name} onChange={(event) => setSchedule({ ...schedule, name: event.target.value })} />
            <div className="grid gap-4 sm:grid-cols-2"><div><label className="mb-1.5 block text-sm font-semibold text-slate-700">Day</label><select className="field" value={schedule.weekday} onChange={(event) => setSchedule({ ...schedule, weekday: event.target.value })}>{DAYS.map((day) => <option key={day.value} value={day.value}>{day.label}</option>)}</select></div><div><label className="mb-1.5 block text-sm font-semibold text-slate-700">Send time *</label><input required type="time" step="60" className="field" value={schedule.send_time} onChange={(event) => setSchedule({ ...schedule, send_time: event.target.value })} /><p className="mt-1 text-xs text-slate-400">Select any time in Africa/Accra time.</p></div></div>
            <div><label className="mb-1.5 block text-sm font-semibold text-slate-700">Audience</label><select className="field" value={schedule.audience_type} onChange={(event) => setSchedule({ ...schedule, audience_type: event.target.value, group_id: '' })}>{AUDIENCE_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></div>
            {schedule.audience_type === 'department' && <select required className="field" value={schedule.group_id} onChange={(event) => setSchedule({ ...schedule, group_id: event.target.value })}><option value="">Select department</option>{groups.map((group) => <option key={group.id} value={group.id}>{group.name}</option>)}</select>}
            <div><label className="mb-1.5 block text-sm font-semibold text-slate-700">SMS template *</label><textarea required maxLength={918} className="field min-h-32 resize-y" value={schedule.message_template} onChange={(event) => setSchedule({ ...schedule, message_template: event.target.value })} /></div>
            <div className="flex flex-wrap gap-2">
              <button type="submit" className="btn-primary justify-center" disabled={saveReminderMutation.isPending}><Clock3 size={15} /> {saveReminderMutation.isPending ? 'Saving…' : editingReminderId ? 'Save changes' : 'Save automatic reminder'}</button>
              {editingReminderId && <button type="button" className="btn-outline justify-center" onClick={cancelReminderEdit} disabled={saveReminderMutation.isPending}><X size={15} /> Cancel edit</button>}
            </div>
          </form>
          <div className="panel p-6"><p className="label-caps">Configured reminders</p><div className="mt-4 space-y-3">{reminders.map((item) => <div key={item.id} className="rounded-xl border border-slate-200 p-4"><div className="flex items-start justify-between gap-3"><div><p className="font-semibold text-slate-900">{item.name}</p><p className="mt-1 text-xs text-slate-500">Every {DAYS.find((day) => day.value === item.weekday)?.label} at {formatReminderTime(item.send_time)} · {formatAudience(item.audience_type, item.group_name)}</p></div><span className={`rounded-full px-2 py-1 text-xs font-semibold ${item.is_active ? 'bg-success-50 text-success-700' : 'bg-slate-100 text-slate-500'}`}>{item.is_active ? 'Active' : 'Paused'}</span></div><p className="mt-3 text-sm text-slate-600">{item.message_template}</p><div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 pt-3"><span className="text-xs text-slate-400">Last run: {formatDate(item.last_run_at)}</span><div className="flex items-center gap-2"><button type="button" className="btn-ghost" onClick={() => editReminder(item)}><Pencil size={14} /> Edit</button>{item.is_active && <button type="button" className="btn-ghost text-accent-700 hover:bg-accent-50" onClick={() => removeReminderMutation.mutate(item.id)}><Trash2 size={14} /> Pause</button>}</div></div></div>)}{!reminders.length && <p className="py-8 text-sm text-slate-500">No automatic reminders configured yet.</p>}</div></div>
        </div>
      )}

      {tab === 'history' && <div className="panel overflow-x-auto"><table className="w-full min-w-[720px] text-left"><thead className="border-b border-slate-200 bg-slate-50"><tr><th className="px-4 py-3 text-xs font-bold uppercase tracking-wider text-slate-500">Date</th><th className="px-4 py-3 text-xs font-bold uppercase tracking-wider text-slate-500">Audience</th><th className="px-4 py-3 text-xs font-bold uppercase tracking-wider text-slate-500">Message</th><th className="px-4 py-3 text-xs font-bold uppercase tracking-wider text-slate-500">Result</th></tr></thead><tbody>{history.map((item) => <tr key={item.id} className="border-b border-slate-100"><td className="px-4 py-3 text-sm text-slate-600">{formatDate(item.sent_at)}</td><td className="px-4 py-3 text-sm font-semibold text-slate-800">{formatAudience(item.audience_type)}</td><td className="max-w-md px-4 py-3 text-sm text-slate-600">{item.body}</td><td className="px-4 py-3 text-sm text-slate-600">{item.successful_count}/{item.recipient_count} successful <span className="ml-1 rounded-full bg-slate-100 px-2 py-1 text-xs">{item.status}</span></td></tr>)} </tbody></table>{!history.length && <p className="p-8 text-center text-sm text-slate-500">No SMS history yet.</p>}</div>}

      {tab === 'announcements' && (
        <div className="grid gap-5 lg:grid-cols-[0.9fr_1.1fr]">
          <form onSubmit={submitAnnouncement} className="panel space-y-4 p-6">
            <div><h2 className="text-lg font-bold text-slate-900">Post an announcement</h2><p className="mt-1 text-sm text-slate-500">Publish an in-app notice for staff and members.</p></div>
            <input required className="field" maxLength={160} placeholder="Announcement title" value={announcement.title} onChange={(event) => setAnnouncement({ ...announcement, title: event.target.value })} />
            <textarea required className="field min-h-40 resize-y" maxLength={5000} placeholder="Write the announcement…" value={announcement.body} onChange={(event) => setAnnouncement({ ...announcement, body: event.target.value })} />
            <div><label className="mb-1.5 block text-sm font-semibold text-slate-700">Expires (optional)</label><input type="datetime-local" className="field" value={announcement.expires_at} onChange={(event) => setAnnouncement({ ...announcement, expires_at: event.target.value })} /></div>
            <button type="submit" className="btn-primary justify-center" disabled={createAnnouncementMutation.isPending}><Megaphone size={15} /> {createAnnouncementMutation.isPending ? 'Publishing…' : 'Publish announcement'}</button>
          </form>
          <div className="panel p-6"><p className="label-caps">Published announcements</p><div className="mt-4 space-y-3">{announcements.map((item) => <div key={item.id} className="rounded-xl border border-slate-200 p-4"><div className="flex items-start justify-between gap-3"><div><p className="font-semibold text-slate-900">{item.title}</p><p className="mt-1 text-xs text-slate-500">Published {formatDate(item.publish_at)}</p></div><span className={`rounded-full px-2 py-1 text-xs font-semibold ${item.is_active ? 'bg-success-50 text-success-700' : 'bg-slate-100 text-slate-500'}`}>{item.is_active ? 'Active' : 'Archived'}</span></div><p className="mt-3 whitespace-pre-wrap text-sm text-slate-600">{item.body}</p>{item.is_active && <button type="button" className="btn-ghost mt-3 text-accent-700 hover:bg-accent-50" onClick={() => removeAnnouncementMutation.mutate(item.id)}><Trash2 size={14} /> Archive</button>}</div>)}{!announcements.length && <p className="py-8 text-sm text-slate-500">No announcements yet.</p>}</div></div>
        </div>
      )}
    </section>
  );
}
