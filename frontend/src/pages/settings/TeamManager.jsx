import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { MailPlus, Trash2 } from 'lucide-react';
import { useState } from 'react';
import Alert from '../../components/shared/Alert';
import Badge from '../../components/shared/Badge';
import LoadingSpinner from '../../components/shared/LoadingSpinner';
import { teamService } from '../../services/churchService';
import { useAuthStore } from '../../store/authStore';
import { ROLE_LABELS, ROLES } from '../../utils/constants';
import { errorMessage, formatDate } from '../../utils/formatters';
import { useBranches } from './BranchesManager';

export default function TeamManager({ showMembers = true }) {
  const queryClient = useQueryClient();
  const me = useAuthStore((s) => s.user);
  const teamQuery = useQuery({ queryKey: ['team'], queryFn: () => teamService.list().then((r) => r.data.data), enabled: showMembers });
  const invitesQuery = useQuery({ queryKey: ['invitations'], queryFn: () => teamService.invitations().then((r) => r.data.data) });
  const branchesQuery = useBranches();
  const [invite, setInvite] = useState({ email: '', role: 'secretary', branch_id: '' });
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const onError = (err) => { setNotice(''); setError(errorMessage(err)); };

  const sendInvite = useMutation({
    mutationFn: (p) => teamService.invite({ ...p, branch_id: p.branch_id || null }),
    onSuccess: () => {
      setNotice(`Invitation sent to ${invite.email}.`);
      setError('');
      setInvite({ email: '', role: invite.role, branch_id: '' });
      queryClient.invalidateQueries({ queryKey: ['invitations'] });
    },
    onError,
  });
  const revoke = useMutation({ mutationFn: (id) => teamService.revokeInvitation(id), onSuccess: () => queryClient.invalidateQueries({ queryKey: ['invitations'] }), onError });
  const update = useMutation({
    mutationFn: ({ id, ...p }) => teamService.update(id, p),
    onSuccess: () => { setError(''); queryClient.invalidateQueries({ queryKey: ['team'] }); },
    onError,
  });

  const branches = branchesQuery.data ?? [];
  const invites = (invitesQuery.data ?? []).filter((i) => !i.accepted_at && !i.revoked_at);

  return (
    <div className="space-y-6">
      <form className="grid gap-3 rounded-2xl bg-slate-50 p-4 md:grid-cols-[1.4fr_1fr_1fr_auto]" onSubmit={(e) => { e.preventDefault(); sendInvite.mutate(invite); }}>
        <input className="field" type="email" required placeholder="colleague@email.com" value={invite.email} onChange={(e) => setInvite({ ...invite, email: e.target.value })} aria-label="Email to invite" />
        <select className="field" value={invite.role} onChange={(e) => setInvite({ ...invite, role: e.target.value })} aria-label="Role">
          {ROLES.map((r) => <option key={r} value={r}>{ROLE_LABELS[r]}</option>)}
        </select>
        <select className="field" value={invite.branch_id} onChange={(e) => setInvite({ ...invite, branch_id: e.target.value })} aria-label="Branch access">
          <option value="">All branches</option>
          {branches.filter((b) => b.is_active).map((b) => <option key={b.id} value={b.id}>{b.name} only</option>)}
        </select>
        <button className="btn-primary justify-center" type="submit" disabled={sendInvite.isPending}><MailPlus size={15} /> {sendInvite.isPending ? 'Sending…' : 'Invite'}</button>
      </form>
      <Alert tone="success">{notice}</Alert>
      <Alert tone="error">{error}</Alert>

      {invites.length > 0 && (
        <div>
          <p className="label-caps mb-2">Pending invitations</p>
          <div className="space-y-2">
            {invites.map((inv) => (
              <div key={inv.id} className="flex flex-wrap items-center gap-3 rounded-xl border border-dashed border-slate-300 px-4 py-3">
                <div className="min-w-0 flex-1">
                  <p className="truncate font-semibold text-slate-900">{inv.email}</p>
                  <p className="text-xs text-slate-500">{ROLE_LABELS[inv.role] ?? inv.role} · expires {formatDate(inv.expires_at)}</p>
                </div>
                <button type="button" className="btn-ghost text-accent-700" onClick={() => revoke.mutate(inv.id)}><Trash2 size={14} /> Revoke</button>
              </div>
            ))}
          </div>
        </div>
      )}

      {showMembers && (
        <div>
          <p className="label-caps mb-2">Team</p>
          {teamQuery.isLoading ? <LoadingSpinner /> : null}
          <div className="overflow-x-auto rounded-2xl border border-slate-200">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-50 text-left text-xs font-bold uppercase tracking-wider text-slate-500">
                <tr><th className="px-4 py-3">Person</th><th className="px-4 py-3">Role</th><th className="px-4 py-3">Branch access</th><th className="px-4 py-3">Status</th></tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {(teamQuery.data ?? []).map((row) => {
                  const isMe = row.user_id === me?.id;
                  return (
                    <tr key={row.membership_id}>
                      <td className="px-4 py-3">
                        <p className="font-semibold text-slate-900">{row.member_name || row.email}{isMe ? ' (you)' : ''}</p>
                        {row.member_name ? <p className="text-xs text-slate-500">{row.email}</p> : null}
                      </td>
                      <td className="px-4 py-3">
                        <select className="field py-1.5" value={row.role} disabled={isMe} onChange={(e) => update.mutate({ id: row.membership_id, role: e.target.value })} aria-label={`Role for ${row.email}`}>
                          {ROLES.map((r) => <option key={r} value={r}>{ROLE_LABELS[r]}</option>)}
                        </select>
                      </td>
                      <td className="px-4 py-3">
                        <select className="field py-1.5" value={row.branch_id ?? ''} disabled={isMe} onChange={(e) => update.mutate({ id: row.membership_id, branch_id: e.target.value || null })} aria-label={`Branch for ${row.email}`}>
                          <option value="">All branches</option>
                          {branches.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
                        </select>
                      </td>
                      <td className="px-4 py-3">
                        {isMe ? <Badge variant="active">Active</Badge> : (
                          <button type="button" onClick={() => update.mutate({ id: row.membership_id, is_active: !row.is_active })} className="btn-ghost">
                            {row.is_active ? <Badge variant="active">Active · disable</Badge> : <Badge variant="inactive">Disabled · enable</Badge>}
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
