import React from 'react';

const ChartToolbar = ({ 
  mode, setMode,
  symbol, setSymbol, fetchHistory,
  timeframe, setTimeframe,
  activeChartType, setActiveChartType,
  indicators, toggleIndicator,
  showDomPanel, setShowDomPanel
}) => {
  const chartTypes = [
    { id: 'candlestick', label: 'Candles' },
    { id: 'heikin_ashi', label: 'Heikin Ashi' },
    { id: 'renko', label: 'Renko' }
  ];
  const timeframes = ['1m', '5m', '15m', '1h', '1d', '1wk'];

  const styles = {
    toolbar: { display: 'flex', flexDirection: 'column', gap: '10px', padding: '12px', background: '#1e222d', borderBottom: '1px solid #2b313f' },
    row: { display: 'flex', flexWrap: 'wrap', gap: '12px', alignItems: 'center' },
    input: { background: '#2b313f', color: '#fff', border: '1px solid #434651', padding: '6px 12px', borderRadius: '4px', textTransform: 'uppercase', width: '120px' },
    btn: { background: '#2b313f', color: '#d1d4dc', border: '1px solid #434651', padding: '6px 12px', borderRadius: '4px', cursor: 'pointer', fontSize: '12px', transition: '0.2s' },
    activeBtn: { background: '#2962ff', color: '#fff', border: '1px solid #2962ff', padding: '6px 12px', borderRadius: '4px', cursor: 'pointer', fontSize: '12px', transition: '0.2s' },
    modeToggle: { display: 'flex', alignItems: 'center', background: '#131722', borderRadius: '20px', padding: '4px', border: '1px solid #2b313f', marginLeft: 'auto' },
    modeBtn: { padding: '4px 12px', borderRadius: '16px', fontSize: '11px', cursor: 'pointer', border: 'none', background: 'transparent', color: '#787b86', fontWeight: 600, transition: '0.3s' },
    modeActive: { background: '#2962ff', color: '#fff' }
  };

  return (
    <div style={styles.toolbar}>
      {/* Top Row: Symbol, Timeframes, Mode */}
      <div style={styles.row}>
        <input 
          type="text" 
          value={symbol} 
          onChange={(e) => setSymbol(e.target.value)} 
          onBlur={fetchHistory}
          onKeyDown={(e) => e.key === 'Enter' && fetchHistory()}
          style={styles.input} 
          placeholder="Symbol..."
        />
        
        {/* Quick Jumps */}
        <div style={{ display: 'flex', gap: '4px' }}>
          {['RELIANCE.NS', '^NSEI', '^NSEBANK'].map(s => (
            <button key={s} style={symbol === s ? styles.activeBtn : styles.btn} onClick={() => { setSymbol(s); setTimeout(fetchHistory, 100); }}>
              {s.replace('.NS', '').replace('^NSEI', 'NIFTY').replace('^NSEBANK', 'BANKNIFTY')}
            </button>
          ))}
        </div>

        <div style={{ width: '1px', height: '24px', background: '#434651', margin: '0 4px' }} />

        {/* Timeframes */}
        <div style={{ display: 'flex', gap: '4px' }}>
          {timeframes.map(tf => (
            <button key={tf} style={timeframe === tf ? styles.activeBtn : styles.btn} onClick={() => setTimeframe(tf)}>
              {tf.toUpperCase()}
            </button>
          ))}
        </div>

        <div style={{ width: '1px', height: '24px', background: '#434651', margin: '0 4px' }} />

        {/* Chart Types */}
        <div style={{ display: 'flex', gap: '4px' }}>
          {chartTypes.map(ct => (
            <button key={ct.id} style={activeChartType === ct.id ? styles.activeBtn : styles.btn} onClick={() => setActiveChartType(ct.id)}>
              {ct.label}
            </button>
          ))}
        </div>

        {/* Mode Toggle */}
        <div style={styles.modeToggle}>
          <button style={{ ...styles.modeBtn, ...(mode === 'BEGINNER' ? styles.modeActive : {}) }} onClick={() => setMode('BEGINNER')}>BEGINNER</button>
          <button style={{ ...styles.modeBtn, ...(mode === 'ADVANCED' ? styles.modeActive : {}) }} onClick={() => setMode('ADVANCED')}>ADVANCED</button>
        </div>
      </div>

      {/* Bottom Row: Indicators (Advanced only) or simplified tools */}
      <div style={styles.row}>
        {mode === 'ADVANCED' ? (
          <>
            <span style={{ fontSize: '11px', color: '#787b86', fontWeight: 600 }}>INDICATORS:</span>
            <select 
              onChange={(e) => {
                if (e.target.value) {
                  toggleIndicator(e.target.value);
                  e.target.value = "";
                }
              }}
              style={{...styles.input, width: '150px'}}
            >
              <option value="">+ Add Indicator</option>
              {Object.keys(indicators).map(ind => (
                <option key={ind} value={ind}>
                  {indicators[ind] ? '✅ ' : '⬜ '}{ind.toUpperCase()}
                </option>
              ))}
            </select>

            <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
              {Object.keys(indicators).filter(k => indicators[k]).map(ind => (
                <span key={ind} style={{ background: '#2962ff', color: '#fff', padding: '4px 8px', borderRadius: '4px', fontSize: '11px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  {ind.toUpperCase()}
                  <span style={{ cursor: 'pointer', fontWeight: 'bold' }} onClick={() => toggleIndicator(ind)}>×</span>
                </span>
              ))}
            </div>
          </>
        ) : (
          <span style={{ fontSize: '12px', color: '#26a69a' }}>Beginner Mode: AI actively monitoring support, resistance, and setups automatically.</span>
        )}
        
        <button 
          style={{ ...(showDomPanel ? styles.activeBtn : styles.btn), marginLeft: 'auto', background: showDomPanel ? '#ff9800' : '#2b313f' }} 
          onClick={() => setShowDomPanel(!showDomPanel)}
        >
          📊 Order Book
        </button>
      </div>
    </div>
  );
};

export default ChartToolbar;
