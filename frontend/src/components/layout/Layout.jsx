import { useEffect, useState } from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useChurch } from '../../hooks/useChurch';
import { useAuthStore, useRole } from '../../store/authStore';
import { applyBrandTheme } from '../../utils/theme';
import AccountBanners from './AccountBanners';
import MobileNav from './MobileNav';
import Navbar from './Navbar';
import Sidebar from './Sidebar';

export default function Layout() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const activeChurch = useAuthStore((state) => state.activeChurch);
  const role = useRole();
  const location = useLocation();
  const churchQuery = useChurch();
  const church = churchQuery.data;

  // Apply the cached colours immediately; useChurch refreshes them from the API.
  useEffect(() => {
    applyBrandTheme(activeChurch);
  }, [activeChurch?.primary_color, activeChurch?.secondary_color]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => setMobileMenuOpen(false), [location.pathname]);

  // A brand-new church's admin goes through the setup wizard first.
  if (church && !church.onboarding_completed_at && role === 'church_admin') {
    return <Navigate to="/onboarding" replace />;
  }

  return (
    <div className="flex h-screen overflow-hidden bg-slate-100">
      <div className="hidden lg:flex lg:flex-shrink-0">
        <Sidebar />
      </div>

      {mobileMenuOpen && (
        <>
          <div className="fixed inset-0 z-30 bg-slate-900/50 lg:hidden" onClick={() => setMobileMenuOpen(false)} />
          <div className="fixed inset-y-0 left-0 z-40 flex lg:hidden">
            <Sidebar onNavigate={() => setMobileMenuOpen(false)} />
          </div>
        </>
      )}

      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <AccountBanners church={church} />
        <Navbar onMenuClick={() => setMobileMenuOpen(true)} />
        <main className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-screen-2xl px-4 pb-24 pt-6 lg:px-6 lg:py-8">
            <Outlet />
          </div>
        </main>
      </div>

      <MobileNav />
    </div>
  );
}
