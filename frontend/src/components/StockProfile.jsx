import React, { useState, useEffect } from 'react';
import { Activity, TrendingUp, TrendingDown, Crosshair, AlertTriangle, ShieldCheck, BarChart2, BookOpen, Layers, Target, Zap, Clock, Users, RefreshCw } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || '';

const StockProfile = ({ token, globalSymbol }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedStyle, setSelectedStyle] = useState('intraday');

  useEffect(() => {
    if (!globalSymbol) return;
    
    const fetchProfile = async () => {
      setLoading(true);
      setError(null);
      try {
        const headers = token ? { 'Authorization': `Bearer ${token}` } : {};
        const res = await fetch(`${API_URL}/api/analysis/full/${globalSymbol}`, { headers });
        if (!res.ok) {
          throw new Error('Failed to fetch stock biodata');
        }
        const json = await res.json();
        setData(json);
      } catch (err) {
        console.error(err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchProfile();
  }, [globalSymbol, token]);

  if (loading) {
    return (
      <div style={{ padding: '4rem', textAlign: 'center' }}>
        <RefreshCw size={40} className="spin" style={{ color: 'var(--accent)', margin: '0 auto 1rem' }} />
        <h2>Analyzing {globalSymbol}...</h2>
        <style>{`.spin { animation: spin 1s linear infinite; } @keyframes spin { 100% { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--signal-sell)' }}>
        <AlertTriangle size={48} style={{ margin: '0 auto 1rem' }} />
        <h3>Error loading Biodata</h3>
        <p>{error}</p>
      </div>
    );
  }

  if (!data) return <div style={{ padding: '2rem' }}>No data available. Search for a stock to see its Biodata.</div>;

  const quote = data.quote || {};
  const price = quote.price ?? 0;
  const change_pct = quote.change_pct ?? 0;
  const four_pillar_signal = data.fused_signal || {};
  const consensus = data.indicator_consensus || {};
  const indicators = data.indicators ? Object.entries(data.indicators).map(([key, ind]) => ({ name: key, ...ind })) : [];
  const institutions = data.institutional || {};
  const regime = data.regime || {};
  const allowed_families = regime.strategy_families_allowed_now || [];
  const trade_plan = data.trade_plan || {};
  const styles = trade_plan.styles || {};

  const isBullish = change_pct >= 0;

  return (
    <div style={{ padding: '20px', maxWidth: '1400px', margin: '0 auto' }}>
      
      {/* Header Profile Section */}
      <div className="panel" style={{ marginBottom: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', background: 'linear-gradient(to right, #1e293b, #0f172a)', border: '1px solid #334155' }}>
        <div>
          <h1 style={{ fontSize: '2.5rem', fontWeight: 'bold', margin: '0 0 10px 0', display: 'flex', alignItems: 'center', gap: '10px' }}>
            {data.symbol}
            <span style={{ fontSize: '1rem', padding: '4px 12px', background: '#334155', borderRadius: '15px', color: 'var(--text-secondary)' }}>
              Stock Profile
            </span>
          </h1>
          <div style={{ display: 'flex', gap: '20px', fontSize: '1.2rem', color: 'var(--text-secondary)' }}>
            <span style={{ fontSize: '2rem', fontWeight: 'bold', color: 'var(--text-primary)' }}>₹{price.toFixed(2)}</span>
            <span style={{ color: isBullish ? 'var(--signal-buy)' : 'var(--signal-sell)', display: 'flex', alignItems: 'center', gap: '5px' }}>
              {isBullish ? <TrendingUp /> : <TrendingDown />} 
              {isBullish ? '+' : ''}{change_pct.toFixed(2)}%
            </span>
          </div>
        </div>
        
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '5px' }}>4-Pillar AI Signal</div>
          <div style={{ 
            fontSize: '1.8rem', 
            fontWeight: 'bold', 
            textTransform: 'uppercase',
            color: four_pillar_signal.final_signal === 'BUY' ? 'var(--signal-buy)' : 
                   four_pillar_signal.final_signal === 'SELL' ? 'var(--signal-sell)' : 'var(--signal-neutral)',
            padding: '8px 20px',
            border: `2px solid ${four_pillar_signal.final_signal === 'BUY' ? 'var(--signal-buy)' : 
                                 four_pillar_signal.final_signal === 'SELL' ? 'var(--signal-sell)' : '#64748b'}`,
            borderRadius: '8px',
            background: 'rgba(0,0,0,0.2)'
          }}>
            {four_pillar_signal.final_signal || 'NEUTRAL'}
          </div>
        </div>
      </div>

      {/* Multi-Style Trading Analysis & Execution Section */}
      <div className="panel" style={{ marginBottom: '20px', borderTop: '4px solid var(--accent)' }}>
        <h3 style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '15px', fontSize: '1.3rem' }}>
          <Target size={24} className="text-accent" /> Style-Wise Trading Analysis & Target / Stoploss Plan
        </h3>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '20px' }}>
          Har trading style (Intraday, Swing, Positional, Long-term) ke liye zaroori analysis weightage aur automatic Target / Stop-loss level:
        </p>

        {/* Style Selection Tabs */}
        <div style={{ display: 'flex', gap: '10px', marginBottom: '20px', borderBottom: '1px solid #1e293b', paddingBottom: '10px' }}>
          {[
            { key: 'intraday', label: '⚡ Intraday Trading (1 Day)' },
            { key: 'swing', label: '📊 Swing Trading (1-3 Weeks)' },
            { key: 'positional', label: '🎯 Positional (1-6 Months)' },
            { key: 'investment', label: '💎 Long-Term Investment (1-5 Yrs)' }
          ].map((style) => (
            <button
              key={style.key}
              onClick={() => setSelectedStyle(style.key)}
              style={{
                padding: '10px 18px',
                background: selectedStyle === style.key ? 'var(--accent)' : '#1e293b',
                color: selectedStyle === style.key ? '#fff' : 'var(--text-secondary)',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                fontWeight: 'bold',
                fontSize: '0.9rem',
                transition: 'all 0.2s'
              }}
            >
              {style.label}
            </button>
          ))}
        </div>

        {/* Selected Style Detail Card */}
        {styles[selectedStyle] && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px', background: '#0f172a', padding: '20px', borderRadius: '8px', border: '1px solid #334155' }}>
            
            {/* Column 1: Required Analysis Weightage */}
            <div>
              <h4 style={{ margin: '0 0 15px 0', color: 'var(--accent)', fontSize: '1.05rem' }}>
                📌 Required Analysis Breakdown ({styles[selectedStyle].title})
              </h4>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '15px' }}>
                Timeframe: <b>{styles[selectedStyle].timeframe}</b>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {Object.entries(styles[selectedStyle].analysis_weightage || {}).map(([name, pct]) => (
                  <div key={name}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '4px' }}>
                      <span>{name}</span>
                      <span style={{ fontWeight: 'bold', color: 'var(--accent)' }}>{pct}</span>
                    </div>
                    <div style={{ width: '100%', height: '8px', background: '#1e293b', borderRadius: '4px' }}>
                      <div style={{ width: pct, height: '100%', background: 'var(--accent)', borderRadius: '4px' }}></div>
                    </div>
                  </div>
                ))}
              </div>
              <div style={{ marginTop: '15px', padding: '10px', background: '#1e293b', borderRadius: '6px', fontSize: '0.85rem' }}>
                🔍 <b>Key Focus:</b> {styles[selectedStyle].key_focus}
              </div>
            </div>

            {/* Column 2: Exact Trade Execution Prices */}
            <div>
              <h4 style={{ margin: '0 0 15px 0', color: 'var(--signal-buy)', fontSize: '1.05rem' }}>
                🎯 Target, Stop-Loss & Entry Plan
              </h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px', background: '#1e293b', borderRadius: '6px' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Suggested Entry Price</span>
                  <span style={{ fontWeight: 'bold', fontSize: '1.1rem' }}>₹{styles[selectedStyle].entry_price}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px', background: 'rgba(239, 68, 68, 0.15)', borderLeft: '4px solid var(--signal-sell)', borderRadius: '6px' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Stop Loss (SL)</span>
                  <span style={{ fontWeight: 'bold', color: 'var(--signal-sell)', fontSize: '1.1rem' }}>₹{styles[selectedStyle].stop_loss}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px', background: 'rgba(16, 185, 129, 0.15)', borderLeft: '4px solid var(--signal-buy)', borderRadius: '6px' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Target 1 (T1)</span>
                  <span style={{ fontWeight: 'bold', color: 'var(--signal-buy)', fontSize: '1.1rem' }}>₹{styles[selectedStyle].target_1}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px', background: 'rgba(16, 185, 129, 0.25)', borderLeft: '4px solid var(--signal-buy)', borderRadius: '6px' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Target 2 (T2)</span>
                  <span style={{ fontWeight: 'bold', color: 'var(--signal-buy)', fontSize: '1.1rem' }}>₹{styles[selectedStyle].target_2}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px', background: '#1e293b', borderRadius: '6px' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Risk : Reward Ratio</span>
                  <span style={{ fontWeight: 'bold', color: 'var(--accent)' }}>{styles[selectedStyle].risk_reward}</span>
                </div>
              </div>
            </div>

          </div>
        )}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '20px' }}>
        
        {/* Market Regime */}
        <div className="panel" style={{ gridColumn: 'span 2' }}>
          <h3 style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '15px' }}><Activity size={20} className="text-accent" /> Market Regime Analysis</h3>
          <div style={{ display: 'flex', gap: '20px', alignItems: 'center' }}>
            <div style={{ flex: 1, padding: '20px', background: '#0f172a', borderRadius: '8px', borderLeft: '4px solid var(--accent)' }}>
              <h2 style={{ margin: '0 0 10px 0', color: 'var(--accent)', textTransform: 'uppercase' }}>{regime.name || 'Unknown'}</h2>
              <p style={{ margin: 0, color: 'var(--text-secondary)', lineHeight: '1.6' }}>{regime.description || 'No regime description available.'}</p>
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '10px' }}>Allowed Strategy Families:</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
                {allowed_families.map(fam => (
                  <span key={fam} style={{ padding: '6px 12px', background: '#1e293b', border: '1px solid #334155', borderRadius: '4px', fontSize: '0.85rem' }}>
                    {fam.replace('_', ' ').toUpperCase()}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* AI Trade Setup */}
        <div className="panel" style={{ borderTop: '4px solid var(--accent)' }}>
          <h3 style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px' }}><Target size={20} className="text-accent" /> AI Trade Plan</h3>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingBottom: '10px', borderBottom: '1px solid #1e293b' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Suggested Action</span>
              <span style={{ fontWeight: 'bold', color: four_pillar_signal.final_signal === 'BUY' ? 'var(--signal-buy)' : four_pillar_signal.final_signal === 'SELL' ? 'var(--signal-sell)' : 'var(--text-primary)' }}>
                {four_pillar_signal.final_signal || 'WAIT'}
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingBottom: '10px', borderBottom: '1px solid #1e293b' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Entry Point</span>
              <span style={{ fontWeight: 'bold' }}>{four_pillar_signal.entry || '---'}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingBottom: '10px', borderBottom: '1px solid #1e293b' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Target (Take Profit)</span>
              <span style={{ fontWeight: 'bold', color: 'var(--signal-buy)' }}>{four_pillar_signal.target || '---'}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingBottom: '10px', borderBottom: '1px solid #1e293b' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Stop Loss</span>
              <span style={{ fontWeight: 'bold', color: 'var(--signal-sell)' }}>{four_pillar_signal.stoploss || '---'}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ color: 'var(--text-secondary)' }}>AI Confidence Score</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{ fontWeight: 'bold', color: 'var(--accent)' }}>{four_pillar_signal.confluence_score || 0}%</span>
              </div>
            </div>
          </div>
        </div>

        {/* Technical Consensus */}
        <div className="panel">
          <h3 style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px' }}><BarChart2 size={20} className="text-accent" /> Technical Consensus</h3>
          <div style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
            <div style={{ flex: 1, padding: '15px', background: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.2)', borderRadius: '8px', textAlign: 'center' }}>
              <div style={{ fontSize: '2rem', fontWeight: 'bold', color: 'var(--signal-buy)' }}>{consensus.bullish || 0}</div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>BULLISH</div>
            </div>
            <div style={{ flex: 1, padding: '15px', background: 'rgba(100, 116, 139, 0.1)', border: '1px solid rgba(100, 116, 139, 0.2)', borderRadius: '8px', textAlign: 'center' }}>
              <div style={{ fontSize: '2rem', fontWeight: 'bold', color: 'var(--text-secondary)' }}>{consensus.neutral || 0}</div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>NEUTRAL</div>
            </div>
            <div style={{ flex: 1, padding: '15px', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.2)', borderRadius: '8px', textAlign: 'center' }}>
              <div style={{ fontSize: '2rem', fontWeight: 'bold', color: 'var(--signal-sell)' }}>{consensus.bearish || 0}</div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>BEARISH</div>
            </div>
          </div>
          
          <div style={{ maxHeight: '180px', overflowY: 'auto', paddingRight: '10px' }}>
            {indicators.map((ind, i) => (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', paddingBottom: '8px', borderBottom: '1px solid #1e293b', fontSize: '0.85rem' }}>
                <span style={{ color: 'var(--text-secondary)' }}>{ind.name}</span>
                <span style={{ 
                  color: ind.signal === 'Bullish' ? 'var(--signal-buy)' : ind.signal === 'Bearish' ? 'var(--signal-sell)' : '#94a3b8',
                  fontWeight: '500'
                }}>
                  {ind.value !== null && typeof ind.value === 'number' ? ind.value.toFixed(2) : ind.value} ({ind.signal})
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Institutional & Sentiment */}
        <div className="panel">
          <h3 style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px' }}><Users size={20} className="text-accent" /> Institutional Activity</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Delivery Percentage</span>
              <span style={{ fontWeight: 'bold' }}>{institutions.delivery_pct || '---'}%</span>
            </div>
            <div style={{ width: '100%', height: '6px', background: '#1e293b', borderRadius: '3px', marginBottom: '5px' }}>
              <div style={{ width: `${Math.min(100, institutions.delivery_pct || 0)}%`, height: '100%', background: 'var(--accent)', borderRadius: '3px' }}></div>
            </div>
            
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '15px 0', borderTop: '1px solid #1e293b' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Overall Sentiment</span>
              <span style={{ 
                padding: '4px 12px', 
                background: institutions.sentiment === 'Bullish' ? 'rgba(16, 185, 129, 0.2)' : institutions.sentiment === 'Bearish' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(100, 116, 139, 0.2)',
                color: institutions.sentiment === 'Bullish' ? 'var(--signal-buy)' : institutions.sentiment === 'Bearish' ? 'var(--signal-sell)' : 'var(--text-secondary)',
                borderRadius: '12px',
                fontWeight: 'bold',
                textTransform: 'uppercase'
              }}>
                {institutions.sentiment || 'Neutral'}
              </span>
            </div>
            
            <div style={{ background: '#0f172a', padding: '15px', borderRadius: '8px' }}>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '5px' }}>AI Logic:</div>
              <div style={{ fontSize: '0.9rem', fontStyle: 'italic', color: '#cbd5e1' }}>
                "{four_pillar_signal.logic || 'Not enough data to form a strong logical conclusion.'}"
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
};

export default StockProfile;
