import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        bridge: {
          50: '#F0F7FF',
          100: '#E0EFFF',
          200: '#BAE0FF',
          300: '#7CC5FF',
          400: '#38A4FF',
          500: '#0C87EB',
          600: '#0069C7',
          700: '#0053A3',
          800: '#054785',
          900: '#0B3C6E',
          950: '#07264A',
        },
        surface: {
          DEFAULT: '#0F172A',
          darker: '#090D16',
          card: '#1E293B',
          border: '#334155',
          muted: '#94A3B8',
        },
        status: {
          supported: '#10B981',
          unsupported: '#EF4444',
          high: '#DC2626',
          medium: '#F59E0B',
          low: '#0EA5E9',
          pending: '#F59E0B',
          approved: '#10B981',
          superseded: '#8B5CF6',
          rejected: '#F43F5E',
          confirmed: '#0D9488',
          possible: '#64748B',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      boxShadow: {
        glow: '0 0 20px -3px rgba(14, 165, 233, 0.25)',
        'glow-red': '0 0 20px -3px rgba(239, 68, 68, 0.25)',
      },
    },
  },
  plugins: [],
};

export default config;

