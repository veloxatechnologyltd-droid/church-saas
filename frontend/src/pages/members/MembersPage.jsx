import { AlertTriangle, Download, Filter, Search, UserCheck, UserPlus, Users, X } from 'lucide-react';
import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import Badge from '../../components/shared/Badge';
import DataTable from '../../components/shared/DataTable';
import LoadingSpinner from '../../components/shared/LoadingSpinner';
import PageHeader from '../../components/shared/PageHeader';
import StatCard from '../../components/shared/StatCard';
import { useMembers, useUpdateMember } from '../../hooks/useMembers';
import { memberService } from '../../services/memberService';
import { useAuthStore } from '../../store/authStore';
import { MEMBERSHIP_STATUS } from '../../utils/constants';
import { formatDate } from '../../utils/formatters';
import { resolvePhotoUrl } from '../../utils/media';

const PAGE_SIZE = 20;

const STATUS_BADGE_MAP = {
  active: 'active',
  inactive: 'inactive',
  visitor: 'visitor',
  new_convert: 'new_convert',
};

export default function MembersPage() {
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('');
  const [page, setPage] = useState(1);
  const [message, setMessage] = useState('');
  const { user } = useAuthStore();

  const skip = (page - 1) * PAGE_SIZE;
  const membersQuery = useMembers({ skip, limit: PAGE_SIZE, search: search || undefined, status: status || undefined });
  const updateMutation = useUpdateMember();

  const rows = membersQuery.data?.data ?? [];
  const total = membersQuery.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const activeCount = rows.filter((row) => row.membership_status === 'active').length;
  const lowAttendanceCount = rows.filter((row) => row.low_attendance).length;

  const canEditStatus = ['church_admin', 'secretary'].includes(user?.role);

  async function onStatusChange(memberId, nextStatus) {
    setMessage('');
    await updateMutation.mutateAsync({ id: memberId, payload: { membership_status: nextStatus } });
    setMessage('Member status updated.');
  }

  const columns = useMemo(
    () => [
      {
        key: 'name',
        label: 'Member',
        render: (row) => (
          <div className="flex items-center gap-3">
            {row.photo_url ? (
              <img
                src={resolvePhotoUrl(row.photo_url)}
                alt={`${row.first_name} ${row.last_name}`}
                className="h-9 w-9 rounded-full object-cover ring-1 ring-slate-200"
              />
            ) : (
              <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full bg-brand-100 text-xs font-bold text-brand-800">
                {(row.first_name?.[0] || '')}
                {(row.last_name?.[0] || '')}
              </div>
            )}
            <Link
              to={`/members/${row.id}`}
              className="font-semibold text-brand-700 hover:text-brand-800 hover:underline"
            >
              {row.first_name} {row.last_name}
            </Link>
          </div>
        ),
      },
      { key: 'phone', label: 'Phone' },
      { key: 'email', label: 'Email', render: (row) => row.email ?? <span className="text-slate-300">—</span> },
      {
        key: 'membership_status',
        label: 'Status',
        render: (row) =>
          canEditStatus ? (
            <select
              value={row.membership_status || 'active'}
              onChange={(e) => onStatusChange(row.id, e.target.value)}
              className="rounded-lg border border-slate-200 bg-white px-2 py-1 text-xs font-semibold text-slate-700 focus:border-brand-700 focus:outline-none focus:ring-1 focus:ring-brand-100"
            >
              {MEMBERSHIP_STATUS.map((item) => (
                <option key={item} value={item}>{item}</option>
              ))}
            </select>
          ) : (
            <Badge variant={STATUS_BADGE_MAP[row.membership_status] ?? 'default'}>
              {row.membership_status || 'unknown'}
            </Badge>
          ),
      },
      { key: 'date_joined', label: 'Joined', render: (row) => formatDate(row.date_joined) },
      {
        key: 'low_attendance',
        label: 'Risk',
        render: (row) =>
          row.low_attendance ? (
            <Badge variant="followup">Follow Up</Badge>
          ) : (
            <Badge variant="stable">Stable</Badge>
          ),
      },
    ],
    [canEditStatus]
  );

  async function onExport() {
    setMessage('');
    const response = await memberService.exportCsv();
    const blob = new Blob([response.data], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `members_${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.URL.revokeObjectURL(url);
    setMessage('CSV export downloaded.');
  }

  const hasFilters = search || status;

  return (
    <section className="space-y-5">
      <PageHeader
        title="Members"
        subtitle="Browse, search, and manage your congregation's member records."
        action={
          <div className="flex gap-2">
            <Link to="/members/register" className="btn-primary">
              <UserPlus size={15} />
              Register Member
            </Link>
            <button type="button" onClick={onExport} className="btn-outline">
              <Download size={15} />
              Export CSV
            </button>
          </div>
        }
      />

      {/* Stat cards */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Total Members" value={total} helper="In current filter" icon={Users} />
        <StatCard label="Active" value={activeCount} helper="Membership status active" tone="good" icon={UserCheck} />
        <StatCard label="Pastoral Follow-Up" value={lowAttendanceCount} helper="Low attendance flagged" tone="warn" icon={AlertTriangle} />
        <StatCard label="Page" value={`${page} / ${totalPages}`} helper={`${rows.length} shown per page`} />
      </div>

      {/* Filter bar */}
      <div className="panel p-4">
        <div className="flex items-center gap-2">
          <Filter size={14} className="flex-shrink-0 text-slate-400" />
          <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Filter Members</p>
        </div>
        <div className="mt-3 grid gap-3 md:grid-cols-3">
          <div className="relative">
            <Search size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              placeholder="Search by name, phone, or email"
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1); }}
              className="field pl-9"
            />
          </div>
          <select
            value={status}
            onChange={(e) => { setStatus(e.target.value); setPage(1); }}
            className="field"
          >
            <option value="">All statuses</option>
            {MEMBERSHIP_STATUS.map((item) => (
              <option key={item} value={item}>{item}</option>
            ))}
          </select>
          {hasFilters && (
            <button
              type="button"
              onClick={() => { setSearch(''); setStatus(''); setPage(1); }}
              className="btn-outline gap-1.5"
            >
              <X size={14} />
              Clear Filters
            </button>
          )}
        </div>
      </div>

      {/* Inline success message */}
      {message && (
        <p className="rounded-xl bg-success-50 px-4 py-2.5 text-sm font-medium text-success-700 ring-1 ring-success-100">
          {message}
        </p>
      )}

      {/* Table */}
      {membersQuery.isLoading ? (
        <LoadingSpinner label="Loading members..." />
      ) : (
        <>
          <DataTable columns={columns} rows={rows} emptyLabel="No members found" />

          {/* Pagination */}
          <div className="flex items-center justify-between">
            <p className="text-sm text-slate-500">
              Showing <span className="font-semibold text-slate-700">{rows.length}</span> of{' '}
              <span className="font-semibold text-slate-700">{total}</span> members
            </p>
            <div className="flex gap-2">
              <button
                type="button"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="btn-outline disabled:opacity-40"
              >
                Previous
              </button>
              <button
                type="button"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                className="btn-outline disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </div>
        </>
      )}
    </section>
  );
}
