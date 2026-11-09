// Horizontal progress bar. `value` and `max` are numbers; max null/0 renders "unlimited".
export default function ProgressBar({ value = 0, max, tone = 'brand', label, helper }) {
  const unlimited = max === null || max === undefined;
  const pct = unlimited || !max ? 0 : Math.min(100, Math.round((Number(value) / Number(max)) * 100));
  const color = pct >= 100 ? 'bg-accent-700' : pct >= 85 ? 'bg-church-700' : tone === 'success' ? 'bg-success-700' : 'bg-brand-700';
  return (
    <div>
      {label ? (
        <div className="mb-1.5 flex items-baseline justify-between gap-2 text-sm">
          <span className="font-semibold text-slate-700">{label}</span>
          <span className="text-xs text-slate-500">{helper ?? (unlimited ? `${value} · unlimited` : `${value} of ${max}`)}</span>
        </div>
      ) : null}
      <div className="h-2.5 overflow-hidden rounded-full bg-slate-100" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
        <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${unlimited ? 4 : pct}%` }} />
      </div>
    </div>
  );
}
