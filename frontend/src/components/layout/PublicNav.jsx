import { Link } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import ProductMark from '../shared/ProductMark';

export default function PublicNav() {
  const token = useAuthStore((state) => state.token);
  return (
    <header className="sticky top-0 z-30 border-b border-slate-200/70 bg-white/90 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4">
        <Link to="/" aria-label="Home"><ProductMark /></Link>
        <nav className="flex items-center gap-1 text-sm font-semibold sm:gap-3">
          <a href="/#features" className="hidden rounded-lg px-3 py-2 text-slate-600 hover:text-slate-900 sm:block">Features</a>
          <Link to="/pricing" className="rounded-lg px-3 py-2 text-slate-600 hover:text-slate-900">Pricing</Link>
          {token ? (
            <Link to="/dashboard" className="btn-primary px-3 py-2">Open app</Link>
          ) : (
            <>
              <Link to="/login" className="rounded-lg px-3 py-2 text-slate-600 hover:text-slate-900">Sign in</Link>
              <Link to="/signup" className="btn-primary px-3 py-2">Start free</Link>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}

export function PublicFooter() {
  return (
    <footer className="border-t border-slate-200 bg-white">
      <div className="mx-auto flex max-w-6xl flex-col gap-3 px-4 py-8 text-sm text-slate-500 sm:flex-row sm:items-center sm:justify-between">
        <ProductMark />
        <div className="flex flex-wrap gap-4">
          <Link to="/pricing" className="hover:text-slate-800">Pricing</Link>
          <Link to="/signup" className="hover:text-slate-800">Start a trial</Link>
          <Link to="/login" className="hover:text-slate-800">Sign in</Link>
          <Link to="/terms" className="hover:text-slate-800">Terms</Link>
          <Link to="/privacy" className="hover:text-slate-800">Privacy</Link>
        </div>
        <p>© {new Date().getFullYear()} Asafo. Made in Accra.</p>
      </div>
    </footer>
  );
}
