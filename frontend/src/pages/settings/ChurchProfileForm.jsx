import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Upload } from 'lucide-react';
import { useEffect, useState } from 'react';
import Alert from '../../components/shared/Alert';
import ChurchMark from '../../components/shared/ChurchMark';
import Field from '../../components/shared/Field';
import { churchService } from '../../services/churchService';
import { useAuthStore } from '../../store/authStore';
import { errorMessage } from '../../utils/formatters';
import { applyBrandTheme, DEFAULT_PRIMARY, DEFAULT_SECONDARY, isValidHex } from '../../utils/theme';

const FIELDS = ['name', 'phone', 'email', 'address', 'website', 'denomination', 'primary_color', 'secondary_color', 'timezone', 'currency', 'sms_sender_id', 'email_from_name', 'email_from'];
const PRESETS = [['#1A4FA0', '#E07218'], ['#6D28D9', '#F59E0B'], ['#047857', '#CA8A04'], ['#B91C1C', '#1E3A8A'], ['#0F766E', '#DB2777'], ['#1E293B', '#D97706']];

// Church profile + branding. `compact` hides the advanced (messaging/locale) fields.
export default function ChurchProfileForm({ church, compact = false, onSaved }) {
  const queryClient = useQueryClient();
  const updateActiveChurch = useAuthStore((s) => s.updateActiveChurch);
  const [form, setForm] = useState({});
  const [message, setMessage] = useState('');

  useEffect(() => {
    if (church) setForm(Object.fromEntries(FIELDS.map((key) => [key, church[key] ?? ''])));
  }, [church]);

  // Live preview of colours while editing.
  useEffect(() => {
    if (!form.primary_color && !form.secondary_color) return undefined;
    applyBrandTheme({ primary_color: form.primary_color, secondary_color: form.secondary_color });
    return undefined;
  }, [form.primary_color, form.secondary_color]);

  const save = useMutation({
    mutationFn: (payload) => churchService.update(payload).then((r) => r.data.data),
    onSuccess: (data) => {
      queryClient.setQueryData(['church', data.id], data);
      updateActiveChurch({ name: data.name, primary_color: data.primary_color, secondary_color: data.secondary_color, logo_url: data.logo_url });
      setMessage('Saved.');
      onSaved?.(data);
    },
  });
  const logo = useMutation({
    mutationFn: (file) => churchService.uploadLogo(file).then((r) => r.data.data),
    onSuccess: (data) => {
      queryClient.setQueryData(['church', data.id], data);
      updateActiveChurch({ logo_url: data.logo_url });
    },
  });

  const set = (key) => (e) => {
    setMessage('');
    setForm((p) => ({ ...p, [key]: e.target.value }));
  };

  function submit(event) {
    event.preventDefault();
    const payload = {};
    FIELDS.forEach((key) => {
      if (compact && ['timezone', 'currency', 'sms_sender_id', 'email_from_name', 'email_from'].includes(key)) return;
      const value = typeof form[key] === 'string' ? form[key].trim() : form[key];
      payload[key] = value === '' ? null : value;
    });
    if (!payload.name) {
      setMessage('');
      return;
    }
    ['primary_color', 'secondary_color'].forEach((key) => {
      if (payload[key] && !isValidHex(payload[key])) payload[key] = null;
    });
    save.mutate(payload);
  }

  return (
    <form onSubmit={submit} className="space-y-6">
      <div className="flex flex-wrap items-center gap-4">
        <ChurchMark church={{ ...church, name: form.name || church?.name }} size="h-16 w-16" className="text-lg" />
        <div>
          <label className="btn-outline cursor-pointer">
            <Upload size={15} /> {logo.isPending ? 'Uploading…' : church?.logo_url ? 'Change logo' : 'Upload logo'}
            <input type="file" accept="image/png,image/jpeg,image/webp,image/svg+xml" className="hidden" onChange={(e) => e.target.files?.[0] && logo.mutate(e.target.files[0])} />
          </label>
          <p className="mt-1 text-xs text-slate-500">Square PNG or JPG, at least 256×256.</p>
          {logo.isError ? <p className="mt-1 text-xs text-accent-700">{errorMessage(logo.error, 'Logo upload failed.')}</p> : null}
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Field label="Church name" required className="md:col-span-2"><input className="field" required value={form.name ?? ''} onChange={set('name')} /></Field>
        <Field label="Phone"><input className="field" value={form.phone ?? ''} onChange={set('phone')} /></Field>
        <Field label="Email"><input className="field" type="email" value={form.email ?? ''} onChange={set('email')} /></Field>
        <Field label="Website"><input className="field" value={form.website ?? ''} onChange={set('website')} placeholder="https://" /></Field>
        <Field label="Denomination"><input className="field" value={form.denomination ?? ''} onChange={set('denomination')} /></Field>
        <Field label="Address" className="md:col-span-2"><textarea className="field min-h-[70px]" value={form.address ?? ''} onChange={set('address')} /></Field>
      </div>

      <div>
        <p className="mb-2 text-sm font-semibold text-slate-700">Brand colours</p>
        <div className="mb-3 flex flex-wrap gap-2">
          {PRESETS.map(([p, s]) => (
            <button key={p} type="button" onClick={() => setForm((f) => ({ ...f, primary_color: p, secondary_color: s }))} className="flex overflow-hidden rounded-lg ring-1 ring-slate-200 hover:ring-2 hover:ring-slate-400" aria-label={`Use ${p} and ${s}`}>
              <span className="h-8 w-8" style={{ background: p }} /><span className="h-8 w-4" style={{ background: s }} />
            </button>
          ))}
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          {[['primary_color', 'Primary', DEFAULT_PRIMARY], ['secondary_color', 'Secondary', DEFAULT_SECONDARY]].map(([key, label, fallback]) => (
            <Field key={key} label={label}>
              <div className="flex items-center gap-2">
                <input type="color" value={isValidHex(form[key]) ? form[key] : fallback} onChange={set(key)} className="h-11 w-14 cursor-pointer rounded-lg border border-slate-300 bg-white p-1" aria-label={`${label} colour picker`} />
                <input className="field font-mono" value={form[key] ?? ''} onChange={set(key)} placeholder={fallback} maxLength={7} />
              </div>
            </Field>
          ))}
        </div>
      </div>

      {!compact && (
        <div className="grid gap-4 md:grid-cols-2">
          <Field label="SMS sender ID" hint="Up to 11 letters, shown as the SMS sender. Must be registered with your SMS provider.">
            <input className="field" maxLength={11} value={form.sms_sender_id ?? ''} onChange={set('sms_sender_id')} />
          </Field>
          <Field label="Email sender name"><input className="field" value={form.email_from_name ?? ''} onChange={set('email_from_name')} /></Field>
          <Field label="Reply-to email"><input className="field" type="email" value={form.email_from ?? ''} onChange={set('email_from')} /></Field>
          <Field label="Currency">
            <select className="field" value={form.currency ?? 'GHS'} onChange={set('currency')}>{['GHS', 'NGN', 'KES', 'ZAR', 'USD', 'GBP', 'EUR'].map((c) => <option key={c}>{c}</option>)}</select>
          </Field>
          <Field label="Time zone"><input className="field" value={form.timezone ?? ''} onChange={set('timezone')} placeholder="Africa/Accra" /></Field>
        </div>
      )}

      {save.isError ? <Alert tone="error">{errorMessage(save.error, 'Could not save church details.')}</Alert> : null}
      {message ? <Alert tone="success">{message}</Alert> : null}
      <button type="submit" className="btn-primary" disabled={save.isPending}>{save.isPending ? 'Saving…' : 'Save changes'}</button>
    </form>
  );
}
