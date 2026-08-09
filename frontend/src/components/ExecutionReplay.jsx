import React, { useState, useEffect, useRef } from 'react';
import { ComposedChart, Line, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceArea } from 'recharts';
import { Play, Pause, Square, FastForward, Activity } from 'lucide-react';

const API_URL = (import.meta.env.VITE_API_URL || 'https://elco-backend.onrender.com').replace(/\/$/, '');

const CustomScatterShape = (props) => {
  const { cx, cy, payload } = props;
  if (!payload || !payload.action) return null;
  
  const size = 12;
  if (payload.action === 'BUY') {
    // Green Triangle pointing UP
    return (
      <polygon 
        points={`${cx},${cy - size} ${cx - size},${cy + size} ${cx + size},${cy + size}`} 
        fill="#10b981" 
        stroke="#047857" 
        strokeWidth={1} 
      />
    );
  } else if (payload.action === 'SELL') {
    // Red Triangle pointing DOWN
    return (
      <polygon 
        points={`${cx},${cy + size} ${cx - size},${cy - size} ${cx + size},${cy - size}`} 
        fill="#ef4444" 
        stroke="#b91c1c" 
        strokeWidth={1} 
      />
    );
  }
  return null;
};

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div style={{ backgroundColor: '#111827', border: '1px solid #374151', padding: '10px', borderRadius: '4px', color: '#f3f4f6' }}>
        <div style={{ fontWeight: 'bold', marginBottom: '5px' }}>{label}</div>
        <div style={{ color: '#9ca3af' }}>Price: <span style={{ color: '#fff' }}>₹{data.price.toFixed(2)}</span></div>
        {data.action && (
          <div style={{ marginTop: '5px', padding: '4px', backgroundColor: data.action === 'BUY' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)', color: data.action === 'BUY' ? '#10b981' : '#ef4444', borderRadius: '4px', fontWeight: 'bold' }}>
            {data.action} {data.qty} Qty
          </div>
        )}
      </div>
    );
  }
  return null;
};

const ExecutionReplay = ({ token, globalSymbol }) => {
  const [symbol, setSymbol] = useState('NIFTY');

  useEffect(() => {
    if (globalSymbol) {
      setSymbol(globalSymbol);
    }
  }, [globalSymbol]);
  const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  
  // Playback state
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [speed, setSpeed] = useState(50); // ms per tick

  const fetchReplayData = async () => {
    setLoading(true);
    setIsPlaying(false);
    setCurrentIndex(0);
    try {
      const res = await fetch(`${API_URL}/api/replay/${symbol}?date=${date}`, {
        headers: token ? { 'Authorization': `Bearer ${token}` } : {}
      });
      if (res.ok) {
        const json = await res.json();
        setData(json);
        setCurrentIndex(json.timeline.length > 0 ? 10 : 0); // Start with a few bars visible
      }
    } catch (err) {
      console.error("Replay fetch error:", err);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchReplayData();
  }, [symbol, date]);

  useEffect(() => {
    let interval;
    if (isPlaying && data && currentIndex < data.timeline.length) {
      interval = setInterval(() => {
        setCurrentIndex(prev => {
          if (prev >= data.timeline.length - 1) {
            setIsPlaying(false);
            return data.timeline.length;
          }
          return prev + 1;
        });
      }, speed);
    }
    return () => clearInterval(interval);
  }, [isPlaying, data, currentIndex, speed]);

  if (!data && loading) return <div style={{ padding: '20px', color: '#9ca3af' }}>Loading Replay Data...</div>;
  if (!data) return null;

  // Sliced data for animation
  const visibleTimeline = data.timeline.slice(0, currentIndex);
  
  // Calculate Y-Axis bounds to keep chart stable
  const prices = data.timeline.map(d => d.price);
  const minPrice = Math.min(...prices) * 0.999;
  const maxPrice = Math.max(...prices) * 1.001;

  // Visible trades for the ledger
  const visibleTrades = data.trades.filter(t => {
    const tradeIdx = data.timeline.findIndex(tl => tl.time === t.time);
    return tradeIdx <= currentIndex;
  }).reverse();

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      
      {/* Top Controls */}
      <div className="panel" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '15px' }}>
        <div style={{ display: 'flex', gap: '15px', alignItems: 'center' }}>
          <div>
            <label style={{ display: 'block', fontSize: '12px', color: '#9ca3af', marginBottom: '4px' }}>Symbol</label>
            <select 
              value={symbol} 
              onChange={e => setSymbol(e.target.value)}
              style={{ padding: '8px', backgroundColor: '#374151', color: 'white', border: '1px solid #4b5563', borderRadius: '4px' }}
            >
              <option value="NIFTY">NIFTY</option>
              <option value="BANKNIFTY">BANKNIFTY</option>
              <option value="RELIANCE">RELIANCE</option>
              <option value="HDFCBANK">HDFCBANK</option>
            </select>
          </div>
          <div>
            <label style={{ display: 'block', fontSize: '12px', color: '#9ca3af', marginBottom: '4px' }}>Date</label>
            <input 
              type="date" 
              value={date} 
              onChange={e => setDate(e.target.value)}
              style={{ padding: '6px', backgroundColor: '#374151', color: 'white', border: '1px solid #4b5563', borderRadius: '4px' }}
            />
          </div>
        </div>

        <div style={{ display: 'flex', gap: '10px', alignItems: 'center', backgroundColor: '#1f2937', padding: '10px 20px', borderRadius: '8px', border: '1px solid #374151' }}>
          <button 
            onClick={() => setIsPlaying(!isPlaying)}
            style={{ display: 'flex', alignItems: 'center', gap: '5px', padding: '8px 16px', backgroundColor: isPlaying ? '#fbbf24' : '#10b981', color: isPlaying ? '#000' : '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}
          >
            {isPlaying ? <><Pause size={18} /> Pause</> : <><Play size={18} /> Play</>}
          </button>
          
          <button 
            onClick={() => { setIsPlaying(false); setCurrentIndex(10); }}
            style={{ display: 'flex', alignItems: 'center', gap: '5px', padding: '8px 16px', backgroundColor: '#ef4444', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}
          >
            <Square size={18} /> Stop
          </button>

          <div style={{ marginLeft: '15px', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '12px', color: '#9ca3af' }}>Speed:</span>
            <select 
              value={speed} 
              onChange={e => setSpeed(Number(e.target.value))}
              style={{ padding: '6px', backgroundColor: '#374151', color: 'white', border: '1px solid #4b5563', borderRadius: '4px' }}
            >
              <option value={200}>Slow (0.5x)</option>
              <option value={100}>Normal (1x)</option>
              <option value={25}>Fast (4x)</option>
              <option value={5}>Max (20x)</option>
            </select>
          </div>
        </div>
        
        <div style={{ fontSize: '14px', color: '#9ca3af' }}>
          Time: <span style={{ color: '#fff', fontWeight: 'bold' }}>{visibleTimeline[visibleTimeline.length - 1]?.time || '09:15'}</span>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '3fr 1fr', gap: '20px' }}>
        
        {/* Main Chart Area */}
        <div className="panel" style={{ height: '600px', display: 'flex', flexDirection: 'column' }}>
          <div className="panel-header" style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span>Intraday Execution Overlay</span>
            <span style={{ fontSize: '12px', color: '#9ca3af', fontWeight: 'normal' }}>
              Progress: {Math.round((currentIndex / data.timeline.length) * 100)}%
            </span>
          </div>
          
          <div style={{ flex: 1, marginTop: '20px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={visibleTimeline} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" vertical={false} />
                <XAxis 
                  dataKey="time" 
                  stroke="#9ca3af" 
                  fontSize={12} 
                  tickMargin={10}
                  minTickGap={30}
                />
                <YAxis 
                  domain={[minPrice, maxPrice]} 
                  stroke="#9ca3af" 
                  fontSize={12}
                  tickFormatter={val => val.toLocaleString()}
                />
                <Tooltip content={<CustomTooltip />} cursor={{ stroke: '#6b7280', strokeWidth: 1, strokeDasharray: '5 5' }} />
                
                {/* Price Line */}
                <Line 
                  type="monotone" 
                  dataKey="price" 
                  stroke="#3b82f6" 
                  strokeWidth={2} 
                  dot={false}
                  isAnimationActive={false} // Disable recharts animation to use our own tick-based animation
                />
                
                {/* Executed Trades (Scatter Overlays) */}
                <Scatter 
                  dataKey="price" 
                  shape={<CustomScatterShape />}
                  isAnimationActive={false}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Ledger Sidebar */}
        <div className="panel" style={{ height: '600px', display: 'flex', flexDirection: 'column' }}>
          <div className="panel-header">Execution Ledger</div>
          <div style={{ flex: 1, overflowY: 'auto', paddingRight: '5px' }}>
            {visibleTrades.length === 0 ? (
              <div style={{ color: '#9ca3af', textAlign: 'center', marginTop: '40px', fontSize: '14px' }}>
                <Activity size={32} style={{ opacity: 0.2, margin: '0 auto 10px' }} />
                Waiting for trade executions...
              </div>
            ) : (
              visibleTrades.map((trade, idx) => (
                <div key={idx} style={{ 
                  backgroundColor: '#1f2937', 
                  border: `1px solid ${trade.action === 'BUY' ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`,
                  borderLeft: `4px solid ${trade.action === 'BUY' ? '#10b981' : '#ef4444'}`,
                  padding: '12px', 
                  borderRadius: '6px', 
                  marginBottom: '10px',
                  animation: 'fadeIn 0.3s ease-out'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                    <span style={{ color: '#9ca3af', fontSize: '12px' }}>{trade.time}</span>
                    <span style={{ fontSize: '12px', fontFamily: 'monospace', color: '#6b7280' }}>{trade.id}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                      <span style={{ fontWeight: 'bold', color: trade.action === 'BUY' ? '#10b981' : '#ef4444' }}>{trade.action}</span>
                      <span style={{ fontWeight: 'bold' }}>{trade.qty} Qty</span>
                    </div>
                    <span style={{ fontFamily: 'monospace', fontSize: '15px' }}>₹{trade.price.toLocaleString()}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
      <style dangerouslySetInnerHTML={{__html: `
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(-10px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}} />
    </div>
  );
};

export default ExecutionReplay;
