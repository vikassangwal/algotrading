import { clsx } from '../../design-system';
import { useId } from 'react';

const inputBase = `
  width: 100%;
  font-family: var(--font-family-sans);
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
  background: var(--color-surface-interactive);
  border: var(--input-border-width) solid var(--color-surface-border);
  border-radius: var(--input-radius);
  transition: all var(--transition-fast);
  outline: none;
  box-sizing: border-box;
`;

const inputSizes = {
  sm: `
    height: var(--input-height-sm);
    padding: var(--input-padding);
    font-size: var(--font-size-xs);
  `,
  default: `
    height: var(--input-height-default);
    padding: var(--input-padding);
    font-size: var(--font-size-sm);
  `,
  lg: `
    height: var(--input-height-lg);
    padding: var(--input-padding);
    font-size: var(--font-size-base);
  `,
};

const inputStates = `
  &::placeholder {
    color: var(--color-text-tertiary);
  }
  &:hover:not(:disabled):not([readonly]) {
    border-color: var(--color-surface-border-strong);
  }
  &:focus {
    border-color: var(--color-brand-500);
    box-shadow: 0 0 0 3px var(--color-brand-100);
  }
  &:disabled, &[readonly] {
    opacity: 0.6;
    cursor: not-allowed;
    background: var(--color-surface-panel);
  }
  &[aria-invalid="true"] {
    border-color: var(--color-market-sell);
  }
  &[aria-invalid="true"]:focus {
    box-shadow: 0 0 0 3px var(--color-market-sell-bg);
  }
`;

export function Input({
  label,
  error,
  hint,
  required = false,
  disabled = false,
  readOnly = false,
  size = 'default',
  leftElement,
  rightElement,
  className = '',
  style = {},
  id: providedId,
  onChange,
  onBlur,
  onFocus,
  ...props
}) {
  const generatedId = useId();
  const id = providedId || generatedId;
  const errorId = `${id}-error`;
  const hintId = `${id}-hint`;
  const hasError = !!error;

  const describedBy = [hasError && errorId, hint && hintId].filter(Boolean).join(' ') || undefined;

  const combinedStyle = `
    ${inputBase}
    ${inputSizes[size] || inputSizes.default}
    ${inputStates}
  `;

  return (
    <div className={clsx('elco-input-wrapper', className)} style={style}>
      {label && (
        <label
          htmlFor={id}
          className="elco-input-label"
          style={{
            display: 'block',
            fontSize: 'var(--font-size-xs)',
            fontWeight: 'var(--font-weight-medium)',
            color: 'var(--color-text-secondary)',
            marginBottom: 'var(--space-1)',
            gap: 'var(--space-1)',
            alignItems: 'center',
          }}
        >
          {label}
          {required && <span style={{ color: 'var(--color-market-sell)' }} aria-hidden="true">*</span>}
        </label>
      )}
      <div className="elco-input-container" style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
        {leftElement && (
          <span
            className="elco-input-adornment"
            style={{
              position: 'absolute',
              left: 'var(--space-3)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--color-text-tertiary)',
              pointerEvents: 'none',
              zIndex: 1,
            }}
            aria-hidden="true"
          >
            {leftElement}
          </span>
        )}
        <input
          id={id}
          disabled={disabled}
          readOnly={readOnly}
          required={required}
          aria-invalid={hasError}
          aria-describedby={describedBy}
          aria-required={required}
          onChange={onChange}
          onBlur={onBlur}
          onFocus={onFocus}
          className={clsx('elco-input', hasError && 'has-error', disabled && 'disabled')}
          style={{
            paddingLeft: leftElement ? 'var(--space-10)' : undefined,
            paddingRight: rightElement ? 'var(--space-10)' : undefined,
          }}
          {...props}
        />
        {rightElement && (
          <span
            className="elco-input-adornment"
            style={{
              position: 'absolute',
              right: 'var(--space-3)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--color-text-tertiary)',
              pointerEvents: 'none',
              zIndex: 1,
            }}
            aria-hidden="true"
          >
            {rightElement}
          </span>
        )}
        <style jsx>{combinedStyle}</style>
      </div>
      {error && (
        <p
          id={errorId}
          className="elco-input-error"
          role="alert"
          style={{
            marginTop: 'var(--space-1)',
            fontSize: 'var(--font-size-xs)',
            color: 'var(--color-market-sell)',
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--space-1)',
          }}
        >
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          {error}
        </p>
      )}
      {hint && !error && (
        <p
          id={hintId}
          className="elco-input-hint"
          style={{
            marginTop: 'var(--space-1)',
            fontSize: 'var(--font-size-xs)',
            color: 'var(--color-text-tertiary)',
          }}
        >
          {hint}
        </p>
      )}
    </div>
  );
}

// Textarea component
export function Textarea({
  label,
  error,
  hint,
  required = false,
  disabled = false,
  readOnly = false,
  rows = 4,
  className = '',
  style = {},
  id: providedId,
  onChange,
  onBlur,
  onFocus,
  ...props
}) {
  const generatedId = useId();
  const id = providedId || generatedId;
  const errorId = `${id}-error`;
  const hintId = `${id}-hint`;
  const hasError = !!error;

  const describedBy = [hasError && errorId, hint && hintId].filter(Boolean).join(' ') || undefined;

  const textareaStyle = `
    ${inputBase}
    min-height: ${rows * 2.5}rem;
    padding: var(--space-3);
    resize: vertical;
    line-height: var(--line-height-normal);
    font-family: var(--font-family-mono);
    ${inputStates}
  `;

  return (
    <div className={clsx('elco-textarea-wrapper', className)} style={style}>
      {label && (
        <label
          htmlFor={id}
          className="elco-input-label"
          style={{
            display: 'block',
            fontSize: 'var(--font-size-xs)',
            fontWeight: 'var(--font-weight-medium)',
            color: 'var(--color-text-secondary)',
            marginBottom: 'var(--space-1)',
          }}
        >
          {label}
          {required && <span style={{ color: 'var(--color-market-sell)' }} aria-hidden="true">*</span>}
        </label>
      )}
      <textarea
        id={id}
        disabled={disabled}
        readOnly={readOnly}
        required={required}
        aria-invalid={hasError}
        aria-describedby={describedBy}
        aria-required={required}
        onChange={onChange}
        onBlur={onBlur}
        onFocus={onFocus}
        className={clsx('elco-textarea', hasError && 'has-error')}
        rows={rows}
        {...props}
      />
      <style jsx>{textareaStyle}</style>
      {error && (
        <p
          id={errorId}
          className="elco-input-error"
          role="alert"
          style={{
            marginTop: 'var(--space-1)',
            fontSize: 'var(--font-size-xs)',
            color: 'var(--color-market-sell)',
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--space-1)',
          }}
        >
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          {error}
        </p>
      )}
      {hint && !error && (
        <p
          id={hintId}
          className="elco-input-hint"
          style={{
            marginTop: 'var(--space-1)',
            fontSize: 'var(--font-size-xs)',
            color: 'var(--color-text-tertiary)',
          }}
        >
          {hint}
        </p>
      )}
    </div>
  );
}

// Select component
export function Select({
  label,
  error,
  hint,
  required = false,
  disabled = false,
  size = 'default',
  options = [],
  placeholder,
  className = '',
  style = {},
  id: providedId,
  onChange,
  onBlur,
  onFocus,
  ...props
}) {
  const generatedId = useId();
  const id = providedId || generatedId;
  const errorId = `${id}-error`;
  const hintId = `${id}-hint`;
  const hasError = !!error;

  const describedBy = [hasError && errorId, hint && hintId].filter(Boolean).join(' ') || undefined;

  const selectStyle = `
    ${inputBase}
    ${inputSizes[size] || inputSizes.default}
    appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%239aa3b2' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right var(--space-3) center;
    padding-right: var(--space-10);
    cursor: ${disabled ? 'not-allowed' : 'pointer'};
    ${inputStates}
  `;

  return (
    <div className={clsx('elco-select-wrapper', className)} style={style}>
      {label && (
        <label
          htmlFor={id}
          className="elco-input-label"
          style={{
            display: 'block',
            fontSize: 'var(--font-size-xs)',
            fontWeight: 'var(--font-weight-medium)',
            color: 'var(--color-text-secondary)',
            marginBottom: 'var(--space-1)',
          }}
        >
          {label}
          {required && <span style={{ color: 'var(--color-market-sell)' }} aria-hidden="true">*</span>}
        </label>
      )}
      <select
        id={id}
        disabled={disabled}
        required={required}
        aria-invalid={hasError}
        aria-describedby={describedBy}
        aria-required={required}
        onChange={onChange}
        onBlur={onBlur}
        onFocus={onFocus}
        className={clsx('elco-select', hasError && 'has-error')}
        {...props}
      >
        {placeholder && (
          <option value="" disabled>
            {placeholder}
          </option>
        )}
        {options.map((option) => (
          <option key={option.value} value={option.value} disabled={option.disabled}>
            {option.label}
          </option>
        ))}
      </select>
      <style jsx>{selectStyle}</style>
      {error && (
        <p
          id={errorId}
          className="elco-input-error"
          role="alert"
          style={{
            marginTop: 'var(--space-1)',
            fontSize: 'var(--font-size-xs)',
            color: 'var(--color-market-sell)',
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--space-1)',
          }}
        >
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          {error}
        </p>
      )}
      {hint && !error && (
        <p
          id={hintId}
          className="elco-input-hint"
          style={{
            marginTop: 'var(--space-1)',
            fontSize: 'var(--font-size-xs)',
            color: 'var(--color-text-tertiary)',
          }}
        >
          {hint}
        </p>
      )}
    </div>
  );
}

// Checkbox component
export function Checkbox({
  label,
  description,
  checked = false,
  indeterminate = false,
  disabled = false,
  required = false,
  className = '',
  style = {},
  id: providedId,
  onChange,
  ...props
}) {
  const generatedId = useId();
  const id = providedId || generatedId;

  const checkboxStyle = `
    width: 18px;
    height: 18px;
    border: 2px solid var(--color-surface-border);
    border-radius: var(--radius-sm);
    background: var(--color-surface-interactive);
    appearance: none;
    cursor: ${disabled ? 'not-allowed' : 'pointer'};
    transition: all var(--transition-fast);
    position: relative;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
  `;

  const checkboxStates = `
    &:hover:not(:disabled) {
      border-color: var(--color-brand-500);
    }
    &:focus-visible {
      outline: none;
      box-shadow: 0 0 0 3px var(--color-brand-100);
    }
    &:checked {
      background: var(--color-brand-500);
      border-color: var(--color-brand-500);
    }
    &:checked::after {
      content: '';
      width: 4px;
      height: 8px;
      border: solid white;
      border-width: 0 2px 2px 0;
      transform: rotate(45deg) translateY(-1px);
    }
    &:indeterminate {
      background: var(--color-brand-500);
      border-color: var(--color-brand-500);
    }
    &:indeterminate::after {
      content: '';
      width: 8px;
      height: 2px;
      background: white;
    }
    &:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
  `;

  return (
    <label
      className={clsx('elco-checkbox-wrapper', className)}
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: 'var(--space-3)',
        cursor: disabled ? 'not-allowed' : 'pointer',
        ...style,
      }}
    >
      <input
        type="checkbox"
        id={id}
        checked={checked}
        disabled={disabled}
        required={required}
        onChange={onChange}
        className="elco-checkbox"
        style={{
          ...{
            width: '18px',
            height: '18px',
            border: '2px solid var(--color-surface-border)',
            borderRadius: 'var(--radius-sm)',
            background: 'var(--color-surface-interactive)',
            appearance: 'none',
            cursor: disabled ? 'not-allowed' : 'pointer',
            transition: 'all var(--transition-fast)',
            position: 'relative',
            flexShrink: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          },
        }}
        {...props}
      >
      <style jsx>{`
        .elco-checkbox:hover:not(:disabled) { border-color: var(--color-brand-500); }
        .elco-checkbox:focus-visible { outline: none; box-shadow: 0 0 0 3px var(--color-brand-100); }
        .elco-checkbox:checked { background: var(--color-brand-500); border-color: var(--color-brand-500); }
        .elco-checkbox:checked::after { content: ''; width: 4px; height: 8px; border: solid white; border-width: 0 2px 2px 0; transform: rotate(45deg) translateY(-1px); }
        .elco-checkbox:indeterminate { background: var(--color-brand-500); border-color: var(--color-brand-500); }
        .elco-checkbox:indeterminate::after { content: ''; width: 8px; height: 2px; background: white; }
        .elco-checkbox:disabled { opacity: 0.5; cursor: not-allowed; }
      `}</style>
      <div style={{ flex: 1, minWidth: 0 }}>
        {label && (
          <span
            className="elco-checkbox-label"
            style={{
              display: 'block',
              fontSize: 'var(--font-size-sm)',
              fontWeight: 'var(--font-weight-medium)',
              color: disabled ? 'var(--color-text-disabled)' : 'var(--color-text-primary)',
            }}
          >
            {label}
          </span>
        )}
        {description && (
          <span
            className="elco-checkbox-description"
            style={{
              display: 'block',
              marginTop: 'var(--space-1)',
              fontSize: 'var(--font-size-xs)',
              color: 'var(--color-text-tertiary)',
            }}
          >
            {description}
          </span>
        )}
      </div>
    </label>
  );
}

// Radio component
export function Radio({
  label,
  description,
  checked = false,
  disabled = false,
  required = false,
  className = '',
  style = {},
  id: providedId,
  onChange,
  name,
  value,
  ...props
}) {
  const generatedId = useId();
  const id = providedId || generatedId;

  return (
    <label
      className={clsx('elco-radio-wrapper', className)}
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: 'var(--space-3)',
        cursor: disabled ? 'not-allowed' : 'pointer',
        ...style,
      }}
    >
      <input
        type="radio"
        id={id}
        name={name}
        value={value}
        checked={checked}
        disabled={disabled}
        required={required}
        onChange={onChange}
        className="elco-radio"
        style={{
          width: '18px',
          height: '18px',
          border: '2px solid var(--color-surface-border)',
          borderRadius: '50%',
          background: 'var(--color-surface-interactive)',
          appearance: 'none',
          cursor: disabled ? 'not-allowed' : 'pointer',
          transition: 'all var(--transition-fast)',
          position: 'relative',
          flexShrink: 0,
        }}
        {...props}
      >
      <style jsx>{`
        .elco-radio:hover:not(:disabled) { border-color: var(--color-brand-500); }
        .elco-radio:focus-visible { outline: none; box-shadow: 0 0 0 3px var(--color-brand-100); }
        .elco-radio:checked { border-color: var(--color-brand-500); }
        .elco-radio:checked::after { content: ''; width: 8px; height: 8px; border-radius: 50%; background: var(--color-brand-500); position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); }
        .elco-radio:disabled { opacity: 0.5; cursor: not-allowed; }
      `}</style>
      <div style={{ flex: 1, minWidth: 0 }}>
        {label && (
          <span
            className="elco-radio-label"
            style={{
              display: 'block',
              fontSize: 'var(--font-size-sm)',
              fontWeight: 'var(--font-weight-medium)',
              color: disabled ? 'var(--color-text-disabled)' : 'var(--color-text-primary)',
            }}
          >
            {label}
          </span>
        )}
        {description && (
          <span
            className="elco-radio-description"
            style={{
              display: 'block',
              marginTop: 'var(--space-1)',
              fontSize: 'var(--font-size-xs)',
              color: 'var(--color-text-tertiary)',
            }}
          >
            {description}
          </span>
        )}
      </div>
    </label>
  );
}

// Switch/Toggle component
export function Switch({
  label,
  description,
  checked = false,
  disabled = false,
  required = false,
  className = '',
  style = {},
  id: providedId,
  onChange,
  ...props
}) {
  const generatedId = useId();
  const id = providedId || generatedId;

  return (
    <label
      className={clsx('elco-switch-wrapper', className)}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 'var(--space-3)',
        cursor: disabled ? 'not-allowed' : 'pointer',
        ...style,
      }}
    >
      <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
        <input
          type="checkbox"
          id={id}
          checked={checked}
          disabled={disabled}
          required={required}
          onChange={onChange}
          className="elco-switch-input"
          style={{
            position: 'absolute',
            opacity: 0,
            width: 0,
            height: 0,
          }}
          {...props}
        />
        <span
          className="elco-switch-track"
          style={{
            width: '44px',
            height: '24px',
            borderRadius: '9999px',
            background: checked ? 'var(--color-brand-500)' : 'var(--color-surface-border)',
            transition: 'all var(--transition-fast)',
            display: 'block',
            cursor: disabled ? 'not-allowed' : 'pointer',
          }}
        >
          <span
            className="elco-switch-thumb"
            style={{
              display: 'block',
              width: '18px',
              height: '18px',
              borderRadius: '50%',
              background: 'white',
              boxShadow: 'var(--shadow-sm)',
              transition: 'transform var(--transition-fast)',
              transform: checked ? 'translateX(20px)' : 'translateX(2px)',
              marginTop: '3px',
              marginLeft: checked ? '0' : '2px',
            }}
          />
        </span>
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        {label && (
          <span
            className="elco-switch-label"
            style={{
              display: 'block',
              fontSize: 'var(--font-size-sm)',
              fontWeight: 'var(--font-weight-medium)',
              color: disabled ? 'var(--color-text-disabled)' : 'var(--color-text-primary)',
            }}
          >
            {label}
          </span>
        )}
        {description && (
          <span
            className="elco-switch-description"
            style={{
              display: 'block',
              marginTop: 'var(--space-1)',
              fontSize: 'var(--font-size-xs)',
              color: 'var(--color-text-tertiary)',
            }}
          >
            {description}
          </span>
        )}
      </div>
      <style jsx>{`
        .elco-switch-input:focus-visible + .elco-switch-track { box-shadow: 0 0 0 3px var(--color-brand-100); }
        .elco-switch-input:disabled + .elco-switch-track { opacity: 0.5; cursor: not-allowed; }
      `}</style>
    </label>
  );
}

export default Input;