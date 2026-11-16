import { clsx } from '../../design-system';
import { useEffect, useRef, useCallback } from 'react';

const modalOverlayStyle = `
  position: fixed;
  inset: 0;
  background: var(--color-surface-overlay);
  backdrop-filter: blur(4px);
  z-index: var(--z-modal);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-4);
  animation: fadeIn var(--transition-fast);
`;

const modalContentStyle = `
  background: var(--color-surface-panel);
  border: 1px solid var(--color-surface-border);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-xl);
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  animation: slideUp var(--transition-spring);
  position: relative;
`;

const modalSizes = {
  sm: 'max-width: 380px; width: 100%;',
  default: 'max-width: 560px; width: 100%;',
  lg: 'max-width: 720px; width: 100%;',
  xl: 'max-width: 960px; width: 100%;',
  full: 'max-width: calc(100vw - 32px); width: 100%; max-height: calc(100vh - 32px);',
};

const keyframes = `
  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }
  @keyframes slideUp {
    from { opacity: 0; transform: translateY(20px) scale(0.95); }
    to { opacity: 1; transform: translateY(0) scale(1); }
  }
  @keyframes slideDown {
    from { opacity: 0; transform: translateY(-20px) scale(0.95); }
    to { opacity: 1; transform: translateY(0) scale(1); }
  }
`;

export function Modal({
  isOpen,
  onClose,
  title,
  description,
  children,
  size = 'default',
  variant = 'default', // 'default' | 'confirmation' | 'form'
  closeOnOverlayClick = true,
  closeOnEscape = true,
  showCloseButton = true,
  footer,
  className = '',
  style = {},
  ...props
}) {
  const contentRef = useRef(null);
  const previousActiveElement = useRef(null);

  // Focus management
  useEffect(() => {
    if (isOpen) {
      previousActiveElement.current = document.activeElement;
      document.body.style.overflow = 'hidden';
      // Focus first focusable element
      setTimeout(() => {
        const focusable = contentRef.current?.querySelector(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        focusable?.focus();
      }, 0);
    } else {
      document.body.style.overflow = '';
      previousActiveElement.current?.focus();
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  // Escape key handler
  useEffect(() => {
    if (!isOpen || !closeOnEscape) return;
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, closeOnEscape, onClose]);

  // Trap focus
  const handleKeyDown = useCallback((e) => {
    if (!isOpen || e.key !== 'Tab') return;
    const focusableElements = contentRef.current?.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    if (!focusableElements?.length) return;
    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];
    if (e.shiftKey && document.activeElement === firstElement) {
      e.preventDefault();
      lastElement.focus();
    } else if (!e.shiftKey && document.activeElement === lastElement) {
      e.preventDefault();
      firstElement.focus();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const sizeStyle = modalSizes[size] || modalSizes.default;

  return (
    <div
      className={clsx('elco-modal-overlay', className)}
      style={{
        ...{ position: 'fixed', inset: 0, zIndex: 'var(--z-modal)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 'var(--space-4)' },
        ...style,
      }}
      onClick={closeOnOverlayClick ? onClose : undefined}
      onKeyDown={handleKeyDown}
      role="dialog"
      aria-modal="true"
      aria-labelledby={title ? 'modal-title' : undefined}
      aria-describedby={description ? 'modal-description' : undefined}
    >
      <div
        className="elco-modal-backdrop"
        style={{
          position: 'absolute',
          inset: 0,
          background: 'var(--color-surface-overlay)',
          backdropFilter: 'blur(4px)',
          animation: 'fadeIn var(--transition-fast)',
        }}
      />
      <div
        ref={contentRef}
        className="elco-modal-content"
        style={{
          ...{ background: 'var(--color-surface-panel)', border: '1px solid var(--color-surface-border)', borderRadius: 'var(--radius-xl)', boxShadow: 'var(--shadow-xl)', maxHeight: '90vh', overflow: 'hidden', display: 'flex', flexDirection: 'column', animation: 'slideUp var(--transition-spring)', position: 'relative', width: '100%', ...sizeStyle },
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {(title || showCloseButton) && (
          <div className="elco-modal-header" style={{
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'space-between',
            gap: 'var(--space-4)',
            padding: 'var(--space-6)',
            borderBottom: '1px solid var(--color-surface-border)',
          }}>
            <div style={{ flex: 1 }}>
              {title && (
                <h2 id="modal-title" className="elco-modal-title" style={{
                  fontSize: 'var(--font-size-xl)',
                  fontWeight: 'var(--font-weight-semibold)',
                  color: 'var(--color-text-primary)',
                  margin: 0,
                  lineHeight: 'var(--line-height-tight)',
                }}>
                  {title}
                </h2>
              )}
              {description && (
                <p id="modal-description" className="elco-modal-description" style={{
                  marginTop: 'var(--space-2)',
                  fontSize: 'var(--font-size-sm)',
                  color: 'var(--color-text-secondary)',
                  lineHeight: 'var(--line-height-normal)',
                }}>
                  {description}
                </p>
              )}
            </div>
            {showCloseButton && (
              <button
                type="button"
                className="elco-modal-close"
                onClick={onClose}
                aria-label="Close modal"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  width: '32px',
                  height: '32px',
                  border: 'none',
                  background: 'var(--color-surface-interactive)',
                  borderRadius: 'var(--radius-md)',
                  color: 'var(--color-text-secondary)',
                  cursor: 'pointer',
                  transition: 'all var(--transition-fast)',
                  flexShrink: 0,
                }}
                onMouseEnter={(e) => { e.target.style.background = 'var(--color-surface-interactive-hover)'; e.target.style.color = 'var(--color-text-primary)'; }}
                onMouseLeave={(e) => { e.target.style.background = 'var(--color-surface-interactive)'; e.target.style.color = 'var(--color-text-secondary)'; }}
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            )}
          </div>
        )}
        <div className="elco-modal-body" style={{
          flex: 1,
          overflow: 'auto',
          padding: title ? 'var(--space-6)' : 'var(--space-6)',
        }}>
          {children}
        </div>
        {(footer || variant === 'confirmation') && (
          <div className="elco-modal-footer" style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'flex-end',
            gap: 'var(--space-3)',
            padding: 'var(--space-4) var(--space-6)',
            borderTop: '1px solid var(--color-surface-border)',
            background: 'var(--color-surface-interactive)',
          }}>
            {footer || (
              <>
                <Button variant="ghost" onClick={onClose}>Cancel</Button>
                <Button variant="primary" onClick={onClose}>Confirm</Button>
              </>
            )}
          </div>
        )}
        <style jsx>{keyframes}</style>
      </div>
    </div>
  );
}

// Confirmation Modal
export function ConfirmModal({
  isOpen,
  onClose,
  onConfirm,
  title = 'Confirm Action',
  message,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  variant = 'danger', // 'danger' | 'primary' | 'warning'
  loading = false,
  ...props
}) {
  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={title}
      size="sm"
      variant="confirmation"
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={loading}>
            {cancelLabel}
          </Button>
          <Button variant={variant} onClick={onConfirm} loading={loading}>
            {confirmLabel}
          </Button>
        </>
      }
      {...props}
    >
      <p style={{ color: 'var(--color-text-secondary)', lineHeight: 'var(--line-height-relaxed)' }}>
        {message}
      </p>
    </Modal>
  );
}

// Form Modal
export function FormModal({
  isOpen,
  onClose,
  onSubmit,
  title,
  description,
  children,
  submitLabel = 'Save',
  cancelLabel = 'Cancel',
  loading = false,
  size = 'default',
  ...props
}) {
  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit?.(e);
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={title}
      description={description}
      size={size}
      variant="form"
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={loading}>
            {cancelLabel}
          </Button>
          <Button type="submit" variant="primary" loading={loading} form="modal-form">
            {submitLabel}
          </Button>
        </>
      }
      {...props}
    >
      <form id="modal-form" onSubmit={handleSubmit}>
        {children}
      </form>
    </Modal>
  );
}

// Drawer (side panel)
export function Drawer({
  isOpen,
  onClose,
  title,
  description,
  children,
  position = 'right', // 'right' | 'left' | 'top' | 'bottom'
  size = 'default', // 'sm' | 'default' | 'lg' | 'full'
  closeOnOverlayClick = true,
  closeOnEscape = true,
  showCloseButton = true,
  className = '',
  style = {},
  ...props
}) {
  const contentRef = useRef(null);
  const previousActiveElement = useRef(null);

  useEffect(() => {
    if (isOpen) {
      previousActiveElement.current = document.activeElement;
      document.body.style.overflow = 'hidden';
      setTimeout(() => {
        const focusable = contentRef.current?.querySelector(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        focusable?.focus();
      }, 0);
    } else {
      document.body.style.overflow = '';
      previousActiveElement.current?.focus();
    }
    return () => { document.body.style.overflow = ''; };
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen || !closeOnEscape) return;
    const handleKeyDown = (e) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, closeOnEscape, onClose]);

  if (!isOpen) return null;

  const positionStyles = {
    right: 'right: 0; top: 0; bottom: 0; border-radius: var(--radius-xl) 0 0 var(--radius-xl); transform: translateX(100%); animation: slideInRight var(--transition-spring);',
    left: 'left: 0; top: 0; bottom: 0; border-radius: 0 var(--radius-xl) var(--radius-xl) 0; transform: translateX(-100%); animation: slideInLeft var(--transition-spring);',
    top: 'top: 0; left: 0; right: 0; border-radius: 0 0 var(--radius-xl) var(--radius-xl); transform: translateY(-100%); animation: slideInDown var(--transition-spring);',
    bottom: 'bottom: 0; left: 0; right: 0; border-radius: var(--radius-xl) var(--radius-xl) 0 0; transform: translateY(100%); animation: slideInUp var(--transition-spring);',
  };

  const sizeStyles = {
    sm: position === 'top' || position === 'bottom' ? 'height: 300px;' : 'width: 380px;',
    default: position === 'top' || position === 'bottom' ? 'height: 500px;' : 'width: 480px;',
    lg: position === 'top' || position === 'bottom' ? 'height: 700px;' : 'width: 640px;',
    full: position === 'top' || position === 'bottom' ? 'height: 100%;' : 'width: 100%;',
  };

  const drawerKeyframes = `
    @keyframes slideInRight { from { transform: translateX(100%); } to { transform: translateX(0); } }
    @keyframes slideInLeft { from { transform: translateX(-100%); } to { transform: translateX(0); } }
    @keyframes slideInDown { from { transform: translateY(-100%); } to { transform: translateY(0); } }
    @keyframes slideInUp { from { transform: translateY(100%); } to { transform: translateY(0); } }
    @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
  `;

  return (
    <div
      className={clsx('elco-drawer-overlay', className)}
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 'var(--z-modal)',
        display: 'flex',
        ...style,
      }}
      onClick={closeOnOverlayClick ? onClose : undefined}
      role="dialog"
      aria-modal="true"
      aria-labelledby={title ? 'drawer-title' : undefined}
      aria-describedby={description ? 'drawer-description' : undefined}
    >
      <div
        className="elco-drawer-backdrop"
        style={{
          position: 'absolute',
          inset: 0,
          background: 'var(--color-surface-overlay)',
          backdropFilter: 'blur(4px)',
          animation: 'fadeIn var(--transition-fast)',
        }}
      />
      <div
        ref={contentRef}
        className="elco-drawer-content"
        style={{
          position: 'relative',
          background: 'var(--color-surface-panel)',
          border: '1px solid var(--color-surface-border)',
          boxShadow: 'var(--shadow-xl)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          ...positionStyles[position],
          ...sizeStyles[size],
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {(title || showCloseButton) && (
          <div className="elco-drawer-header" style={{
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'space-between',
            gap: 'var(--space-4)',
            padding: 'var(--space-6)',
            borderBottom: '1px solid var(--color-surface-border)',
          }}>
            <div style={{ flex: 1 }}>
              {title && (
                <h2 id="drawer-title" style={{
                  fontSize: 'var(--font-size-xl)',
                  fontWeight: 'var(--font-weight-semibold)',
                  color: 'var(--color-text-primary)',
                  margin: 0,
                }}>
                  {title}
                </h2>
              )}
              {description && (
                <p id="drawer-description" style={{
                  marginTop: 'var(--space-2)',
                  fontSize: 'var(--font-size-sm)',
                  color: 'var(--color-text-secondary)',
                }}>
                  {description}
                </p>
              )}
            </div>
            {showCloseButton && (
              <button
                type="button"
                onClick={onClose}
                aria-label="Close drawer"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  width: '32px',
                  height: '32px',
                  border: 'none',
                  background: 'var(--color-surface-interactive)',
                  borderRadius: 'var(--radius-md)',
                  color: 'var(--color-text-secondary)',
                  cursor: 'pointer',
                  transition: 'all var(--transition-fast)',
                }}
                onMouseEnter={(e) => { e.target.style.background = 'var(--color-surface-interactive-hover)'; e.target.style.color = 'var(--color-text-primary)'; }}
                onMouseLeave={(e) => { e.target.style.background = 'var(--color-surface-interactive)'; e.target.style.color = 'var(--color-text-secondary)'; }}
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            )}
          </div>
        )}
        <div className="elco-drawer-body" style={{
          flex: 1,
          overflow: 'auto',
          padding: 'var(--space-6)',
        }}>
          {children}
        </div>
        <style jsx>{drawerKeyframes}</style>
      </div>
    </div>
  );
}

export default Modal;