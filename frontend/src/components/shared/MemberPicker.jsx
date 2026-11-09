import { useQuery } from '@tanstack/react-query';
import { Search, X } from 'lucide-react';
import { useEffect, useState } from 'react';
import { memberService } from '../../services/memberService';

// Search-as-you-type member selector. value: { id, name } | null
export default function MemberPicker({ value, onChange, placeholder = 'Search member by name or phone' }) {
  const [term, setTerm] = useState('');
  const [debounced, setDebounced] = useState('');
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setDebounced(term.trim()), 250);
    return () => clearTimeout(t);
  }, [term]);

  const query = useQuery({
    queryKey: ['member-picker', debounced],
    queryFn: () => memberService.getAll({ search: debounced, limit: 8, status: 'active' }).then((r) => r.data.data),
    enabled: open && debounced.length >= 2,
  });

  if (value) {
    return (
      <div className="flex items-center justify-between rounded-xl border border-slate-300 bg-slate-50 px-4 py-2.5 text-sm">
        <span className="font-semibold text-slate-800">{value.name}</span>
        <button type="button" onClick={() => onChange(null)} className="text-slate-400 hover:text-slate-700" aria-label="Clear member"><X size={16} /></button>
      </div>
    );
  }

  return (
    <div className="relative">
      <Search size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
      <input className="field pl-9" value={term} placeholder={placeholder} onFocus={() => setOpen(true)} onChange={(e) => { setTerm(e.target.value); setOpen(true); }} onBlur={() => setTimeout(() => setOpen(false), 150)} />
      {open && debounced.length >= 2 && (
        <div className="absolute z-20 mt-1 max-h-64 w-full overflow-y-auto rounded-xl bg-white py-1 shadow-lg ring-1 ring-slate-200">
          {query.isLoading ? <p className="px-4 py-2 text-sm text-slate-500">Searching…</p> : null}
          {(query.data ?? []).map((m) => (
            <button key={m.id} type="button" className="block w-full px-4 py-2 text-left text-sm hover:bg-slate-50" onMouseDown={(e) => e.preventDefault()} onClick={() => { onChange({ id: m.id, name: `${m.first_name} ${m.last_name}` }); setTerm(''); setOpen(false); }}>
              <span className="font-semibold text-slate-900">{m.first_name} {m.last_name}</span>
              {m.phone ? <span className="ml-2 text-xs text-slate-500">{m.phone}</span> : null}
            </button>
          ))}
          {!query.isLoading && !(query.data ?? []).length ? <p className="px-4 py-2 text-sm text-slate-500">No members found.</p> : null}
        </div>
      )}
    </div>
  );
}
