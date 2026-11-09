import { useMutation, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, ArrowRight, Check, PartyPopper } from 'lucide-react';
import { useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import Alert from '../../components/shared/Alert';
import LoadingSpinner from '../../components/shared/LoadingSpinner';
import ProductMark from '../../components/shared/ProductMark';
import QrLink from '../../components/shared/QrLink';
import { useChurch } from '../../hooks/useChurch';
import { churchService } from '../../services/churchService';
import { useAuthStore, useRole } from '../../store/authStore';
import { STANDARD_FINANCE_FUNDS } from '../../utils/constants';
import { errorMessage } from '../../utils/formatters';
import BranchesManager from '../settings/BranchesManager';
import ChurchProfileForm from '../settings/ChurchProfileForm';
import TeamManager from '../settings/TeamManager';

const STEPS = [
  { id: 'profile', title: 'Your church', text: 'Add your logo and colours. The whole app will wear your brand.' },
  { id: 'branches', title: 'Branches', text: 'Every church starts with a main branch. Rename it, or add the other locations you run.' },
  { id: 'team', title: 'Invite your team', text: 'Bring in your secretary, finance officer and leaders. Each person only sees what their role needs.' },
  { id: 'ready', title: 'Ready for Sunday', text: 'A few things already set up for you.' },
];

export default function OnboardingPage() {
  const token = useAuthStore((s) => s.token);
  const role = useRole();
  const churchQuery = useChurch();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const church = churchQuery.data;

  const finish = useMutation({
    mutationFn: () => churchService.completeOnboarding().then((r) => r.data.data),
    onSuccess: (data) => {
      queryClient.setQueryData(['church', data.id], data);
      navigate('/dashboard', { replace: true });
    },
  });

  if (!token) return <Navigate to="/login" replace />;
  if (role && role !== 'church_admin') return <Navigate to="/dashboard" replace />;
  if (churchQuery.isLoading || !church) {
    return <main className="flex min-h-screen items-center justify-center"><LoadingSpinner label="Preparing your church…" /></main>;
  }
  if (church.onboarding_completed_at && !finish.isPending) return <Navigate to="/dashboard" replace />;

  const current = STEPS[step];
  return (
    <div className="min-h-screen bg-slate-100">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex h-16 max-w-4xl items-center justify-between px-4">
          <ProductMark />
          <button type="button" className="text-sm font-semibold text-slate-500 hover:text-slate-800" onClick={() => finish.mutate()}>Skip setup</button>
        </div>
      </header>
      <main className="mx-auto max-w-4xl px-4 py-8">
        <ol className="mb-8 grid grid-cols-4 gap-2" aria-label="Setup progress">
          {STEPS.map((s, i) => (
            <li key={s.id} className="text-center">
              <div className={`h-1.5 rounded-full ${i <= step ? 'bg-brand-700' : 'bg-slate-200'}`} />
              <p className={`mt-2 hidden text-xs font-semibold sm:block ${i === step ? 'text-brand-700' : 'text-slate-400'}`}>{s.title}</p>
            </li>
          ))}
        </ol>
        <section className="panel p-6 sm:p-8">
          <p className="label-caps">Step {step + 1} of {STEPS.length}</p>
          <h1 className="mt-1 text-2xl font-extrabold text-slate-900">{current.id === 'profile' ? `Welcome to ${church.name}` : current.title}</h1>
          <p className="mt-1 text-sm text-slate-500">{current.text}</p>
          <div className="mt-6">
            {current.id === 'profile' && <ChurchProfileForm church={church} compact onSaved={() => setStep(1)} />}
            {current.id === 'branches' && <BranchesManager />}
            {current.id === 'team' && <TeamManager showMembers={false} />}
            {current.id === 'ready' && (
              <div className="space-y-5">
                <div className="flex items-start gap-3 rounded-2xl bg-success-50 p-4 text-sm text-success-800">
                  <PartyPopper size={20} className="flex-shrink-0" />
                  <div>
                    <p className="font-bold">Your finance funds are ready</p>
                    <p className="mt-1">We created the standard giving funds: {STANDARD_FINANCE_FUNDS.join(', ')}, plus common expense categories. You can rename or add more under Finance.</p>
                  </div>
                </div>
                <p className="text-sm font-semibold text-slate-700">Share these links with your congregation</p>
                <QrLink url={church.public_urls?.welcome} title="First-timer welcome card" description="Show this QR on the screen so guests can fill in a welcome card from their phone." />
                <QrLink url={church.public_urls?.prayer} title="Prayer requests" description="Members and guests can send prayer requests any time." />
                {finish.isError ? <Alert tone="error">{errorMessage(finish.error)}</Alert> : null}
              </div>
            )}
          </div>
          <div className="mt-8 flex items-center justify-between border-t border-slate-100 pt-5">
            <button type="button" className="btn-outline" disabled={step === 0} onClick={() => setStep((s) => s - 1)}><ArrowLeft size={15} /> Back</button>
            {step < STEPS.length - 1 ? (
              <button type="button" className="btn-primary" onClick={() => setStep((s) => s + 1)}>Continue <ArrowRight size={15} /></button>
            ) : (
              <button type="button" className="btn-primary" disabled={finish.isPending} onClick={() => finish.mutate()}><Check size={15} /> {finish.isPending ? 'Finishing…' : 'Go to my dashboard'}</button>
            )}
          </div>
        </section>
      </main>
    </div>
  );
}
