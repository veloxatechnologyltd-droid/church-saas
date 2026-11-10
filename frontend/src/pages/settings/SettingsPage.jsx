import { Building2, CreditCard, Download, Link2, MessageSquare, Palette, Trash2, Users } from 'lucide-react';
import { Navigate, useNavigate, useParams } from 'react-router-dom';
import LoadingSpinner from '../../components/shared/LoadingSpinner';
import PageHeader from '../../components/shared/PageHeader';
import QrLink from '../../components/shared/QrLink';
import Tabs from '../../components/shared/Tabs';
import { useChurch } from '../../hooks/useChurch';
import { useRole } from '../../store/authStore';
import CloseAccountPanel from './CloseAccountPanel';
import BillingPanel from './BillingPanel';
import BranchesManager from './BranchesManager';
import ChurchProfileForm from './ChurchProfileForm';
import ExportPanel from './ExportPanel';
import SmsCreditsPanel from './SmsCreditsPanel';
import TeamManager from './TeamManager';

const TABS = [
  { id: 'profile', label: 'Church & branding', icon: Palette },
  { id: 'branches', label: 'Branches', icon: Building2 },
  { id: 'team', label: 'Team & roles', icon: Users },
  { id: 'billing', label: 'Billing', icon: CreditCard },
  { id: 'sms', label: 'SMS credits', icon: MessageSquare },
  { id: 'links', label: 'Public links', icon: Link2 },
  { id: 'export', label: 'Data export', icon: Download },
  { id: 'close', label: 'Close account', icon: Trash2, adminOnly: true },
];

export default function SettingsPage() {
  const { tab = 'profile' } = useParams();
  const navigate = useNavigate();
  const churchQuery = useChurch();
  const church = churchQuery.data;
  const role = useRole();
  const tabs = TABS.filter((t) => !t.adminOnly || role === 'church_admin');
  if (!tabs.some((t) => t.id === tab)) return <Navigate to="/settings" replace />;

  return (
    <section className="space-y-5">
      <PageHeader title="Settings" subtitle="Your church profile, team, plan and data." />
      <Tabs items={tabs} value={tab} onChange={(id) => navigate(id === 'profile' ? '/settings' : `/settings/${id}`)} />
      <div className="panel p-5 sm:p-6">
        {churchQuery.isLoading ? <LoadingSpinner /> : null}
        {tab === 'profile' && church && <ChurchProfileForm church={church} />}
        {tab === 'branches' && <BranchesManager />}
        {tab === 'team' && <TeamManager />}
        {tab === 'billing' && <BillingPanel />}
        {tab === 'sms' && <SmsCreditsPanel />}
        {tab === 'export' && <ExportPanel />}
        {tab === 'close' && church && <CloseAccountPanel church={church} />}
        {tab === 'links' && church && (
          <div className="space-y-4">
            <p className="text-sm text-slate-600">Print these QR codes on bulletins or show them on the projector. They open church-branded pages that need no login.</p>
            <QrLink url={church.public_urls?.welcome} title="First-timer welcome card" description="Guests fill this in; they appear under First-timers for follow-up." />
            <QrLink url={church.public_urls?.prayer} title="Prayer request form" description="Requests arrive in the Prayer Requests inbox." />
            <p className="text-xs text-slate-500">Service check-in QR codes are created per service from the Attendance page.</p>
          </div>
        )}
      </div>
    </section>
  );
}
