import { useQuery } from '@tanstack/react-query';
import { CheckCircle2, UserPlus } from 'lucide-react';
import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import Alert from '../../components/shared/Alert';
import { publicService } from '../../services/churchService';
import { errorMessage, formatDate } from '../../utils/formatters';
import PublicChurchShell from './PublicChurchShell';

// Member self check-in from the QR code shown during service.
export default function CheckinPage() {
  const { code } = useParams();
  const infoQuery = useQuery({
    queryKey: ['public-checkin', code],
    queryFn: () => publicService.checkinInfo(code).then((r) => r.data.data),
    retry: false,
  });
  const [phone, setPhone] = useState('');
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const info = infoQuery.data;

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      const response = await publicService.checkin(code, phone.trim());
      setResult(response.data.data);
    } catch (err) {
      setError(errorMessage(err, 'Check-in failed. Please try again.'));
    } finally {
      setBusy(false);
    }
  }

  function reset() {
    setResult(null);
    setPhone('');
  }

  return (
    <PublicChurchShell
      church={info?.church}
      loading={infoQuery.isLoading}
      notFound={infoQuery.isError}
      subtitle={info ? `${info.session?.title} · ${formatDate(info.session?.session_date)}` : ''}
    >
      {info && !info.open ? (
        <Alert tone="warn">Check-in for this service is closed. Please see an usher.</Alert>
      ) : result?.status === 'checked_in' || result?.status === 'already_checked_in' ? (
        <div className="py-6 text-center">
          <CheckCircle2 size={56} className="mx-auto text-success-700" />
          <p className="mt-4 text-2xl font-extrabold text-slate-900">
            {result.status === 'already_checked_in' ? 'You are already checked in' : `Welcome${result.first_name ? `, ${result.first_name}` : ''}!`}
          </p>
          <p className="mt-2 text-sm text-slate-500">Enjoy the service. God bless you.</p>
          <button type="button" className="btn-outline mt-6" onClick={reset}>Check in someone else</button>
        </div>
      ) : result?.status === 'not_found' ? (
        <div className="space-y-4 py-2 text-center">
          <UserPlus size={44} className="mx-auto text-brand-700" />
          <p className="text-lg font-extrabold text-slate-900">We could not find that number</p>
          <p className="text-sm text-slate-500">If this is your first time with us, welcome! Please fill in a quick welcome card.</p>
          {info?.church?.slug ? <Link to={`/welcome/${info.church.slug}`} className="btn-primary w-full justify-center py-3">I am new here</Link> : null}
          <button type="button" className="btn-outline w-full justify-center" onClick={reset}>Try another number</button>
        </div>
      ) : (
        <form onSubmit={submit} className="space-y-4">
          <p className="text-sm text-slate-600">Enter the phone number the church has for you.</p>
          <input className="field py-4 text-center text-xl tracking-wider" type="tel" inputMode="tel" required minLength={9} value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="024 000 0000" autoComplete="tel" autoFocus />
          <Alert tone="error">{error}</Alert>
          <button type="submit" className="btn-primary w-full justify-center py-3 text-base" disabled={busy}>{busy ? 'Checking in…' : 'Check me in'}</button>
        </form>
      )}
    </PublicChurchShell>
  );
}
