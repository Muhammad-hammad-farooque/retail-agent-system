import type { Config } from 'tailwindcss';

/**
 * Palette: "Aubergine & Ash".
 *
 * `brand` and `ash` are anchored on hand-picked values — brand-600, brand-800,
 * brand-100, ash-50, ash-200 and ash-900 are exact; the rest are interpolated
 * from them. Every step used for text clears WCAG AA on its intended surface.
 *
 * Status colours stay emerald / amber / red from the default Tailwind ramps.
 * The brand sits at 295° on the hue wheel, 65-132° from all three, so a brand
 * accent can never be mistaken for a stock status.
 */
const config: Config = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#f7f0f9',
          100: '#ebd7ef',
          200: '#d6b8db',
          300: '#c197c6',
          400: '#a770ad',
          500: '#9b5ea0',
          600: '#8d4893',
          700: '#742279',
          800: '#5f0264',
          900: '#51084a',
          950: '#460c34',
        },
        ash: {
          50: '#faf8fa',
          100: '#ebe5ec',
          200: '#ded5e0',
          300: '#b1a7b2',
          400: '#8d828c',
          500: '#72686f',
          600: '#5b4f58',
          700: '#523349',
          800: '#4c1f3e',
          900: '#460c34',
        },
      },
    },
  },
  plugins: [],
};

export default config;
