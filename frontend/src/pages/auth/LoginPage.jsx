import { Eye, EyeOff } from 'lucide-react';
import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import AuthShell from '../../components/layout/AuthShell';
import Alert from '../../components/shared/Alert';
import { authService } from '../../services/authService';
import { errorMessage } from '../../utils/formatters';
import { startSession } from '../../utils/session';

export default function LoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');
    setIsSubmitting(true);
    try {
      const response = await authService.login({ email: email.trim(), password });
      navigate(startSession(response.data.data), { replace: true });
    } catch (err) {
      setError(errorMessage(err, 'Sign in failed. Please check your email and password.'));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <AuthShell
      eyebrow="Secure sign in"
      title="Welcome back"
      subtitle="Sign in with the email your church invited you with."
      footer={<>New church? <Link to="/signup" className="font-semibold text-brand-700 hover:underline">Start a free 14-day trial</Link></>}
    >
      <form onSubmit={handleSubmit} className="space-y-5">
        <label className="block">
          <span className="mb-1.5 block text-sm font-semibold text-slate-700">Email address</span>
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="email" className="field" placeholder="you@yourchurch.org" />
        </label>
        <label className="block">
          <span className="mb-1.5 flex items-center justify-between text-sm font-semibold text-slate-700">
            Password
            <Link to="/forgot-password" className="text-xs font-semibold text-brand-700 hover:underline">Forgot password?</Link>
          </span>
          <span className="relative block">
            <input type={showPassword ? 'text' : 'password'} value={password} onChange={(e) => setPassword(e.target.value)} required autoComplete="current-password" className="field pr-11" placeholder="Your password" />
            <button type="button" onClick={() => setShowPassword((v) => !v)} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600" aria-label={showPassword ? 'Hide password' : 'Show password'}>
              {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
            </button>
          </span>
        </label>
        <Alert tone="error">{error}</Alert>
        <button type="submit" className="btn-primary w-full justify-center py-3" disabled={isSubmitting}>
          {isSubmitting ? 'Signing in…' : 'Sign in'}
        </button>
      </form>
    </AuthShell>
  );
}
