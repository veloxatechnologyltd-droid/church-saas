import { CheckCircle2 } from 'lucide-react';
import { useState } from 'react';
import { useParams } from 'react-router-dom';
import Alert from '../../components/shared/Alert';
import Field from '../../components/shared/Field';
import { usePublicChurch } from '../../hooks/usePublicChurch';
import { publicService } from '../../services/churchService';
import { AGE_GROUPS, HOW_HEARD } from '../../utils/constants';
import { errorMessage } from '../../utils/formatters';
import PublicChurchShell from './PublicChurchShell';

const EMPTY = {
  first_name: '', last_name: '', phone: '', email: '', gender: '', age_group: '', how_heard: '', invited_by: '',
  prayer_request: '', wants_visit: false, interested_in_membership: false, website: '',
};

// The digital first-timer welcome card. Shared as a link / QR code on the church screen.
export default function WelcomePage() {
  const { slug } = useParams();
  const churchQuery = usePublicChurch(slug);
  const [form, setForm] = useState(EMPTY);
  const [done, setDone] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const set = (key) => (e) => setForm((p) => ({ ...p, [key]: e.target.type === 'checkbox' ? e.target.checked : e.target.value }));

  async function submit(event) {
    event.preventDefault();
    if (!form.phone && !form.email) {
      setError('Please give us a phone number or email so we can say hello.');
      return;
    }
    setBusy(true);
    setError('');
    try {
      const payload = Object.fromEntries(Object.entries(form).filter(([, v]) => v !== ''));
      const response = await publicService.submitVisitor(slug, payload);
      setDone(response.data.data?.message || 'Thank you for worshipping with us today!');
      setForm(EMPTY);
    } catch (err) {
      setError(errorMessage(err, 'We could not send your details. Please try again.'));
    } finally {
      setBusy(false);
    }
  }

  return (
    <PublicChurchShell church={churchQuery.data} loading={churchQuery.isLoading} notFound={churchQuery.isError} subtitle="Welcome! We are glad you came.">
      {done ? (
        <div className="py-6 text-center">
          <CheckCircle2 size={48} className="mx-auto text-success-700" />
          <p className="mt-4 text-lg font-extrabold text-slate-900">{done}</p>
          <button type="button" className="btn-outline mt-6" onClick={() => setDone(null)}>Add another person</button>
        </div>
      ) : (
        <form onSubmit={submit} className="space-y-4">
          <p className="text-sm text-slate-600">First time here? Tell us a little about yourself so we can welcome you properly.</p>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="First name" required><input className="field" required value={form.first_name} onChange={set('first_name')} autoComplete="given-name" /></Field>
            <Field label="Last name"><input className="field" value={form.last_name} onChange={set('last_name')} autoComplete="family-name" /></Field>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Phone"><input className="field" type="tel" value={form.phone} onChange={set('phone')} placeholder="024 000 0000" autoComplete="tel" /></Field>
            <Field label="Email"><input className="field" type="email" value={form.email} onChange={set('email')} autoComplete="email" /></Field>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Gender">
              <select className="field" value={form.gender} onChange={set('gender')}><option value="">Prefer not to say</option><option value="male">Male</option><option value="female">Female</option></select>
            </Field>
            <Field label="Age group">
              <select className="field" value={form.age_group} onChange={set('age_group')}><option value="">Select</option>{AGE_GROUPS.map((a) => <option key={a} value={a} className="capitalize">{a}</option>)}</select>
            </Field>
          </div>
          <Field label="How did you hear about us?">
            <select className="field" value={form.how_heard} onChange={set('how_heard')}><option value="">Select</option>{HOW_HEARD.map((h) => <option key={h} value={h}>{h}</option>)}</select>
          </Field>
          <Field label="Who invited you? (optional)"><input className="field" value={form.invited_by} onChange={set('invited_by')} /></Field>
          <Field label="Anything we can pray with you about? (optional)"><textarea className="field min-h-[90px]" value={form.prayer_request} onChange={set('prayer_request')} /></Field>
          <label className="flex items-start gap-3 text-sm text-slate-700"><input type="checkbox" className="mt-1 h-4 w-4" checked={form.wants_visit} onChange={set('wants_visit')} /> I would like someone to visit or call me</label>
          <label className="flex items-start gap-3 text-sm text-slate-700"><input type="checkbox" className="mt-1 h-4 w-4" checked={form.interested_in_membership} onChange={set('interested_in_membership')} /> I am interested in becoming a member</label>
          {/* Honeypot: hidden from people, bots fill it in. */}
          <input type="text" name="website" value={form.website} onChange={set('website')} tabIndex={-1} autoComplete="off" className="hidden" aria-hidden="true" />
          <Alert tone="error">{error}</Alert>
          <button type="submit" className="btn-primary w-full justify-center py-3" disabled={busy}>{busy ? 'Sending…' : 'Send my welcome card'}</button>
          <p className="text-center text-xs text-slate-400">Your details are only used by this church to follow up with you.</p>
        </form>
      )}
    </PublicChurchShell>
  );
}
