import { clsx } from '../../design-system';

const cardBase = `
  background: var(--color-surface-panel);
  border: var(--card-border-width) solid var(--color-surface-border);
  border-radius: var(--card-radius);
  transition: all var(--transition-fast);
  overflow: hidden;
`;

const cardVariants = {
  default: `
    ${cardBase}
  `,
  elevated: `
    ${cardBase}
    box-shadow: var(--shadow-md);
  `,
  outlined: `
    ${cardBase}
    border-width: 1px;
  `,
  filled: `
    background: var(--color-surface-interactive);
    border: none;
    border-radius: var(--card-radius);
    transition: all var(--transition-fast);
  `,
  glass: `
    background: rgba(17, 20, 26, 0.8);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: var(--card-radius);
    transition: all var(--transition-fast);
  `,
};

const cardPadding = {
  none: 'padding: 0;',
  sm: 'padding: var(--card-padding-sm);',
  default: 'padding: var(--card-padding);',
  lg: 'padding: var(--space-8);',
};

export function Card({
  children,
  variant = 'default',
  padding = 'default',
  className = '',
  style = {},
  onClick,
  hoverable = false,
  ...props
}) {
  const variantStyle = cardVariants[variant] || cardVariants.default;
  const paddingStyle = cardPadding[padding] || cardPadding.default;

  const hoverStyle = hoverable ? `
    &:hover {
      border-color: var(--color-surface-border-strong);
      box-shadow: var(--shadow-lg);
      transform: translateY(-2px);
    }
  ` : '';

  const cursorStyle = onClick || hoverable ? 'cursor: pointer;' : '';

  const combinedStyle = `
    ${variantStyle}
    ${paddingStyle}
    ${hoverStyle}
    ${cursorStyle}
  `;

  return (
    <div
      className={clsx('elco-card', className)}
      style={style}
      onClick={onClick}
      {...props}
    >
      {children}
      <style jsx>{combinedStyle}</style>
    </div>
  );
}

// Card Header
export function CardHeader({
  children,
  title,
  subtitle,
  action,
  className = '',
  style = {},
  ...props
}) {
  return (
    <div
      className={clsx('elco-card-header', className)}
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'space-between',
        gap: 'var(--space-4)',
        marginBottom: 'var(--space-4)',
        paddingBottom: 'var(--space-4)',
        borderBottom: '1px solid var(--color-surface-border)',
        ...style,
      }}
      {...props}
    >
      <div style={{ flex: 1, minWidth: 0 }}>
        {title && (
          <h3
            className="elco-card-title"
            style={{
              fontSize: 'var(--font-size-lg)',
              fontWeight: 'var(--font-weight-semibold)',
              color: 'var(--color-text-primary)',
              margin: 0,
              lineHeight: 'var(--line-height-tight)',
            }}
          >
            {title}
          </h3>
        )}
        {subtitle && (
          <p
            className="elco-card-subtitle"
            style={{
              marginTop: 'var(--space-1)',
              fontSize: 'var(--font-size-sm)',
              color: 'var(--color-text-secondary)',
              lineHeight: 'var(--line-height-normal)',
            }}
          >
            {subtitle}
          </p>
        )}
        {children && !title && !subtitle && (
          <div style={{ flex: 1 }}>{children}</div>
        )}
      </div>
      {action && (
        <div
          className="elco-card-action"
          style={{
            flexShrink: 0,
            display: 'flex',
            alignItems: 'center',
          }}
        >
          {action}
        </div>
      )}
    </div>
  );
}

// Card Content
export function CardContent({
  children,
  className = '',
  style = {},
  ...props
}) {
  return (
    <div
      className={clsx('elco-card-content', className)}
      style={style}
      {...props}
    >
      {children}
    </div>
  );
}

// Card Footer
export function CardFooter({
  children,
  className = '',
  style = {},
  divided = true,
  ...props
}) {
  return (
    <div
      className={clsx('elco-card-footer', className)}
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'flex-end',
        gap: 'var(--space-3)',
        paddingTop: 'var(--space-4)',
        marginTop: 'var(--space-4)',
        borderTop: divided ? '1px solid var(--color-surface-border)' : 'none',
        ...style,
      }}
      {...props}
    >
      {children}
    </div>
  );
}

// Card Grid for dashboard layouts
export function CardGrid({
  children,
  columns = { base: 1, sm: 2, lg: 3, xl: 4 },
  gap = 'default',
  className = '',
  style = {},
  ...props
}) {
  const gapValue = gap === 'default' ? 'var(--grid-gap)' : gap === 'sm' ? 'var(--grid-gap-mobile)' : gap;

  const gridStyle = `
    display: grid;
    gap: ${gapValue};
    grid-template-columns: repeat(${columns.base || 1}, 1fr);
    @media (min-width: 640px) { grid-template-columns: repeat(${columns.sm || columns.base || 1}, 1fr); }
    @media (min-width: 1024px) { grid-template-columns: repeat(${columns.lg || columns.sm || columns.base || 1}, 1fr); }
    @media (min-width: 1280px) { grid-template-columns: repeat(${columns.xl || columns.lg || columns.sm || columns.base || 1}, 1fr); }
  `;

  return (
    <div
      className={clsx('elco-card-grid', className)}
      style={{ ...style }}
      {...props}
    >
      {children}
      <style jsx>{gridStyle}</style>
    </div>
  );
}

// Stat Card - specialized for metrics display
export function StatCard({
  label,
  value,
  change,
  changeLabel,
  trend = 'neutral', // 'up' | 'down' | 'neutral'
  icon,
  prefix,
  suffix,
  className = '',
  style = {},
  ...props
}) {
  const trendColors = {
    up: 'var(--color-market-buy)',
    down: 'var(--color-market-sell)',
    neutral: 'var(--color-market-neutral)',
  };

  const trendIcons = {
    up: '▲',
    down: '▼',
    neutral: '●',
  };

  return (
    <Card variant="default" padding="default" className={clsx('elco-stat-card', className)} style={style} {...props}>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 'var(--space-4)' }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          {label && (
            <p
              className="elco-stat-label"
              style={{
                fontSize: 'var(--font-size-xs)',
                fontWeight: 'var(--font-weight-medium)',
                color: 'var(--color-text-secondary)',
                textTransform: 'uppercase',
                letterSpacing: 'var(--letter-spacing-wider)',
                margin: 0,
                marginBottom: 'var(--space-2)',
              }}
            >
              {label}
            </p>
          )}
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 'var(--space-2)', flexWrap: 'wrap' }}>
            {prefix && (
              <span
                className="elco-stat-prefix"
                style={{
                  fontSize: 'var(--font-size-lg)',
                  fontWeight: 'var(--font-weight-semibold)',
                  color: 'var(--color-text-secondary)',
                }}
              >
                {prefix}
              </span>
            )}
            <span
              className="elco-stat-value"
              style={{
                fontSize: 'var(--font-size-3xl)',
                fontWeight: 'var(--font-weight-bold)',
                color: 'var(--color-text-primary)',
                lineHeight: 'var(--line-height-tight)',
                fontVariantNumeric: 'tabular-nums',
                fontFamily: 'var(--font-family-mono)',
              }}
            >
              {value}
            </span>
            {suffix && (
              <span
                className="elco-stat-suffix"
                style={{
                  fontSize: 'var(--font-size-lg)',
                  fontWeight: 'var(--font-weight-semibold)',
                  color: 'var(--color-text-secondary)',
                }}
              >
                {suffix}
              </span>
            )}
          </div>
          {(change !== undefined || changeLabel) && (
            <div
              className="elco-stat-change"
              style={{
                marginTop: 'var(--space-2)',
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--space-1)',
                fontSize: 'var(--font-size-xs)',
                fontWeight: 'var(--font-weight-medium)',
                color: trendColors[trend],
              }}
            >
              <span aria-hidden="true">{trendIcons[trend]}</span>
              {change !== undefined && (
                <span style={{ fontFamily: 'var(--font-family-mono)' }}>
                  {change >= 0 ? '+' : ''}{change.toFixed(2)}%
                </span>
              )}
              {changeLabel && <span style={{ color: 'var(--color-text-tertiary)' }}>{changeLabel}</span>}
            </div>
          )}
        </div>
        {icon && (
          <div
            className="elco-stat-icon"
            style={{
              flexShrink: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '48px',
              height: '48px',
              borderRadius: 'var(--radius-lg)',
              background: 'var(--color-surface-interactive)',
              color: 'var(--color-text-secondary)',
            }}
            aria-hidden="true"
          >
            {icon}
          </div>
        )}
      </div>
    </Card>
  );
}

export default Card;