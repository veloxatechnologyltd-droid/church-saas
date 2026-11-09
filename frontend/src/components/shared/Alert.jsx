import { AlertTriangle, CheckCircle2, Info, XCircle } from 'lucide-react';

const TONES = {
  info: { box: 'bg-brand-50 text-brand-800 ring-brand-100', icon: Info },
  success: { box: 'bg-success-50 text-success-800 ring-success-100', icon: CheckCircle2 },
  warn: { box: 'bg-church-50 text-church-800 ring-church-100', icon: AlertTriangle },
  error: { box: 'bg-accent-50 text-accent-800 ring-accent-100', icon: XCircle },
};

export default function Alert({ tone = 'info', children, action }) {
  const { box, icon: Icon } = TONES[tone] ?? TONES.info;
  if (!children) return null;
  return (
    <div className={`flex items-start gap-3 rounded-xl px-4 py-3 text-sm ring-1 ${box}`} role={tone === 'error' ? 'alert' : 'status'}>
      <Icon size={18} className="mt-0.5 flex-shrink-0" />
      <div className="min-w-0 flex-1">{children}</div>
      {action ? <div className="flex-shrink-0">{action}</div> : null}
    </div>
  );
}
