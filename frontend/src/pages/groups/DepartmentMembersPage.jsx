import { ArrowLeft, UserMinus, UserPlus, UsersRound } from 'lucide-react';
import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import EmptyState from '../../components/shared/EmptyState';
import PageHeader from '../../components/shared/PageHeader';
import { useMembers } from '../../hooks/useMembers';
import { groupsService } from '../../services/groupsService';

function errorMessage(error) {
  return error?.response?.data?.detail || 'Something went wrong. Please try again.';
}

export default function DepartmentMembersPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [memberId, setMemberId] = useState('');
  const [feedback, setFeedback] = useState(null);

  const groupQuery = useQuery({
    queryKey: ['group', id],
    queryFn: () => groupsService.get(id).then((response) => response.data.data),
  });
  const membersQuery = useMembers({ limit: 2000, status: 'active' });
  const groupMembersQuery = useQuery({
    queryKey: ['group-members', id],
    queryFn: () => groupsService.getMembers(id).then((response) => response.data.data),
  });

  const addMutation = useMutation({
    mutationFn: () => groupsService.addMember(id, memberId),
    onSuccess: () => {
      setMemberId('');
      setFeedback({ type: 'success', text: 'Member added to the department.' });
      queryClient.invalidateQueries({ queryKey: ['group', id] });
      queryClient.invalidateQueries({ queryKey: ['group-members', id] });
      queryClient.invalidateQueries({ queryKey: ['groups'] });
    },
    onError: (error) => setFeedback({ type: 'error', text: errorMessage(error) }),
  });
  const removeMutation = useMutation({
    mutationFn: (member) => groupsService.removeMember(id, member.member_id),
    onSuccess: () => {
      setFeedback({ type: 'success', text: 'Member removed from the department.' });
      queryClient.invalidateQueries({ queryKey: ['group', id] });
      queryClient.invalidateQueries({ queryKey: ['group-members', id] });
      queryClient.invalidateQueries({ queryKey: ['groups'] });
    },
    onError: (error) => setFeedback({ type: 'error', text: errorMessage(error) }),
  });

  const group = groupQuery.data;
  const members = membersQuery.data?.data || [];
  const assignedMembers = groupMembersQuery.data || [];
  const assignedIds = new Set(assignedMembers.map((member) => member.member_id));

  if (groupQuery.isLoading) return <div className="panel p-8 text-sm text-slate-500">Loading department…</div>;
  if (groupQuery.isError || !group) return <div className="panel p-8 text-sm text-accent-700">Unable to load this department.</div>;

  return (
    <section className="space-y-5">
      <PageHeader
        title={`${group.name} Members`}
        subtitle={group.description || 'Manage the members serving in this complete ministry team.'}
        action={<button type="button" className="btn-outline" onClick={() => navigate('/groups')}><ArrowLeft size={15} /> Back to departments</button>}
      />

      {feedback && <p className={`rounded-xl px-4 py-3 text-sm font-medium ring-1 ${feedback.type === 'error' ? 'bg-accent-50 text-accent-700 ring-accent-100' : 'bg-success-50 text-success-700 ring-success-100'}`}>{feedback.text}</p>}

      <div className="grid gap-5 lg:grid-cols-[0.9fr_1.1fr]">
        <div className="panel p-6">
          <div className="flex items-center gap-3"><div className="rounded-xl bg-brand-50 p-3 text-brand-700"><UsersRound size={20} /></div><div><p className="label-caps">Department team</p><p className="text-sm text-slate-500">{assignedMembers.length} active members</p></div></div>
          <div className="mt-6 space-y-3"><label className="block text-sm font-semibold text-slate-700" htmlFor="member-select">Add an active member</label><select id="member-select" className="field" value={memberId} onChange={(event) => setMemberId(event.target.value)}><option value="">Select a member</option>{members.filter((member) => !assignedIds.has(member.id)).map((member) => <option key={member.id} value={member.id}>{member.first_name} {member.last_name}</option>)}</select><button type="button" className="btn-primary w-full justify-center" disabled={!memberId || addMutation.isPending} onClick={() => addMutation.mutate()}><UserPlus size={15} /> {addMutation.isPending ? 'Adding…' : 'Add member'}</button></div>
        </div>

        <div className="panel p-6"><p className="label-caps">Current members</p><div className="mt-4 divide-y divide-slate-100">{assignedMembers.map((member) => <div key={member.id} className="flex items-center justify-between gap-3 py-3"><Link to={`/members/${member.member_id}`} className="group min-w-0 rounded-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-700 focus-visible:ring-offset-2" aria-label={`Open ${member.member_name}'s profile`}><p className="truncate text-sm font-semibold text-brand-700 group-hover:text-brand-800 group-hover:underline">{member.member_name}</p><p className="truncate text-xs text-slate-500">{member.phone || 'No phone number'}</p></Link><button type="button" className="btn-ghost text-accent-700 hover:bg-accent-50" disabled={removeMutation.isPending} onClick={() => removeMutation.mutate(member)}><UserMinus size={14} /> Remove</button></div>)}{!groupMembersQuery.isLoading && !assignedMembers.length && <EmptyState icon={UsersRound} label="No members assigned" sublabel="Use the form to add the first member to this department." />}</div></div>
      </div>
    </section>
  );
}
