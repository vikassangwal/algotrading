import { clsx } from '../../design-system';

const buttonBase = `
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-family: var(--font-family-sans);
  font-weight: var(--btn-font-weight);
  border-radius: var(--btn-radius);
  border: 1px solid transparent;
  cursor: pointer;
  transition: all var(--transition-fast);
  white-space: nowrap;
  user-select: none;
  outline: none;
  position: relative;
  overflow: hidden;
`;

const buttonVariants = {
  primary: `
    background: var(--color-brand-500);
    color: white;
    border-color: var(--color-brand-500);
  `,
  secondary: `
    background: var(--color-surface-interactive);
    color: var(--color-text-primary);
    border-color: var(--color-surface-border);
  `,
  outline: `
    background: transparent;
    color: var(--color-text-primary);
    border-color: var(--color-surface-border);
  `,
  ghost: `
    background: transparent;
    color: var(--color-text-secondary);
    border-color: transparent;
  `,
  danger: `
    background: var(--color-market-sell);
    color: white;
    border-color: var(--color-market-sell);
  `,
  success: `
    background: var(--color-market-buy);
    color: white;
    border-color: var(--color-market-buy);
  `,
  link: `
    background: transparent;
    color: var(--color-brand-400);
    border-color: transparent;
    padding: 0;
    height: auto;
  `,
};

const buttonSizes = {
  sm: `
    height: var(--btn-height-sm);
    padding: var(--btn-padding-sm);
    font-size: var(--font-size-xs);
    gap: 6px;
  `,
  default: `
    height: var(--btn-height-default);
    padding: var(--btn-padding-default);
    font-size: var(--font-size-sm);
    gap: 8px;
  `,
  lg: `
    height: var(--btn-height-lg);
    padding: var(--btn-padding-lg);
    font-size: var(--font-size-base);
    gap: 10px;
  `,
  icon: `
    height: var(--btn-height-default);
    width: var(--btn-height-default);
    padding: 0;
    border-radius: var(--radius-md);
  `,
  iconSm: `
    height: var(--btn-height-sm);
    width: var(--btn-height-sm);
    padding: 0;
    border-radius: var(--radius-sm);
  `,
  iconLg: `
    height: var(--btn-height-lg);
    width: var(--btn-height-lg);
    padding: 0;
    border-radius: var(--radius-lg);
  `,
};

const buttonStates = `
  &:hover:not(:disabled) {
    filter: brightness(1.1);
    transform: translateY(-1px);
  }
  &:active:not(:disabled) {
    transform: translateY(0);
    filter: brightness(0.95);
  }
  &:focus-visible {
    box-shadow: 0 0 0 3px var(--color-brand-500), var(--shadow-default);
  }
  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
    transform: none;
  }
`;

const loadingSpinner = `
  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }
  .btn-spinner {
    width: 1em;
    height: 1em;
    border: 2px solid currentColor;
    border-right-color: transparent;
    border-radius: 50%;
    animation: spin 0.6s linear infinite;
  }
`;

export function Button({
  children,
  variant = 'primary',
  size = 'default',
  disabled = false,
  loading = false,
  leftIcon,
  rightIcon,
  fullWidth = false,
  className = '',
  style = {},
  type = 'button',
  onClick,
  ...props
}) {
  const isIconOnly = !children && (leftIcon || rightIcon);

  const baseStyle = {
    ...(fullWidth ? { width: '100%' } : {}),
    ...style,
  };

  const variantStyle = buttonVariants[variant] || buttonVariants.primary;
  const sizeStyle = buttonSizes[size] || buttonSizes.default;

  // Combine all styles
  const combinedStyle = `
    ${buttonBase}
    ${variantStyle}
    ${sizeStyle}
    ${buttonStates}
    ${loadingSpinner}
  `;

  return (
    <button
      type={type}
      disabled={disabled || loading}
      onClick={onClick}
      className={clsx('elco-btn', className)}
      style={{
        ...baseStyle,
        // We'll use CSS-in-JS approach via style attribute
        // In production, this would be a CSS module or styled-components
      }}
      {...props}
    >
      {loading ? (
        <span className="btn-spinner" aria-hidden="true" />
      ) : (
        <>
          {leftIcon && <span aria-hidden="true">{leftIcon}</span>}
          {children}
          {rightIcon && <span aria-hidden="true">{rightIcon}</span>}
        </>
      )}
      <style jsx>{combinedStyle}</style>
    </button>
  );
}

// Icon Button variant
export function IconButton({
  icon,
  variant = 'ghost',
  size = 'icon',
  disabled = false,
  loading = false,
  className = '',
  'aria-label': ariaLabel,
  onClick,
  ...props
}) {
  return (
    <Button
      variant={variant}
      size={size}
      disabled={disabled}
      loading={loading}
      className={clsx('elco-icon-btn', className)}
      aria-label={ariaLabel}
      onClick={onClick}
      {...props}
    >
      {icon}
    </Button>
  );
}

// Toggle Button for on/off states
export function ToggleButton({
  pressed = false,
  variant = 'outline',
  size = 'default',
  disabled = false,
  className = '',
  children,
  onClick,
  'aria-label': ariaLabel,
  ...props
}) {
  return (
    <Button
      variant={pressed ? 'primary' : variant}
      size={size}
      disabled={disabled}
      className={clsx('elco-toggle-btn', pressed && 'pressed', className)}
      aria-pressed={pressed}
      aria-label={ariaLabel}
      onClick={onClick}
      {...props}
    >
      {children}
    </Button>
  );
}

// Button Group for grouped actions
export function ButtonGroup({ children, className = '', vertical = false, ...props }) {
  return (
    <div
      className={clsx('elco-btn-group', vertical && 'vertical', className)}
      role="group"
      {...props}
      style={{
        display: vertical ? 'flex' : 'inline-flex',
        flexDirection: vertical ? 'column' : 'row',
        borderRadius: 'var(--radius-md)',
        overflow: 'hidden',
        border: '1px solid var(--color-surface-border)',
        background: 'var(--color-surface-panel)',
      }}
    >
      {children}
    </div>
  );
}

// Split Button with dropdown
export function SplitButton({
  children,
  variant = 'primary',
  size = 'default',
  disabled = false,
  className = '',
  onClick,
  dropdownTrigger,
  ...props
}) {
  return (
    <div className={clsx('elco-split-btn', className)} style={{ display: 'inline-flex' }}>
      <Button
        variant={variant}
        size={size}
        disabled={disabled}
        className="split-btn-main"
        onClick={onClick}
        style={{ borderTopRightRadius: 0, borderBottomRightRadius: 0 }}
        {...props}
      >
        {children}
      </Button>
      <Button
        variant={variant}
        size={size}
        disabled={disabled}
        className="split-btn-dropdown"
        style={{
          borderTopLeftRadius: 0,
          borderBottomLeftRadius: 0,
          borderLeft: '1px solid rgba(255,255,255,0.2)',
          paddingLeft: '12px',
          paddingRight: '12px',
        }}
      >
        {dropdownTrigger || '▼'}
      </Button>
    </div>
  );
}

export default Button;