import { useQueryClient } from '@tanstack/react-query';
import { AlertTriangle, Eye, X } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuthStore, useRole } from '../../store/authStore';
import { applyBrandTheme } from '../../utils/theme';

function daysUntil(iso) {
  if (!iso) return null;
  return Math.ceil((new Date(iso).getTime() - Date.now()) / 86_400_000);
}

// Impersonation, read-only (402) and trial banners shown above every church page.
export default function AccountBanners({ church }) {
  const { impersonation, stopImpersonation, billingNotice, setBillingNotice, activeChurch } = useAuthStore();
  const role = useRole();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const trialDays = church?.status === 'trialing' ? daysUntil(church.trial_ends_at) : null;

  function exitImpersonation() {
    stopImpersonation();
    applyBrandTheme(null);
    queryClient.clear();
    navigate('/platform');
  }

  return (
    <>
      {impersonation && (
        <div className="flex items-center justify-between gap-3 bg-slate-900 px-4 py-2 text-sm text-white">
          <span className="flex items-center gap-2"><Eye size={16} /> Impersonating <strong>{activeChurch?.name}</strong> as church admin. Every action is audited.</span>
          <button type="button" onClick={exitImpersonation} className="rounded-lg bg-white/15 px-3 py-1 text-xs font-semibold hover:bg-white/25">Exit</button>
        </div>
      )}
      {billingNotice && (
        <div className="flex items-center justify-between gap-3 bg-accent-700 px-4 py-2 text-sm text-white">
          <span className="flex items-center gap-2"><AlertTriangle size={16} /> {billingNotice.message || 'Your church is in read-only mode until the subscription is renewed.'}</span>
          <span className="flex items-center gap-2">
            {role === 'church_admin' && <Link to="/settings/billing" className="rounded-lg bg-white/20 px-3 py-1 text-xs font-semibold hover:bg-white/30">Renew plan</Link>}
            <button type="button" onClick={() => setBillingNotice(null)} aria-label="Dismiss" className="rounded p-1 hover:bg-white/20"><X size={14} /></button>
          </span>
        </div>
      )}
      {!billingNotice && trialDays !== null && trialDays <= 7 && (
        <div className="flex flex-wrap items-center justify-between gap-2 bg-church-50 px-4 py-2 text-sm text-church-800 ring-1 ring-church-100">
          <span>{trialDays > 0 ? `Your free trial ends in ${trialDays} day${trialDays === 1 ? '' : 's'}.` : 'Your free trial has ended. Your data is safe, but the church is read-only.'}</span>
          {role === 'church_admin' && <Link to="/settings/billing" className="font-semibold underline">Choose a plan</Link>}
        </div>
      )}
    </>
  );
}
