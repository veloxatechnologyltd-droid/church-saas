import { useQueryClient } from '@tanstack/react-query';
import { Check, ChevronsUpDown } from 'lucide-react';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { authService } from '../../services/authService';
import { useAuthStore } from '../../store/authStore';
import { ROLE_LABELS } from '../../utils/constants';
import { errorMessage } from '../../utils/formatters';
import { applyBrandTheme } from '../../utils/theme';
import ChurchMark from '../shared/ChurchMark';

// Lets a user who belongs to several churches move between them (new token per church).
export default function ChurchSwitcher() {
  const { churches, activeChurch, setSession, impersonation } = useAuthStore();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  if (!activeChurch || impersonation || churches.length < 2) return null;

  async function choose(churchId) {
    if (churchId === activeChurch.id) {
      setOpen(false);
      return;
    }
    setBusy(true);
    setError('');
    try {
      const response = await authService.switchChurch(churchId);
      setSession(response.data.data);
      applyBrandTheme(response.data.data.active_church);
      queryClient.clear();
      setOpen(false);
      navigate('/dashboard');
    } catch (err) {
      setError(errorMessage(err, 'Could not switch church.'));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex max-w-[14rem] items-center gap-2 rounded-xl border border-slate-200 px-2.5 py-1.5 text-sm font-semibold text-slate-700 hover:bg-slate-50"
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        <ChurchMark church={activeChurch} size="h-6 w-6" className="rounded-md text-[10px]" />
        <span className="hidden truncate sm:inline">{activeChurch.name}</span>
        <ChevronsUpDown size={14} className="flex-shrink-0 text-slate-400" />
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-11 z-20 w-72 rounded-2xl bg-white p-2 shadow-lg ring-1 ring-slate-200" role="listbox">
            <p className="label-caps px-2 py-1.5">Switch church</p>
            {churches.map((church) => (
              <button
                key={church.id}
                type="button"
                disabled={busy}
                onClick={() => choose(church.id)}
                className="flex w-full items-center gap-3 rounded-xl px-2 py-2 text-left hover:bg-slate-50 disabled:opacity-60"
                role="option"
                aria-selected={church.id === activeChurch.id}
              >
                <ChurchMark church={church} size="h-8 w-8" className="text-xs" />
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-semibold text-slate-900">{church.name}</span>
                  <span className="block text-xs text-slate-500">{ROLE_LABELS[church.role] ?? church.role}</span>
                </span>
                {church.id === activeChurch.id ? <Check size={16} className="text-brand-700" /> : null}
              </button>
            ))}
            {error ? <p className="px-2 py-1 text-xs text-accent-700">{error}</p> : null}
          </div>
        </>
      )}
    </div>
  );
}
