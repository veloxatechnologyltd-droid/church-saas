import PublicNav, { PublicFooter } from '../../components/layout/PublicNav';

// Contact shown in the legal pages. Set VITE_SUPPORT_EMAIL at build time.
export const SUPPORT_EMAIL = import.meta.env.VITE_SUPPORT_EMAIL || '';
export const LEGAL_UPDATED = '10 November 2026';

export function ContactLine() {
  return SUPPORT_EMAIL
    ? <a className="font-semibold text-brand-700 underline" href={`mailto:${SUPPORT_EMAIL}`}>{SUPPORT_EMAIL}</a>
    : <span>the support contact listed in your account</span>;
}

/** Shared shell for the Terms and Privacy pages: a readable column with numbered sections. */
export default function LegalPage({ title, intro, sections }) {
  return (
    <div className="min-h-screen bg-slate-50">
      <PublicNav />
      <main className="mx-auto max-w-3xl px-4 py-12">
        <h1 className="text-3xl font-extrabold text-slate-900">{title}</h1>
        <p className="mt-1 text-sm text-slate-500">Last updated {LEGAL_UPDATED}</p>
        <p className="mt-5 text-slate-700">{intro}</p>
        <div className="mt-8 space-y-7">
          {sections.map((section, index) => (
            <section key={section.heading}>
              <h2 className="text-lg font-bold text-slate-900">{index + 1}. {section.heading}</h2>
              <div className="mt-2 space-y-2 text-sm leading-relaxed text-slate-700">{section.body}</div>
            </section>
          ))}
        </div>
      </main>
      <PublicFooter />
    </div>
  );
}
