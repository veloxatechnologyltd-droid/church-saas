import { useState } from 'react';
import { Link } from 'react-router-dom';
import LoadingSpinner from '../../components/shared/LoadingSpinner';
import PlanCard from '../../components/shared/PlanCard';
import { usePlans } from '../../hooks/usePlans';

export default function PricingSection() {
  const plansQuery = usePlans();
  const [cycle, setCycle] = useState('monthly');
  const plans = (plansQuery.data ?? []).filter((plan) => plan.code !== 'trial');

  return (
    <div>
      <div className="mb-8 flex justify-center">
        <div className="inline-flex rounded-xl bg-white p-1 ring-1 ring-slate-200">
          {['monthly', 'yearly'].map((value) => (
            <button key={value} type="button" onClick={() => setCycle(value)} className={`rounded-lg px-4 py-2 text-sm font-semibold capitalize ${cycle === value ? 'bg-brand-700 text-white' : 'text-slate-600'}`}>
              {value}{value === 'yearly' ? ' · 2 months free' : ''}
            </button>
          ))}
        </div>
      </div>
      {plansQuery.isLoading ? (
        <div className="flex justify-center"><LoadingSpinner label="Loading plans…" /></div>
      ) : plansQuery.isError ? (
        <p className="text-center text-sm text-slate-500">Pricing is temporarily unavailable. Every plan starts with a free 14-day trial.</p>
      ) : (
        <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-4">
          {plans.map((plan) => (
            <PlanCard
              key={plan.code}
              plan={plan}
              cycle={cycle}
              highlighted={plan.code === 'growth'}
              action={
                plan.code === 'enterprise' ? (
                  <a href="mailto:sales@ekklesia.app" className="btn-outline w-full justify-center">Contact sales</a>
                ) : (
                  <Link to={`/signup?plan=${plan.code}`} className={`${plan.code === 'growth' ? 'btn-primary' : 'btn-outline'} w-full justify-center`}>Start free trial</Link>
                )
              }
            />
          ))}
        </div>
      )}
      <p className="mt-6 text-center text-xs text-slate-500">Prices in Ghana cedis. Pay with mobile money or card. Every church starts with a 14-day free trial, no card required.</p>
    </div>
  );
}
