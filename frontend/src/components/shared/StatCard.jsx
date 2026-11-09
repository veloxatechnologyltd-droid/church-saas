/**
 * tone: 'default' | 'good' | 'warn' | 'danger'
 * icon: Lucide icon component (optional)
 */

const toneConfig = {
  default: {
    bg: 'bg-brand-50',
    iconColor: 'text-brand-700',
    valueColor: 'text-slate-900',
  },
  good: {
    bg: 'bg-success-50',
    iconColor: 'text-success-700',
    valueColor: 'text-success-700',
  },
  warn: {
    bg: 'bg-church-50',
    iconColor: 'text-church-700',
    valueColor: 'text-church-700',
  },
  danger: {
    bg: 'bg-accent-50',
    iconColor: 'text-accent-700',
    valueColor: 'text-accent-700',
  },
};

export default function StatCard({ label, value, helper, tone = 'default', icon: Icon }) {
  const config = toneConfig[tone] ?? toneConfig.default;

  return (
    <article className="panel flex min-w-0 items-start gap-4 overflow-hidden p-5">
      {Icon && (
        <div className={`flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl ${config.bg}`}>
          <Icon size={20} className={config.iconColor} strokeWidth={2} />
        </div>
      )}
      <div className="min-w-0 flex-1">
        <p className="truncate text-xs font-semibold uppercase tracking-wider text-slate-500">{label}</p>
        <p
          title={typeof value === 'string' ? value : undefined}
          className={`mt-1 truncate whitespace-nowrap font-extrabold leading-tight ${
            String(value ?? '').length > 9 ? 'text-[clamp(1rem,1.3vw,1.35rem)]' : 'text-[clamp(1.1rem,1.7vw,1.5rem)]'
          } ${config.valueColor}`}
        >
          {value}
        </p>
        {helper ? <p className="mt-1.5 truncate text-xs text-slate-400">{helper}</p> : null}
      </div>
    </article>
  );
}
