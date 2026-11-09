import { useMutation, useQueryClient } from '@tanstack/react-query';
import { QrCode } from 'lucide-react';
import { useEffect, useState } from 'react';
import Alert from '../../components/shared/Alert';
import QrLink from '../../components/shared/QrLink';
import { attendanceService } from '../../services/attendanceService';
import { useRole } from '../../store/authStore';
import { errorMessage } from '../../utils/formatters';

// Opens/closes QR self check-in for one attendance session.
export default function SelfCheckinPanel({ session }) {
  const role = useRole();
  const queryClient = useQueryClient();
  const [state, setState] = useState(null);

  useEffect(() => {
    if (!session) return;
    setState({
      checkin_open: Boolean(session.checkin_open),
      checkin_code: session.checkin_code,
      checkin_url: session.checkin_url || (session.checkin_code ? `${window.location.origin}/checkin/${session.checkin_code}` : null),
    });
  }, [session?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const toggle = useMutation({
    mutationFn: (open) => attendanceService.setCheckin(session.id, open).then((r) => r.data.data),
    onSuccess: (data) => {
      setState(data);
      queryClient.invalidateQueries({ queryKey: ['attendance-session', session.id] });
    },
  });

  // While check-in is open, refresh the board so self check-ins appear.
  useEffect(() => {
    if (!state?.checkin_open || !session?.id) return undefined;
    const timer = setInterval(() => queryClient.invalidateQueries({ queryKey: ['attendance-session', session.id] }), 20_000);
    return () => clearInterval(timer);
  }, [state?.checkin_open, session?.id, queryClient]);

  if (!session || !['church_admin', 'secretary', 'group_leader'].includes(role)) return null;
  const isOpen = state?.checkin_open;

  return (
    <div className="panel p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-50 text-brand-700"><QrCode size={20} /></div>
          <div>
            <p className="text-sm font-bold text-slate-900">QR self check-in</p>
            <p className="text-xs text-slate-500">{isOpen ? 'Open: members can check themselves in with their phone number.' : 'Let members check in from their phones during this service.'}</p>
          </div>
        </div>
        <button type="button" className={isOpen ? 'btn-outline' : 'btn-primary'} disabled={toggle.isPending} onClick={() => toggle.mutate(!isOpen)}>
          {toggle.isPending ? 'Updating…' : isOpen ? 'Close check-in' : 'Open check-in'}
        </button>
      </div>
      {toggle.isError ? <div className="mt-3"><Alert tone="error">{errorMessage(toggle.error)}</Alert></div> : null}
      {isOpen && state?.checkin_url ? (
        <div className="mt-4">
          <QrLink url={state.checkin_url} title={`Check in to ${session.title}`} description="Show this on the projector or print it for the ushers' desk. Self check-ins appear on the board below." size={280} />
        </div>
      ) : null}
    </div>
  );
}
