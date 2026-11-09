import { PRODUCT } from '../../utils/brand';

// The SaaS product's wordmark (used on public pages and the platform console).
export default function ProductMark({ light = false }) {
  return (
    <span className="inline-flex items-center gap-2">
      <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-700 text-white">
        <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" aria-hidden="true">
          <path d="M12 4v16M7 9h10" />
        </svg>
      </span>
      <span className={`text-lg font-extrabold tracking-tight ${light ? 'text-white' : 'text-slate-900'}`}>{PRODUCT.name}</span>
    </span>
  );
}
