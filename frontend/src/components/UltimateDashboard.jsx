import React, { useState, useEffect } from 'react';
import { Activity, ShieldAlert, Zap, TrendingUp, TrendingDown, Crosshair, Lock, PlayCircle, Eye, ShieldCheck, RefreshCw } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || '';

const UltimateDashboard = ({ token }) => {
  const [tradingMode, setTradingMode] = useState('Intraday');
  const [isAuto, setIsAuto] = useState(false);
  const [portfolio, setPortfolio] = useState({ daily_pnl: 0, circuit_breaker: false, active_positions: [] });
  const [analysis, setAnalysis] = useState(null);
  const [hftToggles, setHftToggles] = useState({
    hedge: false,
    iceberg: true,
    twap: false,
    circuitBreaker: true
  });
  const [symbolInput, setSymbolInput] = useState('RELIANCE.NS');

  // Fetch portfolio status every 2 seconds
  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API_URL}/api/dashboard/status`, { headers: token ? { 'Authorization': `Bearer ${token}` } : {} });
        if (res.ok) setPortfolio(await res.json());
      } catch (err) {}
    }, 2000);
    return () => clearInterval(interval);
  }, [token]);

  const fetchAnalysis = async () => {
    try {
      const res = await fetch(`${API_URL}/api/dashboard/analysis/${symbolInput}`);
      if (res.ok) setAnalysis(await res.json());
    } catch (err) {}
  };

  const handleExecute = async (side) => {
    try {
      await fetch(`${API_URL}/api/dashboard/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...(token ? { 'Authorization': `Bearer ${token}` } : {}) },
        body: JSON.stringify({
          symbol: symbolInput,
          side: side,
          qty: 100,
          execution_type: hftToggles.twap ? 'TWAP' : 'MARKET',
          hedge: hftToggles.hedge
        })
      });
    } catch (err) {}
  };

  return (
    <div style={{ backgroundColor: '#020617', minHeight: '100vh', color: '#f8fafc', padding: '20px', fontFamily: 'system-ui, sans-serif' }}>
      
      {/* Top Header - Settings & Toggles */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', backgroundColor: '#0f172a', padding: '16px 24px', borderRadius: '12px', marginBottom: '20px', border: '1px solid #1e293b' }}>
        <div style={{ display: 'flex', gap: '20px', alignItems: 'center' }}>
          <h1 style={{ margin: 0, fontSize: '24px', fontWeight: 'bold', background: 'linear-gradient(90deg, #3b82f6, #8b5cf6)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            Ultimate Command Center
          </h1>
          
          <select value={tradingMode} onChange={e => setTradingMode(e.target.value)} style={{ backgroundColor: '#1e293b', color: '#f8fafc', padding: '8px 16px', borderRadius: '8px', border: '1px solid #334155', outline: 'none' }}>
            <option>Intraday</option>
            <option>Swing</option>
            <option>Positional</option>
            <option>Futures & Options</option>
            <option>Commodity</option>
          </select>
        </div>

        <div style={{ display: 'flex', gap: '24px', alignItems: 'center' }}>
          {/* HFT Toggles */}
          <div style={{ display: 'flex', gap: '12px' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', cursor: 'pointer', color: hftToggles.hedge ? '#10b981' : '#64748b' }}>
              <input type="checkbox" checked={hftToggles.hedge} onChange={e => setHftToggles({...hftToggles, hedge: e.target.checked})} style={{ display: 'none' }} />
              <ShieldCheck size={16} /> Auto Hedge
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', cursor: 'pointer', color: hftToggles.twap ? '#3b82f6' : '#64748b' }}>
              <input type="checkbox" checked={hftToggles.twap} onChange={e => setHftToggles({...hftToggles, twap: e.target.checked})} style={{ display: 'none' }} />
              <RefreshCw size={16} /> TWAP Exec
            </label>
          </div>

          {/* Auto/Manual Toggle */}
          <div style={{ display: 'flex', alignItems: 'center', backgroundColor: '#1e293b', borderRadius: '30px', padding: '4px' }}>
            <button onClick={() => setIsAuto(false)} style={{ padding: '6px 16px', borderRadius: '20px', border: 'none', backgroundColor: !isAuto ? '#3b82f6' : 'transparent', color: !isAuto ? '#fff' : '#94a3b8', cursor: 'pointer', fontWeight: 'bold', fontSize: '13px' }}>Manual</button>
            <button onClick={() => setIsAuto(true)} style={{ padding: '6px 16px', borderRadius: '20px', border: 'none', backgroundColor: isAuto ? '#10b981' : 'transparent', color: isAuto ? '#fff' : '#94a3b8', cursor: 'pointer', fontWeight: 'bold', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '4px' }}><Zap size={14} /> Auto</button>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr 300px', gap: '20px' }}>
        
        {/* Left Panel: 4-Pillar Analysis */}
        <div style={{ backgroundColor: '#0f172a', borderRadius: '12px', padding: '20px', border: '1px solid #1e293b' }}>
          <h2 style={{ fontSize: '16px', margin: '0 0 16px 0', color: '#cbd5e1', display: 'flex', alignItems: 'center', gap: '8px' }}><Crosshair size={18} color="#3b82f6" /> 4-Pillar Master Analysis</h2>
          
          <div style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
            <input type="text" value={symbolInput} onChange={e => setSymbolInput(e.target.value)} style={{ flex: 1, padding: '8px', backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '6px', color: '#fff' }} />
            <button onClick={fetchAnalysis} style={{ padding: '8px 12px', backgroundColor: '#3b82f6', border: 'none', borderRadius: '6px', color: '#fff', cursor: 'pointer' }}>Scan</button>
          </div>

          {analysis ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ padding: '12px', backgroundColor: '#1e293b', borderRadius: '8px', borderLeft: '3px solid #3b82f6' }}>
                <span style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase' }}>Technical</span>
                <div style={{ fontSize: '14px', fontWeight: 'bold', color: '#f8fafc' }}>{analysis.technical}</div>
              </div>
              <div style={{ padding: '12px', backgroundColor: '#1e293b', borderRadius: '8px', borderLeft: '3px solid #8b5cf6' }}>
                <span style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase' }}>Fundamental</span>
                <div style={{ fontSize: '14px', fontWeight: 'bold', color: '#f8fafc' }}>{analysis.fundamental}</div>
              </div>
              <div style={{ padding: '12px', backgroundColor: '#1e293b', borderRadius: '8px', borderLeft: '3px solid #f59e0b' }}>
                <span style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase' }}>Quantitative</span>
                <div style={{ fontSize: '14px', fontWeight: 'bold', color: '#f8fafc' }}>{analysis.quant}</div>
              </div>
              <div style={{ padding: '12px', backgroundColor: '#1e293b', borderRadius: '8px', borderLeft: '3px solid #ec4899' }}>
                <span style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase' }}>Sentiment & Smart Money</span>
                <div style={{ fontSize: '14px', fontWeight: 'bold', color: '#f8fafc' }}>{analysis.sentiment}</div>
              </div>

              <div style={{ marginTop: '10px', padding: '16px', backgroundColor: analysis.verdict === 'BUY' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)', border: `1px solid ${analysis.verdict === 'BUY' ? '#10b981' : '#ef4444'}`, borderRadius: '8px', textAlign: 'center' }}>
                <h3 style={{ margin: '0 0 4px 0', color: analysis.verdict === 'BUY' ? '#10b981' : '#ef4444' }}>AI Verdict: {analysis.verdict}</h3>
                <span style={{ fontSize: '12px', color: '#cbd5e1' }}>{analysis.ai_reason}</span>
              </div>
            </div>
          ) : (
            <div style={{ color: '#64748b', textAlign: 'center', padding: '40px 0', fontSize: '14px' }}>Enter a symbol to scan.</div>
          )}
        </div>

        {/* Center Panel: Execution & Probability */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          
          {/* Probability Meter */}
          <div style={{ backgroundColor: '#0f172a', borderRadius: '12px', padding: '24px', border: '1px solid #1e293b', textAlign: 'center' }}>
            <h2 style={{ fontSize: '16px', margin: '0 0 20px 0', color: '#cbd5e1' }}>AI Direction Probability</h2>
            <div style={{ width: '100%', height: '30px', backgroundColor: '#ef4444', borderRadius: '15px', overflow: 'hidden', position: 'relative', display: 'flex' }}>
              <div style={{ width: analysis ? `${analysis.probability}%` : '50%', backgroundColor: '#10b981', height: '100%', transition: 'width 1s ease-in-out' }}></div>
              <div style={{ position: 'absolute', width: '100%', height: '100%', display: 'flex', justifyContent: 'center', alignItems: 'center', fontWeight: 'bold', textShadow: '0 1px 2px rgba(0,0,0,0.8)' }}>
                {analysis ? (analysis.probability > 50 ? `${analysis.probability}% UP` : `${100 - analysis.probability}% DOWN`) : 'Scanning...'}
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div style={{ display: 'flex', gap: '20px' }}>
            <button onClick={() => handleExecute('BUY')} disabled={isAuto || portfolio.circuit_breaker} style={{ flex: 1, padding: '20px', backgroundColor: '#10b981', border: 'none', borderRadius: '12px', color: '#fff', fontSize: '18px', fontWeight: 'bold', cursor: (isAuto || portfolio.circuit_breaker) ? 'not-allowed' : 'pointer', opacity: (isAuto || portfolio.circuit_breaker) ? 0.5 : 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px' }}>
              <TrendingUp size={24} /> BUY / LONG
            </button>
            <button onClick={() => handleExecute('SELL')} disabled={isAuto || portfolio.circuit_breaker} style={{ flex: 1, padding: '20px', backgroundColor: '#ef4444', border: 'none', borderRadius: '12px', color: '#fff', fontSize: '18px', fontWeight: 'bold', cursor: (isAuto || portfolio.circuit_breaker) ? 'not-allowed' : 'pointer', opacity: (isAuto || portfolio.circuit_breaker) ? 0.5 : 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px' }}>
              <TrendingDown size={24} /> SELL / SHORT
            </button>
          </div>

          {/* Active Positions Table */}
          <div style={{ backgroundColor: '#0f172a', borderRadius: '12px', padding: '20px', border: '1px solid #1e293b', flex: 1 }}>
            <h2 style={{ fontSize: '16px', margin: '0 0 16px 0', color: '#cbd5e1', display: 'flex', alignItems: 'center', gap: '8px' }}><Activity size={18} color="#f59e0b" /> Active Positions</h2>
            {portfolio.active_positions.length === 0 ? (
              <div style={{ color: '#64748b', textAlign: 'center', padding: '20px 0', fontSize: '14px' }}>No active trades.</div>
            ) : (
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                <thead>
                  <tr style={{ color: '#94a3b8', borderBottom: '1px solid #334155', textAlign: 'left' }}>
                    <th style={{ padding: '8px' }}>Symbol</th>
                    <th style={{ padding: '8px' }}>Side</th>
                    <th style={{ padding: '8px' }}>Qty</th>
                    <th style={{ padding: '8px' }}>Avg Price</th>
                  </tr>
                </thead>
                <tbody>
                  {portfolio.active_positions.map((pos, idx) => (
                    <tr key={idx} style={{ borderBottom: '1px solid #1e293b' }}>
                      <td style={{ padding: '12px 8px', color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '6px' }}>
                        {pos.symbol} {pos.hedged && <ShieldCheck size={12} color="#10b981" title="Delta Hedged" />}
                      </td>
                      <td style={{ padding: '12px 8px', color: pos.side === 'BUY' ? '#10b981' : '#ef4444', fontWeight: 'bold' }}>{pos.side}</td>
                      <td style={{ padding: '12px 8px', color: '#cbd5e1' }}>{pos.qty}</td>
                      <td style={{ padding: '12px 8px', color: '#cbd5e1' }}>₹{pos.avg_price}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

        </div>

        {/* Right Panel: P&L and Risk */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          
          <div style={{ backgroundColor: '#0f172a', borderRadius: '12px', padding: '24px', border: '1px solid #1e293b', textAlign: 'center' }}>
            <h2 style={{ fontSize: '16px', margin: '0 0 8px 0', color: '#cbd5e1' }}>Live MTM (P&L)</h2>
            <div style={{ fontSize: '36px', fontWeight: 'bold', color: portfolio.daily_pnl >= 0 ? '#10b981' : '#ef4444' }}>
              {portfolio.daily_pnl >= 0 ? '+' : '-'}₹{Math.abs(portfolio.daily_pnl).toLocaleString()}
            </div>
          </div>

          {portfolio.circuit_breaker && (
            <div style={{ backgroundColor: 'rgba(239, 68, 68, 0.1)', border: '1px solid #ef4444', borderRadius: '12px', padding: '20px', textAlign: 'center' }}>
              <Lock size={32} color="#ef4444" style={{ margin: '0 auto 12px auto' }} />
              <h3 style={{ margin: '0 0 8px 0', color: '#ef4444', fontSize: '16px' }}>Circuit Breaker Active</h3>
              <p style={{ margin: 0, fontSize: '13px', color: '#fca5a5' }}>Max daily loss hit. Manual trading disabled to prevent revenge trading.</p>
            </div>
          )}

          <div style={{ backgroundColor: '#0f172a', borderRadius: '12px', padding: '20px', border: '1px solid #1e293b', flex: 1 }}>
            <h2 style={{ fontSize: '16px', margin: '0 0 16px 0', color: '#cbd5e1', display: 'flex', alignItems: 'center', gap: '8px' }}><Eye size={18} color="#8b5cf6" /> ML Insights</h2>
            <div style={{ padding: '12px', backgroundColor: '#1e293b', borderRadius: '8px', fontSize: '13px', color: '#cbd5e1', lineHeight: '1.6' }}>
              <strong>AI Memory:</strong> The last 3 times you took a breakout trade in High Volatility, it resulted in a loss. AI suggests switching to <strong>Mean Reversion</strong> or <strong>Options Selling</strong> today.
            </div>
            
            <button style={{ width: '100%', marginTop: '16px', padding: '12px', backgroundColor: '#334155', border: 'none', borderRadius: '8px', color: '#f8fafc', cursor: 'pointer', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px' }}>
              <PlayCircle size={16} /> Open Strategy Builder
            </button>
          </div>

        </div>

      </div>
    </div>
  );
};

export default UltimateDashboard;
