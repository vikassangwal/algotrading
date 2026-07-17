import React, { useState } from 'react';

// Icon components using inline SVGs for zero dependencies
const IconUsers = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
    <circle cx="9" cy="7" r="4"></circle>
    <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
    <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
  </svg>
);

const IconDollar = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="12" y1="1" x2="12" y2="23"></line>
    <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path>
  </svg>
);

const IconAlert = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
    <line x1="12" y1="9" x2="12" y2="13"></line>
    <line x1="12" y1="17" x2="12.01" y2="17"></line>
  </svg>
);

const TenantDashboard = () => {
  const [activeTab, setActiveTab] = useState('tenants');

  const mockTenants = [
    { id: 1, name: "Acme Corp", plan: "Enterprise", status: "Active", nextBilling: "2026-08-01", usage: "85%", mrr: "$1,200" },
    { id: 2, name: "Globex UI", plan: "Pro", status: "Past Due", nextBilling: "2026-07-10", usage: "45%", mrr: "$300" },
    { id: 3, name: "Stark Industries", plan: "Enterprise", status: "Active", nextBilling: "2026-08-15", usage: "92%", mrr: "$2,500" },
    { id: 4, name: "Initech", plan: "Basic", status: "Active", nextBilling: "2026-07-25", usage: "20%", mrr: "$99" },
    { id: 5, name: "Umbrella Corp", plan: "Pro", status: "Cancelled", nextBilling: "-", usage: "0%", mrr: "$0" },
  ];

  const styles = {
    container: {
      fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
      backgroundColor: "#f4f7fb",
      color: "#333",
      minHeight: "100vh",
      display: "flex",
      flexDirection: "column",
    },
    header: {
      backgroundColor: "#ffffff",
      padding: "20px 40px",
      borderBottom: "1px solid #e2e8f0",
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
      boxShadow: "0 2px 4px rgba(0,0,0,0.02)",
    },
    title: {
      margin: 0,
      fontSize: "24px",
      fontWeight: "700",
      color: "#1e293b",
    },
    main: {
      padding: "40px",
      flex: 1,
      maxWidth: "1200px",
      margin: "0 auto",
      width: "100%",
      boxSizing: "border-box",
    },
    statsContainer: {
      display: "grid",
      gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))",
      gap: "24px",
      marginBottom: "40px",
    },
    statCard: {
      backgroundColor: "#ffffff",
      borderRadius: "12px",
      padding: "24px",
      display: "flex",
      alignItems: "center",
      boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03)",
    },
    statIcon: {
      padding: "16px",
      borderRadius: "12px",
      marginRight: "20px",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
    },
    statInfo: {
      display: "flex",
      flexDirection: "column",
    },
    statValue: {
      fontSize: "28px",
      fontWeight: "700",
      color: "#0f172a",
      margin: 0,
    },
    statLabel: {
      fontSize: "14px",
      color: "#64748b",
      margin: "4px 0 0 0",
      fontWeight: "500",
    },
    tabs: {
      display: "flex",
      gap: "16px",
      marginBottom: "24px",
      borderBottom: "1px solid #e2e8f0",
      paddingBottom: "16px",
    },
    tabButton: (isActive) => ({
      padding: "10px 20px",
      backgroundColor: isActive ? "#eff6ff" : "transparent",
      color: isActive ? "#2563eb" : "#64748b",
      border: "none",
      borderRadius: "8px",
      fontSize: "15px",
      fontWeight: "600",
      cursor: "pointer",
      transition: "all 0.2s",
    }),
    card: {
      backgroundColor: "#ffffff",
      borderRadius: "12px",
      boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.05)",
      overflow: "hidden",
    },
    table: {
      width: "100%",
      borderCollapse: "collapse",
      textAlign: "left",
    },
    th: {
      padding: "16px 24px",
      backgroundColor: "#f8fafc",
      color: "#475569",
      fontWeight: "600",
      fontSize: "13px",
      textTransform: "uppercase",
      letterSpacing: "0.05em",
      borderBottom: "1px solid #e2e8f0",
    },
    td: {
      padding: "16px 24px",
      borderBottom: "1px solid #e2e8f0",
      color: "#334155",
      fontSize: "14px",
    },
    badge: (status) => {
      let bg = "#e2e8f0";
      let color = "#475569";
      
      if (status === "Active") {
        bg = "#dcfce7";
        color = "#166534";
      } else if (status === "Past Due") {
        bg = "#fee2e2";
        color = "#991b1b";
      }
      
      return {
        display: "inline-block",
        padding: "4px 12px",
        borderRadius: "9999px",
        fontSize: "12px",
        fontWeight: "600",
        backgroundColor: bg,
        color: color,
      };
    },
    usageBar: {
      height: "8px",
      backgroundColor: "#e2e8f0",
      borderRadius: "4px",
      overflow: "hidden",
      width: "100%",
      marginTop: "8px",
    },
    usageFill: (percent) => {
      let num = parseInt(percent);
      let bg = "#3b82f6";
      if (num > 80) bg = "#f59e0b";
      if (num > 95) bg = "#ef4444";
      
      return {
        height: "100%",
        width: percent,
        backgroundColor: bg,
        borderRadius: "4px",
      };
    },
    settingsPanel: {
      padding: "32px",
    },
    settingGroup: {
      marginBottom: "24px",
    },
    toggleSwitch: {
      display: "flex",
      alignItems: "center",
      gap: "12px",
      cursor: "pointer",
    },
    toggleTrack: (isOn) => ({
      width: "44px",
      height: "24px",
      backgroundColor: isOn ? "#2563eb" : "#cbd5e1",
      borderRadius: "12px",
      position: "relative",
      transition: "background-color 0.2s",
    }),
    toggleThumb: (isOn) => ({
      width: "20px",
      height: "20px",
      backgroundColor: "white",
      borderRadius: "50%",
      position: "absolute",
      top: "2px",
      left: isOn ? "22px" : "2px",
      transition: "left 0.2s",
      boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
    })
  };

  const Toggle = ({ label, defaultOn = false }) => {
    const [isOn, setIsOn] = useState(defaultOn);
    return (
      <div style={styles.settingGroup}>
        <div style={styles.toggleSwitch} onClick={() => setIsOn(!isOn)}>
          <div style={styles.toggleTrack(isOn)}>
            <div style={styles.toggleThumb(isOn)} />
          </div>
          <span style={{ color: "#475569", fontSize: "15px" }}>{label}</span>
        </div>
      </div>
    );
  };

  return (
    <div style={styles.container}>
      <header style={styles.header}>
        <h1 style={styles.title}>SaaS Admin Dashboard</h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <button style={{ 
            padding: '8px 16px', 
            backgroundColor: '#2563eb', 
            color: 'white', 
            border: 'none', 
            borderRadius: '6px',
            fontWeight: '600',
            cursor: 'pointer'
          }}>Generate Report</button>
        </div>
      </header>

      <main style={styles.main}>
        <div style={styles.statsContainer}>
          <div style={styles.statCard}>
            <div style={{ ...styles.statIcon, backgroundColor: '#dbeafe', color: '#2563eb' }}>
              <IconUsers />
            </div>
            <div style={styles.statInfo}>
              <h3 style={styles.statValue}>1,248</h3>
              <p style={styles.statLabel}>Total Tenants</p>
            </div>
          </div>
          
          <div style={styles.statCard}>
            <div style={{ ...styles.statIcon, backgroundColor: '#dcfce7', color: '#166534' }}>
              <IconDollar />
            </div>
            <div style={styles.statInfo}>
              <h3 style={styles.statValue}>$42,500</h3>
              <p style={styles.statLabel}>Monthly Recurring Revenue</p>
            </div>
          </div>

          <div style={styles.statCard}>
            <div style={{ ...styles.statIcon, backgroundColor: '#fee2e2', color: '#991b1b' }}>
              <IconAlert />
            </div>
            <div style={styles.statInfo}>
              <h3 style={styles.statValue}>12</h3>
              <p style={styles.statLabel}>Failed Payments (Action Req.)</p>
            </div>
          </div>
        </div>

        <div style={styles.tabs}>
          <button style={styles.tabButton(activeTab === 'tenants')} onClick={() => setActiveTab('tenants')}>
            Tenant Directory
          </button>
          <button style={styles.tabButton(activeTab === 'automation')} onClick={() => setActiveTab('automation')}>
            Billing Automation
          </button>
        </div>

        {activeTab === 'tenants' && (
          <div style={styles.card}>
            <table style={styles.table}>
              <thead>
                <tr>
                  <th style={styles.th}>Tenant Name</th>
                  <th style={styles.th}>Plan & MRR</th>
                  <th style={styles.th}>Status</th>
                  <th style={styles.th}>Next Billing</th>
                  <th style={styles.th}>Resource Usage</th>
                </tr>
              </thead>
              <tbody>
                {mockTenants.map((tenant) => (
                  <tr key={tenant.id}>
                    <td style={{ ...styles.td, fontWeight: '600' }}>{tenant.name}</td>
                    <td style={styles.td}>
                      <div>{tenant.plan}</div>
                      <div style={{ fontSize: '12px', color: '#64748b', marginTop: '4px' }}>{tenant.mrr} / mo</div>
                    </td>
                    <td style={styles.td}>
                      <span style={styles.badge(tenant.status)}>{tenant.status}</span>
                    </td>
                    <td style={styles.td}>{tenant.nextBilling}</td>
                    <td style={styles.td}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: '#475569' }}>
                        <span>Capacity</span>
                        <span>{tenant.usage}</span>
                      </div>
                      <div style={styles.usageBar}>
                        <div style={styles.usageFill(tenant.usage)}></div>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {activeTab === 'automation' && (
          <div style={styles.card}>
            <div style={styles.settingsPanel}>
              <h2 style={{ margin: '0 0 24px 0', color: '#0f172a' }}>Automated Workflows</h2>
              
              <div style={{ borderBottom: '1px solid #e2e8f0', paddingBottom: '24px', marginBottom: '24px' }}>
                <h3 style={{ fontSize: '16px', margin: '0 0 16px 0', color: '#334155' }}>Dunning & Recovery</h3>
                <Toggle label="Automatically retry failed payments every 3 days" defaultOn={true} />
                <Toggle label="Send upcoming invoice reminder 7 days before" defaultOn={true} />
                <Toggle label="Suspend accounts after 14 days of non-payment" defaultOn={false} />
              </div>

              <div>
                <h3 style={{ fontSize: '16px', margin: '0 0 16px 0', color: '#334155' }}>Usage & Provisioning</h3>
                <Toggle label="Auto-scale resources when usage exceeds 90%" defaultOn={true} />
                <Toggle label="Email tenant when approaching usage limits" defaultOn={true} />
                <Toggle label="Automatically apply pro-rated charges on plan upgrades" defaultOn={true} />
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default TenantDashboard;
