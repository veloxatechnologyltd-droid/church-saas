import {
  BarChart3, Building2, CheckSquare, HandCoins, HandHeart, MessageSquare, QrCode, ShieldCheck, Sparkles, Users,
} from 'lucide-react';
import { Link, Navigate } from 'react-router-dom';
import PublicNav, { PublicFooter } from '../../components/layout/PublicNav';
import { useAuthStore } from '../../store/authStore';
import { PRODUCT } from '../../utils/brand';
import PricingSection from './PricingSection';

const FEATURES = [
  { icon: Users, title: 'Members & families', text: 'One profile per person: family, department, baptism, giving and attendance history at a glance.' },
  { icon: QrCode, title: 'QR self check-in', text: 'Put a QR code on the screen. Members check themselves in with their phone number in seconds.' },
  { icon: CheckSquare, title: 'Attendance that cares', text: 'Spot members who have missed several services and turn them into pastoral follow-ups automatically.' },
  { icon: Sparkles, title: 'First-timer follow-up', text: 'A welcome card link captures every guest. Assign follow-up, track visits and convert guests to members.' },
  { icon: HandCoins, title: 'Giving & pledges', text: 'Tithes, offerings and service batches, plus pledge campaigns for building projects and harvest.' },
  { icon: HandHeart, title: 'Prayer requests', text: 'A private prayer inbox your intercessors can work through, with confidential requests kept confidential.' },
  { icon: MessageSquare, title: 'SMS & reminders', text: 'Send to everyone, a department or birthdays. Schedule weekly service reminders that go out on their own.' },
  { icon: Building2, title: 'Multi-branch', text: 'Branch leaders see their branch; headquarters sees the whole ministry and compares branches.' },
  { icon: BarChart3, title: 'Reports & exports', text: 'Growth, attendance and income vs expense reports. Export to Excel any time: your data stays yours.' },
];

export default function LandingPage() {
  const { token, activeChurch } = useAuthStore();
  if (token && activeChurch) return <Navigate to="/dashboard" replace />;

  return (
    <div className="min-h-screen bg-slate-50">
      <PublicNav />
      <main>
        <section className="relative overflow-hidden bg-brand-900 text-white">
          <div className="pointer-events-none absolute -right-24 -top-24 h-96 w-96 rounded-full bg-white/5" />
          <div className="pointer-events-none absolute -bottom-32 left-10 h-80 w-80 rounded-full bg-church-700/20" />
          <div className="relative mx-auto grid max-w-6xl gap-10 px-4 py-20 lg:grid-cols-[1.2fr_1fr] lg:items-center">
            <div>
              <p className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-xs font-semibold">
                <ShieldCheck size={14} /> Built for churches in Ghana and across Africa
              </p>
              <h1 className="mt-5 text-4xl font-extrabold leading-tight sm:text-5xl">Shepherd your people. Not spreadsheets.</h1>
              <p className="mt-5 max-w-xl text-lg text-white/75">
                {PRODUCT.name} brings members, attendance, giving, first-timer follow-up, prayer requests and SMS into one simple app your church office will actually use.
              </p>
              <div className="mt-8 flex flex-wrap gap-3">
                <Link to="/signup" className="inline-flex items-center rounded-xl bg-white px-5 py-3 text-sm font-bold text-brand-900 hover:bg-brand-50">Start your free 14-day trial</Link>
                <Link to="/pricing" className="inline-flex items-center rounded-xl px-5 py-3 text-sm font-bold text-white ring-1 ring-white/40 hover:bg-white/10">See pricing</Link>
              </div>
              <p className="mt-4 text-xs text-white/50">No card required · Cancel any time · Export your data whenever you like</p>
            </div>
            <div className="rounded-3xl bg-white p-5 text-slate-900 shadow-2xl">
              <p className="label-caps">This Sunday</p>
              <div className="mt-3 grid grid-cols-2 gap-3">
                {[['Present', '342', 'text-success-700'], ['First-timers', '18', 'text-brand-700'], ['Offering', 'GH₵ 12,480', 'text-church-700'], ['Need follow-up', '9', 'text-accent-700']].map(([label, value, tone]) => (
                  <div key={label} className="rounded-2xl bg-slate-50 p-4">
                    <p className="text-xs font-semibold text-slate-500">{label}</p>
                    <p className={`mt-1 text-xl font-extrabold ${tone}`}>{value}</p>
                  </div>
                ))}
              </div>
              <div className="mt-4 rounded-2xl bg-brand-50 p-4 text-sm text-brand-800">
                <p className="font-bold">Akosua Mensah checked in · 9:02am</p>
                <p className="text-xs">via QR self check-in at Main Auditorium</p>
              </div>
            </div>
          </div>
        </section>

        <section id="features" className="mx-auto max-w-6xl px-4 py-20">
          <div className="mx-auto mb-12 max-w-2xl text-center">
            <p className="text-xs font-bold uppercase tracking-widest text-brand-700">Everything in one place</p>
            <h2 className="mt-2 text-3xl font-extrabold text-slate-900">Tools for the whole ministry, not just the office</h2>
          </div>
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map(({ icon: Icon, title, text }) => (
              <article key={title} className="panel p-6">
                <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand-50 text-brand-700"><Icon size={22} /></div>
                <h3 className="mt-4 font-extrabold text-slate-900">{title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-600">{text}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="bg-white py-20">
          <div className="mx-auto grid max-w-6xl gap-8 px-4 md:grid-cols-3">
            {[
              ['1', 'Create your church', 'Sign up in two minutes. Add your logo and colours: the app wears your brand.'],
              ['2', 'Bring your people', 'Import members, invite your secretary, finance team and branch leaders with the right access.'],
              ['3', 'Run Sunday', 'Open QR check-in, record the offering batch, and send the welcome SMS to first-timers.'],
            ].map(([step, title, text]) => (
              <div key={step}>
                <span className="flex h-10 w-10 items-center justify-center rounded-full bg-church-100 font-extrabold text-church-800">{step}</span>
                <h3 className="mt-4 text-lg font-extrabold text-slate-900">{title}</h3>
                <p className="mt-2 text-sm text-slate-600">{text}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-4 py-20">
          <div className="mx-auto mb-10 max-w-2xl text-center">
            <p className="text-xs font-bold uppercase tracking-widest text-brand-700">Pricing</p>
            <h2 className="mt-2 text-3xl font-extrabold text-slate-900">Fair pricing in cedis</h2>
          </div>
          <PricingSection />
        </section>

        <section className="bg-brand-900 py-16 text-center text-white">
          <h2 className="text-3xl font-extrabold">Ready for a calmer Sunday?</h2>
          <p className="mt-3 text-white/70">Set up your church today. It takes less time than counting the offering.</p>
          <Link to="/signup" className="mt-6 inline-flex rounded-xl bg-white px-6 py-3 text-sm font-bold text-brand-900 hover:bg-brand-50">Start free trial</Link>
        </section>
      </main>
      <PublicFooter />
    </div>
  );
}
