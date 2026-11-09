import PublicNav, { PublicFooter } from '../../components/layout/PublicNav';
import PricingSection from './PricingSection';

export default function PricingPage() {
  return (
    <div className="min-h-screen bg-slate-50">
      <PublicNav />
      <main className="mx-auto max-w-6xl px-4 py-14">
        <div className="mx-auto mb-10 max-w-2xl text-center">
          <p className="text-xs font-bold uppercase tracking-widest text-brand-700">Pricing</p>
          <h1 className="mt-2 text-4xl font-extrabold text-slate-900">Simple plans that grow with your church</h1>
          <p className="mt-3 text-slate-600">Start free. Upgrade when you add branches, staff or SMS. Your data is always yours to export.</p>
        </div>
        <PricingSection />
        <section className="mx-auto mt-16 max-w-3xl space-y-4">
          <h2 className="text-xl font-extrabold text-slate-900">Questions churches ask</h2>
          {[
            ['What happens when my trial ends?', 'Nothing is deleted. Your church becomes read-only until you pick a plan, so you can still look up members and reports.'],
            ['How do SMS credits work?', 'Paid plans include monthly SMS credits. Need more for a convention or crusade? Top up a credit pack any time.'],
            ['Can we manage several branches?', 'Yes. Branch leaders only see their branch, while church-wide admins see everything and compare branches.'],
            ['Is our members’ data safe?', 'Every church’s data is isolated at the database level, access is role-based, and every change is recorded in an audit trail.'],
          ].map(([q, a]) => (
            <details key={q} className="panel p-4">
              <summary className="cursor-pointer font-semibold text-slate-900">{q}</summary>
              <p className="mt-2 text-sm text-slate-600">{a}</p>
            </details>
          ))}
        </section>
      </main>
      <PublicFooter />
    </div>
  );
}
