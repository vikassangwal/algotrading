import React, { useState, useEffect } from 'react';
import { RefreshCw, TrendingUp, AlertTriangle, Crosshair, Filter, ChevronDown, ChevronRight, Activity, Zap, Target, BarChart2 } from 'lucide-react';
const API_URL = (import.meta.env.VITE_API_URL || 'https://elco-backend.onrender.com').replace(/\/$/, '');

const DEFAULT_OPPORTUNITIES = [
  { symbol: "CDSL", segment: "EQUITY", current_price: 1540.20, decision: "STRONG BUY", analytical_score: 0.95, catalysts: "New Demat Spurt, High Intraday Volume Surge", tp: 1680.00, sl: 1450.00, strategy: ["INTRADAY", "BREAKOUT", "OPTIONS", "TOP_PROFIT"] },
  { symbol: "POLYCAB", segment: "EQUITY", current_price: 6850.00, decision: "STRONG BUY", analytical_score: 0.93, catalysts: "Capex Order Win, 20-EMA Swing Pullback", tp: 7400.00, sl: 6500.00, strategy: ["SWING", "OPTIONS", "TOP_PROFIT"] },
  { symbol: "MCX", segment: "EQUITY", current_price: 5890.00, decision: "STRONG BUY", analytical_score: 0.91, catalysts: "Options Volume ATH, 52W High Breakout", tp: 6400.00, sl: 5500.00, strategy: ["INTRADAY", "BREAKOUT", "OPTIONS", "TOP_PROFIT"] },
  { symbol: "KALYANKJIL", segment: "EQUITY", current_price: 645.00, decision: "BUY", analytical_score: 0.89, catalysts: "Store Expansion, Multi-Day Swing Trend", tp: 720.00, sl: 605.00, strategy: ["SWING", "TOP_PROFIT"] },
  { symbol: "DIXON", segment: "EQUITY", current_price: 12450.00, decision: "BUY", analytical_score: 0.88, catalysts: "Mobile Export Growth, Consolidation Breakout", tp: 13500.00, sl: 11800.00, strategy: ["BREAKOUT", "SWING", "TOP_PROFIT"] },
  { symbol: "HAL", segment: "EQUITY", current_price: 4680.00, decision: "STRONG BUY", analytical_score: 0.87, catalysts: "Defence Export Order, 50-EMA Swing Stack", tp: 5100.00, sl: 4400.00, strategy: ["SWING", "OPTIONS", "TOP_PROFIT"] },
  { symbol: "RVNL", segment: "EQUITY", current_price: 580.00, decision: "BUY", analytical_score: 0.85, catalysts: "Rail Infra Orderbook, Intraday VWAP Breakout", tp: 650.00, sl: 535.00, strategy: ["INTRADAY", "BREAKOUT", "TOP_PROFIT"] },
  { symbol: "IREDA", segment: "EQUITY", current_price: 235.40, decision: "BUY", analytical_score: 0.84, catalysts: "Green Financing Expansion, Intraday Scalping Momentum", tp: 275.00, sl: 215.00, strategy: ["INTRADAY", "TOP_PROFIT"] },
  { symbol: "SUZLON", segment: "EQUITY", current_price: 68.40, decision: "BUY", analytical_score: 0.76, catalysts: "Clean Energy Volume Spike, Intraday Momentum", tp: 82.00, sl: 61.50, strategy: ["INTRADAY", "TOP_PROFIT"] },
  { symbol: "RELIANCE", segment: "EQUITY", current_price: 2980.00, decision: "BUY", analytical_score: 0.75, catalysts: "EMA20 Stack Aligned, F&O Open Interest Surge", tp: 3150.00, sl: 2890.00, strategy: ["SWING", "OPTIONS", "TOP_PROFIT"] },
  { symbol: "HDFCBANK", segment: "EQUITY", current_price: 1640.00, decision: "BUY", analytical_score: 0.72, catalysts: "RSI Bullish Divergence, F&O Long Build-Up", tp: 1720.00, sl: 1595.00, strategy: ["SWING", "OPTIONS"] },
  { symbol: "TCS", segment: "EQUITY", current_price: 4150.00, decision: "BUY", analytical_score: 0.68, catalysts: "Orderbook Expansion, F&O Gamma Accumulation", tp: 4350.00, sl: 4020.00, strategy: ["OPTIONS", "SWING"] },
  { symbol: "GOLD (GC=F)", segment: "COMMODITY", current_price: 2420.50, decision: "STRONG BUY", analytical_score: 0.91, catalysts: "Central Bank Buying, Intraday Macro Breakout", tp: 2520.00, sl: 2360.00, strategy: ["INTRADAY", "BREAKOUT", "TOP_PROFIT"] },
  { symbol: "SILVER (SI=F)", segment: "COMMODITY", current_price: 28.40, decision: "BUY", analytical_score: 0.74, catalysts: "Industrial Demand Spike, Intraday Momentum", tp: 31.50, sl: 26.80, strategy: ["INTRADAY"] },
  { symbol: "CRUDE OIL (CL=F)", segment: "COMMODITY", current_price: 76.80, decision: "SELL", analytical_score: -0.65, catalysts: "OPEC Production Relief, Short Swing Setup", tp: 71.00, sl: 80.50, strategy: ["SWING", "INTRADAY"] },
  { symbol: "USDINR (INR=X)", segment: "CURRENCY", current_price: 83.92, decision: "HOLD", analytical_score: 0.10, catalysts: "RBI Range Defense, Rangebound Scalping", tp: 84.20, sl: 83.60, strategy: ["INTRADAY"] },
  { symbol: "EURINR (EURINR=X)", segment: "CURRENCY", current_price: 91.50, decision: "BUY", analytical_score: 0.58, catalysts: "ECB Policy Alignment, Forex Swing", tp: 93.10, sl: 90.40, strategy: ["SWING"] }
];

export default function UniversalScreener({ token, globalSymbol, onSelectSymbol }) {
  const [data, setData] = useState(DEFAULT_OPPORTUNITIES);
  const [loading, setLoading] = useState(false);
  const [lastScan, setLastScan] = useState(new Date().toLocaleTimeString());
  const [filter, setFilter] = useState('ALL'); // ALL, INTRADAY, SWING, BREAKOUT, OPTIONS, TOP 10 HIGH PROFIT
  const [expandedRow, setExpandedRow] = useState(null);

  const handleJump = (sym, targetTab) => {
    const cleanSym = sym.includes('.NS') || sym.includes('.BO') || sym.includes('=') ? sym : `${sym}.NS`;
    if (onSelectSymbol) {
      onSelectSymbol(cleanSym, targetTab);
    }
  };

  const toggleRow = (symbol) => {
    if (expandedRow === symbol) setExpandedRow(null);
    else setExpandedRow(symbol);
  };

  const fetchScan = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/screener/universal`, {
        headers: token && token.length > 20 ? { 'Authorization': `Bearer ${token}` } : {}
      });
      if (res.ok) {
        const json = await res.json();
        if (json && json.data && json.data.length > 0) {
          setData(json.data);
        }
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

  const NIFTY50_SYMBOLS = ["RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS", "BHARTIARTL", "ITC", "SBIN", "LT", "KOTAKBANK", "AXISBANK", "HINDUNILVR", "BAJFINANCE", "ASIANPAINT", "MARUTI", "M&M", "HCLTECH", "SUNPHARMA", "TITAN", "ULTRACEMCO", "NTPC", "POWERGRID", "TATASTEEL", "NESTLEIND", "WIPRO", "JSWSTEEL", "ADANIENT", "ADANIPORTS", "TECHM", "ONGC", "COALINDIA", "BAJAJFINSV", "HINDALCO", "GRASIM", "DRREDDY", "CIPLA", "EICHERMOT", "BRITANNIA", "DIVISLAB", "HEROMOTOCO", "APOLLOHOSP", "BAJAJ-AUTO", "TATACONSUM", "INDUSINDBK", "SBILIFE", "HDFCLIFE", "SHRIRAMFIN", "BPCL"];
  const SENSEX30_SYMBOLS = ["RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS", "BHARTIARTL", "ITC", "SBIN", "LT", "KOTAKBANK", "AXISBANK", "HINDUNILVR", "BAJFINANCE", "ASIANPAINT", "MARUTI", "M&M", "HCLTECH", "SUNPHARMA", "TITAN", "ULTRACEMCO", "NTPC", "POWERGRID", "TATASTEEL", "NESTLEIND", "WIPRO", "JSWSTEEL", "TECHM", "BAJAJFINSV", "INDUSINDBK"];

  let filteredData = data.filter(d => {
    if (filter === 'ALL') return true;
    if (filter === '⚡ INTRADAY') return (d.strategy && d.strategy.includes('INTRADAY')) || (d.catalysts && (d.catalysts.toLowerCase().includes('intraday') || d.catalysts.toLowerCase().includes('volume')));
    if (filter === '🌊 SWING TRADING') return (d.strategy && d.strategy.includes('SWING')) || (d.catalysts && (d.catalysts.toLowerCase().includes('swing') || d.catalysts.toLowerCase().includes('ema')));
    if (filter === '🚀 BREAKOUT') return (d.strategy && d.strategy.includes('BREAKOUT')) || (d.catalysts && (d.catalysts.toLowerCase().includes('breakout') || d.catalysts.toLowerCase().includes('high')));
    if (filter === '📊 OPTIONS & F&O') return (d.strategy && d.strategy.includes('OPTIONS')) || (d.catalysts && (d.catalysts.toLowerCase().includes('f&o') || d.catalysts.toLowerCase().includes('options')));
    if (filter === 'TOP 10 HIGH PROFIT') return (d.decision === 'STRONG BUY' || d.decision === 'BUY') && Math.abs(d.analytical_score || 0.7) >= 0.7;
    if (filter === 'NIFTY 50') return NIFTY50_SYMBOLS.includes(d.symbol.replace('.NS', '').replace('.BO', ''));
    if (filter === 'SENSEX 30') return SENSEX30_SYMBOLS.includes(d.symbol.replace('.NS', '').replace('.BO', ''));
    if (filter === 'MIDCAP & SMALLCAP') return d.segment === 'EQUITY' && !NIFTY50_SYMBOLS.includes(d.symbol.replace('.NS', '').replace('.BO', ''));
    if (filter === 'COMMODITIES (MCX)') return d.segment === 'COMMODITY' || d.symbol.includes('=F') || d.symbol.includes('GOLD') || d.symbol.includes('SILVER') || d.symbol.includes('CRUDE');
    if (filter === 'FOREX (USDINR)') return d.segment === 'CURRENCY' || d.symbol.includes('=X') || d.symbol.includes('INR');
    if (filter === 'BUY') return d.decision === 'BUY' || d.decision === 'STRONG BUY';
    if (filter === 'SELL') return d.decision === 'SELL' || d.decision === 'STRONG SELL';
    return true;
  });

  if (filter === 'TOP 10 HIGH PROFIT') {
    filteredData = [...filteredData].sort((a, b) => (Math.abs(b.analytical_score || 0.7) - Math.abs(a.analytical_score || 0.7))).slice(0, 10);
  }

  return (
    <div style={{ padding: '20px', color: 'var(--text-primary)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <h2 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Crosshair className="text-accent" /> Universal Screener (Multi-Asset Institutional Radar)
          </h2>
          <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
            Filter dynamically by Intraday, Swing Trading, Breakout, Options F&O, Nifty 50, Sensex & Commodities.
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

      <div style={{ display: 'flex', gap: '10px', marginBottom: '20px', backgroundColor: '#1e293b', padding: '12px', borderRadius: '8px', flexWrap: 'wrap', alignItems: 'center' }}>
        <Filter size={18} style={{ color: '#9ca3af', marginLeft: '5px' }} />
        {[
          'ALL', 
          '⚡ INTRADAY', 
          '🌊 SWING TRADING', 
          '🚀 BREAKOUT', 
          '📊 OPTIONS & F&O', 
          '💎 TOP 10 HIGH PROFIT', 
          'NIFTY 50', 
          'SENSEX 30', 
          'MIDCAP & SMALLCAP', 
          'COMMODITIES (MCX)', 
          'FOREX (USDINR)'
        ].map(f => {
          const isTop = f.includes('TOP 10');
          const isStrategy = f.includes('INTRADAY') || f.includes('SWING') || f.includes('BREAKOUT') || f.includes('OPTIONS');
          const isActive = filter === f || (isTop && filter === 'TOP 10 HIGH PROFIT');
          return (
            <button
              key={f}
              onClick={() => setFilter(f.includes('TOP 10') ? 'TOP 10 HIGH PROFIT' : f)}
              style={{
                padding: (isTop || isStrategy) ? '8px 16px' : '6px 14px',
                backgroundColor: isActive ? (isTop ? '#f59e0b' : isStrategy ? '#10b981' : '#8b5cf6') : (isTop ? 'rgba(245, 158, 11, 0.15)' : isStrategy ? 'rgba(16, 185, 129, 0.12)' : 'transparent'),
                color: isActive ? (isTop ? '#0f172a' : 'white') : (isTop ? '#fbbf24' : isStrategy ? '#34d399' : '#cbd5e1'),
                border: '1px solid',
                borderColor: isActive ? (isTop ? '#f59e0b' : isStrategy ? '#10b981' : '#8b5cf6') : (isTop ? '#f59e0b' : isStrategy ? '#10b981' : '#334155'),
                borderRadius: '20px',
                cursor: 'pointer',
                fontSize: '0.85rem',
                fontWeight: 'bold',
                boxShadow: (isActive && isTop) ? '0 0 10px rgba(245, 158, 11, 0.4)' : 'none'
              }}
            >
              {f}
            </button>
          );
        })}
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
              <th style={{ padding: '12px' }}>Catalysts</th>
              <th style={{ padding: '12px' }}>Quick Analysis Links</th>
            </tr>
          </thead>
          <tbody>
            {loading && data.length === 0 ? (
              <tr><td colSpan="7" style={{ padding: '20px', textAlign: 'center' }}>Initializing Global Scan Engine...</td></tr>
            ) : filteredData.length === 0 ? (
              <tr><td colSpan="7" style={{ padding: '20px', textAlign: 'center' }}>No opportunities found matching this filter.</td></tr>
            ) : (
              filteredData.map((row, idx) => {
                let actionClass = "bg-neutral";
                let actionColor = "var(--signal-neutral)";
                if (row.decision === "BUY" || row.decision === "STRONG BUY") { actionClass = "bg-buy"; actionColor = "var(--signal-buy)"; }
                if (row.decision === "SELL" || row.decision === "STRONG SELL") { actionClass = "bg-sell"; actionColor = "var(--signal-sell)"; }

                return (
                  <React.Fragment key={idx}>
                    <tr 
                      style={{ borderBottom: '1px solid #1F2937', backgroundColor: expandedRow === row.symbol ? '#1e293b' : 'transparent' }}
                    >
                      <td 
                        onClick={() => toggleRow(row.symbol)}
                        style={{ padding: '12px', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}
                      >
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
                              width: `${Math.abs((row.analytical_score || 0.7) * 100)}%`, 
                              height: '100%', 
                              backgroundColor: actionColor, 
                              borderRadius: '3px' 
                            }} />
                          </div>
                          <span style={{ fontSize: '0.85rem', color: actionColor }}>
                            {(Math.abs(row.analytical_score || 0.7) * 100).toFixed(1)}%
                          </span>
                        </div>
                      </td>
                      <td style={{ padding: '12px', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                        {row.catalysts || Object.keys(row.contributions || {})
                          .filter(k => Math.abs(row.contributions[k].score) > 0.5)
                          .map(k => k.toUpperCase())
                          .join(", ") || "Technical Confluence"}
                      </td>
                      <td style={{ padding: '12px' }}>
                        <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                          <button onClick={() => handleJump(row.symbol, 'profile')} style={{ padding: '3px 8px', fontSize: '11px', background: '#1e293b', border: '1px solid #3b82f6', color: '#60a5fa', borderRadius: '4px', cursor: 'pointer' }}>📊 Biodata</button>
                          <button onClick={() => handleJump(row.symbol, 'options')} style={{ padding: '3px 8px', fontSize: '11px', background: '#1e293b', border: '1px solid #8b5cf6', color: '#c084fc', borderRadius: '4px', cursor: 'pointer' }}>⛓️ Option Chain</button>
                          <button onClick={() => handleJump(row.symbol, 'scanner')} style={{ padding: '3px 8px', fontSize: '11px', background: '#1e293b', border: '1px solid #10b981', color: '#34d399', borderRadius: '4px', cursor: 'pointer' }}>📈 Technicals</button>
                          <button onClick={() => handleJump(row.symbol, 'market-scanner')} style={{ padding: '3px 8px', fontSize: '11px', background: '#1e293b', border: '1px solid #f59e0b', color: '#fbbf24', borderRadius: '4px', cursor: 'pointer' }}>🤖 AI Scanner</button>
                          <button onClick={() => handleJump(row.symbol, 'heatmap')} style={{ padding: '3px 8px', fontSize: '11px', background: '#1e293b', border: '1px solid #ec4899', color: '#f472b6', borderRadius: '4px', cursor: 'pointer' }}>🗺️ Heatmap</button>
                          <button onClick={() => handleJump(row.symbol, 'radar')} style={{ padding: '3px 8px', fontSize: '11px', background: '#1e293b', border: '1px solid #ef4444', color: '#f87171', borderRadius: '4px', cursor: 'pointer' }}>🛡️ Risk Radar</button>
                        </div>
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
