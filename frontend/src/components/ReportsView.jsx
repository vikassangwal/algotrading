import React, { useState, useEffect } from 'react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, BarChart, Bar, Legend
} from 'recharts';

const mockWinRateData = [
  { name: 'Wins', value: 65, color: '#10b981' },
  { name: 'Losses', value: 35, color: '#ef4444' }
];

const ReportsView = ({ token }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch(`${import.meta.env.VITE_API_URL || ''}/api/reports`, {
          headers: token ? { 'Authorization': `Bearer ${token}` } : {}
        });
        const json = await res.json();
        setData(json);
        setLoading(false);
      } catch (err) {
        console.error("Error fetching reports", err);
        setLoading(false);
      }
    };
    fetchData();
  }, [token]);
  // Styles for a sleek dark mode UI
  const containerStyle = {
    padding: '24px',
    backgroundColor: '#0f172a',
    color: '#f8fafc',
    minHeight: '100vh',
    fontFamily: '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  };

  const headerStyle = {
    fontSize: '28px',
    fontWeight: '700',
    marginBottom: '24px',
    color: '#f1f5f9'
  };

  const gridStyle = {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
    gap: '24px',
    marginBottom: '24px'
  };

  const cardStyle = {
    backgroundColor: '#1e293b',
    borderRadius: '12px',
    padding: '20px',
    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -1px rgba(0, 0, 0, 0.15)',
    border: '1px solid #334155'
  };

  const cardTitleStyle = {
    fontSize: '16px',
    fontWeight: '600',
    color: '#94a3b8',
    marginBottom: '16px',
    textTransform: 'uppercase',
    letterSpacing: '0.05em'
  };

  const statValueStyle = {
    fontSize: '36px',
    fontWeight: '700',
    color: '#f8fafc'
  };

  const statPositiveStyle = { ...statValueStyle, color: '#10b981' };
  
  const chartContainerStyle = {
    width: '100%',
    height: '300px',
    marginTop: '16px'
  };

  // Custom tooltip for P&L charts
  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div style={{
          backgroundColor: '#0f172a',
          padding: '12px',
          border: '1px solid #334155',
          borderRadius: '8px',
          color: '#f8fafc',
          boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.5)'
        }}>
          <p style={{ margin: '0 0 8px 0', fontWeight: 'bold' }}>{label}</p>
          {payload.map((entry, index) => (
            <p key={index} style={{ margin: '4px 0', color: entry.color, fontWeight: '500' }}>
              {entry.name}: {entry.value < 0 ? '-' : ''}${Math.abs(entry.value).toLocaleString()}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  return (
    <div style={containerStyle}>
      <h1 style={headerStyle}>Trading Performance Reports</h1>
      
      {/* Top Stats */}
      <div style={gridStyle}>
        <div style={cardStyle}>
          <h3 style={cardTitleStyle}>Total P&L</h3>
          <div style={statPositiveStyle}>+$8,400.00</div>
          <div style={{ color: '#10b981', fontSize: '14px', marginTop: '8px', fontWeight: '500' }}>+12% this month 📈</div>
        </div>
        <div style={cardStyle}>
          <h3 style={cardTitleStyle}>Win Rate</h3>
          <div style={statValueStyle}>65.0%</div>
          <div style={{ color: '#10b981', fontSize: '14px', marginTop: '8px', fontWeight: '500' }}>+2.5% this month 📈</div>
        </div>
        <div style={cardStyle}>
          <h3 style={cardTitleStyle}>Profit Factor</h3>
          <div style={statValueStyle}>1.85</div>
          <div style={{ color: '#94a3b8', fontSize: '14px', marginTop: '8px' }}>Average across all trades</div>
        </div>
      </div>

      {/* Main Charts */}
      <div style={{ ...gridStyle, gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))' }}>
        {/* Cumulative P&L Area Chart */}
        <div style={cardStyle}>
          <h3 style={cardTitleStyle}>Cumulative P&L Over Time</h3>
          <div style={chartContainerStyle}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data?.pnl_curve || []} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorCumulative" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8}/>
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                <XAxis dataKey="date" stroke="#94a3b8" tick={{ fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                <YAxis stroke="#94a3b8" tick={{ fill: '#94a3b8' }} axisLine={false} tickLine={false} tickFormatter={(value) => `$${value}`} />
                <Tooltip content={<CustomTooltip />} />
                <Area type="monotone" dataKey="cumulative" name="Total P&L" stroke="#3b82f6" strokeWidth={3} fillOpacity={1} fill="url(#colorCumulative)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Win Rate Pie Chart */}
        <div style={cardStyle}>
          <h3 style={cardTitleStyle}>Win/Loss Ratio</h3>
          <div style={chartContainerStyle}>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={data?.win_rate || []}
                  cx="50%"
                  cy="50%"
                  innerRadius={70}
                  outerRadius={110}
                  paddingAngle={5}
                  dataKey="value"
                  stroke="none"
                >
                  {(data?.win_rate || []).map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip 
                  contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #334155', borderRadius: '8px', color: '#f8fafc', boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.5)' }}
                  itemStyle={{ color: '#f8fafc' }}
                />
                <Legend verticalAlign="bottom" height={36} iconType="circle" wrapperStyle={{ color: '#94a3b8' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Secondary Charts */}
      <div style={{ ...gridStyle, gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))' }}>
        {/* Monthly P&L Bar Chart */}
        <div style={cardStyle}>
          <h3 style={cardTitleStyle}>Monthly Net P&L</h3>
          <div style={chartContainerStyle}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data?.pnl_curve || []} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                <XAxis dataKey="date" stroke="#94a3b8" tick={{ fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                <YAxis stroke="#94a3b8" tick={{ fill: '#94a3b8' }} axisLine={false} tickLine={false} tickFormatter={(value) => `$${value}`} />
                <Tooltip content={<CustomTooltip />} cursor={{ fill: '#334155', opacity: 0.4 }} />
                <Bar dataKey="pnl" name="Net P&L" radius={[4, 4, 4, 4]}>
                  {(data?.pnl_curve || []).map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.pnl >= 0 ? '#10b981' : '#ef4444'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Trade Distribution by Day */}
        <div style={cardStyle}>
          <h3 style={cardTitleStyle}>Trade Outcomes by Day</h3>
          <div style={chartContainerStyle}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data?.daily_performance || []} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                <XAxis dataKey="day" stroke="#94a3b8" tick={{ fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                <YAxis stroke="#94a3b8" tick={{ fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #334155', borderRadius: '8px', color: '#f8fafc', boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.5)' }}
                  itemStyle={{ color: '#f8fafc' }}
                  cursor={{ fill: '#334155', opacity: 0.4 }}
                />
                <Legend verticalAlign="top" height={36} iconType="circle" wrapperStyle={{ color: '#94a3b8', paddingBottom: '10px' }} />
                <Bar dataKey="profit" name="Wins" stackId="a" fill="#10b981" radius={[0, 0, 4, 4]} />
                <Bar dataKey="loss" name="Losses" stackId="a" fill="#ef4444" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ReportsView;
