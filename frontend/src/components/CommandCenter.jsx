import React, { useState, useEffect } from 'react';
import {
  Play, Pause, TrendingUp, TrendingDown, Minus, Zap, RefreshCw, Activity,
} from 'lucide-react';

const API_URL = (import.meta.env.VITE_API_URL || 'https://elco-backend.onrender.com').replace(/\/$/, '');

const TYPE_LABELS = {
  scalping: 'Scalping', intraday: 'Intraday', swing: 'Swing', positional: 'Positional',
  options_buying: 'Options Buying', options_selling: 'Options Selling', futures: 'Futures',
  equity: 'Equity Delivery', commodity: 'Commodity', currency: 'Currency', etf: 'ETF',
  portfolio_strategy: 'Portfolio', basket_strategy: 'Basket', pair_trading: 'Pair Trading',
  hedging: 'Hedging',
};

const fmt = (v, d = 2) => (typeof v === 'number' && !isNaN(v) ? v.toFixed(d) : '—');
const verdictColor = (v) => {
  const s = (v || '').toLowerCase();
  if (s.includes('bull')) return '#10b981';
  if (s.includes('bear')) return '#ef4444';
  return '#94a3b8';
};

// Green (up) / red (down) probability bar
function DirectionBar({ direction }) {
  const up = direction?.up_pct ?? 50;
  const down = direction?.down_pct ?? 50;
  return (
    <div style={{ width: '100%' }}>
      <div style={{ display: 'flex', height: 14, borderRadius: 7, overflow: 'hidden', background: '#1e293b' }}>
        <div style={{ width: `${up}%`, background: '#10b981' }} />
        <div style={{ width: `${down}%`, background: '#ef4444' }} />
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginTop: 3 }}>
        <span style={{ color: '#10b981' }}>▲ {fmt(up, 1)}%</span>
        <span style={{ color: '#ef4444' }}>▼ {fmt(down, 1)}%</span>
      </div>
    </div>
  );
}

// Signed score bar for analysis breakdown (-1..+1)
function ScoreBar({ score }) {
  const s = Math.max(-1, Math.min(1, score || 0));
  const pct = Math.abs(s) * 50;
  return (
    <div style={{ display: 'flex', alignItems: 'center', height: 10, background: '#1e293b', borderRadius: 5, position: 'relative' }}>
      <div style={{ position: 'absolute', left: '50%', top: 0, bottom: 0, width: 1, background: '#475569' }} />
      <div style={{
        position: 'absolute', left: s >= 0 ? '50%' : `${50 - pct}%`,
        width: `${pct}%`, top: 0, bottom: 0,
        background: s >= 0 ? '#10b981' : '#ef4444', borderRadius: 5,
      }} />
    </div>
  );
}

const CommandCenter = ({ globalSymbol }) => {
  const [symbol, setSymbol] = useState('RELIANCE');

  useEffect(() => {
    if (globalSymbol) {
      const clean = globalSymbol.replace('.NS', '').replace('.BO', '');
      setSymbol(clean);
      setInput(clean);
      load(clean);
    }
  }, [globalSymbol]);
  const [input, setInput] = useState('RELIANCE');
  const [data, setData] = useState(null);
  const [pnl, setPnl] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState('');
  const token = localStorage.getItem('elco_token');
  const headers = (token && token.length > 20 && !token.includes('demo') && !token.includes('guest'))
    ? { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }
    : { 'Content-Type': 'application/json' };

  const load = async (sym) => {
    setLoading(true); setError(null);
    let attempts = 0;
    const maxAttempts = 4;
    while (attempts < maxAttempts) {
      try {
        const res = await fetch(`${API_URL}/api/command-center/${sym}`, { headers });
        if (res.ok) {
          const json = await res.json();
          setData(json);
          setError(null);
          setLoading(false);
          return;
        }
      } catch (e) {
        console.warn(`Command center fetch attempt ${attempts + 1} failed, retrying...`, e);
      }
      attempts++;
      if (attempts < maxAttempts) {
        await new Promise(r => setTimeout(r, 2000));
      }
    }
    setError("Live market server is starting up. Please click Analyze / Refresh in a few seconds.");
    setLoading(false);
  };

  const loadPnl = async () => {
    try {
      const res = await fetch(`${API_URL}/portfolio`, { headers });
      if (res.ok) setPnl(await res.json());
    } catch { /* ignore */ }
  };

  useEffect(() => { load(symbol); loadPnl(); /* eslint-disable-next-line */ }, [symbol]);

  const analyze = () => { const s = input.trim().toUpperCase(); if (s) setSymbol(s); };

  const setMode = async (mode) => {
    setBusy('mode');
    try {
      await fetch(`${API_URL}/api/mode`, { method: 'POST', headers, body: JSON.stringify({ mode }) });
      await load(symbol);
    } finally { setBusy(''); }
  };

  const autoExecute = async () => {
    setBusy('exec');
    try {
      const res = await fetch(`${API_URL}/api/auto/execute/${symbol}`, { method: 'POST', headers });
      const r = await res.json();
      alert(r.executed ? `Trade placed: ${r.action}` : `Not executed: ${r.reason}`);
      await loadPnl();
    } finally { setBusy(''); }
  };

  const manage = async () => {
    setBusy('manage');
    try {
      const res = await fetch(`${API_URL}/api/auto/manage`, { method: 'POST', headers });
      const r = await res.json();
      alert(`Exits: ${r.exits?.length || 0} | Open: ${r.open_positions}`);
      await loadPnl();
    } finally { setBusy(''); }
  };

  const mode = data?.mode || 'off';
  const best = data?.best_setup || {};
  const verdicts = data?.trading_type_verdicts || {};
  const breakdown = data?.analysis_breakdown || {};
  const plan = data?.trade_plan;

  const card = { background: '#0f172a', border: '1px solid #1e293b', borderRadius: 12, padding: 16 };

  return (
    <div style={{ color: '#e2e8f0' }}>
      {/* Header controls */}
      <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 16, flexWrap: 'wrap' }}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && analyze()}
          placeholder="Symbol e.g. RELIANCE"
          style={{ background: '#1e293b', border: '1px solid #334155', color: '#fff', padding: '10px 14px', borderRadius: 8, fontSize: 14 }}
        />
        <button onClick={analyze} style={{ ...btn, background: '#3b82f6' }}><Activity size={16} /> Analyze</button>
        <button onClick={() => { load(symbol); loadPnl(); }} style={{ ...btn, background: '#475569' }} disabled={loading}>
          <RefreshCw size={16} className={loading ? 'spin' : ''} /> Refresh
        </button>

        {/* Auto / Manual toggle */}
        <div style={{ display: 'flex', gap: 6, marginLeft: 'auto', alignItems: 'center' }}>
          <span style={{ fontSize: 13, color: '#94a3b8' }}>Mode:</span>
          <button onClick={() => setMode('off')} disabled={busy === 'mode'}
            style={{ ...btn, background: mode === 'off' ? '#f59e0b' : '#1e293b' }}>
            <Pause size={15} /> Manual
          </button>
          <button onClick={() => setMode('active')} disabled={busy === 'mode'}
            style={{ ...btn, background: mode === 'active' ? '#10b981' : '#1e293b' }}>
            <Play size={15} /> Auto
          </button>
          {mode === 'halted' && <span style={{ color: '#ef4444', fontWeight: 700 }}>⚠ HALTED</span>}
        </div>
      </div>

      {error && <div style={{ ...card, borderColor: '#ef4444', color: '#fca5a5', marginBottom: 16 }}>Error: {error}</div>}
      {loading && !data && <div style={card}>Loading command center…</div>}

      {data && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 340px', gap: 16, alignItems: 'start' }}>
          {/* LEFT COLUMN: best setup + trade plan + pnl */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div style={card}>
              <div style={{ fontSize: 13, color: '#94a3b8', marginBottom: 8 }}>BEST SETUP · {data.symbol}</div>
              <div style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>
                {TYPE_LABELS[best.trading_type] || best.trading_type || '—'}
              </div>
              <div style={{ fontSize: 15, marginBottom: 10, color: verdictColor(best.action) }}>
                {best.action || 'NEUTRAL'} · conviction {fmt(best.conviction_pct, 1)}%
              </div>
              <DirectionBar direction={best.direction} />
              {best.auto_tradeable && mode === 'active' && (
                <button onClick={autoExecute} disabled={busy === 'exec'}
                  style={{ ...btn, background: '#10b981', width: '100%', marginTop: 12, justifyContent: 'center' }}>
                  <Zap size={16} /> Auto-Execute Best Setup
                </button>
              )}
            </div>

            {plan && (
              <div style={card}>
                <div style={{ fontSize: 13, color: '#94a3b8', marginBottom: 8 }}>TRADE PLAN</div>
                <Row label="Composite" value={plan.composite_action} />
                <Row label="Entry" value={fmt(plan.entry)} />
                <Row label="Stop Loss" value={fmt(plan.stop_loss)} color="#ef4444" />
                <Row label="Target 1" value={fmt(plan.target_1)} color="#10b981" />
                <Row label="Target 2" value={fmt(plan.target_2)} color="#10b981" />
              </div>
            )}

            <div style={card}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <span style={{ fontSize: 13, color: '#94a3b8' }}>LIVE P&L</span>
                <button onClick={manage} disabled={busy === 'manage'} style={{ ...btn, background: '#475569', padding: '4px 10px', fontSize: 12 }}>
                  Manage
                </button>
              </div>
              <Row label="Realized" value={pnl ? fmt(pnl.realized_pnl) : '—'} color={pnl?.realized_pnl >= 0 ? '#10b981' : '#ef4444'} />
              <Row label="Unrealized" value={pnl ? fmt(pnl.unrealized_pnl) : '—'} color={pnl?.unrealized_pnl >= 0 ? '#10b981' : '#ef4444'} />
              <Row label="Total" value={pnl ? fmt(pnl.total_pnl) : '—'} color={pnl?.total_pnl >= 0 ? '#10b981' : '#ef4444'} />
            </div>
          </div>

          {/* MIDDLE COLUMN: trading type verdicts */}
          <div style={card}>
            <div style={{ fontSize: 13, color: '#94a3b8', marginBottom: 12 }}>VERDICT · EVERY TRADING TYPE</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {Object.entries(verdicts).map(([key, v]) => (
                <div key={key} style={{ display: 'grid', gridTemplateColumns: '110px 70px 1fr', gap: 8, alignItems: 'center' }}>
                  <span style={{ fontSize: 13 }}>{TYPE_LABELS[key] || key}</span>
                  <span style={{ fontSize: 12, fontWeight: 700, color: verdictColor(v.verdict) }}>
                    {v.verdict?.includes('ull') ? <TrendingUp size={12} /> : v.verdict?.includes('ear') ? <TrendingDown size={12} /> : <Minus size={12} />}
                    {' '}{v.verdict}
                  </span>
                  <DirectionBar direction={v.direction} />
                </div>
              ))}
            </div>
          </div>

          {/* RIGHT COLUMN: analysis breakdown */}
          <div style={{ ...card, maxHeight: 620, overflowY: 'auto' }}>
            <div style={{ fontSize: 13, color: '#94a3b8', marginBottom: 12 }}>
              ANALYSIS BREAKDOWN · {Object.keys(breakdown).length}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {Object.entries(breakdown).map(([name, d]) => (
                <div key={name}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 3 }}>
                    <span style={{ textTransform: 'capitalize' }}>{name.replace(/_/g, ' ')}</span>
                    <span style={{ color: (d.score || 0) >= 0 ? '#10b981' : '#ef4444' }}>
                      {(d.score || 0) >= 0 ? '+' : ''}{fmt(d.score)} · {fmt((d.confidence || 0) * 100, 0)}%
                    </span>
                  </div>
                  <ScoreBar score={d.score} />
                  {d.reasons?.[0] && (
                    <div style={{ fontSize: 11, color: '#64748b', marginTop: 3 }}>{d.reasons[0]}</div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {data?.disclaimer && (
        <div style={{ fontSize: 11, color: '#64748b', marginTop: 16, fontStyle: 'italic' }}>{data.disclaimer}</div>
      )}
    </div>
  );
};

const btn = {
  display: 'inline-flex', alignItems: 'center', gap: 6, border: 'none', color: '#fff',
  padding: '9px 14px', borderRadius: 8, cursor: 'pointer', fontSize: 13, fontWeight: 600,
};

const Row = ({ label, value, color }) => (
  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0', fontSize: 13 }}>
    <span style={{ color: '#94a3b8' }}>{label}</span>
    <span style={{ color: color || '#e2e8f0', fontWeight: 600 }}>{value}</span>
  </div>
);

export default CommandCenter;
