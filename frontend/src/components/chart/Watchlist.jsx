import React, { useState, useEffect, useRef } from 'react';

const API_URL = (import.meta.env.VITE_API_URL || 'https://elco-backend.onrender.com').replace(/\/$/, '');

const WATCHLIST_SYMBOLS = [
  { sym: 'RELIANCE', label: 'RELIANCE' },
  { sym: '^NSEI', label: 'NIFTY 50' },
  { sym: '^NSEBANK', label: 'BANKNIFTY' },
  { sym: 'TCS', label: 'TCS' },
  { sym: 'HDFCBANK', label: 'HDFC BANK' },
  { sym: 'INFY', label: 'INFOSYS' },
  { sym: 'ICICIBANK', label: 'ICICI BANK' },
  { sym: 'SBIN', label: 'SBI' },
  { sym: 'BHARTIARTL', label: 'AIRTEL' },
  { sym: 'ITC', label: 'ITC' },
];

const Watchlist = ({ onSymbolClick, currentSymbol }) => {
  const [quotes, setQuotes] = useState({});
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    let active = true;
    const fetchAll = async () => {
      for (const { sym } of WATCHLIST_SYMBOLS) {
        try {
          const r = await fetch(`${API_URL}/api/quote/${sym}`);
          if (r.ok && active) {
            const q = await r.json();
            setQuotes(prev => ({ ...prev, [sym]: q }));
          }
        } catch {}
      }
    };
    fetchAll();
    const iv = setInterval(fetchAll, 15000);
    return () => { active = false; clearInterval(iv); };
  }, []);

  if (collapsed) {
    return (
      <div style={{
        background: '#0d1117', borderRight: '1px solid #1e222d', width: '32px',
        display: 'flex', flexDirection: 'column', alignItems: 'center', paddingTop: '12px', cursor: 'pointer'
      }} onClick={() => setCollapsed(false)}>
        <span style={{ writingMode: 'vertical-rl', color: '#565d6e', fontSize: '10px', fontWeight: 700, letterSpacing: '1px' }}>WATCHLIST</span>
        <span style={{ color: '#2962ff', fontSize: '14px', marginTop: '6px' }}>▶</span>
      </div>
    );
  }

  return (
    <div style={{
      background: '#0d1117', borderRight: '1px solid #1e222d', width: '200px',
      display: 'flex', flexDirection: 'column', overflowY: 'auto', fontSize: '11px'
    }}>
      <div style={{
        padding: '10px 12px', borderBottom: '1px solid #1e222d',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center'
      }}>
        <span style={{ color: '#fff', fontWeight: 800, fontSize: '12px' }}>📋 Watchlist</span>
        <span style={{ cursor: 'pointer', color: '#565d6e', fontSize: '14px' }} onClick={() => setCollapsed(true)}>◀</span>
      </div>

      {WATCHLIST_SYMBOLS.map(({ sym, label }) => {
        const q = quotes[sym];
        const isActive = currentSymbol?.toUpperCase().replace('.NS', '') === sym.replace('^', '');
        const chg = q?.change_pct || 0;

        return (
          <div
            key={sym}
            onClick={() => onSymbolClick(sym)}
            style={{
              padding: '8px 12px', cursor: 'pointer', borderBottom: '1px solid #0f1318',
              background: isActive ? '#2962ff15' : 'transparent',
              borderLeft: isActive ? '2px solid #2962ff' : '2px solid transparent',
              transition: '0.1s',
            }}
            onMouseEnter={(e) => { if (!isActive) e.currentTarget.style.background = '#ffffff06'; }}
            onMouseLeave={(e) => { if (!isActive) e.currentTarget.style.background = 'transparent'; }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ color: isActive ? '#fff' : '#b0b8c8', fontWeight: 700, fontSize: '11px' }}>{label}</span>
              {q ? (
                <span style={{ fontWeight: 700, color: '#e1e3e8', fontFamily: 'monospace', fontSize: '11px' }}>
                  ₹{q.price?.toFixed(2)}
                </span>
              ) : (
                <span style={{ color: '#363c4e', fontSize: '9px' }}>—</span>
              )}
            </div>
            {q && (
              <div style={{ marginTop: '2px', textAlign: 'right' }}>
                <span style={{
                  fontSize: '10px', fontWeight: 700, padding: '1px 5px', borderRadius: '3px',
                  background: chg >= 0 ? 'rgba(0,230,118,0.1)' : 'rgba(255,23,68,0.1)',
                  color: chg >= 0 ? '#00e676' : '#ff1744'
                }}>
                  {chg >= 0 ? '+' : ''}{chg.toFixed(2)}%
                </span>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};

export default Watchlist;
