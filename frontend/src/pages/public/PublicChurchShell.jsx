import { useEffect } from 'react';
import ChurchMark from '../../components/shared/ChurchMark';
import LoadingSpinner from '../../components/shared/LoadingSpinner';
import ProductMark from '../../components/shared/ProductMark';
import { applyBrandTheme } from '../../utils/theme';

// Church-branded frame for public forms (welcome card, prayer, check-in), phone-first.
export default function PublicChurchShell({ church, loading, notFound, children, subtitle }) {
  useEffect(() => {
    if (church) applyBrandTheme(church);
  }, [church]);

  return (
    <div className="min-h-screen bg-slate-100">
      <div className="h-36 bg-brand-800" />
      <main className="mx-auto -mt-28 max-w-lg px-4 pb-12">
        <div className="panel overflow-hidden">
          {loading ? (
            <div className="flex justify-center p-10"><LoadingSpinner /></div>
          ) : notFound || !church ? (
            <div className="p-8 text-center">
              <p className="text-lg font-extrabold text-slate-900">Page not found</p>
              <p className="mt-2 text-sm text-slate-500">This link is not active. Please ask the church for the current link.</p>
            </div>
          ) : (
            <>
              <div className="flex items-center gap-3 border-b border-slate-100 px-6 py-5">
                <ChurchMark church={church} size="h-12 w-12" />
                <div className="min-w-0">
                  <p className="truncate text-lg font-extrabold text-slate-900">{church.name}</p>
                  {subtitle ? <p className="text-sm text-slate-500">{subtitle}</p> : null}
                </div>
              </div>
              <div className="px-6 py-6">{children}</div>
            </>
          )}
        </div>
        <div className="mt-6 flex justify-center opacity-70"><a href="/" aria-label="Powered by Asafo"><ProductMark /></a></div>
      </main>
    </div>
  );
}
