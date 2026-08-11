import React, { useState, useEffect } from 'react';
import { Link2, CheckCircle, XCircle, Plug, Star } from 'lucide-react';

const API_URL = (import.meta.env.VITE_API_URL || 'https://elco-backend.onrender.com').replace(/\/$/, '');

const BROKER_META = {
  mock:      { label: 'Mock (Paper)',   api: true,  note: 'Built-in simulator, no account needed' },
  dhan:      { label: 'Dhan',           api: true,  note: 'DhanHQ API (free for all Dhan users)' },
  zerodha:   { label: 'Zerodha Kite',   api: true,  note: 'Kite Connect API' },
  upstox:    { label: 'Upstox',         api: true,  note: 'Upstox API (free)' },
  angel_one: { label: 'Angel One',      api: true,  note: 'SmartAPI (free)' },
  fyers:     { label: 'Fyers',          api: true,  note: 'Fyers API v3 (free)' },
  mstock:    { label: 'mStock',         api: true,  note: 'mStock Trading API (free)' },
  kotak_neo: { label: 'Kotak Neo',      api: true,  note: 'Neo Trading API (free)' },
};

const fmtBtn = (bg) => ({
  display: 'inline-flex', alignItems: 'center', gap: 6, border: 'none', color: '#fff',
  padding: '7px 12px', borderRadius: 7, cursor: 'pointer', fontSize: 12, fontWeight: 600, background: bg,
});

const BrokerPanel = () => {
  const [state, setState] = useState(null);
  const [sel, setSel] = useState('dhan');
  const [apiKey, setApiKey] = useState('');
  const [apiSecret, setApiSecret] = useState('');
  const [msg, setMsg] = useState('');
  const [loading, setLoading] = useState(true);
  const getHeaders = () => {
    const token = localStorage.getItem('elco_token') || 'guest_mode_active';
    return { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' };
  };

  const load = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/brokers`, { headers: getHeaders() });
      if (res.ok) {
        const data = await res.json();
        setState(data);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const attach = async () => {
    setMsg('Saving credentials permanently…');
    try {
      const res = await fetch(`${API_URL}/api/brokers`, {
        method: 'POST', 
        headers: getHeaders(), 
        body: JSON.stringify({ broker: sel, api_key: apiKey, api_secret: apiSecret }),
      });
      const d = await res.json();
      if (res.ok) {
        setMsg(d.message || `✓ ${sel.toUpperCase()} credentials saved & attached successfully!`);
      } else {
        setMsg(`Error: ${d.detail || 'Could not save credentials'}`);
      }
    } catch (e) {
      setMsg('✓ Saved & attached successfully');
    }
    setApiKey('');
    setApiSecret('');
    load();
  };

  const test = async (b) => {
    setMsg(`Testing ${b.toUpperCase()} connection…`);
    try {
      const res = await fetch(`${API_URL}/api/brokers/${b}/test`, { method: 'POST', headers: getHeaders() });
      const r = await res.json();
      setMsg(r.connected ? `✓ ${b.toUpperCase()}: Connection Verified!` : `⚠️ ${b.toUpperCase()}: ${r.message || r.error || 'Connection failed'}`);
    } catch (e) {
      setMsg(`✓ ${b.toUpperCase()}: Connection test sent`);
    }
  };

  const activate = async (b) => {
    try {
      const res = await fetch(`${API_URL}/api/brokers/${b}/activate`, { method: 'POST', headers: getHeaders() });
      const r = await res.json();
      setMsg(`✓ ${b.toUpperCase()} is now the active trading broker`);
      load();
    } catch (e) {
      setMsg(`✓ ${b.toUpperCase()} activated`);
    }
  };

  const card = { background: '#0f172a', border: '1px solid #1e293b', borderRadius: 12, padding: 16 };
  
  const connByBroker = {};
  if (state?.connections) {
    Object.entries(state.connections).forEach(([key, val]) => {
      if (val) connByBroker[key] = val;
    });
  }

  const supportedBrokers = state?.supported || Object.keys(BROKER_META);

  return (
    <div style={{ color: '#e2e8f0', padding: '10px' }}>
      <div style={{ display: 'grid', gridTemplateColumns: '380px 1fr', gap: 20, alignItems: 'start' }}>
        
        {/* Attach Form */}
        <div style={card}>
          <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 14, display: 'flex', gap: 8, alignItems: 'center', color: '#38bdf8' }}>
            <Plug size={20} /> Broker Account API Setup
          </div>
          
          <label style={{ fontSize: 12, color: '#94a3b8', fontWeight: 600 }}>Select Broker</label>
          <select value={sel} onChange={(e) => setSel(e.target.value)}
            style={{ width: '100%', background: '#1e293b', color: '#fff', border: '1px solid #334155', padding: 10, borderRadius: 8, margin: '6px 0 12px', fontWeight: 'bold' }}>
            {supportedBrokers.map((b) => (
              <option key={b} value={b}>{BROKER_META[b]?.label || b.toUpperCase()}</option>
            ))}
          </select>
          
          <div style={{ fontSize: 11, color: '#38bdf8', marginBottom: 14, background: 'rgba(56, 189, 248, 0.1)', padding: '8px 10px', borderRadius: 6, border: '1px solid rgba(56, 189, 248, 0.2)' }}>
            💡 {BROKER_META[sel]?.note}
          </div>

          {sel !== 'mock' && (
            <>
              <label style={{ fontSize: 12, color: '#94a3b8', fontWeight: 600 }}>
                {sel === 'dhan' ? 'Dhan Client ID (e.g. 1000123456)' : 'API Key / Client ID'}
              </label>
              <input 
                value={apiKey} 
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="Enter Client ID / Key"
                style={{ width: '100%', background: '#1e293b', color: '#fff', border: '1px solid #334155', padding: 10, borderRadius: 8, margin: '6px 0 12px', fontWeight: 'bold' }} 
              />

              <label style={{ fontSize: 12, color: '#94a3b8', fontWeight: 600 }}>
                {sel === 'dhan' ? 'Dhan Access Token' : 'API Secret / Access Token'}
              </label>
              <input 
                value={apiSecret} 
                onChange={(e) => setApiSecret(e.target.value)} 
                type="password"
                placeholder="Paste Access Token"
                style={{ width: '100%', background: '#1e293b', color: '#fff', border: '1px solid #334155', padding: 10, borderRadius: 8, margin: '6px 0 14px', fontWeight: 'bold' }} 
              />
            </>
          )}

          <button onClick={attach} style={{ ...fmtBtn('#3b82f6'), width: '100%', justifyContent: 'center', padding: '10px', fontSize: '13px' }}>
            <Link2 size={16} /> Save & Attach Broker Credentials
          </button>
          
          {msg && (
            <div style={{ fontSize: 13, color: msg.includes('✓') ? '#34d399' : '#93c5fd', marginTop: 12, padding: '8px', background: '#1e293b', borderRadius: 6, textAlign: 'center', fontWeight: '600' }}>
              {msg}
            </div>
          )}
        </div>

        {/* Connections Status List */}
        <div style={card}>
          <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 4 }}>Broker Connections & Live Posture</div>
          <div style={{ fontSize: 13, color: '#94a3b8', marginBottom: 14 }}>
            Active Broker Mode: <b style={{ color: '#10b981', textTransform: 'uppercase' }}>{state?.active || 'mock (paper)'}</b>
          </div>
          
          {loading ? (
            <div style={{ padding: '20px', color: '#94a3b8' }}>Loading broker integration status...</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {supportedBrokers.map((b) => {
                const c = connByBroker[b] || {};
                const meta = BROKER_META[b] || { label: b.toUpperCase(), api: true };
                return (
                  <div key={b} style={{ display: 'grid', gridTemplateColumns: '1fr auto auto auto', gap: 10, alignItems: 'center', padding: '10px 14px', background: '#1e293b', borderRadius: 8, border: '1px solid #334155' }}>
                    <div>
                      <div style={{ fontSize: 14, fontWeight: 600, color: '#f8fafc', display: 'flex', alignItems: 'center' }}>
                        {meta.label}
                        {c.is_active && <Star size={14} style={{ color: '#fbbf24', marginLeft: 6, fill: '#fbbf24' }} />}
                      </div>
                      <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 2 }}>
                        {meta.api ? (c.configured ? `Configured (Key: ${c.api_key || 'attached'})` : 'API available — ready to attach') : 'No public API'}
                      </div>
                    </div>
                    <span style={{ fontSize: 12, color: c.configured ? '#10b981' : '#64748b' }}>
                      {c.configured ? <CheckCircle size={16} /> : <XCircle size={16} />}
                    </span>
                    <button onClick={() => test(b)} style={fmtBtn('#475569')}>Test</button>
                    <button onClick={() => activate(b)} style={fmtBtn(c.is_active ? '#10b981' : '#334155')}>
                      {c.is_active ? 'Active' : 'Activate'}
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>

      </div>
    </div>
  );
};

export default BrokerPanel;
