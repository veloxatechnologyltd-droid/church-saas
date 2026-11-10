import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import AuthShell from '../../components/layout/AuthShell';
import Alert from '../../components/shared/Alert';
import { authService } from '../../services/authService';
import { ROLE_LABELS } from '../../utils/constants';
import { errorMessage } from '../../utils/formatters';

// New users choose a password here; people who already have an account confirm it with their own password.
export default function AcceptInvitePage() {
  const [params] = useSearchParams();
  const token = params.get('token') || '';
  const [password, setPassword] = useState('');
  const [needsPassword, setNeedsPassword] = useState(false);
  const [existingAccount, setExistingAccount] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      const response = await authService.acceptInvite({ token, password: password || undefined });
      setResult(response.data.data);
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (err.response?.status === 422 && detail?.code === 'existing_account') {
        setExistingAccount(true);
        setError(detail.message);
      } else if (err.response?.status === 422 && !password) {
        setNeedsPassword(true);
        setError('Welcome! Choose a password to create your account.');
      } else {
        setError(errorMessage(err, 'This invitation is invalid or has expired.'));
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell eyebrow="Invitation" title="Join your church team" subtitle="Accept the invitation your church administrator sent you.">
      {!token ? (
        <Alert tone="error">This invitation link is incomplete. Ask your administrator to send it again.</Alert>
      ) : result ? (
        <div className="space-y-4">
          <Alert tone="success">
            You have joined <strong>{result.church?.name}</strong> as {ROLE_LABELS[result.role] ?? result.role}.
            {result.account_created ? ' Your account is ready.' : ''}
          </Alert>
          <Link to="/login" className="btn-primary w-full justify-center py-3">Sign in as {result.email}</Link>
        </div>
      ) : (
        <form onSubmit={submit} className="space-y-5">
          {existingAccount ? (
            <label className="block">
              <span className="mb-1.5 block text-sm font-semibold text-slate-700">Your current password</span>
              <input type="password" required value={password} onChange={(e) => setPassword(e.target.value)} className="field" autoComplete="current-password" />
              <span className="mt-1 block text-xs text-slate-500">Forgot it? <Link to="/forgot-password" className="font-semibold text-brand-700 underline">Reset your password</Link>, then open this link again.</span>
            </label>
          ) : needsPassword ? (
            <label className="block">
              <span className="mb-1.5 block text-sm font-semibold text-slate-700">Choose a password</span>
              <input type="password" required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} className="field" autoComplete="new-password" />
              <span className="mt-1 block text-xs text-slate-500">At least 8 characters.</span>
            </label>
          ) : (
            <p className="text-sm text-slate-600">If you already use {` `}this app with another church, accepting adds this church to your account.</p>
          )}
          <Alert tone={(needsPassword || existingAccount) && !password ? 'info' : 'error'}>{error}</Alert>
          <button type="submit" className="btn-primary w-full justify-center py-3" disabled={busy}>{busy ? 'Accepting…' : needsPassword ? 'Create account and join' : existingAccount ? 'Join with my password' : 'Accept invitation'}</button>
        </form>
      )}
    </AuthShell>
  );
}
