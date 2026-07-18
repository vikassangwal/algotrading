import React, { useState, useEffect } from 'react';

const API_URL = import.meta.env.VITE_API_URL || '';

const OptionChain = ({ token }) => {
  const [symbol, setSymbol] = useState('NIFTY');
  const [expirations, setExpirations] = useState([]);
  const [selectedDate, setSelectedDate] = useState('');
  
  const [chainData, setChainData] = useState([]);
  const [spotPrice, setSpotPrice] = useState(0);
  const [maxPain, setMaxPain] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Fetch expirations when symbol changes
  useEffect(() => {
    if (!symbol) return;
    const fetchExpirations = async () => {
      setLoading(true);
      try {
        const res = await fetch(`${API_URL}/api/options/${symbol}/expirations`);
        if (res.ok) {
          const dates = await res.json();
          setExpirations(dates);
          if (dates.length > 0) setSelectedDate(dates[0]);
        }
      } catch (err) {
        setError('Failed to fetch expirations');
      }
      setLoading(false);
    };
    
    // Debounce to avoid spamming
    const timeoutId = setTimeout(fetchExpirations, 1000);
    return () => clearTimeout(timeoutId);
  }, [symbol]);

  // Fetch option chain when symbol or selectedDate changes
  useEffect(() => {
    if (!symbol || !selectedDate) return;
    fetchChain();
    // Refresh every 10s
    const interval = setInterval(fetchChain, 10000);
    return () => clearInterval(interval);
  }, [symbol, selectedDate]);

  const fetchChain = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/options/${symbol}/chain?date=${selectedDate}`);
      if (res.ok) {
        const data = await res.json();
        setSpotPrice(data.underlyingPrice || 0);
        setMaxPain(data.max_pain || 0);
        
        // Map data into rows by strike
        const rows = data.strikes.map(strike => {
          const call = data.calls.find(c => c.strike === strike) || {};
          const put = data.puts.find(p => p.strike === strike) || {};
          return { strike, call, put };
        });
        setChainData(rows);
        setError('');
      } else {
        setError('Failed to fetch chain data');
      }
    } catch (err) {
      setError('Connection error');
    }
    setLoading(false);
  };

  return (
    <div style={{ fontFamily: 'system-ui, -apple-system, sans-serif', padding: '20px', backgroundColor: '#111827', borderRadius: '8px', boxShadow: '0 4px 6px rgba(0,0,0,0.3)', overflowX: 'auto', maxWidth: '100%', color: '#f3f4f6' }}>
      
      {/* Controls Header */}
      <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', flexWrap: 'wrap', gap: '15px'}}>
        <div>
          <h2 style={{ color: '#f9fafb', fontSize: '20px', fontWeight: 'bold', margin: '0 0 10px 0' }}>Live Option Chain</h2>
          <div style={{display: 'flex', gap: '10px', alignItems: 'center'}}>
            <input 
              type="text" 
              value={symbol} 
              onChange={(e) => setSymbol(e.target.value.toUpperCase())}
              style={{padding: '8px 12px', borderRadius: '4px', border: '1px solid #374151', backgroundColor: '#1f2937', color: '#fff', outline: 'none', width: '150px'}}
              placeholder="Symbol (e.g. NIFTY)"
            />
            <select 
              value={selectedDate} 
              onChange={(e) => setSelectedDate(e.target.value)}
              style={{padding: '8px 12px', borderRadius: '4px', border: '1px solid #374151', backgroundColor: '#1f2937', color: '#fff', outline: 'none'}}
            >
              {expirations.map(d => <option key={d} value={d}>{d}</option>)}
              {expirations.length === 0 && <option value="">No Expirations Found</option>}
            </select>
            {loading && <span style={{color: '#9ca3af', fontSize: '14px'}}>Loading...</span>}
            {error && <span style={{color: '#ef4444', fontSize: '14px'}}>{error}</span>}
          </div>
        </div>
        
        <div style={{display: 'flex', gap: '15px'}}>
          <div style={{backgroundColor: '#1f2937', padding: '8px 16px', borderRadius: '6px', border: '1px solid #374151'}}>
            <span style={{color: '#9ca3af', marginRight: '8px', fontSize: '14px'}}>Underlying:</span>
            <span style={{ color: '#10b981', fontWeight: 'bold', fontSize: '16px' }}>{spotPrice.toFixed(2)}</span>
          </div>
          <div style={{backgroundColor: '#1f2937', padding: '8px 16px', borderRadius: '6px', border: '1px solid #374151'}}>
            <span style={{color: '#9ca3af', marginRight: '8px', fontSize: '14px'}}>Max Pain:</span>
            <span style={{ color: '#f59e0b', fontWeight: 'bold', fontSize: '16px' }}>{maxPain ? maxPain.toFixed(2) : '-'}</span>
          </div>
        </div>
      </div>
      
      {/* Option Chain Table */}
      <div style={{ overflowX: 'auto', borderRadius: '6px', border: '1px solid #374151' }}>
        <table style={{ width: '100%', minWidth: '800px', borderCollapse: 'collapse', backgroundColor: '#1f2937', fontSize: '13px' }}>
          <thead>
            <tr>
              <th colSpan="7" style={{ backgroundColor: '#1e3a8a', color: '#bfdbfe', padding: '10px', textAlign: 'center', fontSize: '14px', letterSpacing: '0.05em', borderRight: '1px solid #374151' }}>CALLS</th>
              <th style={{ backgroundColor: '#374151', color: '#f3f4f6', padding: '10px', textAlign: 'center', fontSize: '14px', letterSpacing: '0.05em' }}>STRIKE</th>
              <th colSpan="7" style={{ backgroundColor: '#831843', color: '#fbcfe8', padding: '10px', textAlign: 'center', fontSize: '14px', letterSpacing: '0.05em', borderLeft: '1px solid #374151' }}>PUTS</th>
            </tr>
            <tr style={{ backgroundColor: '#111827', color: '#9ca3af', borderBottom: '1px solid #374151', fontSize: '12px' }}>
              <th style={thStyle}>Vega</th>
              <th style={thStyle}>Theta</th>
              <th style={thStyle}>Gamma</th>
              <th style={thStyle}>Delta</th>
              <th style={thStyle}>Volume</th>
              <th style={thStyle}>OI</th>
              <th style={{...thStyle, borderRight: '1px solid #374151'}}>LTP</th>
              
              <th style={{ ...thStyle, backgroundColor: '#374151', fontWeight: 'bold', color: '#f3f4f6', textAlign: 'center' }}>Price</th>
              
              <th style={{...thStyle, borderLeft: '1px solid #374151'}}>LTP</th>
              <th style={thStyle}>OI</th>
              <th style={thStyle}>Volume</th>
              <th style={thStyle}>Delta</th>
              <th style={thStyle}>Gamma</th>
              <th style={thStyle}>Theta</th>
              <th style={thStyle}>Vega</th>
            </tr>
          </thead>
          <tbody>
            {chainData.length === 0 && !loading && (
              <tr><td colSpan="7" style={{padding: '30px', textAlign: 'center', color: '#9ca3af'}}>No options data available for this symbol/expiry.</td></tr>
            )}
            {chainData.map((row, index) => {
              const isITMCall = row.strike < spotPrice;
              const isITMPut = row.strike > spotPrice;
              
              const formatNum = (val) => val ? val.toLocaleString() : '-';
              const formatLTP = (val) => val ? val.toFixed(2) : '-';
              
              return (
                <tr key={index} style={{ borderBottom: '1px solid #374151', backgroundColor: index % 2 === 0 ? '#1f2937' : '#111827' }}>
                  {/* CALLS */}
                  <td style={{ ...tdStyle, backgroundColor: isITMCall ? '#1e3a8a33' : 'inherit', color: '#9ca3af' }}>{row.call.vega?.toFixed(3) || '-'}</td>
                  <td style={{ ...tdStyle, backgroundColor: isITMCall ? '#1e3a8a33' : 'inherit', color: '#9ca3af' }}>{row.call.theta?.toFixed(3) || '-'}</td>
                  <td style={{ ...tdStyle, backgroundColor: isITMCall ? '#1e3a8a33' : 'inherit', color: '#9ca3af' }}>{row.call.gamma?.toFixed(4) || '-'}</td>
                  <td style={{ ...tdStyle, backgroundColor: isITMCall ? '#1e3a8a33' : 'inherit', color: row.call.delta > 0 ? '#10b981' : '#9ca3af' }}>{row.call.delta?.toFixed(3) || '-'}</td>
                  <td style={{ ...tdStyle, backgroundColor: isITMCall ? '#1e3a8a33' : 'inherit' }}>{formatNum(row.call.volume)}</td>
                  <td style={{ ...tdStyle, backgroundColor: isITMCall ? '#1e3a8a33' : 'inherit' }}>{formatNum(row.call.oi)}</td>
                  <td style={{ ...tdStyle, backgroundColor: isITMCall ? '#1e3a8a33' : 'inherit', fontWeight: 'bold', color: '#3b82f6', borderRight: '1px solid #374151' }}>
                    {formatLTP(row.call.ltp)}
                  </td>
                  
                  {/* STRIKE */}
                  <td style={{ ...tdStyle, backgroundColor: '#374151', fontWeight: 'bold', color: '#f9fafb', textAlign: 'center' }}>
                    {row.strike.toFixed(1)}
                  </td>
                  
                  {/* PUTS */}
                  <td style={{ ...tdStyle, backgroundColor: isITMPut ? '#83184333' : 'inherit', fontWeight: 'bold', color: '#ec4899', borderLeft: '1px solid #374151' }}>
                    {formatLTP(row.put.ltp)}
                  </td>
                  <td style={{ ...tdStyle, backgroundColor: isITMPut ? '#83184333' : 'inherit' }}>{formatNum(row.put.oi)}</td>
                  <td style={{ ...tdStyle, backgroundColor: isITMPut ? '#83184333' : 'inherit' }}>{formatNum(row.put.volume)}</td>
                  <td style={{ ...tdStyle, backgroundColor: isITMPut ? '#83184333' : 'inherit', color: row.put.delta < 0 ? '#ef4444' : '#9ca3af' }}>{row.put.delta?.toFixed(3) || '-'}</td>
                  <td style={{ ...tdStyle, backgroundColor: isITMPut ? '#83184333' : 'inherit', color: '#9ca3af' }}>{row.put.gamma?.toFixed(4) || '-'}</td>
                  <td style={{ ...tdStyle, backgroundColor: isITMPut ? '#83184333' : 'inherit', color: '#9ca3af' }}>{row.put.theta?.toFixed(3) || '-'}</td>
                  <td style={{ ...tdStyle, backgroundColor: isITMPut ? '#83184333' : 'inherit', color: '#9ca3af' }}>{row.put.vega?.toFixed(3) || '-'}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <div style={{ marginTop: '12px', fontSize: '12px', color: '#6b7280', textAlign: 'right' }}>
        Data fetched via highly realistic options engine / yfinance
      </div>
    </div>
  );
};

const thStyle = {
  padding: '10px 8px',
  textAlign: 'right',
  fontWeight: '600',
  whiteSpace: 'nowrap',
};

const tdStyle = {
  padding: '10px 8px',
  textAlign: 'right',
  whiteSpace: 'nowrap',
  color: '#d1d5db',
  fontFamily: 'monospace',
  fontSize: '13px'
};

export default OptionChain;
