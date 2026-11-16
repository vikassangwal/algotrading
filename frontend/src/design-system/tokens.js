/**
 * ELCO Trader Design System Tokens
 * A cohesive, opinionated design language for algorithmic trading
 * Built for precision, clarity, and trader confidence
 */

export const colors = {
  // Core brand - deep midnight with subtle blue undertone
  brand: {
    50: '#eef2ff',
    100: '#e0e7ff',
    200: '#c7d2fe',
    300: '#a5b4fc',
    400: '#818cf8',
    500: '#6366f1',  // Primary brand
    600: '#4f46e5',
    700: '#4338ca',
    800: '#3730a3',
    900: '#312e81',
    950: '#1e1b4b',
  },

  // Market semantics - buy/sell/neutral with purpose
  market: {
    buy: {
      light: '#059669',
      DEFAULT: '#10b981',
      dark: '#047857',
      bg: 'rgba(16, 185, 129, 0.1)',
      border: 'rgba(16, 185, 129, 0.3)',
      glow: 'rgba(16, 185, 129, 0.4)',
    },
    sell: {
      light: '#dc2626',
      DEFAULT: '#ef4444',
      dark: '#b91c1c',
      bg: 'rgba(239, 68, 68, 0.1)',
      border: 'rgba(239, 68, 68, 0.3)',
      glow: 'rgba(239, 68, 68, 0.4)',
    },
    neutral: {
      light: '#d97706',
      DEFAULT: '#f59e0b',
      dark: '#b45309',
      bg: 'rgba(245, 158, 11, 0.1)',
      border: 'rgba(245, 158, 11, 0.3)',
      glow: 'rgba(245, 158, 11, 0.4)',
    },
    warning: {
      light: '#f97316',
      DEFAULT: '#fb923c',
      dark: '#ea580c',
      bg: 'rgba(251, 146, 60, 0.1)',
      border: 'rgba(251, 146, 60, 0.3)',
    },
    info: {
      light: '#0284c7',
      DEFAULT: '#0ea5e9',
      dark: '#0369a1',
      bg: 'rgba(14, 165, 233, 0.1)',
      border: 'rgba(14, 165, 233, 0.3)',
    },
  },

  // Surface system - layered depth for trading density
  surface: {
    // Base layer - deepest
    base: '#0a0c10',
    // Elevated panels
    panel: '#11141a',
    panelHover: '#161a22',
    // Interactive elements
    interactive: '#1a1e28',
    interactiveHover: '#202532',
    // Borders and dividers
    border: '#242936',
    borderStrong: '#2d3444',
    // Overlay/modal
    overlay: 'rgba(10, 12, 16, 0.85)',
    overlayStrong: 'rgba(10, 12, 16, 0.95)',
  },

  // Text hierarchy - optimized for data density
  text: {
    primary: '#e8ebf0',
    secondary: '#9aa3b2',
    tertiary: '#6b7280',
    inverse: '#0a0c10',
    disabled: '#4b5563',
    // Market-specific text
    buy: '#10b981',
    sell: '#ef4444',
    neutral: '#f59e0b',
    // Accent text
    accent: '#818cf8',
    accentStrong: '#a5b4fc',
  },

  // Chart-specific palette (colorblind-safe)
  chart: {
    grid: '#1e2430',
    axis: '#4b5563',
    tooltip: '#0a0c10',
    tooltipBorder: '#2d3444',
    series: {
      primary: '#6366f1',
      secondary: '#f59e0b',
      tertiary: '#10b981',
      quaternary: '#ef4444',
      quinary: '#0ea5e9',
      senary: '#a855f7',
      // Volume
      volumeUp: 'rgba(16, 185, 129, 0.5)',
      volumeDown: 'rgba(239, 68, 68, 0.5)',
      volumeNeutral: 'rgba(139, 148, 158, 0.5)',
      // Indicators
      ma: '#6366f1',
      ema: '#f59e0b',
      bbUpper: '#ef4444',
      bbLower: '#10b981',
      rsi: '#a855f7',
      macd: '#0ea5e9',
      signal: '#f59e0b',
      histogram: '#6366f1',
    },
  },

  // Status indicators
  status: {
    connected: '#10b981',
    disconnected: '#ef4444',
    connecting: '#f59e0b',
    error: '#ef4444',
    success: '#10b981',
    warning: '#fb923c',
    info: '#0ea5e9',
  },
};

export const typography = {
  // Single typeface family with clear hierarchy
  // Using system font stack for performance and native feel
  fontFamily: {
    sans: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
    mono: 'JetBrains Mono, "Fira Code", "SF Mono", Monaco, Consolas, monospace',
    // Display font for headlines - distinctive but readable
    display: 'Inter Tight, Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  },

  // Fluid type scale - responsive without breakpoints
  fontSize: {
    xs: 'clamp(0.6875rem, 0.65rem + 0.1875vw, 0.75rem)',      // 11-12px
    sm: 'clamp(0.8125rem, 0.765rem + 0.2375vw, 0.875rem)',      // 13-14px
    base: 'clamp(0.9375rem, 0.875rem + 0.3125vw, 1rem)',        // 15-16px
    lg: 'clamp(1.0625rem, 0.984rem + 0.3925vw, 1.125rem)',      // 17-18px
    xl: 'clamp(1.25rem, 1.14rem + 0.55vw, 1.5rem)',             // 20-24px
    '2xl': 'clamp(1.5rem, 1.35rem + 0.75vw, 1.875rem)',         // 24-30px
    '3xl': 'clamp(1.875rem, 1.65rem + 1.125vw, 2.5rem)',        // 30-40px
    '4xl': 'clamp(2.5rem, 2.15rem + 1.75vw, 3.5rem)',           // 40-56px
  },

  fontWeight: {
    normal: 400,
    medium: 500,
    semibold: 600,
    bold: 700,
    extrabold: 800,
  },

  lineHeight: {
    tight: 1.1,
    snug: 1.375,
    normal: 1.5,
    relaxed: 1.625,
    loose: 2,
  },

  letterSpacing: {
    tighter: '-0.02em',
    tight: '-0.01em',
    normal: '0',
    wide: '0.01em',
    wider: '0.02em',
    widest: '0.04em',
  },
};

export const spacing = {
  // 4px base unit with semantic naming
  0: '0',
  1: '0.25rem',   // 4px
  2: '0.5rem',    // 8px
  3: '0.75rem',   // 12px
  4: '1rem',      // 16px
  5: '1.25rem',   // 20px
  6: '1.5rem',    // 24px
  8: '2rem',      // 32px
  10: '2.5rem',   // 40px
  12: '3rem',     // 48px
  16: '4rem',     // 64px
  20: '5rem',     // 80px
  24: '6rem',     // 96px
};

export const borderRadius = {
  none: '0',
  sm: '0.25rem',    // 4px
  DEFAULT: '0.375rem', // 6px
  md: '0.5rem',     // 8px
  lg: '0.75rem',    // 12px
  xl: '1rem',       // 16px
  '2xl': '1.5rem',  // 24px
  full: '9999px',
};

export const shadows = {
  // Subtle, purposeful shadows for depth
  xs: '0 1px 2px rgba(0, 0, 0, 0.3)',
  sm: '0 2px 4px rgba(0, 0, 0, 0.35)',
  DEFAULT: '0 4px 8px rgba(0, 0, 0, 0.4)',
  md: '0 8px 16px rgba(0, 0, 0, 0.45)',
  lg: '0 16px 32px rgba(0, 0, 0, 0.5)',
  xl: '0 24px 48px rgba(0, 0, 0, 0.55)',
  // Inset for pressed states
  inset: 'inset 0 2px 4px rgba(0, 0, 0, 0.4)',
  // Glow effects for market signals
  glowBuy: '0 0 12px rgba(16, 185, 129, 0.3)',
  glowSell: '0 0 12px rgba(239, 68, 68, 0.3)',
  glowBrand: '0 0 12px rgba(99, 102, 241, 0.3)',
};

export const transitions = {
  // Purposeful motion - fast for trading UI
  fast: '100ms cubic-bezier(0.4, 0, 0.2, 1)',
  DEFAULT: '150ms cubic-bezier(0.4, 0, 0.2, 1)',
  slow: '200ms cubic-bezier(0.4, 0, 0.2, 1)',
  // Spring for organic feel
  spring: '300ms cubic-bezier(0.34, 1.56, 0.64, 1)',
};

export const zIndex = {
  hide: -1,
  base: 0,
  dropdown: 100,
  sticky: 200,
  overlay: 300,
  modal: 400,
  popover: 500,
  tooltip: 600,
  toast: 700,
  max: 9999,
};

export const breakpoints = {
  sm: '640px',
  md: '768px',
  lg: '1024px',
  xl: '1280px',
  '2xl': '1536px',
};

export const layout = {
  sidebar: {
    width: '280px',
    widthCollapsed: '72px',
    widthMobile: '100%',
  },
  header: {
    height: '56px',
    heightMobile: '52px',
  },
  content: {
    maxWidth: '1440px',
    padding: '1.5rem',
    paddingMobile: '1rem',
  },
  // Grid for dashboard panels
  grid: {
    columns: 12,
    gap: '1.5rem',
    gapMobile: '1rem',
  },
};

// Semantic component tokens
export const components = {
  button: {
    height: {
      sm: '32px',
      DEFAULT: '40px',
      lg: '48px',
    },
    padding: {
      sm: '0 12px',
      DEFAULT: '0 16px',
      lg: '0 24px',
    },
    borderRadius: '0.5rem',
    fontWeight: 500,
  },
  input: {
    height: {
      sm: '32px',
      DEFAULT: '40px',
      lg: '48px',
    },
    padding: '0 12px',
    borderRadius: '0.5rem',
    borderWidth: '1px',
  },
  card: {
    padding: '1.5rem',
    paddingSm: '1rem',
    borderRadius: '0.75rem',
    borderWidth: '1px',
  },
  table: {
    cellPadding: '0.75rem 1rem',
    headerHeight: '40px',
    rowHeight: '48px',
    fontSize: '0.875rem',
  },
  badge: {
    height: '20px',
    padding: '0 8px',
    fontSize: '0.6875rem',
    fontWeight: 600,
    borderRadius: '0.25rem',
  },
};

export default {
  colors,
  typography,
  spacing,
  borderRadius,
  shadows,
  transitions,
  zIndex,
  breakpoints,
  layout,
  components,
};