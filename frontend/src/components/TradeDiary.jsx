import React, { useState, useEffect } from 'react';
import { BrainCircuit, AlertTriangle, CheckCircle, Target, Activity } from 'lucide-react';
import { RadialBarChart, RadialBar, PolarAngleAxis, ResponsiveContainer, Tooltip } from 'recharts';

const API_URL = (import.meta.env.VITE_API_URL || 'https://elco-backend.onrender.com').replace(/\/$/, '');

const CircleProgress = ({ value, label, color }) => {
  const data = [{ name: label, value: value, fill: color }];
  
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
      <div style={{ width: '120px', height: '120px' }}>
        <ResponsiveContainer width="100%" height="100%">
          <RadialBarChart 
            cx="50%" cy="50%" innerRadius="70%" outerRadius="100%" 
            barSize={10} data={data} startAngle={90} endAngle={-270}
          >
            <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
            <RadialBar minAngle={15} background={{ fill: '#374151' }} clockWise={true} dataKey="value" cornerRadius={5} />
            <text x="50%" y="50%" textAnchor="middle" dominantBaseline="middle" className="progress-label" fill="#fff" fontSize="24px" fontWeight="bold">
              {value}%
            </text>
          </RadialBarChart>
        </ResponsiveContainer>
      </div>
      <span style={{ color: '#9ca3af', fontSize: '14px', marginTop: '8px', fontWeight: '500' }}>{label}</span>
    </div>
  );
};

const TradeDiary = ({ token }) => {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const res = await fetch(`${API_URL}/api/psychology/metrics`, {
          headers: token ? { 'Authorization': `Bearer ${token}` } : {}
        });
        if (res.ok) {
          setMetrics(await res.json());
        }
      } catch (err) {
        console.error(err);
      }
      setLoading(false);
    };

    fetchMetrics();
    const interval = setInterval(fetchMetrics, 15000); // refresh every 15s to simulate live coaching
    return () => clearInterval(interval);
  }, [token]);

  if (loading || !metrics) {
    return <div style={{ padding: '24px', color: '#94a3b8' }}>Analyzing Trading Psychology...</div>;
  }

  const { 
    discipline_score, fomo_index, revenge_probability, ai_coaching, recent_tilt_events,
    mistake_analysis = [], win_loss_strategy = [], best_setup = "N/A"
  } = metrics;

  return (
    <div style={{ fontFamily: 'system-ui, -apple-system, sans-serif', padding: '24px', backgroundColor: '#0f172a', minHeight: '100vh', color: '#f8fafc' }}>
      
      {/* Header */}
      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ fontSize: '24px', fontWeight: 'bold', margin: '0 0 8px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <BrainCircuit size={28} color="#06b6d4" />
          AI Trading Psychology & Discipline
        </h1>
        <p style={{ margin: 0, color: '#94a3b8' }}>Real-time cognitive analysis of your trading behavior to prevent emotional leaks.</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '24px', marginBottom: '24px' }}>
        
        {/* Core Metrics Gauges */}
        <div style={{ backgroundColor: '#1e293b', borderRadius: '12px', border: '1px solid #334155', padding: '24px' }}>
          <h2 style={{ fontSize: '18px', margin: '0 0 24px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Target size={20} color="#94a3b8" /> Behavioral Metrics
          </h2>
          
          <div style={{ display: 'flex', justifyContent: 'space-around', flexWrap: 'wrap', gap: '20px' }}>
            <CircleProgress 
              value={discipline_score} 
              label="Discipline" 
              color={discipline_score >= 80 ? '#10b981' : discipline_score >= 50 ? '#f59e0b' : '#ef4444'} 
            />
            <CircleProgress 
              value={fomo_index} 
              label="FOMO Index" 
              color={fomo_index <= 30 ? '#10b981' : fomo_index <= 60 ? '#f59e0b' : '#ef4444'} 
            />
            <CircleProgress 
              value={revenge_probability} 
              label="Revenge Risk" 
              color={revenge_probability <= 20 ? '#10b981' : revenge_probability <= 50 ? '#f59e0b' : '#ef4444'} 
            />
          </div>
        </div>

        {/* Tilt Events */}
        <div style={{ backgroundColor: '#1e293b', borderRadius: '12px', border: '1px solid #334155', padding: '24px', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', textAlign: 'center' }}>
          <Activity size={48} color={recent_tilt_events > 0 ? '#ef4444' : '#10b981'} style={{ marginBottom: '16px' }} />
          <div style={{ fontSize: '48px', fontWeight: 'bold', color: recent_tilt_events > 0 ? '#ef4444' : '#10b981', lineHeight: '1' }}>
            {recent_tilt_events}
          </div>
          <div style={{ color: '#94a3b8', fontSize: '16px', marginTop: '8px' }}>Detected Tilt Events Today</div>
          <p style={{ fontSize: '13px', color: '#64748b', marginTop: '16px', maxWidth: '250px' }}>
            Tilt events include moving stop losses, doubling down on losers, and breaking daily max loss limits.
          </p>
        </div>

      </div>

      {/* Trade Analytics: Mistakes & Strategy Performance */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '24px', marginBottom: '24px' }}>
        
        {/* Mistake Analysis */}
        <div style={{ backgroundColor: '#1e293b', borderRadius: '12px', border: '1px solid #334155', padding: '24px' }}>
          <h2 style={{ fontSize: '18px', margin: '0 0 20px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <AlertTriangle size={20} color="#f59e0b" /> Mistake Analysis
          </h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {mistake_analysis.map((mistake, idx) => (
              <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingBottom: '8px', borderBottom: '1px solid #334155' }}>
                <span style={{ color: '#f8fafc', fontSize: '14px' }}>{mistake.name}</span>
                <span style={{ color: '#ef4444', fontWeight: 'bold' }}>{mistake.count} times</span>
              </div>
            ))}
            {mistake_analysis.length === 0 && <span style={{ color: '#94a3b8' }}>No major mistakes recorded yet.</span>}
          </div>
        </div>

        {/* Win/Loss by Strategy */}
        <div style={{ backgroundColor: '#1e293b', borderRadius: '12px', border: '1px solid #334155', padding: '24px' }}>
          <h2 style={{ fontSize: '18px', margin: '0 0 20px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Target size={20} color="#10b981" /> Win/Loss by Strategy
          </h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {win_loss_strategy.map((strat, idx) => (
              <div key={idx} style={{ paddingBottom: '8px', borderBottom: '1px solid #334155' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                  <span style={{ color: '#f8fafc', fontSize: '14px' }}>{strat.name}</span>
                  <span style={{ color: strat.win_rate >= 50 ? '#10b981' : '#ef4444', fontWeight: 'bold' }}>{strat.win_rate}% Win</span>
                </div>
                <div style={{ width: '100%', height: '6px', backgroundColor: '#334155', borderRadius: '3px' }}>
                  <div style={{ width: `${strat.win_rate}%`, height: '100%', backgroundColor: strat.win_rate >= 50 ? '#10b981' : '#ef4444', borderRadius: '3px' }} />
                </div>
              </div>
            ))}
            <div style={{ marginTop: '10px', fontSize: '14px', color: '#94a3b8' }}>
              <strong>Best Setup:</strong> <span style={{ color: '#3b82f6' }}>{best_setup}</span>
            </div>
          </div>
        </div>

      </div>

      {/* AI Coaching Feed */}
      <div style={{ backgroundColor: '#1e293b', borderRadius: '12px', border: '1px solid #334155', padding: '24px' }}>
        <h2 style={{ fontSize: '18px', margin: '0 0 20px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <BrainCircuit size={20} color="#06b6d4" /> Live AI Coaching Interventions
        </h2>
        
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {ai_coaching.map((msg, idx) => {
            const isWarning = msg.includes('⚠️');
            const isGood = msg.includes('✅');
            
            return (
              <div key={idx} style={{ 
                padding: '16px 20px', 
                backgroundColor: isWarning ? 'rgba(239, 68, 68, 0.1)' : isGood ? 'rgba(16, 185, 129, 0.1)' : '#0f172a', 
                borderLeft: `4px solid ${isWarning ? '#ef4444' : isGood ? '#10b981' : '#3b82f6'}`,
                borderRadius: '8px',
                display: 'flex',
                alignItems: 'flex-start',
                gap: '12px'
              }}>
                <div style={{ marginTop: '2px' }}>
                  {isWarning ? <AlertTriangle size={20} color="#ef4444" /> : 
                   isGood ? <CheckCircle size={20} color="#10b981" /> : 
                   <Activity size={20} color="#3b82f6" />}
                </div>
                <div style={{ fontSize: '15px', color: '#f8fafc', lineHeight: '1.5' }}>
                  {msg}
                </div>
              </div>
            );
          })}
        </div>
      </div>
      
    </div>
  );
};

export default TradeDiary;
