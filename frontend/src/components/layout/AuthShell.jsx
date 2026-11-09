import { CheckCircle2 } from 'lucide-react';
import { Link } from 'react-router-dom';
import { PRODUCT } from '../../utils/brand';
import ProductMark from '../shared/ProductMark';

const DEFAULT_POINTS = [
  'Members, families and departments in one place',
  'Attendance with QR self check-in',
  'Giving, pledges and finance reports',
  'First-timer follow-up and prayer requests',
];

// Two-panel layout shared by sign-in, sign-up and password pages.
export default function AuthShell({ title, eyebrow, subtitle, children, points = DEFAULT_POINTS, footer }) {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-100 px-4 py-10">
      <div className="grid w-full max-w-5xl overflow-hidden rounded-3xl bg-white shadow-2xl ring-1 ring-slate-200 lg:grid-cols-[1fr_1.1fr]">
        <div className="relative hidden flex-col justify-between overflow-hidden bg-brand-900 p-10 text-white lg:flex">
          <div className="pointer-events-none absolute -left-16 -top-16 h-64 w-64 rounded-full bg-white/5" />
          <div className="pointer-events-none absolute -bottom-20 right-0 h-72 w-72 rounded-full bg-white/5" />
          <div className="relative">
            <Link to="/"><ProductMark light /></Link>
            <h1 className="mt-10 text-3xl font-extrabold leading-tight">Shepherd your people. Not spreadsheets.</h1>
            <p className="mt-4 text-sm leading-relaxed text-white/70">{PRODUCT.tagline}. Built for churches in Ghana and across Africa.</p>
          </div>
          <div className="relative mt-8 space-y-3">
            {points.map((point) => (
              <div key={point} className="flex items-start gap-3">
                <CheckCircle2 size={16} className="mt-0.5 flex-shrink-0 text-church-400" />
                <span className="text-sm text-white/80">{point}</span>
              </div>
            ))}
          </div>
          <p className="relative mt-8 text-xs text-white/40">© {new Date().getFullYear()} {PRODUCT.name}</p>
        </div>

        <div className="flex flex-col justify-center px-6 py-10 sm:px-10 lg:px-12">
          <div className="mx-auto w-full max-w-md">
            <div className="mb-6 lg:hidden"><Link to="/"><ProductMark /></Link></div>
            {eyebrow ? <p className="text-xs font-bold uppercase tracking-widest text-brand-700">{eyebrow}</p> : null}
            <h2 className="mt-2 text-2xl font-extrabold text-slate-900">{title}</h2>
            {subtitle ? <p className="mt-1.5 text-sm text-slate-500">{subtitle}</p> : null}
            <div className="mt-7">{children}</div>
            {footer ? <div className="mt-6 text-center text-sm text-slate-500">{footer}</div> : null}
          </div>
        </div>
      </div>
    </main>
  );
}
