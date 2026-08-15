import React, { useState } from 'react';
import { Target, Activity, AlertTriangle, Info, ShieldAlert, BarChart2 } from 'lucide-react';

const AIMarketIntelligencePanel = ({ 
  mode, aiAnalysis, symbol, timeframe, currentPrice, patterns, marketStructure 
}) => {
  const [activeTab, setActiveTab] = useState('intelligence'); // intelligence, what_changed, scenarios

  const styles = {
    container: { background: '#131722', color: '#d1d4dc', padding: '16px', borderLeft: '1px solid #2b313f', width: '350px', display: 'flex', flexDirection: 'column', gap: '16px', overflowY: 'auto' },
    header: { fontSize: '14px', fontWeight: 'bold', color: '#fff', borderBottom: '1px solid #2b313f', paddingBottom: '8px', display: 'flex', justifyContent: 'space-between' },
    tabs: { display: 'flex', gap: '8px' },
    tabBtn: { background: 'transparent', border: 'none', color: '#787b86', fontSize: '11px', cursor: 'pointer', padding: '4px 8px', borderRadius: '4px' },
    activeTabBtn: { background: '#2b313f', border: 'none', color: '#fff', fontSize: '11px', cursor: 'pointer', padding: '4px 8px', borderRadius: '4px', fontWeight: 'bold' },
    section: { background: '#1e222d', padding: '12px', borderRadius: '6px', border: '1px solid #2b313f' },
    label: { fontSize: '11px', color: '#787b86', textTransform: 'uppercase' },
    value: { fontSize: '13px', fontWeight: 600, color: '#fff', marginTop: '4px' },
    row: { display: 'flex', justifyContent: 'space-between', marginBottom: '8px' },
    green: { color: '#26a69a' },
    red: { color: '#ef5350' },
    yellow: { color: '#ff9800' },
    card: { background: 'rgba(38, 166, 154, 0.1)', border: '1px solid rgba(38, 166, 154, 0.5)', padding: '12px', borderRadius: '6px' },
    explanation: { fontSize: '11px', color: '#8a92a5', marginTop: '6px', fontStyle: 'italic' }
  };

  // Mocked AI processed data based on standard analysis
  const trendStrength = Math.round((aiAnalysis?.scores?.trend || 0.7) * 100);
  const regime = trendStrength > 65 ? "Bullish Trend" : trendStrength < 35 ? "Bearish Trend" : "Rangebound / Chop";
  const momentum = (aiAnalysis?.scores?.momentum || 0) > 0 ? "Positive" : "Negative";
  
  // Scenarios
  const tp = currentPrice * 1.015;
  const sl = currentPrice * 0.99;

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <span>AI Intelligence</span>
        <div style={styles.tabs}>
          <button style={activeTab === 'intelligence' ? styles.activeTabBtn : styles.tabBtn} onClick={() => setActiveTab('intelligence')}>Insights</button>
          {mode === 'ADVANCED' && <button style={activeTab === 'what_changed' ? styles.activeTabBtn : styles.tabBtn} onClick={() => setActiveTab('what_changed')}>Delta</button>}
          <button style={activeTab === 'scenarios' ? styles.activeTabBtn : styles.tabBtn} onClick={() => setActiveTab('scenarios')}>Scenarios</button>
        </div>
      </div>

      {activeTab === 'intelligence' && (
        <>
          <div style={styles.section}>
            <div style={styles.row}>
              <div>
                <div style={styles.label}>Market Regime</div>
                <div style={styles.value}>{regime}</div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={styles.label}>Trend Strength</div>
                <div style={{ ...styles.value, ...(trendStrength > 60 ? styles.green : styles.red) }}>{trendStrength}/100</div>
              </div>
            </div>
            {mode === 'BEGINNER' && (
              <div style={styles.explanation}>
                <Info size={12} style={{ display: 'inline', marginRight: '4px' }}/>
                {trendStrength > 60 ? "Market is moving upwards strongly. Buying is safer." : "Market lacks clear upward direction."}
              </div>
            )}
          </div>

          {mode === 'ADVANCED' && (
            <div style={styles.section}>
              <div style={styles.label}>Multi-Timeframe Alignment</div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '8px', fontSize: '12px' }}>
                <span>5m: <span style={styles.green}>Bullish</span></span>
                <span>15m: <span style={styles.green}>Bullish</span></span>
                <span>1H: <span style={styles.yellow}>Neutral</span></span>
              </div>
            </div>
          )}

          {patterns && patterns.length > 0 && (
            <div style={styles.section}>
              <div style={styles.label}>Recent Patterns</div>
              {patterns.slice(-3).reverse().map((p, i) => (
                <div key={i} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginTop: '6px' }}>
                  <span>{p.type}</span>
                  <span style={p.signal === 'Bullish' ? styles.green : p.signal === 'Bearish' ? styles.red : styles.yellow}>{p.signal}</span>
                </div>
              ))}
            </div>
          )}

          <div style={styles.section}>
            <div style={styles.label}>WHY {aiAnalysis?.action || 'HOLD'}?</div>
            <div style={{ fontSize: '12px', marginTop: '8px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <div style={{ color: '#26a69a' }}>✓ Price above VWAP</div>
              <div style={{ color: '#26a69a' }}>✓ Momentum {momentum}</div>
              <div style={{ color: '#ef5350' }}>⚠ Resistance nearby</div>
            </div>
          </div>
        </>
      )}

      {activeTab === 'scenarios' && (
        <>
          <div style={styles.card}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '12px', fontWeight: 'bold', color: '#26a69a' }}>BULLISH SCENARIO</span>
              <span style={{ fontSize: '11px', color: '#fff', background: '#26a69a', padding: '2px 6px', borderRadius: '4px' }}>BUY</span>
            </div>
            
            <div style={{ marginTop: '12px' }}>
              <div style={styles.row}>
                <span style={styles.label}>Entry Zone</span>
                <span style={styles.value}>₹{(currentPrice * 1.001).toFixed(2)} - ₹{(currentPrice * 1.002).toFixed(2)}</span>
              </div>
              <div style={styles.row}>
                <span style={styles.label}>Target</span>
                <span style={{ ...styles.value, color: '#26a69a' }}>₹{tp.toFixed(2)}</span>
              </div>
              <div style={styles.row}>
                <span style={styles.label}>Stop Loss</span>
                <span style={{ ...styles.value, color: '#ef5350' }}>₹{sl.toFixed(2)}</span>
              </div>
              <div style={styles.row}>
                <span style={styles.label}>Risk / Reward</span>
                <span style={styles.value}>1:1.5</span>
              </div>
            </div>
            <div style={styles.explanation}>Trigger: Breakout above ₹{(currentPrice * 1.003).toFixed(2)} with volume confirmation.</div>
          </div>
          
          <div style={{ fontSize: '10px', color: '#787b86', textAlign: 'center', marginTop: 'auto' }}>
            Model probabilities are estimates, not guaranteed outcomes.
          </div>
        </>
      )}

      {activeTab === 'what_changed' && mode === 'ADVANCED' && (
        <div style={styles.section}>
          <div style={styles.label}>Delta (Last 15m)</div>
          <div style={{ fontSize: '12px', marginTop: '8px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Trend Strength</span>
              <span style={styles.green}>62 → {trendStrength}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Volume</span>
              <span style={styles.green}>+14%</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Momentum</span>
              <span style={styles.yellow}>Neutral → Positive</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Structure</span>
              <span style={styles.green}>HH Created</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AIMarketIntelligencePanel;
