import React, { useState, useEffect } from 'react';
import { BellRing, Plus, Trash2 } from 'lucide-react';

const API_URL = (import.meta.env.VITE_API_URL || 'https://elco-backend.onrender.com').replace(/\/$/, '');

const AlertsPanel = ({ symbol, currentPrice, token }) => {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [condition, setCondition] = useState('above');
  const [price, setPrice] = useState(currentPrice || 0);

  const fetchAlerts = async () => {
    try {
      const res = await fetch(`${API_URL}/api/alerts`);
      if (res.ok) {
        const data = await res.json();
        setAlerts(data.alerts.filter(a => a.symbol === symbol));
      }
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchAlerts();
    if (currentPrice && !price) setPrice(currentPrice);
  }, [symbol]);

  const addAlert = async () => {
    if (!price) return;
    setLoading(true);
    try {
      await fetch(`${API_URL}/api/alerts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol, condition, price: parseFloat(price) })
      });
      fetchAlerts();
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  const removeAlert = async (id) => {
    try {
      await fetch(`${API_URL}/api/alerts/${id}`, { method: 'DELETE' });
      fetchAlerts();
    } catch (e) {
      console.error(e);
    }
  };

  const st = {
    panel: { background: '#0d1117', borderTop: '1px solid #1e222d', padding: '12px 16px', color: '#fff' },
    header: { display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', fontWeight: 800, marginBottom: '10px' },
    form: { display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '16px' },
    select: { background: '#131722', color: '#b0b8c8', border: '1px solid #1e222d', padding: '6px', borderRadius: '4px', fontSize: '11px', outline: 'none' },
    input: { background: '#131722', color: '#fff', border: '1px solid #1e222d', padding: '6px', borderRadius: '4px', fontSize: '12px', outline: 'none', width: '80px' },
    btn: { background: '#2962ff', color: '#fff', border: 'none', padding: '6px 12px', borderRadius: '4px', cursor: 'pointer', fontSize: '11px', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '4px' },
    list: { display: 'flex', flexDirection: 'column', gap: '6px' },
    item: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#131722', padding: '8px 12px', borderRadius: '4px', fontSize: '11px', borderLeft: '2px solid #2962ff' },
    delBtn: { background: 'transparent', border: 'none', color: '#ff1744', cursor: 'pointer', padding: '4px' }
  };

  return (
    <div style={st.panel}>
      <div style={st.header}>
        <BellRing size={14} color="#2962ff" />
        Price Alerts for {symbol}
      </div>

      <div style={st.form}>
        <span style={{ fontSize: '11px', color: '#787b86' }}>If price goes</span>
        <select style={st.select} value={condition} onChange={e => setCondition(e.target.value)}>
          <option value="above">Above</option>
          <option value="below">Below</option>
        </select>
        <input style={st.input} type="number" value={price} onChange={e => setPrice(e.target.value)} step="0.05" />
        <button style={st.btn} onClick={addAlert} disabled={loading}>
          <Plus size={12} /> Add
        </button>
      </div>

      <div style={st.list}>
        {alerts.length === 0 && <span style={{ fontSize: '10px', color: '#565d6e' }}>No active alerts.</span>}
        {alerts.map(a => (
          <div key={a.id} style={st.item}>
            <span>
              <span style={{ color: '#787b86' }}>If</span> {a.symbol} <span style={{ color: a.condition === 'above' ? '#00e676' : '#ff1744' }}>{a.condition}</span> ₹{a.price.toFixed(2)}
            </span>
            <button style={st.delBtn} onClick={() => removeAlert(a.id)}>
              <Trash2 size={12} />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};

export default AlertsPanel;
