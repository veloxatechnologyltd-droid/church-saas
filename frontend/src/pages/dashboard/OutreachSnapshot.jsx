import { useQuery } from '@tanstack/react-query';
import { ArrowRight, HandHeart, Sparkles } from 'lucide-react';
import { Link } from 'react-router-dom';
import { prayerService, visitorService } from '../../services/outreachService';
import { useRole } from '../../store/authStore';

// "Who needs a call this week" strip for the people who do follow-up.
export default function OutreachSnapshot() {
  const role = useRole();
  const enabled = ['church_admin', 'secretary'].includes(role);
  const visitors = useQuery({ queryKey: ['visitor-summary'], queryFn: () => visitorService.summary().then((r) => r.data.data), enabled });
  const prayers = useQuery({ queryKey: ['prayer-requests', 'new'], queryFn: () => prayerService.list({ status: 'new', limit: 1 }).then((r) => r.data), enabled });
  if (!enabled) return null;

  const v = visitors.data;
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <Link to="/visitors" className="panel flex items-center gap-4 p-5 transition hover:ring-2 hover:ring-brand-200">
        <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand-50 text-brand-700"><Sparkles size={22} /></div>
        <div className="min-w-0 flex-1">
          <p className="font-bold text-slate-900">{v ? `${v.new ?? 0} first-timer${v.new === 1 ? '' : 's'} waiting for a call` : 'First-timers'}</p>
          <p className="text-sm text-slate-500">{v ? `${v.this_month ?? 0} visited this month · ${Math.round(Number(v.conversion_rate ?? 0))}% became members` : 'Loading…'}</p>
        </div>
        <ArrowRight size={18} className="text-slate-400" />
      </Link>
      <Link to="/prayer" className="panel flex items-center gap-4 p-5 transition hover:ring-2 hover:ring-brand-200">
        <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-church-50 text-church-700"><HandHeart size={22} /></div>
        <div className="min-w-0 flex-1">
          <p className="font-bold text-slate-900">{prayers.data ? `${prayers.data.total ?? 0} new prayer request${prayers.data.total === 1 ? '' : 's'}` : 'Prayer requests'}</p>
          <p className="text-sm text-slate-500">Requests from the welcome card and prayer page</p>
        </div>
        <ArrowRight size={18} className="text-slate-400" />
      </Link>
    </div>
  );
}
