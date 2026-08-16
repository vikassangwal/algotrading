import React, { useState, useRef, useEffect } from 'react';

// Indicator display names and categories for the dropdown
const INDICATOR_META = {
  vol: { name: 'Volume', category: 'Basic', color: '#26a69a' },
  sma20: { name: 'SMA 20', category: 'Moving Avg', color: '#ffeb3b' },
  sma50: { name: 'SMA 50', category: 'Moving Avg', color: '#ff9800' },
  ema9: { name: 'EMA 9', category: 'Moving Avg', color: '#00bcd4' },
  vwap: { name: 'VWAP', category: 'Volume', color: '#e040fb' },
  bb: { name: 'Bollinger Bands', category: 'Volatility', color: '#2196f3' },
  supertrend: { name: 'Supertrend', category: 'Trend', color: '#00e676' },
  rsi: { name: 'RSI (14)', category: 'Oscillator', color: '#9c27b0' },
  macd: { name: 'MACD', category: 'Oscillator', color: '#2196f3' },
  stochrsi: { name: 'Stochastic RSI', category: 'Oscillator', color: '#00bcd4' },
  adx: { name: 'ADX (+DI/-DI)', category: 'Oscillator', color: '#ff9800' },
  atr: { name: 'ATR', category: 'Volatility', color: '#ff5252' },
  ichimoku: { name: 'Ichimoku Cloud', category: 'Trend', color: '#4caf50' },
  fibonacci: { name: 'Fibonacci Retracement', category: 'Levels', color: '#e040fb' },
  pivots: { name: 'Pivot Points (R/S)', category: 'Levels', color: '#ff9800' },
  sr: { name: 'Support / Resistance', category: 'Levels', color: '#ef5350' },
  aipredictor: { name: '🧠 AI Super Predictor', category: '⭐ AI', color: '#e040fb' },
};

const CATEGORIES = ['⭐ AI', 'Basic', 'Moving Avg', 'Trend', 'Oscillator', 'Volatility', 'Volume', 'Levels'];

const ChartToolbar = ({
  mode, setMode,
  symbol, setSymbol, fetchHistory,
  timeframe, setTimeframe,
  activeChartType, setActiveChartType,
  indicators, toggleIndicator,
  showDomPanel, setShowDomPanel,
  onAutoAnalyze
}) => {
  const [showDropdown, setShowDropdown] = useState(false);
  const dropdownRef = useRef(null);

  const [showChartTypeDropdown, setShowChartTypeDropdown] = useState(false);
  const chartTypeDropdownRef = useRef(null);

  const [showTimeframeDropdown, setShowTimeframeDropdown] = useState(false);
  const timeframeDropdownRef = useRef(null);

  // Auto Trade Setup State
  const [orderPrice, setOrderPrice] = useState('');
  const [stopLoss, setStopLoss] = useState('');
  const [targetPrice, setTargetPrice] = useState('');
  const [riskReward, setRiskReward] = useState('1:2');

  useEffect(() => {
    if (orderPrice && stopLoss && riskReward !== 'Custom') {
      const op = parseFloat(orderPrice);
      const sl = parseFloat(stopLoss);
      if (!isNaN(op) && !isNaN(sl) && op !== sl) {
        const risk = Math.abs(op - sl);
        const rewardMultiplier = parseFloat(riskReward.split(':')[1]);
        const tp = op > sl ? op + (risk * rewardMultiplier) : op - (risk * rewardMultiplier);
        setTargetPrice(tp.toFixed(2));
      }
    }
  }, [orderPrice, stopLoss, riskReward]);

  const handleAiAutoSetup = () => {
    if (onAutoAnalyze) {
      const result = onAutoAnalyze();
      if (result) {
        setOrderPrice(result.entry);
        setStopLoss(result.sl);
        setTargetPrice(result.tp);
        setRiskReward(result.rr);
      }
    }
  };

  const chartTypes = [
    { id: 'candlestick', label: 'Candles', icon: '🕯️' },
    { id: 'heikin_ashi', label: 'Heikin Ashi', icon: '📊' },
    { id: 'renko', label: 'Renko (Line)', icon: '📈' }
  ];
  const timeframes = ['1m', '5m', '15m', '1h', '1d', '1wk'];

  const activeCount = Object.keys(indicators).filter(k => indicators[k]).length;

  const styles = {
    toolbar: { display: 'flex', flexDirection: 'column', gap: '8px', padding: '10px 14px', background: '#1a1e2e', borderBottom: '1px solid #2b313f' },
    row: { display: 'flex', flexWrap: 'wrap', gap: '8px', alignItems: 'center' },
    input: { background: '#2b313f', color: '#fff', border: '1px solid #434651', padding: '6px 12px', borderRadius: '6px', textTransform: 'uppercase', width: '130px', fontSize: '13px', fontWeight: 600, outline: 'none' },
    btn: { background: '#252a3a', color: '#8a92a5', border: '1px solid #363c4e', padding: '5px 10px', borderRadius: '6px', cursor: 'pointer', fontSize: '11px', fontWeight: 600, transition: '0.15s', whiteSpace: 'nowrap' },
    activeBtn: { background: '#2962ff', color: '#fff', border: '1px solid #2962ff', padding: '5px 10px', borderRadius: '6px', cursor: 'pointer', fontSize: '11px', fontWeight: 600, transition: '0.15s', whiteSpace: 'nowrap', boxShadow: '0 0 8px rgba(41,98,255,0.3)' },
    modeToggle: { display: 'flex', alignItems: 'center', background: '#131722', borderRadius: '20px', padding: '3px', border: '1px solid #2b313f', marginLeft: 'auto' },
    modeBtn: { padding: '4px 14px', borderRadius: '16px', fontSize: '11px', cursor: 'pointer', border: 'none', background: 'transparent', color: '#787b86', fontWeight: 600, transition: '0.2s' },
    modeActive: { background: '#2962ff', color: '#fff', boxShadow: '0 0 6px rgba(41,98,255,0.4)' },
    separator: { width: '1px', height: '24px', background: '#363c4e', margin: '0 2px' },
    tag: {
      display: 'inline-flex', alignItems: 'center', gap: '4px',
      padding: '3px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: 600,
      cursor: 'pointer', transition: '0.15s'
    },
    dropdown: {
      position: 'absolute', top: '100%', left: 0, marginTop: '4px',
      background: '#1e222d', border: '1px solid #363c4e', borderRadius: '8px',
      boxShadow: '0 8px 32px rgba(0,0,0,0.5)', zIndex: 1000, width: '260px',
      maxHeight: '400px', overflowY: 'auto', padding: '8px 0'
    },
    dropdownItem: {
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '8px 14px', cursor: 'pointer', fontSize: '12px', transition: '0.1s',
    },
    catHeader: { padding: '6px 14px', fontSize: '10px', color: '#787b86', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px' }
  };

  // Close dropdowns on outside click
  const handleBlur = (e) => {
    if (dropdownRef.current && !dropdownRef.current.contains(e.relatedTarget)) {
      setTimeout(() => setShowDropdown(false), 150);
    }
  };

  const handleChartTypeBlur = (e) => {
    if (chartTypeDropdownRef.current && !chartTypeDropdownRef.current.contains(e.relatedTarget)) {
      setTimeout(() => setShowChartTypeDropdown(false), 150);
    }
  };

  const handleTimeframeBlur = (e) => {
    if (timeframeDropdownRef.current && !timeframeDropdownRef.current.contains(e.relatedTarget)) {
      setTimeout(() => setShowTimeframeDropdown(false), 150);
    }
  };

  return (
    <div style={styles.toolbar}>
      {/* Top Row */}
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


        <div style={styles.separator} />

        {/* Timeframes Dropdown */}
        <div style={{ position: 'relative' }} ref={timeframeDropdownRef} tabIndex={-1} onBlur={handleTimeframeBlur}>
          <button
            style={{ ...styles.activeBtn, background: showTimeframeDropdown ? '#1565c0' : '#2962ff', display: 'flex', alignItems: 'center', gap: '6px', minWidth: '70px', justifyContent: 'center' }}
            onClick={() => setShowTimeframeDropdown(!showTimeframeDropdown)}
          >
            🕒 {timeframe.toUpperCase()}
            <span style={{ fontSize: '9px', marginLeft: 'auto' }}>{showTimeframeDropdown ? '▲' : '▼'}</span>
          </button>

          {showTimeframeDropdown && (
            <div style={{ ...styles.dropdown, width: '100px', zIndex: 1001 }}>
              {timeframes.map(tf => (
                <div
                  key={tf}
                  style={{ ...styles.dropdownItem, background: timeframe === tf ? '#252a3a' : 'transparent', color: timeframe === tf ? '#2962ff' : '#d1d4dc', justifyContent: 'center' }}
                  onClick={() => { setTimeframe(tf); setShowTimeframeDropdown(false); }}
                >
                  <span style={{ fontSize: '13px', fontWeight: 600 }}>{tf.toUpperCase()}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div style={styles.separator} />

        {/* Chart Types Dropdown */}
        <div style={{ position: 'relative' }} ref={chartTypeDropdownRef} tabIndex={-1} onBlur={handleChartTypeBlur}>
          <button
            style={{ ...styles.activeBtn, background: showChartTypeDropdown ? '#1565c0' : '#2962ff', display: 'flex', alignItems: 'center', gap: '6px', minWidth: '130px', justifyContent: 'center' }}
            onClick={() => setShowChartTypeDropdown(!showChartTypeDropdown)}
          >
            {chartTypes.find(c => c.id === activeChartType)?.icon} {chartTypes.find(c => c.id === activeChartType)?.label || 'Chart Type'}
            <span style={{ fontSize: '9px', marginLeft: 'auto' }}>{showChartTypeDropdown ? '▲' : '▼'}</span>
          </button>

          {showChartTypeDropdown && (
            <div style={{ ...styles.dropdown, width: '150px' }}>
              {chartTypes.map(ct => (
                <div
                  key={ct.id}
                  style={{ ...styles.dropdownItem, background: activeChartType === ct.id ? '#252a3a' : 'transparent', color: activeChartType === ct.id ? '#2962ff' : '#d1d4dc' }}
                  onClick={() => { setActiveChartType(ct.id); setShowChartTypeDropdown(false); }}
                >
                  <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '14px' }}>{ct.icon}</span>
                    <span>{ct.label}</span>
                  </span>
                  {activeChartType === ct.id && <span style={{ fontSize: '12px', color: '#2962ff' }}>✓</span>}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Auto Trade Setup */}
        {mode === 'ADVANCED' && (
          <>
            <div style={styles.separator} />
            <div style={{ display: 'flex', gap: '6px', alignItems: 'center', background: '#131722', padding: '3px 8px', borderRadius: '8px', border: '1px solid #2b313f' }}>
              <span style={{ fontSize: '10px', color: '#8a92a5', fontWeight: 700, letterSpacing: '0.5px' }}>AUTO SETUP</span>
              
              <button 
                onClick={handleAiAutoSetup}
                style={{ ...styles.activeBtn, padding: '2px 8px', fontSize: '10px', background: 'linear-gradient(90deg, #6200ea, #2962ff)', border: 'none', marginLeft: '4px', marginRight: '4px' }}
                title="AI Auto Analyze & Fill"
              >
                🪄 AI Setup
              </button>
              
              <input type="number" placeholder="Order Price" value={orderPrice} onChange={e => setOrderPrice(e.target.value)} style={{ ...styles.input, width: '75px', padding: '3px 6px', fontSize: '11px', height: '22px' }} title="Entry Price" />
              
              <input type="number" placeholder="Stoploss" value={stopLoss} onChange={e => setStopLoss(e.target.value)} style={{ ...styles.input, width: '65px', padding: '3px 6px', fontSize: '11px', height: '22px', border: '1px solid rgba(239, 83, 80, 0.5)' }} title="Stoploss Price" />
              
              <select value={riskReward} onChange={e => setRiskReward(e.target.value)} style={{ background: '#252a3a', color: '#d1d4dc', border: '1px solid #363c4e', borderRadius: '4px', fontSize: '11px', padding: '2px 4px', height: '22px', cursor: 'pointer', outline: 'none' }} title="Risk Reward Ratio">
                <option value="1:1">RR 1:1</option>
                <option value="1:2">RR 1:2</option>
                <option value="1:3">RR 1:3</option>
                <option value="1:4">RR 1:4</option>
                <option value="Custom">Custom</option>
              </select>
              
              <input type="number" placeholder="Target" value={targetPrice} onChange={e => setTargetPrice(e.target.value)} style={{ ...styles.input, width: '65px', padding: '3px 6px', fontSize: '11px', height: '22px', border: '1px solid rgba(38, 166, 154, 0.5)' }} title="Target Price" />
            </div>
          </>
        )}

        {/* Mode Toggle */}
        <div style={styles.modeToggle}>
          <button style={{ ...styles.modeBtn, ...(mode === 'BEGINNER' ? styles.modeActive : {}) }} onClick={() => setMode('BEGINNER')}>BEGINNER</button>
          <button style={{ ...styles.modeBtn, ...(mode === 'ADVANCED' ? styles.modeActive : {}) }} onClick={() => setMode('ADVANCED')}>PRO</button>
        </div>
      </div>

      {/* Bottom Row: Indicators */}
      <div style={styles.row}>
        {mode === 'ADVANCED' ? (
          <>
            {/* Indicator Dropdown Button */}
            <div style={{ position: 'relative' }} ref={dropdownRef} tabIndex={-1} onBlur={handleBlur}>
              <button
                style={{ ...styles.activeBtn, background: showDropdown ? '#1565c0' : '#2962ff', display: 'flex', alignItems: 'center', gap: '6px' }}
                onClick={() => setShowDropdown(!showDropdown)}
              >
                📈 Indicators ({activeCount})
                <span style={{ fontSize: '9px' }}>{showDropdown ? '▲' : '▼'}</span>
              </button>

              {showDropdown && (
                <div style={styles.dropdown}>
                  {CATEGORIES.map(cat => {
                    const items = Object.entries(INDICATOR_META).filter(([, m]) => m.category === cat);
                    if (items.length === 0) return null;
                    return (
                      <div key={cat}>
                        <div style={styles.catHeader}>{cat}</div>
                        {items.map(([key, meta]) => (
                          <div
                            key={key}
                            style={{
                              ...styles.dropdownItem,
                              background: indicators[key] ? 'rgba(41,98,255,0.1)' : 'transparent',
                            }}
                            onClick={() => toggleIndicator(key)}
                            onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(41,98,255,0.15)'}
                            onMouseLeave={(e) => e.currentTarget.style.background = indicators[key] ? 'rgba(41,98,255,0.1)' : 'transparent'}
                          >
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                              <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: meta.color, display: 'inline-block' }} />
                              <span style={{ color: '#d1d4dc' }}>{meta.name}</span>
                            </div>
                            <span style={{ fontSize: '14px' }}>{indicators[key] ? '✅' : '⬜'}</span>
                          </div>
                        ))}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Active Indicator Tags */}
            <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
              {Object.keys(indicators).filter(k => indicators[k] && INDICATOR_META[k]).map(ind => (
                <span key={ind} style={{
                  ...styles.tag,
                  background: `${INDICATOR_META[ind].color}22`,
                  color: INDICATOR_META[ind].color,
                  border: `1px solid ${INDICATOR_META[ind].color}44`
                }}>
                  {INDICATOR_META[ind].name}
                  <span style={{ cursor: 'pointer', fontWeight: 'bold', marginLeft: '2px' }} onClick={() => toggleIndicator(ind)}>×</span>
                </span>
              ))}
            </div>
          </>
        ) : (
          <span style={{ fontSize: '12px', color: '#26a69a', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ fontSize: '16px' }}>🤖</span> AI Mode: Auto-monitoring Support, Resistance & Patterns
          </span>
        )}

        <button
          style={{ ...(showDomPanel ? styles.activeBtn : styles.btn), marginLeft: 'auto', background: showDomPanel ? '#ff9800' : '#252a3a' }}
          onClick={() => setShowDomPanel(!showDomPanel)}
        >
          📊 Order Book
        </button>
      </div>
    </div>
  );
};

export default ChartToolbar;
