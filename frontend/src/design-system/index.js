/**
 * ELCO Trader Design System
 * Main export barrel file
 */

// Tokens
export * from './tokens.js';
export { default as tokens } from './tokens.js';

// CSS Variables (imported globally)
import './variables.css';

// Utility functions
export const clsx = (...classes) => {
  return classes
    .flat()
    .filter(Boolean)
    .join(' ');
};

export const twMerge = (...classes) => {
  // Simple tailwind-like class merging for conflicting utilities
  const classMap = new Map();
  classes.flat().filter(Boolean).forEach(cls => {
    const parts = cls.split(' ');
    parts.forEach(part => {
      const [prefix] = part.split('-');
      classMap.set(prefix, part);
    });
  });
  return Array.from(classMap.values()).join(' ');
};

// Component variants using clsx
export const createVariants = (base, variants = {}) => {
  return (props = {}) => {
    const { className, variant, size, ...rest } = props;
    const variantClasses = variant ? variants[variant] : '';
    const sizeClasses = size ? variants[size] : '';
    return clsx(base, variantClasses, sizeClasses, className);
  };
};

// Format utilities for trading data
export const formatters = {
  price: (value, decimals = 2) => {
    if (value === null || value === undefined || isNaN(value)) return '—';
    return new Intl.NumberFormat('en-IN', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    }).format(value);
  },

  priceCompact: (value) => {
    if (value === null || value === undefined || isNaN(value)) return '—';
    const abs = Math.abs(value);
    if (abs >= 1e7) return `₹${(value / 1e7).toFixed(2)}Cr`;
    if (abs >= 1e5) return `₹${(value / 1e5).toFixed(2)}L`;
    if (abs >= 1e3) return `₹${(value / 1e3).toFixed(2)}K`;
    return `₹${value.toFixed(2)}`;
  },

  percent: (value, decimals = 2, showSign = true) => {
    if (value === null || value === undefined || isNaN(value)) return '—';
    const sign = showSign && value > 0 ? '+' : '';
    return `${sign}${value.toFixed(decimals)}%`;
  },

  volume: (value) => {
    if (value === null || value === undefined || isNaN(value)) return '—';
    const abs = Math.abs(value);
    if (abs >= 1e7) return `${(value / 1e7).toFixed(2)}Cr`;
    if (abs >= 1e5) return `${(value / 1e5).toFixed(2)}L`;
    if (abs >= 1e3) return `${(value / 1e3).toFixed(2)}K`;
    return value.toString();
  },

  quantity: (value) => {
    if (value === null || value === undefined || isNaN(value)) return '—';
    return new Intl.NumberFormat('en-IN').format(Math.round(value));
  },

  timestamp: (timestamp, options = {}) => {
    if (!timestamp) return '—';
    const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp;
    return date.toLocaleString('en-IN', {
      hour12: false,
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      ...options,
    });
  },

  timeOnly: (timestamp) => {
    if (!timestamp) return '—';
    const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp;
    return date.toLocaleTimeString('en-IN', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  },

  change: (current, previous, decimals = 2) => {
    if (current === null || previous === null || previous === 0) return { value: 0, percent: 0, direction: 'neutral' };
    const change = current - previous;
    const percent = (change / previous) * 100;
    return {
      value: change,
      percent,
      direction: change > 0 ? 'up' : change < 0 ? 'down' : 'neutral',
    };
  },
};

// Market status helpers
export const marketStatus = {
  isMarketOpen: () => {
    const now = new Date();
    const day = now.getDay(); // 0 = Sunday, 6 = Saturday
    const hours = now.getHours();
    const minutes = now.getMinutes();
    const timeInMinutes = hours * 60 + minutes;

    // NSE: Monday-Friday, 9:15 AM - 3:30 PM IST
    if (day === 0 || day === 6) return false; // Weekend
    const marketOpen = 9 * 60 + 15; // 9:15 AM
    const marketClose = 15 * 60 + 30; // 3:30 PM
    return timeInMinutes >= marketOpen && timeInMinutes <= marketClose;
  },

  getMarketPhase: () => {
    const now = new Date();
    const day = now.getDay();
    const hours = now.getHours();
    const minutes = now.getMinutes();
    const timeInMinutes = hours * 60 + minutes;

    if (day === 0 || day === 6) return 'closed_weekend';

    const preMarketStart = 9 * 60; // 9:00 AM
    const marketOpen = 9 * 60 + 15; // 9:15 AM
    const marketClose = 15 * 60 + 30; // 3:30 PM
    const postMarketEnd = 16 * 60; // 4:00 PM

    if (timeInMinutes < preMarketStart) return 'closed';
    if (timeInMinutes < marketOpen) return 'pre_market';
    if (timeInMinutes <= marketClose) return 'open';
    if (timeInMinutes <= postMarketEnd) return 'post_market';
    return 'closed';
  },

  getTimeToNextSession: () => {
    const now = new Date();
    const day = now.getDay();
    const hours = now.getHours();
    const minutes = now.getMinutes();
    const timeInMinutes = hours * 60 + minutes;

    const marketOpen = 9 * 60 + 15;

    if (day === 0) { // Sunday
      return { days: 1, minutes: (24 * 60 - timeInMinutes) + marketOpen };
    }
    if (day === 6) { // Saturday
      return { days: 2, minutes: (24 * 60 - timeInMinutes) + marketOpen };
    }
    if (timeInMinutes < marketOpen) {
      return { days: 0, minutes: marketOpen - timeInMinutes };
    }
    // After market close, next session is tomorrow (or Monday if Friday)
    const daysUntilNext = day === 5 ? 3 : 1; // Friday -> Monday (3 days)
    return { days: daysUntilNext, minutes: (24 * 60 - timeInMinutes) + marketOpen };
  },
};

// Color utilities
export const colorUtils = {
  getMarketColor: (value) => {
    if (value > 0) return 'var(--color-market-buy)';
    if (value < 0) return 'var(--color-market-sell)';
    return 'var(--color-market-neutral)';
  },

  getMarketBgColor: (value) => {
    if (value > 0) return 'var(--color-market-buy-bg)';
    if (value < 0) return 'var(--color-market-sell-bg)';
    return 'var(--color-market-neutral-bg)';
  },

  getMarketBorderColor: (value) => {
    if (value > 0) return 'var(--color-market-buy-border)';
    if (value < 0) return 'var(--color-market-sell-border)';
    return 'var(--color-market-neutral-border)';
  },

  hexToRgba: (hex, alpha = 1) => {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    if (!result) return hex;
    const r = parseInt(result[1], 16);
    const g = parseInt(result[2], 16);
    const b = parseInt(result[3], 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  },

  adjustBrightness: (hex, percent) => {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    if (!result) return hex;
    const adjust = (color) => Math.max(0, Math.min(255, Math.round(color * (1 + percent / 100))));
    const r = adjust(parseInt(result[1], 16));
    const g = adjust(parseInt(result[2], 16));
    const b = adjust(parseInt(result[3], 16));
    return `#${((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1)}`;
  },
};

// Responsive helpers
export const mediaQuery = {
  sm: `@media (min-width: 640px)`,
  md: `@media (min-width: 768px)`,
  lg: `@media (min-width: 1024px)`,
  xl: `@media (min-width: 1280px)`,
  '2xl': `@media (min-width: 1536px)`,
  mobile: `@media (max-width: 767px)`,
  tablet: `@media (min-width: 768px) and (max-width: 1023px)`,
  desktop: `@media (min-width: 1024px)`,
  reducedMotion: `@media (prefers-reduced-motion: reduce)`,
  highContrast: `@media (prefers-contrast: high)`,
  dark: `@media (prefers-color-scheme: dark)`,
  light: `@media (prefers-color-scheme: light)`,
};

// Animation keyframes (as CSS-in-JS strings)
export const keyframes = {
  fadeIn: `
    @keyframes fadeIn {
      from { opacity: 0; }
      to { opacity: 1; }
    }
  `,
  slideUp: `
    @keyframes slideUp {
      from { opacity: 0; transform: translateY(10px); }
      to { opacity: 1; transform: translateY(0); }
    }
  `,
  slideDown: `
    @keyframes slideDown {
      from { opacity: 0; transform: translateY(-10px); }
      to { opacity: 1; transform: translateY(0); }
    }
  `,
  slideInRight: `
    @keyframes slideInRight {
      from { opacity: 0; transform: translateX(20px); }
      to { opacity: 1; transform: translateX(0); }
    }
  `,
  pulse: `
    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.5; }
    }
  `,
  spin: `
    @keyframes spin {
      from { transform: rotate(0deg); }
      to { transform: rotate(360deg); }
    }
  `,
  marquee: `
    @keyframes marquee {
      0% { transform: translateX(0); }
      100% { transform: translateX(-50%); }
    }
  `,
  glowPulse: `
    @keyframes glowPulse {
      0%, 100% { box-shadow: 0 0 12px rgba(16, 185, 129, 0.3); }
      50% { box-shadow: 0 0 24px rgba(16, 185, 129, 0.6); }
    }
  `,
  shimmer: `
    @keyframes shimmer {
      0% { background-position: -200% 0; }
      100% { background-position: 200% 0; }
    }
  `,
};

// Generate all keyframes as a single style string
export const allKeyframes = Object.values(keyframes).join('\n');

export default {
  tokens: require('./tokens.js').default,
  clsx,
  twMerge,
  createVariants,
  formatters,
  marketStatus,
  colorUtils,
  mediaQuery,
  keyframes,
  allKeyframes,
};