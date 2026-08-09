import React, { useState, useEffect } from 'react';
import { Link2, CheckCircle, XCircle, Plug, Star } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || '';

// Which brokers actually expose a public trading API today (honest labels).
const BROKER_META = {
  mock:      { label: 'Mock (Paper)',   api: true,  note: 'Built-in simulator, no account needed' },
  zerodha:   { label: 'Zerodha Kite',   api: true,  note: 'Kite Connect API (paid)' },
  upstox:    { label: 'Upstox',         api: true,  note: 'Upstox API (free)' },
  angel_one: { label: 'Angel One',      api: true,  note: 'SmartAPI (free)' },
  fyers:     { label: 'Fyers',          api: true,  note: 'Fyers API v3 (free)' },
  dhan:      { label: 'Dhan',           api: true,  note: 'DhanHQ API (free)' },
  mstock:    { label: 'mStock',         api: true,  note: 'mStock Trading API (free)' },
  kotak_neo: { label: 'Kotak Neo',      api: true,  note: 'Neo Trading API (free)' },
};

const fmtBtn = (bg) => ({
  display: 'inline-flex', alignItems: 'center', gap: 6, border: 'none', color: '#fff',
  padding: '7px 12px', borderRadius: 7, cursor: 'pointer', fontSize: 12, fontWeight: 600, background: bg,
});

const BrokerPanel = () => {
  const [state, setState] = useState(null);
  const [sel, setSel] = useState('mock');
  const [apiKey, setApiKey] = useState('');
  const [apiSecret, setApiSecret] = useState('');
  const [msg, setMsg] = useState('');
  const [loading, setLoading] = useState(true);
  const token = localStorage.getItem('elco_token');
  const headers = { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' };

  const load = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/brokers`, { headers });
      if (res.ok) setState(await res.json());
    } catch (e) { setMsg('Failed to load brokers'); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); /* eslint-disable-next-line */ }, []);

  const attach = async () => {
    setMsg('Saving…');
    const res = await fetch(`${API_URL}/api/brokers`, {
      method: 'POST', headers, body: JSON.stringify({ broker: sel, api_key: apiKey, api_secret: apiSecret }),
    });
    setMsg(res.ok ? `Attached ${sel}` : 'Save failed');
    setApiKey(''); setApiSecret(''); load();
  };

  const test = async (b) => {
    setMsg(`Testing ${b}…`);
    const res = await fetch(`${API_URL}/api/brokers/${b}/test`, { method: 'POST', headers });
    const r = await res.json();
    setMsg(r.connected ? `${b}: connected ✓` : `${b}: not connected — ${r.error || 'check keys'}`);
  };

  const activate = async (b) => {
    const res = await fetch(`${API_URL}/api/brokers/${b}/activate`, { method: 'POST', headers });
    setMsg(res.ok ? `${b} is now active` : 'Activate failed');
    load();
  };

  const card = { background: '#0f172a', border: '1px solid #1e293b', borderRadius: 12, padding: 16 };
  const connByBroker = {};
  Object.values(state?.connections || {}).forEach((c) => { connByBroker[c.broker] = c; });

  return (
    <div style={{ color: '#e2e8f0' }}>
      <div style={{ display: 'grid', gridTemplateColumns: '360px 1fr', gap: 16, alignItems: 'start' }}>
        {/* Attach form */}
        <div style={card}>
          <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 12, display: 'flex', gap: 8, alignItems: 'center' }}>
            <Plug size={18} /> Attach Broker
          </div>
          <label style={{ fontSize: 12, color: '#94a3b8' }}>Broker</label>
          <select value={sel} onChange={(e) => setSel(e.target.value)}
            style={{ width: '100%', background: '#1e293b', color: '#fff', border: '1px solid #334155', padding: 9, borderRadius: 8, margin: '4px 0 12px' }}>
            {(state?.supported || Object.keys(BROKER_META)).map((b) => (
              <option key={b} value={b}>{BROKER_META[b]?.label || b}</option>
            ))}
          </select>
          <div style={{ fontSize: 11, color: '#64748b', marginBottom: 12 }}>{BROKER_META[sel]?.note}</div>

          {sel !== 'mock' && (
            <>
              <label style={{ fontSize: 12, color: '#94a3b8' }}>API Key</label>
              <input value={apiKey} onChange={(e) => setApiKey(e.target.value)}
                style={{ width: '100%', background: '#1e293b', color: '#fff', border: '1px solid #334155', padding: 9, borderRadius: 8, margin: '4px 0 10px' }} />
              <label style={{ fontSize: 12, color: '#94a3b8' }}>API Secret / Access Token</label>
              <input value={apiSecret} onChange={(e) => setApiSecret(e.target.value)} type="password"
                style={{ width: '100%', background: '#1e293b', color: '#fff', border: '1px solid #334155', padding: 9, borderRadius: 8, margin: '4px 0 12px' }} />
            </>
          )}
          <button onClick={attach} style={{ ...fmtBtn('#3b82f6'), width: '100%', justifyContent: 'center' }}>
            <Link2 size={15} /> Attach / Save
          </button>
          {msg && <div style={{ fontSize: 12, color: '#93c5fd', marginTop: 10 }}>{msg}</div>}
        </div>

        {/* Connections list */}
        <div style={card}>
          <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 4 }}>Brokers</div>
          <div style={{ fontSize: 12, color: '#94a3b8', marginBottom: 12 }}>
            Active: <b style={{ color: '#10b981' }}>{state?.active || 'mock'}</b>
          </div>
          {loading ? <div>Loading…</div> : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {(state?.supported || []).map((b) => {
                const c = connByBroker[b] || {};
                const meta = BROKER_META[b] || { label: b, api: true };
                return (
                  <div key={b} style={{ display: 'grid', gridTemplateColumns: '1fr auto auto auto', gap: 8, alignItems: 'center', padding: '8px 10px', background: '#1e293b', borderRadius: 8 }}>
                    <div>
                      <div style={{ fontSize: 13, fontWeight: 600 }}>
                        {meta.label}
                        {c.is_active && <Star size={13} style={{ color: '#fbbf24', marginLeft: 6 }} />}
                      </div>
                      <div style={{ fontSize: 11, color: '#64748b' }}>
                        {meta.api ? (c.configured ? `key ${c.api_key || ''}` : 'API available — not attached') : 'No public API'}
                      </div>
                    </div>
                    <span style={{ fontSize: 11, color: c.configured ? '#10b981' : '#64748b' }}>
                      {c.configured ? <CheckCircle size={14} /> : <XCircle size={14} />}
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
