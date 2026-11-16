import { clsx } from '../../design-system';

const badgeBase = `
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-1);
  font-family: var(--font-family-sans);
  font-size: var(--badge-font-size);
  font-weight: var(--badge-font-weight);
  line-height: 1;
  border-radius: var(--badge-radius);
  height: var(--badge-height);
  padding: var(--badge-padding);
  white-space: nowrap;
  user-select: none;
`;

const badgeVariants = {
  default: `
    background: var(--color-surface-interactive);
    color: var(--color-text-secondary);
    border: 1px solid var(--color-surface-border);
  `,
  primary: `
    background: var(--color-brand-100);
    color: var(--color-brand-700);
    border: 1px solid var(--color-brand-200);
  `,
  success: `
    background: var(--color-market-buy-bg);
    color: var(--color-market-buy);
    border: 1px solid var(--color-market-buy-border);
  `,
  danger: `
    background: var(--color-market-sell-bg);
    color: var(--color-market-sell);
    border: 1px solid var(--color-market-sell-border);
  `,
  warning: `
    background: var(--color-market-warning-bg);
    color: var(--color-market-warning-dark);
    border: 1px solid var(--color-market-warning-border);
  `,
  info: `
    background: var(--color-market-info-bg);
    color: var(--color-market-info);
    border: 1px solid var(--color-market-info-border);
  `,
  outline: `
    background: transparent;
    color: var(--color-text-primary);
    border: 1px solid var(--color-surface-border);
  `,
  ghost: `
    background: transparent;
    color: var(--color-text-secondary);
    border: none;
  `,
  // Market-specific variants
  buy: `
    background: var(--color-market-buy-bg);
    color: var(--color-market-buy);
    border: 1px solid var(--color-market-buy-border);
  `,
  sell: `
    background: var(--color-market-sell-bg);
    color: var(--color-market-sell);
    border: 1px solid var(--color-market-sell-border);
  `,
  neutral: `
    background: var(--color-market-neutral-bg);
    color: var(--color-market-neutral);
    border: 1px solid var(--color-market-neutral-border);
  `,
  // Status variants
  connected: `
    background: var(--color-status-success);
    color: white;
    border: none;
  `,
  disconnected: `
    background: var(--color-status-error);
    color: white;
    border: none;
  `,
  connecting: `
    background: var(--color-status-warning);
    color: white;
    border: none;
  `,
};

const badgeSizes = {
  sm: `
    height: 16px;
    padding: 0 6px;
    font-size: 0.625rem;
    gap: 4px;
  `,
  default: `
    height: var(--badge-height);
    padding: var(--badge-padding);
    font-size: var(--badge-font-size);
    gap: var(--space-1);
  `,
  lg: `
    height: 24px;
    padding: 0 10px;
    font-size: var(--font-size-xs);
    gap: var(--space-2);
  `,
};

export function Badge({
  children,
  variant = 'default',
  size = 'default',
  className = '',
  style = {},
  dot = false,
  dotColor,
  removable = false,
  onRemove,
  ...props
}) {
  const variantStyle = badgeVariants[variant] || badgeVariants.default;
  const sizeStyle = badgeSizes[size] || badgeSizes.default;

  const combinedStyle = `
    ${badgeBase}
    ${variantStyle}
    ${sizeStyle}
  `;

  return (
    <span
      className={clsx('elco-badge', className)}
      style={style}
      {...props}
    >
      {dot && (
        <span
          className="elco-badge-dot"
          style={{
            width: '6px',
            height: '6px',
            borderRadius: '50%',
            background: dotColor || 'currentColor',
            flexShrink: 0,
            ...(variant === 'connecting' && {
              animation: 'pulse 1.5s ease-in-out infinite',
            }),
          }}
          aria-hidden="true"
        />
      )}
      <span className="elco-badge-content">{children}</span>
      {removable && (
        <button
          type="button"
          className="elco-badge-remove"
          onClick={(e) => {
            e.stopPropagation();
            onRemove?.(e);
          }}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '16px',
            height: '16px',
            border: 'none',
            background: 'transparent',
            color: 'inherit',
            opacity: 0.6,
            borderRadius: '50%',
            cursor: 'pointer',
            padding: 0,
            marginLeft: '4px',
            transition: 'opacity var(--transition-fast)',
          }}
          onMouseEnter={(e) => e.target.style.opacity = '1'}
          onMouseLeave={(e) => e.target.style.opacity = '0.6'}
          aria-label="Remove"
        >
          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      )}
      <style jsx>{`
        ${combinedStyle}
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
      `}</style>
    </span>
  );
}

// Status Badge with dot indicator
export function StatusBadge({
  status, // 'connected' | 'disconnected' | 'connecting' | 'error' | 'warning' | 'success' | 'idle'
  label,
  className = '',
  style = {},
  ...props
}) {
  const statusMap = {
    connected: { variant: 'connected', label: label || 'Connected' },
    disconnected: { variant: 'disconnected', label: label || 'Disconnected' },
    connecting: { variant: 'connecting', label: label || 'Connecting...' },
    error: { variant: 'danger', label: label || 'Error' },
    warning: { variant: 'warning', label: label || 'Warning' },
    success: { variant: 'success', label: label || 'Success' },
    idle: { variant: 'default', label: label || 'Idle' },
  };

  const { variant, label: statusLabel } = statusMap[status] || statusMap.idle;

  return (
    <Badge variant={variant} dot={true} className={clsx('elco-status-badge', className)} style={style} {...props}>
      {statusLabel}
    </Badge>
  );
}

// Pill Badge - rounded full
export function PillBadge({
  children,
  variant = 'default',
  size = 'default',
  className = '',
  style = {},
  leftIcon,
  rightIcon,
  onClick,
  ...props
}) {
  const variantStyle = badgeVariants[variant] || badgeVariants.default;
  const sizeStyle = badgeSizes[size] || badgeSizes.default;

  const combinedStyle = `
    ${badgeBase}
    ${variantStyle}
    ${sizeStyle}
    border-radius: var(--radius-full);
    ${onClick ? 'cursor: pointer;' : ''}
  `;

  return (
    <span
      className={clsx('elco-pill-badge', className)}
      style={style}
      onClick={onClick}
      {...props}
    >
      {leftIcon && <span aria-hidden="true">{leftIcon}</span>}
      <span>{children}</span>
      {rightIcon && <span aria-hidden="true">{rightIcon}</span>}
      <style jsx>{combinedStyle}</style>
    </span>
  );
}

// Counter Badge - for notification counts
export function CounterBadge({
  count,
  max = 99,
  variant = 'danger',
  className = '',
  style = {},
  ...props
}) {
  if (!count || count <= 0) return null;

  const displayCount = count > max ? `${max}+` : count.toString();

  return (
    <Badge
      variant={variant}
      size="sm"
      className={clsx('elco-counter-badge', className)}
      style={{
        minWidth: '18px',
        height: '18px',
        padding: '0 4px',
        fontSize: '10px',
        ...style,
      }}
      {...props}
    >
      {displayCount}
    </Badge>
  );
}

export default Badge;