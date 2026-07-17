import React, { useState, useEffect } from 'react';
import { Target, Activity, Zap, BarChart2, ChevronDown, ChevronUp, BrainCircuit, ExternalLink } from 'lucide-react';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer } from 'recharts';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const RadarScore = ({ scores, color }) => {
  const data = [
    { subject: 'Trend', A: scores.trend, fullMark: 100 },
    { subject: 'Momentum', A: scores.momentum, fullMark: 100 },
    { subject: 'Volume', A: scores.volume, fullMark: 100 },
    { subject: 'Volatility', A: scores.volatility, fullMark: 100 },
    { subject: 'Pattern', A: scores.pattern, fullMark: 100 },
  ];

  return (
    <div style={{ width: '200px', height: '160px' }}>
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart cx="50%" cy="50%" outerRadius="60%" data={data}>
          <PolarGrid stroke="#334155" />
          <PolarAngleAxis dataKey="subject" tick={{ fill: '#94a3b8', fontSize: 10 }} />
          <Radar name="Score" dataKey="A" stroke={color} fill={color} fillOpacity={0.4} />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
};

const StockCard = ({ data, type }) => {
  const [expanded, setExpanded] = useState(false);
  const color = type === 'BULLISH' ? '#10b981' : '#ef4444';
  const bgColor = type === 'BULLISH' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)';

  return (
    <div style={{ backgroundColor: '#1e293b', border: `1px solid ${color}`, borderRadius: '8px', marginBottom: '12px', overflow: 'hidden' }}>
      
      {/* Header Summary */}
      <div 
        onClick={() => setExpanded(!expanded)}
        style={{ padding: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer', backgroundColor: expanded ? bgColor : 'transparent', transition: 'background 0.2s' }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '18px', fontWeight: 'bold', color: '#f8fafc' }}>{data.symbol}</span>
            <span style={{ fontSize: '12px', padding: '2px 8px', borderRadius: '4px', backgroundColor: color, color: '#fff', fontWeight: 'bold' }}>
              {data.chance_pct}% Chance
            </span>
          </div>
          <span style={{ color: '#94a3b8', fontSize: '14px' }}>LTP: ₹{data.current_price.toFixed(2)}</span>
        </div>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ textAlign: 'right', marginRight: '10px' }}>
            <div style={{ color: '#f8fafc', fontSize: '14px', fontWeight: '500' }}>{data.trend_status}</div>
            <div style={{ color: '#64748b', fontSize: '12px' }}>{data.breakout_status}</div>
          </div>
          {expanded ? <ChevronUp color="#94a3b8" /> : <ChevronDown color="#94a3b8" />}
        </div>
      </div>

      {/* Expanded Details */}
      {expanded && (
        <div style={{ padding: '20px', borderTop: '1px solid #334155', backgroundColor: '#0f172a' }}>
          
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '24px' }}>
            {/* Left: Technical Stats */}
            <div style={{ flex: 1, minWidth: '250px' }}>
              <h4 style={{ color: '#e2e8f0', margin: '0 0 12px 0', fontSize: '14px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Activity size={16} color="#3b82f6" /> Technical Breakdown
              </h4>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', fontSize: '13px' }}>
                <div><span style={{color: '#64748b'}}>RSI (Momentum):</span> <span style={{color: '#f8fafc'}}>{data.momentum_rsi}</span></div>
                <div><span style={{color: '#64748b'}}>ATR (Volatility):</span> <span style={{color: '#f8fafc'}}>{data.volatility_atr}</span></div>
                <div><span style={{color: '#64748b'}}>Candlestick:</span> <span style={{color: '#f8fafc'}}>{data.candlestick}</span></div>
                <div><span style={{color: '#64748b'}}>Chart Pattern:</span> <span style={{color: '#f8fafc'}}>{data.chart_pattern}</span></div>
              </div>

              <div style={{ marginTop: '20px', padding: '12px', backgroundColor: 'rgba(59, 130, 246, 0.1)', borderRadius: '6px', borderLeft: '3px solid #3b82f6' }}>
                <p style={{ margin: 0, fontSize: '13px', color: '#cbd5e1', lineHeight: '1.5' }}>
                  <strong>AI Reasoning:</strong> {data.ai_reason}
                </p>
              </div>
            </div>

            {/* Center: Radar Score */}
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
              <h4 style={{ color: '#e2e8f0', margin: '0 0 4px 0', fontSize: '14px' }}>Quality Score</h4>
              <RadarScore scores={data.quality_scores} color={color} />
            </div>

            {/* Right: Trading Plan */}
            <div style={{ flex: 1, minWidth: '250px' }}>
              <h4 style={{ color: '#e2e8f0', margin: '0 0 12px 0', fontSize: '14px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Target size={16} color="#f59e0b" /> AI Trading Plan
              </h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '13px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{color: '#64748b'}}>Entry Zone:</span> <span style={{color: '#cbd5e1', fontWeight: 'bold'}}>{data.trading_plan.entry_zone}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{color: '#64748b'}}>Stop Loss:</span> <span style={{color: '#ef4444', fontWeight: 'bold'}}>{data.trading_plan.stop_loss}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{color: '#64748b'}}>Target 1:</span> <span style={{color: color, fontWeight: 'bold'}}>{data.trading_plan.targets[0]}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{color: '#64748b'}}>Target 2:</span> <span style={{color: color, fontWeight: 'bold'}}>{data.trading_plan.targets[1]}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{color: '#64748b'}}>Holding Period:</span> <span style={{color: '#f8fafc'}}>{data.trading_plan.holding_period}</span>
                </div>
              </div>
              
              <div style={{ marginTop: '16px', display: 'flex', gap: '10px' }}>
                <button style={{ flex: 1, padding: '8px', backgroundColor: '#3b82f6', border: 'none', borderRadius: '4px', color: '#fff', cursor: 'pointer', fontSize: '12px', fontWeight: 'bold', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}>
                  <ExternalLink size={14} /> Open Chart
                </button>
                <button style={{ flex: 1, padding: '8px', backgroundColor: 'transparent', border: '1px solid #3b82f6', borderRadius: '4px', color: '#3b82f6', cursor: 'pointer', fontSize: '12px', fontWeight: 'bold' }}>
                  Paper Trade
                </button>
              </div>
            </div>
          </div>

        </div>
      )}
    </div>
  );
};

const AdvancedScannerUI = ({ token }) => {
  const [data, setData] = useState({ top_bullish: [], top_bearish: [] });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchScan = async () => {
      try {
        const res = await fetch(`${API_URL}/api/scanner/top20`, {
          headers: token ? { 'Authorization': `Bearer ${token}` } : {}
        });
        if (res.ok) {
          const json = await res.json();
          if (json.status === 'success') {
            setData(json.data);
          }
        }
      } catch (err) {
        console.error("Scanner fetch failed", err);
      }
      setLoading(false);
    };

    fetchScan();
  }, [token]);

  return (
    <div style={{ padding: '24px', backgroundColor: '#0f172a', minHeight: '100vh', color: '#f8fafc', fontFamily: 'system-ui, -apple-system, sans-serif' }}>
      
      {/* Header */}
      <div style={{ marginBottom: '30px', borderBottom: '1px solid #334155', paddingBottom: '20px' }}>
        <h1 style={{ fontSize: '28px', fontWeight: 'bold', margin: '0 0 10px 0', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <BrainCircuit size={32} color="#8b5cf6" />
          Institutional AI Scanner
        </h1>
        <p style={{ margin: 0, color: '#94a3b8', fontSize: '15px' }}>
          Real-time Top 20 actionable setups calculated across 22 technical sub-modules. Probabilities represent the AI's confidence in the projected direction.
        </p>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', color: '#94a3b8', padding: '40px' }}>
          <Zap size={48} color="#eab308" style={{ animation: 'pulse 2s infinite' }} />
          <p>Running Quantitative Scan across Market Universe...</p>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '30px' }}>
          
          {/* Bullish Column */}
          <div>
            <h2 style={{ fontSize: '20px', color: '#10b981', display: 'flex', alignItems: 'center', gap: '8px', borderBottom: '2px solid #10b981', paddingBottom: '10px', marginBottom: '20px' }}>
              <TrendingUp size={24} /> Top 10 Bullish Opportunities
            </h2>
            {data.top_bullish.map(stock => (
              <StockCard key={stock.symbol} data={stock} type="BULLISH" />
            ))}
            {data.top_bullish.length === 0 && <p style={{ color: '#64748b' }}>No high-probability bullish setups found.</p>}
          </div>

          {/* Bearish Column */}
          <div>
            <h2 style={{ fontSize: '20px', color: '#ef4444', display: 'flex', alignItems: 'center', gap: '8px', borderBottom: '2px solid #ef4444', paddingBottom: '10px', marginBottom: '20px' }}>
              <TrendingDown size={24} /> Top 10 Bearish Opportunities
            </h2>
            {data.top_bearish.map(stock => (
              <StockCard key={stock.symbol} data={stock} type="BEARISH" />
            ))}
            {data.top_bearish.length === 0 && <p style={{ color: '#64748b' }}>No high-probability bearish setups found.</p>}
          </div>

        </div>
      )}

    </div>
  );
};

// SVG icons fallback (for TrendingUp/Down which weren't imported from lucide above)
import { TrendingUp, TrendingDown } from 'lucide-react';

export default AdvancedScannerUI;
