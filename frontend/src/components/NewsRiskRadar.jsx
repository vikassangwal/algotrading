import React, { useState, useEffect } from 'react';
import { 
  Activity, AlertTriangle, TrendingUp, TrendingDown, 
  Globe, Clock, ShieldAlert, BarChart2 
} from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || '';

const NewsRiskRadar = ({ token }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch(`${API_URL}/api/risk/radar`, {
          headers: token ? { 'Authorization': `Bearer ${token}` } : {}
        });
        if (res.ok) {
          setData(await res.json());
        }
      } catch (err) {
        console.error(err);
      }
      setLoading(false);
    };

    fetchData();
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, [token]);

  if (loading || !data) {
    return <div style={{ padding: '24px', color: '#94a3b8' }}>Scanning Global Markets...</div>;
  }

  const { systemic_risk_score, threat_level, vix_simulated, news } = data;

  let threatColor = '#10b981'; // NORMAL
  let bgAlert = 'rgba(16, 185, 129, 0.1)';
  if (threat_level === 'CRITICAL RISK') {
    threatColor = '#ef4444';
    bgAlert = 'rgba(239, 68, 68, 0.1)';
  } else if (threat_level === 'ELEVATED') {
    threatColor = '#f59e0b';
    bgAlert = 'rgba(245, 158, 11, 0.1)';
  }

  return (
    <div style={{ fontFamily: 'system-ui, -apple-system, sans-serif', padding: '24px', backgroundColor: '#0f172a', minHeight: '100vh', color: '#f8fafc' }}>
      
      {/* Header */}
      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ fontSize: '24px', fontWeight: 'bold', margin: '0 0 8px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Activity size={28} color="#ef4444" />
          News & Macro Risk Radar
        </h1>
        <p style={{ margin: 0, color: '#94a3b8' }}>Real-time event scanning, sentiment analysis, and portfolio shock alerts.</p>
      </div>

      {/* Top Metrics */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '16px', marginBottom: '24px' }}>
        <div style={{ backgroundColor: '#1e293b', padding: '20px', borderRadius: '12px', border: '1px solid #334155', display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{ padding: '12px', backgroundColor: bgAlert, borderRadius: '50%' }}>
            <AlertTriangle size={24} color={threatColor} />
          </div>
          <div>
            <div style={{ color: '#94a3b8', fontSize: '14px', marginBottom: '4px' }}>Systemic Risk Level</div>
            <div style={{ fontSize: '24px', fontWeight: 'bold', color: threatColor }}>
              {threat_level} ({systemic_risk_score}%)
            </div>
          </div>
        </div>

        <div style={{ backgroundColor: '#1e293b', padding: '20px', borderRadius: '12px', border: '1px solid #334155', display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{ padding: '12px', backgroundColor: 'rgba(59, 130, 246, 0.1)', borderRadius: '50%' }}>
            <Globe size={24} color="#3b82f6" />
          </div>
          <div>
            <div style={{ color: '#94a3b8', fontSize: '14px', marginBottom: '4px' }}>Implied VIX (Simulated)</div>
            <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#3b82f6' }}>{vix_simulated.toFixed(2)}</div>
          </div>
        </div>

        <div style={{ backgroundColor: '#1e293b', padding: '20px', borderRadius: '12px', border: '1px solid #334155', display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{ padding: '12px', backgroundColor: 'rgba(245, 158, 11, 0.1)', borderRadius: '50%' }}>
            <ShieldAlert size={24} color="#f59e0b" />
          </div>
          <div>
            <div style={{ color: '#94a3b8', fontSize: '14px', marginBottom: '4px' }}>Portfolio Value at Risk (VaR)</div>
            <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#f59e0b' }}>₹ {(systemic_risk_score * 1250).toLocaleString()}</div>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '24px' }}>
        {/* Live News Feed */}
        <div style={{ backgroundColor: '#1e293b', borderRadius: '12px', border: '1px solid #334155', padding: '20px' }}>
          <h2 style={{ fontSize: '18px', margin: '0 0 20px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Clock size={20} color="#94a3b8" /> Live Event Feed
          </h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {news.map((item, idx) => (
              <div key={idx} style={{ 
                padding: '16px', backgroundColor: '#0f172a', borderRadius: '8px',
                borderLeft: `3px solid ${
                  item.status === 'BEARISH' ? '#ef4444' : '#10b981'
                }`
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                  <h3 style={{ margin: 0, fontSize: '16px', fontWeight: '600', color: '#f8fafc' }}>{item.headline}</h3>
                </div>
                <div style={{ display: 'flex', gap: '16px', alignItems: 'center', fontSize: '13px' }}>
                  <span style={{ color: '#94a3b8' }}>VADER Compound: <span style={{ color: '#cbd5e1' }}>{item.compound}</span></span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: item.status === 'BULLISH' ? '#10b981' : '#ef4444' }}>
                    {item.status === 'BULLISH' ? <TrendingUp size={14} /> : <TrendingDown size={14} />} 
                    {item.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Action Panel */}
        <div style={{ backgroundColor: '#1e293b', borderRadius: '12px', border: '1px solid #334155', padding: '20px' }}>
          <h2 style={{ fontSize: '18px', margin: '0 0 20px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <BarChart2 size={20} color="#94a3b8" /> Automated Defense
          </h2>
          
          <div style={{ marginTop: '30px', padding: '16px', backgroundColor: bgAlert, border: `1px solid ${threatColor}`, borderRadius: '8px' }}>
            <h4 style={{ margin: '0 0 8px 0', color: threatColor, fontSize: '14px' }}>
              {threat_level === 'CRITICAL RISK' ? '🚨 Crash Warning Triggered' : 
               threat_level === 'ELEVATED' ? '⚠️ Elevated Risk Detected' : '✅ No Active Threats'}
            </h4>
            <p style={{ margin: 0, fontSize: '13px', color: '#cbd5e1', lineHeight: '1.5' }}>
              {threat_level === 'CRITICAL RISK' ? 'System recommends closing all open leveraged long positions and deploying NIFTY Out-of-the-Money Put spreads as a tail-risk hedge.' : 
               threat_level === 'ELEVATED' ? 'System recommends tightening stop-losses on momentum plays.' : 'Market structure remains stable. Alpha generation algorithms operating normally.'}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default NewsRiskRadar;
