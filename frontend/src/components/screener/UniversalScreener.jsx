import React, { useState, useEffect } from 'react';

const API_URL = (import.meta.env.VITE_API_URL || 'https://elco-backend.onrender.com').replace(/\/$/, '');

const SCREENER_SYMBOLS = [
  'RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK', 
  'SBIN', 'BHARTIARTL', 'ITC', 'LARSEN', 'BAJFINANCE',
  'KOTAKBANK', 'AXISBANK', 'HINDUNILVR', 'TATAMOTORS', 'SUNPHARMA'
];

const UniversalScreener = ({ onNavigate }) => {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [lastUpdate, setLastUpdate] = useState(null);

  const fetchScreener = async () => {
    setLoading(true);
    try {
      const symStr = SCREENER_SYMBOLS.join(',');
      const res = await fetch(`${API_URL}/api/screener?symbols=${symStr}`);
      if (res.ok) {
        const data = await res.json();
        setResults(data.screener || []);
        setLastUpdate(new Date().toLocaleTimeString());
      }
    } catch (e) {
      console.error('Screener error:', e);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchScreener();
    const iv = setInterval(fetchScreener, 30000); // 30 sec refresh
    return () => clearInterval(iv);
  }, []);

  const st = {
    wrapper: { padding: '20px', background: '#0a0e17', minHeight: '82vh', color: '#fff', borderRadius: '10px' },
    header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' },
    title: { fontSize: '20px', fontWeight: 800, color: '#e1e3e8' },
    btn: { background: '#2962ff', color: '#fff', border: 'none', padding: '8px 16px', borderRadius: '6px', cursor: 'pointer', fontWeight: 700 },
    table: { width: '100%', borderCollapse: 'collapse', fontSize: '13px' },
    th: { textAlign: 'left', padding: '12px 16px', color: '#787b86', borderBottom: '1px solid #1e222d', fontWeight: 700, textTransform: 'uppercase', fontSize: '11px' },
    td: { padding: '12px 16px', borderBottom: '1px solid #141820', color: '#b0b8c8' },
    pill: { padding: '4px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: 800, display: 'inline-block', textAlign: 'center', minWidth: '60px' }
  };

  return (
    <div style={st.wrapper}>
      <div style={st.header}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <button style={{ ...st.btn, background: '#1e222d', color: '#b0b8c8' }} onClick={() => onNavigate('CHART')}>
            ◀ Back to Chart
          </button>
          <span style={st.title}>🔭 Universal AI Screener</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ color: '#565d6e', fontSize: '12px' }}>Last scan: {lastUpdate || '--:--'}</span>
          <button style={st.btn} onClick={fetchScreener} disabled={loading}>
            {loading ? 'Scanning...' : '🔄 Rescan Now'}
          </button>
        </div>
      </div>

      <div style={{ background: '#0d1117', border: '1px solid #1e222d', borderRadius: '8px', overflow: 'hidden' }}>
        <table style={st.table}>
          <thead>
            <tr>
              <th style={st.th}>Symbol</th>
              <th style={st.th}>Price</th>
              <th style={st.th}>Change %</th>
              <th style={st.th}>Market Regime</th>
              <th style={st.th}>AI Signal</th>
              <th style={st.th}>Confidence</th>
              <th style={st.th}>Action</th>
            </tr>
          </thead>
          <tbody>
            {results.length === 0 && !loading && (
              <tr><td colSpan={7} style={{ textAlign: 'center', padding: '40px', color: '#565d6e' }}>No data available.</td></tr>
            )}
            {results.map((r, i) => (
              <tr key={i} style={{ background: i % 2 === 0 ? '#0d1117' : '#0f1318' }}>
                <td style={{ ...st.td, fontWeight: 800, color: '#fff' }}>{r.symbol}</td>
                <td style={{ ...st.td, fontFamily: 'monospace', fontWeight: 600 }}>₹{r.price.toFixed(2)}</td>
                <td style={st.td}>
                  <span style={{ color: r.change_pct >= 0 ? '#00e676' : '#ff1744', fontWeight: 700 }}>
                    {r.change_pct >= 0 ? '+' : ''}{r.change_pct.toFixed(2)}%
                  </span>
                </td>
                <td style={st.td}>
                  <span style={{ color: '#787b86' }}>{r.regime || 'Neutral'}</span>
                </td>
                <td style={st.td}>
                  <span style={{
                    ...st.pill,
                    background: r.action === 'BUY' ? '#00e67622' : r.action === 'SELL' ? '#ff174422' : '#ff980022',
                    color: r.action === 'BUY' ? '#00e676' : r.action === 'SELL' ? '#ff1744' : '#ff9800',
                  }}>
                    {r.action}
                  </span>
                </td>
                <td style={st.td}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <div style={{ flex: 1, background: '#1e222d', height: '6px', borderRadius: '3px', overflow: 'hidden' }}>
                      <div style={{
                        width: `${r.confidence * 100}%`, height: '100%',
                        background: r.action === 'BUY' ? '#00e676' : r.action === 'SELL' ? '#ff1744' : '#ff9800'
                      }} />
                    </div>
                    <span style={{ fontSize: '11px', fontWeight: 700 }}>{(r.confidence * 100).toFixed(0)}%</span>
                  </div>
                </td>
                <td style={st.td}>
                  <button 
                    style={{ background: 'transparent', border: '1px solid #2962ff', color: '#2962ff', padding: '4px 12px', borderRadius: '4px', cursor: 'pointer', fontSize: '11px', fontWeight: 700 }}
                    onClick={() => { window.dispatchEvent(new CustomEvent('OPEN_CHART', { detail: r.symbol })); onNavigate('CHART'); }}
                  >
                    Open Chart
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default UniversalScreener;
