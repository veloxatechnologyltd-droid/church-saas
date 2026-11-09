import { lazy, Suspense, useEffect, useState } from 'react';
import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import Layout from './components/layout/Layout';
import { ROUTE_ROLES } from './components/layout/navConfig';
import LoadingSpinner from './components/shared/LoadingSpinner';
const AttendancePage = lazy(() => import('./pages/attendance/AttendancePage'));
const AcceptInvitePage = lazy(() => import('./pages/auth/AcceptInvitePage'));
const ForgotPasswordPage = lazy(() => import('./pages/auth/ForgotPasswordPage'));
import LoginPage from './pages/auth/LoginPage';
const ResetPasswordPage = lazy(() => import('./pages/auth/ResetPasswordPage'));
const SelectChurchPage = lazy(() => import('./pages/auth/SelectChurchPage'));
const SuspendedPage = lazy(() => import('./pages/auth/SuspendedPage'));
const FakeCheckoutPage = lazy(() => import('./pages/billing/FakeCheckoutPage'));
const CommunicationPage = lazy(() => import('./pages/communication/CommunicationPage'));
const DashboardPage = lazy(() => import('./pages/dashboard/DashboardPage'));
const DonationsPage = lazy(() => import('./pages/donations/DonationsPage'));
const EventsPage = lazy(() => import('./pages/events/EventsPage'));
const FinanceLayout = lazy(() => import('./pages/finance/FinanceLayout'));
const GroupsPage = lazy(() => import('./pages/groups/GroupsPage'));
const DepartmentMembersPage = lazy(() => import('./pages/groups/DepartmentMembersPage'));
const MemberProfilePage = lazy(() => import('./pages/members/MemberProfilePage'));
const MemberRegistrationPage = lazy(() => import('./pages/members/MemberRegistrationPage'));
const MembersPage = lazy(() => import('./pages/members/MembersPage'));
const OnboardingPage = lazy(() => import('./pages/onboarding/OnboardingPage'));
const PastoralPage = lazy(() => import('./pages/pastoral/PastoralPage'));
const PlatformPage = lazy(() => import('./pages/platform/PlatformPage'));
const PledgeCampaignPage = lazy(() => import('./pages/pledges/PledgeCampaignPage'));
const PledgesPage = lazy(() => import('./pages/pledges/PledgesPage'));
const PrayerRequestsPage = lazy(() => import('./pages/prayer/PrayerRequestsPage'));
const CheckinPage = lazy(() => import('./pages/public/CheckinPage'));
import LandingPage from './pages/public/LandingPage';
const PricingPage = lazy(() => import('./pages/public/PricingPage'));
const PrayerRequestPage = lazy(() => import('./pages/public/PrayerRequestPage'));
const SignupPage = lazy(() => import('./pages/public/SignupPage'));
const WelcomePage = lazy(() => import('./pages/public/WelcomePage'));
const ReportsPage = lazy(() => import('./pages/reports/ReportsPage'));
const SettingsPage = lazy(() => import('./pages/settings/SettingsPage'));
const VisitorsPage = lazy(() => import('./pages/visitors/VisitorsPage'));
import { authService } from './services/authService';
import { useAuthStore, useRole } from './store/authStore';
import { applyBrandTheme } from './utils/theme';

// Signed in AND inside a church. Sends church-less sessions to the picker / platform console.
function ChurchRoute({ children }) {
  const { token, user, activeChurch, churches, suspension } = useAuthStore();
  const role = useRole();
  const location = useLocation();

  if (!token) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  if (!activeChurch) {
    if (churches.length > 0) return <Navigate to="/select-church" replace />;
    if (user?.is_platform_admin) return <Navigate to="/platform" replace />;
    return <Navigate to="/login" replace />;
  }
  if (suspension) return <SuspendedPage message={suspension.message} />;

  const root = `/${location.pathname.split('/')[1]}`;
  const allowed = ROUTE_ROLES[root];
  if (allowed && !allowed.includes(role)) return <Navigate to="/dashboard" replace />;
  return children;
}

// Re-validates a stored session on load and refreshes the user / church list.
function AuthBootstrap({ children }) {
  const token = useAuthStore((s) => s.token);
  const [checking, setChecking] = useState(Boolean(token));

  useEffect(() => {
    let mounted = true;
    applyBrandTheme(useAuthStore.getState().activeChurch);
    if (!token) {
      setChecking(false);
      return undefined;
    }
    authService
      .me()
      .then((response) => {
        if (!mounted) return;
        const data = response.data.data;
        const { setMe, impersonation } = useAuthStore.getState();
        setMe({ user: data.user, active_church: data.active_church, churches: impersonation ? [] : data.churches });
        applyBrandTheme(data.active_church);
      })
      .catch((error) => {
        if (mounted && error.response?.status === 401) useAuthStore.getState().logout();
      })
      .finally(() => mounted && setChecking(false));
    return () => {
      mounted = false;
    };
    // Only on first load / token change.
  }, [token]);

  if (checking) {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <LoadingSpinner label="Verifying session..." />
      </main>
    );
  }
  return children;
}

export default function App() {
  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <AuthBootstrap>
        <Suspense fallback={<main className="flex min-h-[50vh] items-center justify-center"><LoadingSpinner /></main>}>
        <Routes>
          {/* Public */}
          <Route path="/" element={<LandingPage />} />
          <Route path="/pricing" element={<PricingPage />} />
          <Route path="/signup" element={<SignupPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          <Route path="/reset-password" element={<ResetPasswordPage />} />
          <Route path="/accept-invite" element={<AcceptInvitePage />} />
          <Route path="/welcome/:slug" element={<WelcomePage />} />
          <Route path="/pray/:slug" element={<PrayerRequestPage />} />
          <Route path="/checkin/:code" element={<CheckinPage />} />

          {/* Signed in, outside the church shell */}
          <Route path="/select-church" element={<SelectChurchPage />} />
          <Route path="/platform" element={<PlatformPage />} />
          <Route path="/onboarding" element={<ChurchRoute><OnboardingPage /></ChurchRoute>} />
          <Route path="/billing/fake-checkout" element={<ChurchRoute><FakeCheckoutPage /></ChurchRoute>} />

          {/* Church app */}
          <Route element={<ChurchRoute><Layout /></ChurchRoute>}>
            <Route path="dashboard" element={<DashboardPage />} />
            <Route path="members" element={<MembersPage />} />
            <Route path="members/register" element={<MemberRegistrationPage />} />
            <Route path="members/:id" element={<MemberProfilePage />} />
            <Route path="attendance" element={<AttendancePage />} />
            <Route path="visitors" element={<VisitorsPage />} />
            <Route path="finance" element={<FinanceLayout />}>
              <Route index element={<DonationsPage view="overview" />} />
              <Route path="giving" element={<DonationsPage view="giving" />} />
              <Route path="expenses" element={<DonationsPage view="expenses" />} />
              <Route path="batches" element={<DonationsPage view="batches" />} />
              <Route path="funds" element={<DonationsPage view="funds" />} />
              <Route path="reports" element={<DonationsPage view="reports" />} />
            </Route>
            <Route path="donations" element={<Navigate to="/finance" replace />} />
            <Route path="pledges" element={<PledgesPage />} />
            <Route path="pledges/:id" element={<PledgeCampaignPage />} />
            <Route path="groups" element={<GroupsPage />} />
            <Route path="groups/:id/members" element={<DepartmentMembersPage />} />
            <Route path="events" element={<EventsPage />} />
            <Route path="communication" element={<CommunicationPage />} />
            <Route path="prayer" element={<PrayerRequestsPage />} />
            <Route path="pastoral" element={<PastoralPage />} />
            <Route path="reports" element={<ReportsPage />} />
            <Route path="settings" element={<SettingsPage />} />
            <Route path="settings/:tab" element={<SettingsPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        </Suspense>
      </AuthBootstrap>
    </BrowserRouter>
  );
}
