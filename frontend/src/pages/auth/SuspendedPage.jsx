import { ShieldAlert } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import { PRODUCT } from '../../utils/brand';

// Shown instead of the app when the platform has suspended the active church.
export default function SuspendedPage({ message }) {
  const { churches, logout, setSuspension } = useAuthStore();
  const navigate = useNavigate();
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-100 px-4">
      <div className="panel max-w-md p-8 text-center">
        <ShieldAlert size={48} className="mx-auto text-accent-700" />
        <h1 className="mt-4 text-xl font-extrabold text-slate-900">This church account is suspended</h1>
        <p className="mt-2 text-sm text-slate-600">{message || 'Access has been paused by the platform team.'} Your data is safe and nothing has been deleted.</p>
        <p className="mt-2 text-sm text-slate-600">Please contact <a className="font-semibold text-brand-700" href={`mailto:${PRODUCT.supportEmail}`}>{PRODUCT.supportEmail}</a> to restore access.</p>
        <div className="mt-6 flex flex-wrap justify-center gap-2">
          {churches.length > 1 && <button type="button" className="btn-outline" onClick={() => { setSuspension(null); navigate('/select-church'); }}>Switch church</button>}
          <button type="button" className="btn-primary" onClick={() => { logout(); navigate('/login'); }}>Sign out</button>
        </div>
      </div>
    </main>
  );
}
