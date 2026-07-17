import React, { useState, useEffect } from 'react';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

// Mock data generator for visualization
const generateData = () => {
  const data = [];
  let time = new Date();
  time.setMinutes(time.getMinutes() - 30);
  for (let i = 0; i < 30; i++) {
    data.push({
      time: time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      cpu: Math.floor(Math.random() * 40) + 20, // 20-60%
      ram: Math.floor(Math.random() * 30) + 50, // 50-80%
      latency: Math.floor(Math.random() * 100) + 20, // 20-120ms
      margin: Math.floor(Math.random() * 50) + 10, // 10-60%
    });
    time.setMinutes(time.getMinutes() + 1);
  }
  return data;
};

const SystemDashboard = () => {
  const [data, setData] = useState([]);

  useEffect(() => {
    setData(generateData());
    
    // Simulate real-time data updates every minute
    const interval = setInterval(() => {
      setData((prevData) => {
        const newData = [...prevData.slice(1)];
        const time = new Date();
        newData.push({
          time: time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          cpu: Math.floor(Math.random() * 40) + 20,
          ram: Math.floor(Math.random() * 30) + 50,
          latency: Math.floor(Math.random() * 100) + 20,
          margin: Math.floor(Math.random() * 50) + 10,
        });
        return newData;
      });
    }, 60000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="system-dashboard" style={{ padding: '20px', backgroundColor: '#1e1e2f', color: '#fff', fontFamily: 'sans-serif' }}>
      <h2 style={{ textAlign: 'center', marginBottom: '20px', color: '#4fd1c5' }}>System Dashboard</h2>
      
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '20px' }}>
        
        {/* CPU & RAM Usage Line Chart */}
        <div style={{ backgroundColor: '#2d3748', padding: '20px', borderRadius: '10px', boxShadow: '0 4px 6px rgba(0,0,0,0.1)' }}>
          <h3 style={{ marginBottom: '15px', color: '#a0aec0', fontSize: '1.1em', textAlign: 'center' }}>CPU & RAM Usage (%)</h3>
          <div style={{ height: '300px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#4a5568" />
                <XAxis dataKey="time" stroke="#cbd5e0" />
                <YAxis stroke="#cbd5e0" domain={[0, 100]} />
                <Tooltip contentStyle={{ backgroundColor: '#1a202c', border: 'none', color: '#fff', borderRadius: '8px' }} />
                <Legend />
                <Line type="monotone" dataKey="cpu" stroke="#fc8181" strokeWidth={2} activeDot={{ r: 8 }} name="CPU" />
                <Line type="monotone" dataKey="ram" stroke="#68d391" strokeWidth={2} name="RAM" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* API Latency Bar Chart */}
        <div style={{ backgroundColor: '#2d3748', padding: '20px', borderRadius: '10px', boxShadow: '0 4px 6px rgba(0,0,0,0.1)' }}>
          <h3 style={{ marginBottom: '15px', color: '#a0aec0', fontSize: '1.1em', textAlign: 'center' }}>API Latency (ms)</h3>
          <div style={{ height: '300px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#4a5568" />
                <XAxis dataKey="time" stroke="#cbd5e0" />
                <YAxis stroke="#cbd5e0" />
                <Tooltip contentStyle={{ backgroundColor: '#1a202c', border: 'none', color: '#fff', borderRadius: '8px' }} cursor={{fill: '#4a5568', opacity: 0.4}} />
                <Legend />
                <Bar dataKey="latency" fill="#f6e05e" name="Latency" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Margin Utilization Line Chart */}
        <div style={{ backgroundColor: '#2d3748', padding: '20px', borderRadius: '10px', boxShadow: '0 4px 6px rgba(0,0,0,0.1)', gridColumn: '1 / -1' }}>
          <h3 style={{ marginBottom: '15px', color: '#a0aec0', fontSize: '1.1em', textAlign: 'center' }}>Margin Utilization (%)</h3>
          <div style={{ height: '300px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#4a5568" />
                <XAxis dataKey="time" stroke="#cbd5e0" />
                <YAxis stroke="#cbd5e0" domain={[0, 100]} />
                <Tooltip contentStyle={{ backgroundColor: '#1a202c', border: 'none', color: '#fff', borderRadius: '8px' }} />
                <Legend />
                <Line type="monotone" dataKey="margin" stroke="#63b3ed" strokeWidth={3} name="Margin" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

      </div>
    </div>
  );
};

export default SystemDashboard;
