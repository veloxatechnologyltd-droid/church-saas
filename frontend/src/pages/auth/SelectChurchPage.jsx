import { ChevronRight } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import AuthShell from '../../components/layout/AuthShell';
import Alert from '../../components/shared/Alert';
import ChurchMark from '../../components/shared/ChurchMark';
import { authService } from '../../services/authService';
import { useAuthStore } from '../../store/authStore';
import { ROLE_LABELS } from '../../utils/constants';
import { errorMessage } from '../../utils/formatters';
import { startSession } from '../../utils/session';

export default function SelectChurchPage() {
  const { token, churches, user, setMe } = useAuthStore();
  const navigate = useNavigate();
  const [busyId, setBusyId] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!token) return;
    authService.churches().then((r) => setMe({ churches: r.data.data, active_church: null })).catch(() => {});
  }, [token, setMe]);

  if (!token) return <Navigate to="/login" replace />;

  async function choose(id) {
    setBusyId(id);
    setError('');
    try {
      const response = await authService.switchChurch(id);
      navigate(startSession(response.data.data), { replace: true });
    } catch (err) {
      setError(errorMessage(err, 'Could not open that church.'));
    } finally {
      setBusyId(null);
    }
  }

  return (
    <AuthShell eyebrow="Choose a church" title="Where are you serving today?" subtitle="Your account belongs to more than one church.">
      <div className="space-y-2">
        {churches.map((church) => (
          <button
            key={church.id}
            type="button"
            onClick={() => choose(church.id)}
            disabled={Boolean(busyId)}
            className="flex w-full items-center gap-3 rounded-2xl border border-slate-200 p-3 text-left transition hover:border-brand-300 hover:bg-brand-50 disabled:opacity-60"
          >
            <ChurchMark church={church} />
            <span className="min-w-0 flex-1">
              <span className="block truncate font-semibold text-slate-900">{church.name}</span>
              <span className="block text-xs text-slate-500">{ROLE_LABELS[church.role] ?? church.role}{church.status === 'suspended' ? ' · suspended' : ''}</span>
            </span>
            {busyId === church.id ? <span className="h-4 w-4 animate-spin rounded-full border-2 border-brand-700 border-t-transparent" /> : <ChevronRight size={18} className="text-slate-400" />}
          </button>
        ))}
        {!churches.length && <p className="text-sm text-slate-500">You are not a member of any church yet.</p>}
        {user?.is_platform_admin && (
          <button type="button" onClick={() => navigate('/platform')} className="btn-outline w-full justify-center">Open platform console</button>
        )}
        <Alert tone="error">{error}</Alert>
      </div>
    </AuthShell>
  );
}
