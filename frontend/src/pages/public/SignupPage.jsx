import { Check, X } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import AuthShell from '../../components/layout/AuthShell';
import Alert from '../../components/shared/Alert';
import Field from '../../components/shared/Field';
import { authService } from '../../services/authService';
import { COUNTRIES } from '../../utils/constants';
import { errorMessage } from '../../utils/formatters';
import { startSession } from '../../utils/session';

function slugify(value) {
  return value.toLowerCase().normalize('NFKD').replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 40);
}

export default function SignupPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [form, setForm] = useState({
    church_name: '', slug: '', first_name: '', last_name: '', email: '', password: '', phone: '', country: 'GH', denomination: '', accept_terms: false,
  });
  const [slugTouched, setSlugTouched] = useState(false);
  const [slugState, setSlugState] = useState({ status: 'idle' });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const checkId = useRef(0);

  const set = (key) => (event) => setForm((prev) => ({ ...prev, [key]: event.target.value }));

  useEffect(() => {
    if (!slugTouched) setForm((prev) => ({ ...prev, slug: slugify(prev.church_name) }));
  }, [form.church_name, slugTouched]);

  useEffect(() => {
    const slug = form.slug;
    if (!slug || slug.length < 3) {
      setSlugState({ status: 'idle' });
      return undefined;
    }
    const id = ++checkId.current;
    setSlugState({ status: 'checking' });
    const timer = setTimeout(async () => {
      try {
        const response = await authService.slugAvailable(slug);
        if (id !== checkId.current) return;
        const data = response.data.data;
        setSlugState({ status: data.available ? 'available' : 'taken', suggestion: data.suggestion });
      } catch {
        if (id === checkId.current) setSlugState({ status: 'idle' });
      }
    }, 350);
    return () => clearTimeout(timer);
  }, [form.slug]);

  async function submit(event) {
    event.preventDefault();
    setError('');
    if (slugState.status === 'taken') {
      setError('That church web address is taken. Use the suggestion or choose another.');
      return;
    }
    const country = COUNTRIES.find((c) => c.code === form.country) ?? COUNTRIES[0];
    setBusy(true);
    try {
      const payload = {
        ...form,
        email: form.email.trim(),
        timezone: country.timezone,
        currency: country.currency,
        phone: form.phone || undefined,
        denomination: form.denomination || undefined,
        slug: form.slug || undefined,
      };
      const response = await authService.signup(payload);
      const path = startSession(response.data.data);
      navigate(path === '/dashboard' ? '/onboarding' : path, { replace: true });
    } catch (err) {
      setError(errorMessage(err, 'We could not create your church. Please check the form.'));
    } finally {
      setBusy(false);
    }
  }

  const plan = params.get('plan');

  return (
    <AuthShell
      eyebrow="Free 14-day trial"
      title="Set up your church"
      subtitle={plan && plan !== 'free' ? `You picked the ${plan} plan. Try everything free for 14 days first.` : 'No card required. You can invite your team right after.'}
      footer={<>Already have an account? <Link to="/login" className="font-semibold text-brand-700 hover:underline">Sign in</Link></>}
    >
      <form onSubmit={submit} className="space-y-4">
        <Field label="Church name" required>
          <input className="field" required minLength={2} value={form.church_name} onChange={set('church_name')} placeholder="Grace Chapel International" />
        </Field>
        <Field
          label="Church web address"
          hint={
            slugState.status === 'checking' ? 'Checking…'
              : slugState.status === 'available' ? <span className="inline-flex items-center gap-1 text-success-700"><Check size={12} /> Available</span>
                : slugState.status === 'taken' ? (
                  <span className="inline-flex flex-wrap items-center gap-1 text-accent-700"><X size={12} /> Taken.
                    {slugState.suggestion ? <button type="button" className="font-semibold underline" onClick={() => { setSlugTouched(true); setForm((p) => ({ ...p, slug: slugState.suggestion })); }}>Use {slugState.suggestion}</button> : null}
                  </span>
                ) : 'Used for your public welcome and prayer pages.'
          }
        >
          <div className="flex items-center rounded-xl border border-slate-300 bg-white focus-within:border-brand-700 focus-within:ring-2 focus-within:ring-brand-100">
            <span className="pl-4 text-sm text-slate-400">/welcome/</span>
            <input className="min-w-0 flex-1 rounded-xl border-0 bg-transparent px-1 py-2.5 text-sm outline-none" value={form.slug} onChange={(e) => { setSlugTouched(true); setForm((p) => ({ ...p, slug: slugify(e.target.value) })); }} placeholder="grace-chapel" />
          </div>
        </Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Your first name" required><input className="field" required value={form.first_name} onChange={set('first_name')} autoComplete="given-name" /></Field>
          <Field label="Last name" required><input className="field" required value={form.last_name} onChange={set('last_name')} autoComplete="family-name" /></Field>
        </div>
        <Field label="Email" required><input className="field" type="email" required value={form.email} onChange={set('email')} autoComplete="email" /></Field>
        <Field label="Password" required hint="At least 8 characters."><input className="field" type="password" required minLength={8} value={form.password} onChange={set('password')} autoComplete="new-password" /></Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Country">
            <select className="field" value={form.country} onChange={set('country')}>
              {COUNTRIES.map((c) => <option key={c.code} value={c.code}>{c.name}</option>)}
            </select>
          </Field>
          <Field label="Phone"><input className="field" value={form.phone} onChange={set('phone')} placeholder="024 000 0000" autoComplete="tel" /></Field>
        </div>
        <Field label="Denomination (optional)"><input className="field" value={form.denomination} onChange={set('denomination')} placeholder="e.g. Pentecostal, Methodist" /></Field>
        <label className="flex items-start gap-2 text-sm text-slate-600">
          <input type="checkbox" className="mt-1" required checked={form.accept_terms} onChange={(e) => setForm((p) => ({ ...p, accept_terms: e.target.checked }))} />
          <span>I agree to the <Link to="/terms" target="_blank" className="font-semibold text-brand-700 underline">Terms of Service</Link> and <Link to="/privacy" target="_blank" className="font-semibold text-brand-700 underline">Privacy Policy</Link>.</span>
        </label>
        <Alert tone="error">{error}</Alert>
        <button type="submit" className="btn-primary w-full justify-center py-3" disabled={busy}>{busy ? 'Creating your church…' : 'Create church'}</button>
        <p className="text-center text-xs text-slate-500">By creating an account you agree to handle your members’ data responsibly under the Ghana Data Protection Act.</p>
      </form>
    </AuthShell>
  );
}
