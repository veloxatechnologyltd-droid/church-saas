import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Building2, Pencil, Plus, Star } from 'lucide-react';
import { useState } from 'react';
import Alert from '../../components/shared/Alert';
import Badge from '../../components/shared/Badge';
import LoadingSpinner from '../../components/shared/LoadingSpinner';
import { branchService } from '../../services/churchService';
import { errorMessage } from '../../utils/formatters';

export function useBranches(enabled = true) {
  return useQuery({ queryKey: ['branches'], queryFn: () => branchService.list().then((r) => r.data.data), enabled });
}

export default function BranchesManager() {
  const queryClient = useQueryClient();
  const branchesQuery = useBranches();
  const [newBranch, setNewBranch] = useState({ name: '', address: '' });
  const [editing, setEditing] = useState(null);
  const [error, setError] = useState('');
  const refresh = () => queryClient.invalidateQueries({ queryKey: ['branches'] });
  const onError = (err) => setError(errorMessage(err));

  const create = useMutation({ mutationFn: (p) => branchService.create(p), onSuccess: () => { setNewBranch({ name: '', address: '' }); setError(''); refresh(); }, onError });
  const update = useMutation({ mutationFn: ({ id, ...p }) => branchService.update(id, p), onSuccess: () => { setEditing(null); setError(''); refresh(); }, onError });
  const makeMain = useMutation({ mutationFn: (id) => branchService.makeMain(id), onSuccess: refresh, onError });

  const branches = branchesQuery.data ?? [];

  return (
    <div className="space-y-4">
      {branchesQuery.isLoading ? <LoadingSpinner /> : null}
      <div className="space-y-2">
        {branches.map((branch) => (
          <div key={branch.id} className="rounded-2xl border border-slate-200 p-4">
            {editing?.id === branch.id ? (
              <form className="grid gap-3 md:grid-cols-[1fr_1.5fr_auto]" onSubmit={(e) => { e.preventDefault(); update.mutate(editing); }}>
                <input className="field" required value={editing.name} onChange={(e) => setEditing({ ...editing, name: e.target.value })} aria-label="Branch name" />
                <input className="field" value={editing.address ?? ''} onChange={(e) => setEditing({ ...editing, address: e.target.value })} placeholder="Address" aria-label="Branch address" />
                <div className="flex gap-2"><button className="btn-primary" type="submit">Save</button><button className="btn-outline" type="button" onClick={() => setEditing(null)}>Cancel</button></div>
              </form>
            ) : (
              <div className="flex flex-wrap items-center gap-3">
                <Building2 size={20} className="text-slate-400" />
                <div className="min-w-0 flex-1">
                  <p className="flex flex-wrap items-center gap-2 font-semibold text-slate-900">
                    {branch.name}
                    {branch.is_main ? <Badge variant="visitor">Main</Badge> : null}
                    {!branch.is_active ? <Badge variant="inactive">Inactive</Badge> : null}
                  </p>
                  <p className="text-xs text-slate-500">{branch.address || 'No address'}{branch.member_count !== undefined ? ` · ${branch.member_count} members` : ''}</p>
                </div>
                <div className="flex flex-wrap gap-1">
                  <button type="button" className="btn-ghost" onClick={() => setEditing({ id: branch.id, name: branch.name, address: branch.address })}><Pencil size={14} /> Edit</button>
                  {!branch.is_main && branch.is_active && <button type="button" className="btn-ghost" onClick={() => makeMain.mutate(branch.id)}><Star size={14} /> Make main</button>}
                  {!branch.is_main && (
                    <button type="button" className="btn-ghost" onClick={() => update.mutate({ id: branch.id, is_active: !branch.is_active })}>{branch.is_active ? 'Deactivate' : 'Reactivate'}</button>
                  )}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
      <form className="grid gap-3 rounded-2xl bg-slate-50 p-4 md:grid-cols-[1fr_1.5fr_auto]" onSubmit={(e) => { e.preventDefault(); create.mutate(newBranch); }}>
        <input className="field" required placeholder="New branch name, e.g. Kasoa Branch" value={newBranch.name} onChange={(e) => setNewBranch({ ...newBranch, name: e.target.value })} aria-label="New branch name" />
        <input className="field" placeholder="Address (optional)" value={newBranch.address} onChange={(e) => setNewBranch({ ...newBranch, address: e.target.value })} aria-label="New branch address" />
        <button className="btn-primary justify-center" type="submit" disabled={create.isPending}><Plus size={15} /> Add branch</button>
      </form>
      <Alert tone="error">{error}</Alert>
    </div>
  );
}
