import { HandHeart } from 'lucide-react';
import { useState } from 'react';
import { useParams } from 'react-router-dom';
import Alert from '../../components/shared/Alert';
import Field from '../../components/shared/Field';
import { usePublicChurch } from '../../hooks/usePublicChurch';
import { publicService } from '../../services/churchService';
import { PRAYER_CATEGORIES } from '../../utils/constants';
import { errorMessage } from '../../utils/formatters';
import PublicChurchShell from './PublicChurchShell';

const EMPTY = { name: '', phone: '', email: '', request: '', category: '', is_confidential: false, website: '' };

export default function PrayerRequestPage() {
  const { slug } = useParams();
  const churchQuery = usePublicChurch(slug);
  const [form, setForm] = useState(EMPTY);
  const [done, setDone] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const set = (key) => (e) => setForm((p) => ({ ...p, [key]: e.target.type === 'checkbox' ? e.target.checked : e.target.value }));

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      const payload = Object.fromEntries(Object.entries(form).filter(([, v]) => v !== ''));
      await publicService.submitPrayer(slug, payload);
      setDone(true);
      setForm(EMPTY);
    } catch (err) {
      setError(errorMessage(err, 'We could not send your request. Please try again.'));
    } finally {
      setBusy(false);
    }
  }

  return (
    <PublicChurchShell church={churchQuery.data} loading={churchQuery.isLoading} notFound={churchQuery.isError} subtitle="Share a prayer request">
      {done ? (
        <div className="py-6 text-center">
          <HandHeart size={48} className="mx-auto text-brand-700" />
          <p className="mt-4 text-lg font-extrabold text-slate-900">We are praying with you.</p>
          <p className="mt-2 text-sm text-slate-500">“The prayer of a righteous person is powerful and effective.” James 5:16</p>
          <button type="button" className="btn-outline mt-6" onClick={() => setDone(false)}>Send another request</button>
        </div>
      ) : (
        <form onSubmit={submit} className="space-y-4">
          <Field label="Your prayer request" required>
            <textarea className="field min-h-[140px]" required minLength={3} value={form.request} onChange={set('request')} placeholder="How can we pray for you?" />
          </Field>
          <Field label="Category">
            <select className="field capitalize" value={form.category} onChange={set('category')}><option value="">Select (optional)</option>{PRAYER_CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}</select>
          </Field>
          <Field label="Your name" hint="Leave blank to stay anonymous."><input className="field" value={form.name} onChange={set('name')} /></Field>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Phone (optional)"><input className="field" type="tel" value={form.phone} onChange={set('phone')} /></Field>
            <Field label="Email (optional)"><input className="field" type="email" value={form.email} onChange={set('email')} /></Field>
          </div>
          <label className="flex items-start gap-3 text-sm text-slate-700"><input type="checkbox" className="mt-1 h-4 w-4" checked={form.is_confidential} onChange={set('is_confidential')} /> Keep this confidential (pastors only)</label>
          <input type="text" name="website" value={form.website} onChange={set('website')} tabIndex={-1} autoComplete="off" className="hidden" aria-hidden="true" />
          <Alert tone="error">{error}</Alert>
          <button type="submit" className="btn-primary w-full justify-center py-3" disabled={busy}>{busy ? 'Sending…' : 'Send prayer request'}</button>
        </form>
      )}
    </PublicChurchShell>
  );
}
