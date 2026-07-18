import React, { useState, useEffect } from 'react';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer } from 'recharts';
import { Route, BrainCircuit, Target, Briefcase, Zap } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || '';

const TradingPathways = ({ token }) => {
  const [profiles, setProfiles] = useState(null);
  const [selectedRole, setSelectedRole] = useState('Intraday Scalper');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchPathways = async () => {
      try {
        const res = await fetch(`${API_URL}/api/system/pathways`, {
          headers: token ? { 'Authorization': `Bearer ${token}` } : {}
        });
        if (res.ok) {
          setProfiles(await res.json());
        }
      } catch (err) {
        console.error(err);
      }
      setLoading(false);
    };
    fetchPathways();
  }, [token]);

  if (loading || !profiles) {
    return <div style={{ padding: '24px', color: '#94a3b8' }}>Loading Syllabus Configurator...</div>;
  }

  const roleData = profiles[selectedRole];
  
  // Custom icons mapping for roles
  const roleIcons = {
    "Intraday": <Zap size={20} />,
    "Swing": <Activity size={20} />,
    "Positional": <TrendingUp size={20} />,
    "Long-term Investing": <Briefcase size={20} />,
    "Futures": <Activity size={20} />,
    "Options": <Target size={20} />,
    "Equity Delivery": <Briefcase size={20} />,
    "Commodity": <Layers size={20} />,
    "Currency": <Activity size={20} />,
    "Quant / Algo Developer": <BrainCircuit size={20} />
  };

  return (
    <div style={{ fontFamily: 'system-ui, -apple-system, sans-serif', padding: '24px', backgroundColor: '#0f172a', minHeight: '100vh', color: '#f8fafc' }}>
      
      {/* Header */}
      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ fontSize: '24px', fontWeight: 'bold', margin: '0 0 8px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Route size={28} color="#8b5cf6" />
          Trading Pathways & Syllabus Configurator
        </h1>
        <p style={{ margin: 0, color: '#94a3b8' }}>Select your trading goal. The AI will prescribe exactly which ELCO modules you need to master.</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '24px' }}>
        
        {/* Role Selector Panel */}
        <div style={{ backgroundColor: '#1e293b', borderRadius: '12px', border: '1px solid #334155', padding: '24px' }}>
          <h2 style={{ fontSize: '18px', margin: '0 0 20px 0', color: '#f8fafc' }}>Select Your Role</h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {Object.keys(profiles).map((role) => {
              const isSelected = selectedRole === role;
              return (
                <button
                  key={role}
                  onClick={() => setSelectedRole(role)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px',
                    width: '100%',
                    padding: '16px',
                    backgroundColor: isSelected ? 'rgba(139, 92, 246, 0.15)' : '#0f172a',
                    border: `1px solid ${isSelected ? '#8b5cf6' : '#334155'}`,
                    borderRadius: '8px',
                    color: isSelected ? '#a78bfa' : '#cbd5e1',
                    cursor: 'pointer',
                    textAlign: 'left',
                    transition: 'all 0.2s'
                  }}
                >
                  {roleIcons[role]}
                  <span style={{ fontWeight: isSelected ? 'bold' : 'normal', fontSize: '15px' }}>{role}</span>
                </button>
              );
            })}
          </div>
          
          <div style={{ marginTop: '32px', padding: '16px', backgroundColor: 'rgba(14, 165, 233, 0.1)', border: '1px solid rgba(14, 165, 233, 0.2)', borderRadius: '8px' }}>
            <h4 style={{ margin: '0 0 8px 0', color: '#38bdf8', fontSize: '14px' }}>Role Description</h4>
            <p style={{ margin: 0, fontSize: '13px', color: '#cbd5e1', lineHeight: '1.5' }}>
              {roleData.description}
            </p>
          </div>
        </div>

        {/* Syllabus Matrix Visualization */}
        <div style={{ backgroundColor: '#1e293b', borderRadius: '12px', border: '1px solid #334155', padding: '24px', display: 'flex', flexDirection: 'column' }}>
          <h2 style={{ fontSize: '18px', margin: '0 0 8px 0', color: '#f8fafc' }}>Module Importance Heatmap</h2>
          <p style={{ margin: '0 0 24px 0', color: '#94a3b8', fontSize: '14px' }}>Visualizing the ELCO tools you must master for this path.</p>
          
          <div style={{ flex: 1, minHeight: '350px', position: 'relative' }}>
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart cx="50%" cy="50%" outerRadius="70%" data={roleData.weights}>
                <PolarGrid stroke="#334155" />
                <PolarAngleAxis dataKey="subject" tick={{ fill: '#cbd5e1', fontSize: 12 }} />
                <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                <Radar 
                  name={selectedRole} 
                  dataKey="importance" 
                  stroke="#8b5cf6" 
                  strokeWidth={3}
                  fill="#8b5cf6" 
                  fillOpacity={0.5} 
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>
          
          <div style={{ marginTop: '24px', padding: '16px', backgroundColor: '#0f172a', borderLeft: '4px solid #8b5cf6', borderRadius: '8px' }}>
            <h4 style={{ margin: '0 0 8px 0', color: '#a78bfa', fontSize: '14px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <BrainCircuit size={16} /> AI Syllabus Guidance
            </h4>
            <p style={{ margin: 0, fontSize: '14px', color: '#f8fafc', lineHeight: '1.6' }}>
              {roleData.guidance}
            </p>
          </div>
        </div>

      </div>
    </div>
  );
};

export default TradingPathways;
