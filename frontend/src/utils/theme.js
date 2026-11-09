// Tenant theming. Tailwind's `brand-*` (primary) and `church-*` (secondary) palettes read
// CSS variables holding "R G B" triplets, so `bg-brand-700/20` style opacity still works.
export const DEFAULT_PRIMARY = '#1A4FA0';
export const DEFAULT_SECONDARY = '#E07218';

const SHADES = { 50: 0.92, 100: 0.82, 200: 0.64, 300: 0.45, 400: 0.28, 500: 0.14, 600: 0.06, 700: 0, 800: -0.18, 900: -0.38 };

function parseHex(hex) {
  const match = /^#?([0-9a-f]{3}|[0-9a-f]{6})$/i.exec(String(hex || '').trim());
  if (!match) return null;
  let value = match[1];
  if (value.length === 3) value = value.split('').map((c) => c + c).join('');
  return [0, 2, 4].map((i) => parseInt(value.slice(i, i + 2), 16));
}

function mix(rgb, amount) {
  // amount > 0 mixes toward white, < 0 toward black.
  const target = amount > 0 ? 255 : 0;
  const t = Math.abs(amount);
  return rgb.map((c) => Math.round(c + (target - c) * t));
}

export function isValidHex(hex) {
  return Boolean(parseHex(hex));
}

function applyPalette(root, name, hex, fallback) {
  const rgb = parseHex(hex) || parseHex(fallback);
  Object.entries(SHADES).forEach(([shade, amount]) => {
    root.style.setProperty(`--${name}-${shade}`, mix(rgb, amount).join(' '));
  });
}

export function applyBrandTheme(church) {
  const root = document.documentElement;
  applyPalette(root, 'brand', church?.primary_color, DEFAULT_PRIMARY);
  applyPalette(root, 'church', church?.secondary_color, DEFAULT_SECONDARY);
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.setAttribute('content', parseHex(church?.primary_color) ? church.primary_color : DEFAULT_PRIMARY);
}
