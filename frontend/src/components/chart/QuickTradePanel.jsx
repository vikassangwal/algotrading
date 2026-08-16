import React, { useState } from 'react';

const API_URL = (import.meta.env.VITE_API_URL || 'https://elco-backend.onrender.com').replace(/\/$/, '');

const QuickTradePanel = ({ symbol, currentPrice, token, atr }) => {
  const [qty, setQty] = useState(1);
  const [orderType, setOrderType] = useState('MARKET');
  const [msg, setMsg] = useState('');
  const [loading, setLoading] = useState(false);

  const placeTrade = async (action) => {
    setLoading(true);
    setMsg('');
    try {
      const headers = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;
      const res = await fetch(`${API_URL}/api/orders`, {
        method: 'POST', headers,
        body: JSON.stringify({ symbol: symbol.toUpperCase().replace('.NS', ''), action, qty: parseInt(qty), type: orderType })
      });
      const data = await res.json();
      setMsg(data.message || data.detail || 'Order placed');
    } catch (e) {
      setMsg('Error: ' + e.message);
    }
    setLoading(false);
    setTimeout(() => setMsg(''), 5000);
  };

  const riskAmt = (atr ? (atr * qty) : (currentPrice * qty * 0.01)).toFixed(2);
  const posValue = (currentPrice * qty).toFixed(2);

  const s = {
    panel: {
      display: 'flex', alignItems: 'center', gap: '10px', padding: '8px 14px',
      background: '#0d1117', borderTop: '1px solid #1e222d', fontSize: '11px',
      flexWrap: 'wrap',
    },
    label: { color: '#565d6e', fontSize: '10px', fontWeight: 700, textTransform: 'uppercase' },
    input: {
      background: '#131722', color: '#fff', border: '1px solid #1e222d', padding: '5px 8px',
      borderRadius: '5px', width: '60px', fontSize: '12px', fontWeight: 700, textAlign: 'center', outline: 'none',
    },
    select: {
      background: '#131722', color: '#b0b8c8', border: '1px solid #1e222d', padding: '5px 8px',
      borderRadius: '5px', fontSize: '11px', outline: 'none', cursor: 'pointer',
    },
    buyBtn: {
      background: 'linear-gradient(135deg, #00c853, #00e676)', color: '#000', border: 'none',
      padding: '7px 20px', borderRadius: '6px', fontSize: '12px', fontWeight: 800,
      cursor: 'pointer', transition: '0.15s', letterSpacing: '0.5px',
    },
    sellBtn: {
      background: 'linear-gradient(135deg, #d50000, #ff1744)', color: '#fff', border: 'none',
      padding: '7px 20px', borderRadius: '6px', fontSize: '12px', fontWeight: 800,
      cursor: 'pointer', transition: '0.15s', letterSpacing: '0.5px',
    },
    info: { color: '#565d6e', fontSize: '10px', fontFamily: 'monospace' },
    msg: { fontSize: '11px', fontWeight: 600, padding: '2px 8px', borderRadius: '4px' },
  };

  return (
    <div style={s.panel}>
      <span style={{ color: '#fff', fontWeight: 800, fontSize: '12px' }}>
        {symbol?.toUpperCase().replace('.NS', '')}
      </span>
      <span style={{ color: '#787b86', fontFamily: 'monospace', fontWeight: 700 }}>
        ₹{currentPrice?.toFixed(2)}
      </span>

      <div style={{ width: '1px', height: '20px', background: '#1e222d' }} />

      <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
        <span style={s.label}>Qty</span>
        <input type="number" value={qty} onChange={e => setQty(Math.max(1, e.target.value))} style={s.input} min={1} />
      </div>

      <select value={orderType} onChange={e => setOrderType(e.target.value)} style={s.select}>
        <option value="MARKET">MARKET</option>
        <option value="LIMIT">LIMIT</option>
        <option value="SL">SL</option>
      </select>

      <button style={s.buyBtn} onClick={() => placeTrade('BUY')} disabled={loading}
        onMouseEnter={e => e.target.style.transform = 'scale(1.05)'}
        onMouseLeave={e => e.target.style.transform = 'scale(1)'}>
        {loading ? '...' : '📈 BUY'}
      </button>
      <button style={s.sellBtn} onClick={() => placeTrade('SELL')} disabled={loading}
        onMouseEnter={e => e.target.style.transform = 'scale(1.05)'}
        onMouseLeave={e => e.target.style.transform = 'scale(1)'}>
        {loading ? '...' : '📉 SELL'}
      </button>

      <div style={{ width: '1px', height: '20px', background: '#1e222d' }} />

      <span style={s.info}>Val: ₹{posValue}</span>
      <span style={s.info}>Risk (ATR): ₹{riskAmt}</span>

      {msg && (
        <span style={{
          ...s.msg,
          background: msg.includes('Error') ? '#ff174422' : '#00e67622',
          color: msg.includes('Error') ? '#ff1744' : '#00e676',
        }}>{msg}</span>
      )}
    </div>
  );
};

export default QuickTradePanel;
