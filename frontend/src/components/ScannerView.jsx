import React, { useState } from 'react';

const ScannerView = ({ token }) => {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [scanned, setScanned] = useState(false);

  const runScan = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL || ''}/api/screener/nifty50`, {
        headers: token ? { 'Authorization': `Bearer ${token}` } : {}
      });
      const json = await res.json();
      if (json.status === "success") {
        setData(json.data);
      }
      setScanned(true);
      setLoading(false);
    } catch (err) {
      console.error("Error running screener", err);
      setLoading(false);
    }
  };

  return (
    <div style={styles.container}>
      <header style={styles.header}>
        <div>
          <h1 style={styles.title}>Institutional Screener</h1>
          <p style={styles.subtitle}>Scans Nifty 50 using 15-step AI engine.</p>
        </div>
        <div style={styles.statusContainer}>
          <button 
            onClick={runScan}
            disabled={loading}
            style={{
              ...styles.filterButton, 
              backgroundColor: loading ? '#64748b' : '#38bdf8',
              color: '#0f172a'
            }}
          >
            {loading ? 'Scanning Universe (ETA 60s)...' : 'Run Nifty 50 Scan'}
          </button>
        </div>
      </header>

      <div style={styles.tableContainer}>
        <table style={styles.table}>
          <thead>
            <tr style={styles.tableHeaderRow}>
              <th style={styles.tableHeaderCell}>Symbol</th>
              <th style={styles.tableHeaderCell}>Price</th>
              <th style={styles.tableHeaderCell}>Decision</th>
              <th style={styles.tableHeaderCell}>God Mode Score</th>
              <th style={styles.tableHeaderCell}>Action</th>
            </tr>
          </thead>
          <tbody>
            {!scanned && !loading ? (
              <tr>
                <td colSpan="5" style={styles.emptyState}>
                  Click 'Run Nifty 50 Scan' to begin analyzing the universe.
                </td>
              </tr>
            ) : loading ? (
              <tr>
                <td colSpan="5" style={styles.emptyState}>
                  <div style={{color: '#38bdf8', fontWeight: 'bold'}}>Processing 50 stocks through 18 models...</div>
                </td>
              </tr>
            ) : data && data.length > 0 ? (
              data.map((item, index) => {
                let color = '#94a3b8';
                if (item.decision === 'STRONG BUY' || item.decision === 'BUY') color = '#10b981';
                if (item.decision === 'STRONG SELL' || item.decision === 'SELL') color = '#ef4444';
                
                return (
                  <tr key={index} style={styles.tableRow}>
                    <td style={styles.tableCellSymbol}>{item.symbol}</td>
                    <td style={styles.tableCell}>{item.current_price.toFixed(2)}</td>
                    <td style={{ ...styles.tableCell, color: color, fontWeight: 'bold' }}>
                      {item.decision}
                    </td>
                    <td style={styles.tableCell}>
                      <div style={{display: 'flex', alignItems: 'center', gap: '10px'}}>
                        <div style={{width: '100px', height: '8px', backgroundColor: '#334155', borderRadius: '4px'}}>
                          <div style={{width: `${item.analytical_score * 100}%`, height: '100%', backgroundColor: color, borderRadius: '4px'}}></div>
                        </div>
                        <span>{(item.analytical_score * 100).toFixed(0)}%</span>
                      </div>
                    </td>
                    <td style={styles.tableCell}>
                      <button
                        style={styles.actionButton}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.backgroundColor = '#38bdf8';
                          e.currentTarget.style.color = '#0f172a';
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.backgroundColor = 'transparent';
                          e.currentTarget.style.color = '#38bdf8';
                        }}
                      >
                        Deep Dive
                      </button>
                    </td>
                  </tr>
                )
              })
            ) : (
              <tr>
                <td colSpan="5" style={styles.emptyState}>
                  No symbols matched or scan failed.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

const styles = {
  container: {
    backgroundColor: '#0f172a',
    color: '#f8fafc',
    minHeight: '100vh',
    padding: '2rem',
    fontFamily: '"Inter", system-ui, -apple-system, sans-serif',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '2rem',
  },
  title: {
    fontSize: '2.5rem',
    fontWeight: '800',
    margin: 0,
    background: 'linear-gradient(135deg, #38bdf8 0%, #818cf8 100%)',
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
    letterSpacing: '-0.025em'
  },
  subtitle: {
    color: '#94a3b8',
    marginTop: '0.5rem',
    fontSize: '1rem'
  },
  statusContainer: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
  },
  filterButton: {
    padding: '0.75rem 1.5rem',
    borderRadius: '12px',
    cursor: 'pointer',
    fontWeight: '600',
    transition: 'all 0.2s ease',
    whiteSpace: 'nowrap',
    fontSize: '0.95rem',
    border: 'none',
    boxShadow: '0 0 15px rgba(56, 189, 248, 0.4)'
  },
  tableContainer: {
    backgroundColor: '#1e293b',
    borderRadius: '16px',
    overflow: 'hidden',
    boxShadow: '0 10px 25px rgba(0, 0, 0, 0.5)',
    border: '1px solid #334155'
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    textAlign: 'left'
  },
  tableHeaderRow: {
    backgroundColor: '#0f172a',
    borderBottom: '1px solid #334155'
  },
  tableHeaderCell: {
    padding: '1.25rem 1.5rem',
    color: '#94a3b8',
    fontWeight: '600',
    fontSize: '0.875rem',
    textTransform: 'uppercase',
    letterSpacing: '0.05em'
  },
  tableRow: {
    borderBottom: '1px solid #334155',
    transition: 'background-color 0.2s ease'
  },
  tableCell: {
    padding: '1.25rem 1.5rem',
    fontSize: '1rem'
  },
  tableCellSymbol: {
    padding: '1.25rem 1.5rem',
    fontSize: '1rem',
    fontWeight: 'bold',
    color: '#e2e8f0'
  },
  actionButton: {
    padding: '0.5rem 1rem',
    backgroundColor: 'transparent',
    color: '#38bdf8',
    border: '1px solid #38bdf8',
    borderRadius: '8px',
    cursor: 'pointer',
    fontWeight: '600',
    transition: 'all 0.2s ease',
    fontSize: '0.875rem'
  },
  emptyState: {
    padding: '4rem',
    textAlign: 'center',
    color: '#64748b',
    fontSize: '1.1rem',
    fontStyle: 'italic'
  }
};

export default ScannerView;
