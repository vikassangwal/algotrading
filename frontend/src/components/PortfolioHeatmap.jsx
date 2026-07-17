import React, { useState, useEffect } from 'react';
import { Treemap, ResponsiveContainer, Tooltip } from 'recharts';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const PortfolioHeatmap = ({ token }) => {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 15000); // refresh every 15s
    return () => clearInterval(interval);
  }, [token]);

  const fetchData = async () => {
    try {
      const res = await fetch(`${API_URL}/api/portfolio/heatmap`, {
        headers: token ? { 'Authorization': `Bearer ${token}` } : {}
      });
      if (res.ok) {
        const json = await res.json();
        setData([json]); // Treemap expects array with 1 root object, or array of children
      }
    } catch (err) {
      console.error("Heatmap fetch error:", err);
    }
    setLoading(false);
  };

  // Custom coloring function based on % change
  const getColor = (change) => {
    if (change === undefined) return '#1f2937';
    if (change >= 3) return '#059669'; // Deep green
    if (change > 1) return '#10b981'; // Green
    if (change > 0) return '#34d399'; // Light green
    if (change === 0) return '#4b5563'; // Neutral grey
    if (change > -1) return '#f87171'; // Light red
    if (change > -3) return '#ef4444'; // Red
    return '#dc2626'; // Deep red
  };

  const CustomizedContent = (props) => {
    const { root, depth, x, y, width, height, index, payload, name, value } = props;
    
    // Depth 1 = Sectors, Depth 2 = Stocks
    if (depth === 1) {
      // Draw sector borders
      return (
        <g>
          <rect
            x={x}
            y={y}
            width={width}
            height={height}
            fill="none"
            stroke="#111827"
            strokeWidth={4}
          />
        </g>
      );
    }
    if (depth === 2) {
      const { change } = payload;
      const fill = getColor(change);
      
      // Only render text if box is large enough
      const showText = width > 50 && height > 30;
      
      return (
        <g>
          <rect
            x={x}
            y={y}
            width={width}
            height={height}
            fill={fill}
            stroke="#1f2937"
            strokeWidth={1}
            style={{ cursor: 'pointer', transition: 'fill 0.2s' }}
            className="heatmap-cell"
          />
          {showText && (
            <text x={x + width / 2} y={y + height / 2 - 5} textAnchor="middle" fill="#fff" fontSize={14} fontWeight="bold">
              {name}
            </text>
          )}
          {showText && (
            <text x={x + width / 2} y={y + height / 2 + 15} textAnchor="middle" fill="#fff" fontSize={12}>
              {change > 0 ? '+' : ''}{change}%
            </text>
          )}
        </g>
      );
    }
    return null;
  };

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div style={{ backgroundColor: '#111827', border: '1px solid #374151', padding: '10px', borderRadius: '4px', color: '#f3f4f6', boxShadow: '0 4px 6px rgba(0,0,0,0.3)' }}>
          <div style={{ fontWeight: 'bold', fontSize: '16px', marginBottom: '4px' }}>{data.name}</div>
          <div style={{ fontSize: '13px', color: '#9ca3af', marginBottom: '8px' }}>{data.sector}</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', fontSize: '14px' }}>
            <div>
              <div style={{ color: '#6b7280', fontSize: '12px' }}>Allocation</div>
              <div>₹{data.size?.toLocaleString()}</div>
            </div>
            <div>
              <div style={{ color: '#6b7280', fontSize: '12px' }}>Today's Change</div>
              <div style={{ color: data.change >= 0 ? '#10b981' : '#ef4444', fontWeight: 'bold' }}>
                {data.change > 0 ? '+' : ''}{data.change}%
              </div>
            </div>
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <div style={{ padding: '20px', backgroundColor: '#111827', borderRadius: '8px', minHeight: '600px', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <h2 style={{ color: '#f9fafb', fontSize: '24px', margin: '0 0 5px 0' }}>Institutional Portfolio Heatmap</h2>
          <div style={{ color: '#9ca3af', fontSize: '14px' }}>Size = Capital Allocation | Color = Daily Performance</div>
        </div>
        
        {/* Legend */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '12px', color: '#d1d5db' }}>
          <span>Loss</span>
          <div style={{ width: '20px', height: '12px', backgroundColor: '#dc2626' }} />
          <div style={{ width: '20px', height: '12px', backgroundColor: '#ef4444' }} />
          <div style={{ width: '20px', height: '12px', backgroundColor: '#f87171' }} />
          <div style={{ width: '20px', height: '12px', backgroundColor: '#4b5563' }} />
          <div style={{ width: '20px', height: '12px', backgroundColor: '#34d399' }} />
          <div style={{ width: '20px', height: '12px', backgroundColor: '#10b981' }} />
          <div style={{ width: '20px', height: '12px', backgroundColor: '#059669' }} />
          <span>Profit</span>
        </div>
      </div>

      <div style={{ flex: 1, minHeight: '500px', border: '1px solid #374151', borderRadius: '8px', overflow: 'hidden' }}>
        {loading && data.length === 0 ? (
          <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#9ca3af' }}>
            Crunching portfolio data...
          </div>
        ) : data.length > 0 && data[0].children ? (
          <ResponsiveContainer width="100%" height="100%">
            <Treemap
              data={data[0].children} // recharts treemap works best by passing the children of the root directly
              dataKey="size"
              aspectRatio={4 / 3}
              stroke="#fff"
              content={<CustomizedContent />}
            >
              <Tooltip content={<CustomTooltip />} />
            </Treemap>
          </ResponsiveContainer>
        ) : (
          <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#9ca3af' }}>
            No portfolio data available.
          </div>
        )}
      </div>
    </div>
  );
};

export default PortfolioHeatmap;
