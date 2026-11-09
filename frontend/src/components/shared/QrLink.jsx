import { Check, Copy, ExternalLink } from 'lucide-react';
import { useState } from 'react';

// Shows a QR code (rendered by api.qrserver.com) plus the URL with copy/open buttons.
export default function QrLink({ url, title, description, size = 200 }) {
  const [copied, setCopied] = useState(false);
  if (!url) return null;
  const qr = `https://api.qrserver.com/v1/create-qr-code/?size=${size}x${size}&margin=8&data=${encodeURIComponent(url)}`;

  async function copy() {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-4 sm:flex-row sm:items-center">
      <img src={qr} alt={`QR code for ${title || url}`} width={size / 1.6} height={size / 1.6} className="mx-auto rounded-xl ring-1 ring-slate-200 sm:mx-0" />
      <div className="min-w-0 flex-1">
        {title ? <p className="font-bold text-slate-900">{title}</p> : null}
        {description ? <p className="mt-0.5 text-sm text-slate-500">{description}</p> : null}
        <p className="mt-2 break-all rounded-lg bg-slate-50 px-3 py-2 font-mono text-xs text-slate-700">{url}</p>
        <div className="mt-2 flex flex-wrap gap-2">
          <button type="button" onClick={copy} className="btn-outline px-3 py-1.5 text-xs">
            {copied ? <Check size={14} /> : <Copy size={14} />}
            {copied ? 'Copied' : 'Copy link'}
          </button>
          <a href={url} target="_blank" rel="noreferrer" className="btn-outline px-3 py-1.5 text-xs">
            <ExternalLink size={14} /> Open
          </a>
          <a href={qr.replace(`${size}x${size}`, '600x600')} target="_blank" rel="noreferrer" className="btn-ghost text-xs">
            Print-size QR
          </a>
        </div>
      </div>
    </div>
  );
}
