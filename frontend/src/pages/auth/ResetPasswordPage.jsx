import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import AuthShell from '../../components/layout/AuthShell';
import Alert from '../../components/shared/Alert';
import { authService } from '../../services/authService';
import { errorMessage } from '../../utils/formatters';

export default function ResetPasswordPage() {
  const [params] = useSearchParams();
  const token = params.get('token') || '';
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [done, setDone] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    if (password !== confirm) {
      setError('The two passwords do not match.');
      return;
    }
    setBusy(true);
    setError('');
    try {
      await authService.resetPassword({ token, new_password: password });
      setDone(true);
    } catch (err) {
      setError(errorMessage(err, 'This reset link is invalid or has expired.'));
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell eyebrow="Account recovery" title="Choose a new password" footer={<Link to="/login" className="font-semibold text-brand-700 hover:underline">Back to sign in</Link>}>
      {!token ? (
        <Alert tone="error">This link is missing its token. Request a new reset email.</Alert>
      ) : done ? (
        <div className="space-y-4">
          <Alert tone="success">Your password has been changed. Other devices have been signed out.</Alert>
          <Link to="/login" className="btn-primary w-full justify-center py-3">Sign in</Link>
        </div>
      ) : (
        <form onSubmit={submit} className="space-y-5">
          <label className="block">
            <span className="mb-1.5 block text-sm font-semibold text-slate-700">New password</span>
            <input type="password" required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} className="field" autoComplete="new-password" />
            <span className="mt-1 block text-xs text-slate-500">At least 8 characters.</span>
          </label>
          <label className="block">
            <span className="mb-1.5 block text-sm font-semibold text-slate-700">Confirm password</span>
            <input type="password" required minLength={8} value={confirm} onChange={(e) => setConfirm(e.target.value)} className="field" autoComplete="new-password" />
          </label>
          <Alert tone="error">{error}</Alert>
          <button type="submit" className="btn-primary w-full justify-center py-3" disabled={busy}>{busy ? 'Saving…' : 'Set new password'}</button>
        </form>
      )}
    </AuthShell>
  );
}
