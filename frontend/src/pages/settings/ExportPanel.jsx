import { Download } from 'lucide-react';
import { useState } from 'react';
import Alert from '../../components/shared/Alert';
import { churchService } from '../../services/churchService';
import { errorMessage } from '../../utils/formatters';

const DATASETS = [
  { id: 'members', label: 'Members', text: 'Every member profile with contact details, status and branch.' },
  { id: 'donations', label: 'Giving', text: 'All recorded donations with fund, member, method and date.' },
  { id: 'attendance', label: 'Attendance', text: 'Every attendance mark per service.' },
  { id: 'visitors', label: 'First-timers', text: 'Guests captured by staff or the welcome card, with follow-up status.' },
];

export default function ExportPanel() {
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');

  async function run(dataset, format) {
    setBusy(`${dataset}-${format}`);
    setError('');
    try {
      await churchService.exportData(dataset, format);
    } catch (err) {
      let message = errorMessage(err, 'Export failed.');
      // Blob error bodies need decoding to show the server's message.
      if (err.response?.data instanceof Blob) {
        try { message = JSON.parse(await err.response.data.text()).detail?.message ?? JSON.parse(await err.response.data.text()).detail ?? message; } catch { /* keep generic */ }
      }
      setError(typeof message === 'string' ? message : 'Export failed.');
    } finally {
      setBusy('');
    }
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-600">Your church’s data belongs to you. Download it any time as CSV (for any spreadsheet) or Excel.</p>
      <Alert tone="error">{error}</Alert>
      <div className="grid gap-4 md:grid-cols-2">
        {DATASETS.map((d) => (
          <div key={d.id} className="rounded-2xl border border-slate-200 p-5">
            <p className="font-bold text-slate-900">{d.label}</p>
            <p className="mt-1 text-sm text-slate-500">{d.text}</p>
            <div className="mt-4 flex gap-2">
              {['csv', 'xlsx'].map((format) => (
                <button key={format} type="button" className="btn-outline" disabled={Boolean(busy)} onClick={() => run(d.id, format)}>
                  <Download size={15} /> {busy === `${d.id}-${format}` ? 'Preparing…' : format.toUpperCase()}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
