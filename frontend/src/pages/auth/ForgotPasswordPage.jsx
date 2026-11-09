import { useState } from 'react';
import { Link } from 'react-router-dom';
import AuthShell from '../../components/layout/AuthShell';
import Alert from '../../components/shared/Alert';
import { authService } from '../../services/authService';
import { errorMessage } from '../../utils/formatters';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      await authService.forgotPassword(email.trim());
      setSent(true);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell eyebrow="Account recovery" title="Reset your password" subtitle="We will email you a link to choose a new password." footer={<Link to="/login" className="font-semibold text-brand-700 hover:underline">Back to sign in</Link>}>
      {sent ? (
        <Alert tone="success">If an account exists for <strong>{email}</strong>, a reset link is on its way. The link expires in one hour.</Alert>
      ) : (
        <form onSubmit={submit} className="space-y-5">
          <label className="block">
            <span className="mb-1.5 block text-sm font-semibold text-slate-700">Email address</span>
            <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className="field" autoComplete="email" />
          </label>
          <Alert tone="error">{error}</Alert>
          <button type="submit" className="btn-primary w-full justify-center py-3" disabled={busy}>{busy ? 'Sending…' : 'Send reset link'}</button>
        </form>
      )}
    </AuthShell>
  );
}
