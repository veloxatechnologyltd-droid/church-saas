/** @type {import('tailwindcss').Config} */
// `brand` (primary) and `church` (secondary) come from the active church's colours via CSS
// variables set in src/utils/theme.js. `accent` (danger) and `success` are fixed semantics.
const fromVar = (name) =>
  Object.fromEntries(
    [50, 100, 200, 300, 400, 500, 600, 700, 800, 900].map((shade) => [shade, `rgb(var(--${name}-${shade}) / <alpha-value>)`])
  );

export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        brand: fromVar('brand'),
        primary: fromVar('brand'),
        church: fromVar('church'),
        secondary: fromVar('church'),
        accent: {
          50: '#FEF2F0',
          100: '#FDDBD7',
          600: '#D42A1A',
          700: '#C02416',
          800: '#9A1C10',
        },
        success: {
          50: '#F0FDF4',
          100: '#DCFCE7',
          700: '#15803D',
          800: '#166534',
        },
      },
      fontFamily: {
        sans: ['Manrope', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
