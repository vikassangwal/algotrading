import React, { useState, useEffect } from 'react';
import { RefreshCw, TrendingUp, AlertTriangle, Crosshair, Filter, ChevronDown, ChevronRight, Activity, Zap, Target, BarChart2 } from 'lucide-react';
const API_URL = (import.meta.env.VITE_API_URL || 'https://elco-backend.onrender.com').replace(/\/$/, '');

export default function UniversalScreener({ token, globalSymbol }) {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [lastScan, setLastScan] = useState(null);
  const [filter, setFilter] = useState('ALL'); // ALL, EQUITY, COMMODITY, CURRENCY, BUY, SELL
  const [expandedRow, setExpandedRow] = useState(null);

  const toggleRow = (symbol) => {
    if (expandedRow === symbol) setExpandedRow(null);
    else setExpandedRow(symbol);
  };

  const fetchScan = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/screener/universal`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const json = await res.json();
        setData(json.data);
        setLastScan(new Date().toLocaleTimeString());
      }
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchScan();
    // Auto refresh every 2 minutes
    const interval = setInterval(fetchScan, 120000);
    return () => clearInterval(interval);
  }, [token]);

  const filteredData = data.filter(d => {
    if (filter === 'ALL') return true;
    if (filter === 'EQUITY' || filter === 'COMMODITY' || filter === 'CURRENCY') {
      return d.segment === filter;
    }
    if (filter === 'BUY') return d.decision === 'BUY' || d.decision === 'STRONG BUY';
    if (filter === 'SELL') return d.decision === 'SELL' || d.decision === 'STRONG SELL';
    return true;
  });

  return (
    <div style={{ padding: '20px', color: 'var(--text-primary)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <h2 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Crosshair className="text-accent" /> Global Radar (Multi-Asset Screener)
          </h2>
          <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
            Scanning Equities, Commodities, and Currencies simultaneously for institutional setups.
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
          <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            Last Scan: {lastScan || 'Never'}
          </span>
          <button 
            onClick={fetchScan} 
            disabled={loading}
            style={{
              padding: '8px 16px', backgroundColor: 'var(--accent)', color: 'white',
              border: 'none', borderRadius: '4px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '5px',
              opacity: loading ? 0.7 : 1
            }}
          >
            <RefreshCw size={16} className={loading ? 'spin' : ''} />
            {loading ? 'Scanning Universe...' : 'Force Scan'}
          </button>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '10px', marginBottom: '20px', backgroundColor: '#1e293b', padding: '10px', borderRadius: '8px' }}>
        <Filter size={18} style={{ color: '#9ca3af', alignSelf: 'center', marginLeft: '5px' }} />
        {['ALL', 'EQUITY', 'COMMODITY', 'CURRENCY', 'BUY', 'SELL'].map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            style={{
              padding: '6px 12px',
              backgroundColor: filter === f ? '#8b5cf6' : 'transparent',
              color: filter === f ? 'white' : '#cbd5e1',
              border: '1px solid',
              borderColor: filter === f ? '#8b5cf6' : '#334155',
              borderRadius: '20px',
              cursor: 'pointer',
              fontSize: '0.85rem'
            }}
          >
            {f}
          </button>
        ))}
      </div>

      <div className="panel" style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #374151', color: 'var(--text-secondary)', textAlign: 'left' }}>
              <th style={{ padding: '12px' }}>Symbol</th>
              <th style={{ padding: '12px' }}>Segment</th>
              <th style={{ padding: '12px' }}>LTP</th>
              <th style={{ padding: '12px' }}>AI Decision</th>
              <th style={{ padding: '12px' }}>Confidence</th>
              <th style={{ padding: '12px' }}>Top Catalysts</th>
            </tr>
          </thead>
          <tbody>
            {loading && data.length === 0 ? (
              <tr><td colSpan="6" style={{ padding: '20px', textAlign: 'center' }}>Initializing Global Scan Engine...</td></tr>
            ) : filteredData.length === 0 ? (
              <tr><td colSpan="6" style={{ padding: '20px', textAlign: 'center' }}>No opportunities found matching this filter.</td></tr>
            ) : (
              filteredData.map((row, idx) => {
                let actionClass = "bg-neutral";
                let actionColor = "var(--signal-neutral)";
                if (row.decision === "BUY" || row.decision === "STRONG BUY") { actionClass = "bg-buy"; actionColor = "var(--signal-buy)"; }
                if (row.decision === "SELL" || row.decision === "STRONG SELL") { actionClass = "bg-sell"; actionColor = "var(--signal-sell)"; }

                return (
                  <React.Fragment key={idx}>
                    <tr 
                      onClick={() => toggleRow(row.symbol)}
                      style={{ borderBottom: '1px solid #1F2937', cursor: 'pointer', backgroundColor: expandedRow === row.symbol ? '#1e293b' : 'transparent' }}
                    >
                      <td style={{ padding: '12px', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '8px' }}>
                        {expandedRow === row.symbol ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                        {row.symbol}
                      </td>
                      <td style={{ padding: '12px' }}>
                        <span style={{ 
                          fontSize: '0.75rem', padding: '3px 6px', borderRadius: '4px', 
                          backgroundColor: row.segment === 'EQUITY' ? '#1e3a8a' : row.segment === 'COMMODITY' ? '#78350f' : '#064e3b',
                          color: 'white'
                        }}>
                          {row.segment}
                        </span>
                      </td>
                      <td style={{ padding: '12px' }}>₹{row.current_price?.toFixed(2)}</td>
                      <td style={{ padding: '12px' }}>
                        <span className={actionClass} style={{ padding: '4px 8px', borderRadius: '4px', color: actionColor, fontSize: '0.8rem', fontWeight: 600 }}>
                          {row.decision}
                        </span>
                      </td>
                      <td style={{ padding: '12px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                          <div style={{ width: '50px', height: '6px', backgroundColor: '#374151', borderRadius: '3px' }}>
                            <div style={{ 
                              width: `${Math.abs(row.analytical_score * 100)}%`, 
                              height: '100%', 
                              backgroundColor: actionColor, 
                              borderRadius: '3px' 
                            }} />
                          </div>
                          <span style={{ fontSize: '0.85rem', color: actionColor }}>
                            {(Math.abs(row.analytical_score) * 100).toFixed(1)}%
                          </span>
                        </div>
                      </td>
                      <td style={{ padding: '12px', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                        {Object.keys(row.contributions || {})
                          .filter(k => Math.abs(row.contributions[k].score) > 0.5)
                          .map(k => k.toUpperCase())
                          .join(", ") || "Mixed Signals"}
                      </td>
                    </tr>
                    
                    {expandedRow === row.symbol && row.ai_composite && (
                      <tr style={{ backgroundColor: '#0f172a' }}>
                        <td colSpan="6" style={{ padding: '20px', borderBottom: '1px solid #1F2937' }}>
                          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '20px' }}>
                            
                            {/* AI Composite Scores */}
                            <div className="panel" style={{ backgroundColor: '#1e293b' }}>
                              <h4 style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '15px' }}>
                                <Activity size={16} className="text-accent" /> Institutional Sub-Scores
                              </h4>
                              {Object.entries(row.ai_composite.sub_scores || {}).map(([key, val]) => (
                                <div key={key} style={{ marginBottom: '10px' }}>
                                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '4px', textTransform: 'capitalize' }}>
                                    <span style={{ color: 'var(--text-secondary)' }}>{key.replace('_', ' ')}</span>
                                    <span style={{ color: val > 60 ? 'var(--signal-buy)' : val < 40 ? 'var(--signal-sell)' : 'var(--signal-neutral)' }}>
                                      {val}%
                                    </span>
                                  </div>
                                  <div style={{ width: '100%', height: '4px', backgroundColor: '#334155', borderRadius: '2px' }}>
                                    <div style={{ 
                                      width: `${val}%`, height: '100%', borderRadius: '2px',
                                      backgroundColor: val > 60 ? 'var(--signal-buy)' : val < 40 ? 'var(--signal-sell)' : 'var(--signal-neutral)'
                                    }} />
                                  </div>
                                </div>
                              ))}
                            </div>

                            {/* Trade Setup */}
                            <div className="panel" style={{ backgroundColor: '#1e293b' }}>
                              <h4 style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '15px' }}>
                                <Target size={16} style={{ color: '#f59e0b' }} /> AI Trade Setup
                              </h4>
                              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '8px', borderBottom: '1px solid #334155' }}>
                                  <span style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Entry Range</span>
                                  <span style={{ fontWeight: 'bold' }}>₹{row.ai_composite.trade_setup?.entry}</span>
                                </div>
                                <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '8px', borderBottom: '1px solid #334155' }}>
                                  <span style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Stop Loss</span>
                                  <span style={{ color: 'var(--signal-sell)', fontWeight: 'bold' }}>₹{row.ai_composite.trade_setup?.stop_loss}</span>
                                </div>
                                <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '8px', borderBottom: '1px solid #334155' }}>
                                  <span style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Target 1</span>
                                  <span style={{ color: 'var(--signal-buy)', fontWeight: 'bold' }}>₹{row.ai_composite.trade_setup?.target_1}</span>
                                </div>
                                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                  <span style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Target 2</span>
                                  <span style={{ color: 'var(--signal-buy)', fontWeight: 'bold' }}>₹{row.ai_composite.trade_setup?.target_2}</span>
                                </div>
                              </div>
                            </div>

                            {/* Confluence & Patterns */}
                            <div className="panel" style={{ backgroundColor: '#1e293b' }}>
                              <h4 style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '15px' }}>
                                <Zap size={16} style={{ color: '#ec4899' }} /> Advanced Patterns
                              </h4>
                              <div style={{ marginBottom: '15px' }}>
                                <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '5px' }}>
                                  Detected Formations:
                                </span>
                                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px' }}>
                                  {row.ai_composite.patterns_detected?.map(p => (
                                    <span key={p} style={{ backgroundColor: '#334155', padding: '4px 8px', borderRadius: '4px', fontSize: '0.75rem' }}>
                                      {p}
                                    </span>
                                  ))}
                                </div>
                              </div>
                              <div>
                                <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '5px' }}>
                                  Institutional Filters Passed:
                                </span>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                  <span style={{ fontSize: '1.5rem', fontWeight: 'bold', color: row.ai_composite.confluence_filters_passed >= 8 ? 'var(--signal-buy)' : '#eab308' }}>
                                    {row.ai_composite.confluence_filters_passed}/12
                                  </span>
                                  <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                                    (Trend, Vol, RSI, MACD, VWAP, ATR, OI, etc.)
                                  </span>
                                </div>
                              </div>
                            </div>

                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })
            )}
          </tbody>
        </table>
      </div>
      
      <style>{`
        .spin { animation: spin 1s linear infinite; }
        @keyframes spin { 100% { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
