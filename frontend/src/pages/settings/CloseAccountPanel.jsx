import { AlertTriangle } from 'lucide-react';
import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import Alert from '../../components/shared/Alert';
import ConfirmDialog from '../../components/shared/ConfirmDialog';
import Field from '../../components/shared/Field';
import { churchService } from '../../services/churchService';
import { useAuthStore } from '../../store/authStore';
import { errorMessage } from '../../utils/formatters';

/** Church-admin only. Closing is reversible by support for 30 days, then the data is erased. */
export default function CloseAccountPanel({ church }) {
  const navigate = useNavigate();
  const logout = useAuthStore((state) => state.logout);
  const [form, setForm] = useState({ confirm_slug: '', password: '', reason: '' });
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const ready = form.confirm_slug.trim().toLowerCase() === church.slug && form.password.length > 0;
  const set = (key) => (e) => setForm((p) => ({ ...p, [key]: e.target.value }));

  async function close() {
    setBusy(true);
    setError('');
    try {
      await churchService.close({ ...form, reason: form.reason || undefined });
      logout();
      navigate('/login', { replace: true });
    } catch (err) {
      setConfirming(false);
      setError(errorMessage(err, 'We could not close the account.'));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="max-w-xl space-y-5">
      <div className="flex gap-3 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-900">
        <AlertTriangle className="mt-0.5 shrink-0" size={18} />
        <div className="space-y-1">
          <p className="font-bold">Closing the account stops access for everyone on your team.</p>
          <p>Your data is kept for 30 days in case you change your mind (contact support to reopen). After that, all members, giving, attendance, messages and uploaded files are permanently deleted and cannot be recovered.</p>
        </div>
      </div>
      <p className="text-sm text-slate-600">Before you close, <Link className="font-semibold text-brand-700 underline" to="/settings/export">download your data</Link>. Any unused SMS credits are forfeited.</p>
      <Alert tone="error">{error}</Alert>
      <Field label={<>Type your church’s URL name <code className="rounded bg-slate-100 px-1">{church.slug}</code> to confirm</>}>
        <input className="field" value={form.confirm_slug} onChange={set('confirm_slug')} autoComplete="off" />
      </Field>
      <Field label="Your password">
        <input className="field" type="password" value={form.password} onChange={set('password')} autoComplete="current-password" />
      </Field>
      <Field label="Why are you leaving? (optional)">
        <input className="field" value={form.reason} onChange={set('reason')} maxLength={500} />
      </Field>
      <button type="button" className="btn-danger" disabled={!ready || busy} onClick={() => setConfirming(true)}>Close this church account</button>
      <ConfirmDialog
        open={confirming}
        danger
        title={`Close ${church.name}?`}
        description="Everyone on your team will be signed out and locked out immediately. Data is deleted for good after 30 days."
        confirmLabel={busy ? 'Closing…' : 'Yes, close the account'}
        onConfirm={close}
        onCancel={() => setConfirming(false)}
      />
    </div>
  );
}
