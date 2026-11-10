/**
 * BRIDGE Design System Tokens
 * Comprehensive color system, typography scale, spacing, border radiuses, and shadows.
 */

export const colors = {
  // Brand primary palette
  primary: {
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

  // Surfaces & Backgrounds
  background: '#0B0F19',
  surface: {
    primary: '#111827',
    secondary: '#1F2937',
    card: '#151D2F',
    elevated: '#1E293B',
    hover: '#26334D',
    border: '#334155',
    borderMuted: '#1E293B',
  },

  // Typography Colors
  text: {
    primary: '#F8FAFC',
    secondary: '#94A3B8',
    muted: '#64748B',
    inverse: '#0F172A',
    accent: '#38BDF8',
  },

  // Governance & Verification Status Colors
  status: {
    supported: {
      text: '#10B981',
      bg: 'rgba(16, 185, 129, 0.12)',
      border: 'rgba(16, 185, 129, 0.3)',
      solid: '#10B981',
    },
    unsupported: {
      text: '#F43F5E',
      bg: 'rgba(244, 63, 94, 0.12)',
      border: 'rgba(244, 63, 94, 0.3)',
      solid: '#F43F5E',
    },
    high: {
      text: '#EF4444',
      bg: 'rgba(239, 68, 68, 0.12)',
      border: 'rgba(239, 68, 68, 0.35)',
      solid: '#DC2626',
    },
    medium: {
      text: '#F59E0B',
      bg: 'rgba(245, 158, 11, 0.12)',
      border: 'rgba(245, 158, 11, 0.35)',
      solid: '#D97706',
    },
    low: {
      text: '#0EA5E9',
      bg: 'rgba(14, 165, 233, 0.12)',
      border: 'rgba(14, 165, 233, 0.35)',
      solid: '#0284C7',
    },
    pending: {
      text: '#FBBF24',
      bg: 'rgba(251, 191, 36, 0.12)',
      border: 'rgba(251, 191, 36, 0.3)',
      solid: '#D97706',
    },
    approved: {
      text: '#34D399',
      bg: 'rgba(52, 211, 153, 0.12)',
      border: 'rgba(52, 211, 153, 0.3)',
      solid: '#059669',
    },
    superseded: {
      text: '#A78BFA',
      bg: 'rgba(167, 139, 250, 0.12)',
      border: 'rgba(167, 139, 250, 0.3)',
      solid: '#7C3AED',
    },
    rejected: {
      text: '#FB7185',
      bg: 'rgba(251, 113, 133, 0.12)',
      border: 'rgba(251, 113, 133, 0.3)',
      solid: '#E11D48',
    },
    confirmed: {
      text: '#2DD4BF',
      bg: 'rgba(45, 212, 191, 0.12)',
      border: 'rgba(45, 212, 191, 0.3)',
      solid: '#0D9488',
    },
    possible: {
      text: '#94A3B8',
      bg: 'rgba(148, 163, 184, 0.12)',
      border: 'rgba(148, 163, 184, 0.3)',
      solid: '#64748B',
    },
  },
} as const;

export const spacing = {
  xs: '0.25rem',   // 4px
  sm: '0.5rem',    // 8px
  md: '1rem',      // 16px
  lg: '1.5rem',    // 24px
  xl: '2rem',      // 32px
  '2xl': '3rem',   // 48px
  '3xl': '4rem',   // 64px
} as const;

export const typography = {
  fontFamily: {
    sans: 'Inter, system-ui, -apple-system, sans-serif',
    mono: 'JetBrains Mono, monospace',
  },
  fontSize: {
    xs: ['0.75rem', { lineHeight: '1rem' }],
    sm: ['0.875rem', { lineHeight: '1.25rem' }],
    base: ['1rem', { lineHeight: '1.5rem' }],
    lg: ['1.125rem', { lineHeight: '1.75rem' }],
    xl: ['1.25rem', { lineHeight: '1.75rem' }],
    '2xl': ['1.5rem', { lineHeight: '2rem' }],
    '3xl': ['1.875rem', { lineHeight: '2.25rem' }],
    '4xl': ['2.25rem', { lineHeight: '2.5rem' }],
  },
  fontWeight: {
    light: '300',
    normal: '400',
    medium: '500',
    semibold: '600',
    bold: '700',
  },
} as const;

export const borderRadius = {
  sm: '0.25rem',  // 4px
  DEFAULT: '0.375rem', // 6px
  md: '0.5rem',   // 8px
  lg: '0.75rem',  // 12px
  xl: '1rem',     // 16px
  full: '9999px',
} as const;

export const shadows = {
  subtle: '0 1px 3px rgba(0, 0, 0, 0.3)',
  card: '0 4px 6px -1px rgba(0, 0, 0, 0.4), 0 2px 4px -2px rgba(0, 0, 0, 0.3)',
  elevated: '0 10px 15px -3px rgba(0, 0, 0, 0.5), 0 4px 6px -4px rgba(0, 0, 0, 0.4)',
  glow: '0 0 20px -3px rgba(56, 189, 248, 0.25)',
  glowEmerald: '0 0 20px -3px rgba(16, 185, 129, 0.25)',
  glowRed: '0 0 20px -3px rgba(239, 68, 68, 0.25)',
} as const;

