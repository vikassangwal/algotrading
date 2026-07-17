import React, { useState } from 'react';

const styles = {
  container: {
    padding: '2rem',
    fontFamily: 'system-ui, -apple-system, sans-serif',
    maxWidth: '800px',
    margin: '0 auto',
    color: '#333'
  },
  header: {
    fontSize: '24px',
    fontWeight: '600',
    marginBottom: '8px'
  },
  subHeader: {
    color: '#666',
    marginBottom: '32px'
  },
  section: {
    backgroundColor: '#fff',
    border: '1px solid #eaeaea',
    borderRadius: '8px',
    padding: '24px',
    marginBottom: '24px',
    boxShadow: '0 1px 3px rgba(0,0,0,0.05)'
  },
  sectionTitle: {
    fontSize: '18px',
    fontWeight: '500',
    marginBottom: '16px',
    display: 'flex',
    alignItems: 'center',
    gap: '8px'
  },
  formGroup: {
    marginBottom: '16px'
  },
  label: {
    display: 'block',
    fontWeight: '500',
    marginBottom: '8px',
    fontSize: '14px'
  },
  input: {
    width: '100%',
    padding: '10px',
    border: '1px solid #d1d5db',
    borderRadius: '6px',
    fontSize: '14px',
    boxSizing: 'border-box'
  },
  button: {
    backgroundColor: '#000',
    color: '#fff',
    padding: '10px 16px',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: '500',
    marginTop: '16px'
  },
  buttonOutline: {
    backgroundColor: '#fff',
    color: '#000',
    padding: '10px 16px',
    border: '1px solid #000',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: '500',
    marginTop: '16px'
  },
  flexRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '16px 0',
    borderBottom: '1px solid #eaeaea'
  },
  flexRowLast: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '16px 0 0 0'
  },
  switchContainer: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px'
  },
  switch: (isActive) => ({
    width: '44px',
    height: '24px',
    backgroundColor: isActive ? '#10b981' : '#e5e7eb',
    borderRadius: '24px',
    position: 'relative',
    cursor: 'pointer',
    transition: 'background-color 0.2s'
  }),
  switchKnob: (isActive) => ({
    width: '20px',
    height: '20px',
    backgroundColor: '#fff',
    borderRadius: '50%',
    position: 'absolute',
    top: '2px',
    left: isActive ? '22px' : '2px',
    transition: 'left 0.2s',
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
  }),
  badge: (isActive) => ({
    padding: '4px 8px',
    borderRadius: '12px',
    fontSize: '12px',
    fontWeight: '500',
    backgroundColor: isActive ? '#d1fae5' : '#f3f4f6',
    color: isActive ? '#065f46' : '#4b5563'
  }),
  icon: {
    width: '20px',
    height: '20px',
    color: '#4b5563'
  }
};

const SSOSettings = () => {
  const [ssoEnabled, setSsoEnabled] = useState(true);
  const [mfaEnforced, setMfaEnforced] = useState(false);

  return (
    <div style={styles.container}>
      <h1 style={styles.header}>Enterprise Security</h1>
      <p style={styles.subHeader}>Manage Single Sign-On, Multi-Factor Authentication, and Cryptographic Keys.</p>

      {/* SSO Section */}
      <div style={styles.section}>
        <h2 style={styles.sectionTitle}>
          <svg style={styles.icon} fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 11c0 3.517-1.009 6.799-2.753 9.571m-3.44-2.04l.054-.09A13.916 13.916 0 008 11a4 4 0 118 0c0 1.017-.07 2.019-.203 3m-2.118 6.844A21.88 21.88 0 0015.171 17m3.839 1.132c.645-2.266.99-4.659.99-7.132A8 8 0 008 4.07M3 15.364c.64-1.319 1-2.8 1-4.364 0-1.457.39-2.823 1.07-4" />
          </svg>
          Single Sign-On (SSO)
        </h2>
        
        <div style={styles.flexRow}>
          <div>
            <div style={styles.label}>Enable SAML 2.0 SSO</div>
            <div style={{color: '#666', fontSize: '13px'}}>Allow users to log in using your Identity Provider (IdP).</div>
          </div>
          <div style={styles.switchContainer}>
            <span style={styles.badge(ssoEnabled)}>{ssoEnabled ? 'Active' : 'Inactive'}</span>
            <div style={styles.switch(ssoEnabled)} onClick={() => setSsoEnabled(!ssoEnabled)}>
              <div style={styles.switchKnob(ssoEnabled)}></div>
            </div>
          </div>
        </div>

        {ssoEnabled && (
          <div style={{marginTop: '24px'}}>
            <div style={styles.formGroup}>
              <label style={styles.label}>IdP Entity ID</label>
              <input style={styles.input} type="text" placeholder="https://idp.example.com/metadata" defaultValue="https://login.microsoftonline.com/example/v2.0" />
            </div>
            <div style={styles.formGroup}>
              <label style={styles.label}>SSO Login URL</label>
              <input style={styles.input} type="url" placeholder="https://idp.example.com/sso" defaultValue="https://login.microsoftonline.com/example/saml2" />
            </div>
            <div style={styles.formGroup}>
              <label style={styles.label}>X.509 Certificate</label>
              <textarea style={{...styles.input, height: '100px', fontFamily: 'monospace'}} placeholder="-----BEGIN CERTIFICATE-----\n..." defaultValue={"-----BEGIN CERTIFICATE-----\nMIIDpDCCAoygAwIBAgIGAX...\n-----END CERTIFICATE-----"} />
            </div>
            <button style={styles.button}>Save SSO Configuration</button>
          </div>
        )}
      </div>

      {/* MFA Section */}
      <div style={styles.section}>
        <h2 style={styles.sectionTitle}>
          <svg style={styles.icon} fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
          </svg>
          Multi-Factor Authentication (MFA)
        </h2>
        
        <div style={styles.flexRowLast}>
          <div>
            <div style={styles.label}>Enforce MFA for all users</div>
            <div style={{color: '#666', fontSize: '13px'}}>Require all enterprise users to configure 2FA (Authenticator App or Security Key).</div>
          </div>
          <div style={styles.switchContainer}>
            <span style={styles.badge(mfaEnforced)}>{mfaEnforced ? 'Enforced' : 'Optional'}</span>
            <div style={styles.switch(mfaEnforced)} onClick={() => setMfaEnforced(!mfaEnforced)}>
              <div style={styles.switchKnob(mfaEnforced)}></div>
            </div>
          </div>
        </div>
      </div>

      {/* Key Rotation Section */}
      <div style={styles.section}>
        <h2 style={styles.sectionTitle}>
          <svg style={styles.icon} fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
          </svg>
          API Key & Secret Rotation
        </h2>
        
        <div style={{marginBottom: '16px', color: '#666', fontSize: '14px'}}>
          Manage your organization's API keys and shared secrets. Keys should be rotated every 90 days.
        </div>

        <div style={{border: '1px solid #eaeaea', borderRadius: '6px', padding: '16px'}}>
          <div style={{display: 'flex', justifyContent: 'space-between', marginBottom: '8px'}}>
            <span style={{fontWeight: '500', fontSize: '14px'}}>Production API Key</span>
            <span style={{fontSize: '12px', color: '#ef4444'}}>Expires in 12 days</span>
          </div>
          <div style={{fontFamily: 'monospace', backgroundColor: '#f3f4f6', padding: '8px', borderRadius: '4px', fontSize: '13px', marginBottom: '12px'}}>
            sk_prod_************************************
          </div>
          <div style={{display: 'flex', gap: '12px'}}>
            <button style={styles.buttonOutline}>Rotate Key</button>
            <button style={{...styles.buttonOutline, color: '#ef4444', borderColor: '#ef4444'}}>Revoke</button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SSOSettings;
