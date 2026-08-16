import React, { useState, useMemo } from 'react';

const AIMarketIntelligencePanel = ({
  mode, aiAnalysis, symbol, timeframe, currentPrice, data, patterns, marketStructure, indicators, indData
}) => {
  const [activeTab, setActiveTab] = useState('intelligence');
  const [collapsed, setCollapsed] = useState(false);

  // ─── Real-time calculated metrics from actual data ───
  const metrics = useMemo(() => {
    if (!data || data.length < 20) return null;

    const closes = data.map(d => d.close);
    const last = closes[closes.length - 1];
    const prev = closes[closes.length - 2];
    const open = data[data.length - 1].open;

    // Trend: compare last close vs 20-bar SMA
    const sma20 = closes.slice(-20).reduce((a, b) => a + b, 0) / 20;
    const sma50 = closes.length >= 50 ? closes.slice(-50).reduce((a, b) => a + b, 0) / 50 : sma20;

    // RSI calculation (last value)
    let gains = 0, losses = 0;
    const rsiPeriod = Math.min(14, closes.length - 1);
    for (let i = closes.length - rsiPeriod; i < closes.length; i++) {
      const diff = closes[i] - closes[i - 1];
      if (diff > 0) gains += diff; else losses -= diff;
    }
    const avgGain = gains / rsiPeriod;
    const avgLoss = losses / rsiPeriod;
    const rsi = avgLoss === 0 ? 100 : 100 - (100 / (1 + avgGain / avgLoss));

    // Volatility
    const atr = data.slice(-14).reduce((sum, d) => sum + (d.high - d.low), 0) / 14;
    const volatilityPct = (atr / last) * 100;

    // Volume analysis
    const volumes = data.map(d => d.volume || d.value || 0);
    const avgVol = volumes.slice(-20).reduce((a, b) => a + b, 0) / 20;
    const lastVol = volumes[volumes.length - 1];
    const volRatio = avgVol > 0 ? lastVol / avgVol : 1;

    // Trend strength composite score (0-100)
    let trendScore = 50;
    if (last > sma20) trendScore += 10; else trendScore -= 10;
    if (last > sma50) trendScore += 10; else trendScore -= 10;
    if (sma20 > sma50) trendScore += 8; else trendScore -= 8;
    if (rsi > 50) trendScore += 5; else trendScore -= 5;
    if (last > prev) trendScore += 5; else trendScore -= 5;
    if (volRatio > 1.2) trendScore += 7;
    if (last > open) trendScore += 5; else trendScore -= 5;
    trendScore = Math.max(0, Math.min(100, trendScore));

    // Market regime
    let regime, regimeColor;
    if (trendScore >= 70) { regime = '🟢 Strong Bullish'; regimeColor = '#00e676'; }
    else if (trendScore >= 55) { regime = '🟡 Mild Bullish'; regimeColor = '#69f0ae'; }
    else if (trendScore >= 45) { regime = '⚪ Rangebound'; regimeColor = '#ff9800'; }
    else if (trendScore >= 30) { regime = '🟠 Mild Bearish'; regimeColor = '#ff8a80'; }
    else { regime = '🔴 Strong Bearish'; regimeColor = '#ff1744'; }

    // AI Signal
    const bullSignals = [];
    const bearSignals = [];
    if (last > sma20) bullSignals.push('Price > SMA20'); else bearSignals.push('Price < SMA20');
    if (last > sma50) bullSignals.push('Price > SMA50'); else bearSignals.push('Price < SMA50');
    if (sma20 > sma50) bullSignals.push('Golden Cross (SMA20>50)'); else bearSignals.push('Death Cross (SMA20<50)');
    if (rsi > 50 && rsi < 70) bullSignals.push(`RSI Bullish (${rsi.toFixed(0)})`);
    else if (rsi >= 70) bearSignals.push(`RSI Overbought (${rsi.toFixed(0)})`);
    else if (rsi <= 30) bullSignals.push(`RSI Oversold (${rsi.toFixed(0)})`);
    else bearSignals.push(`RSI Bearish (${rsi.toFixed(0)})`);
    if (volRatio > 1.5) bullSignals.push(`Volume Surge (${(volRatio * 100).toFixed(0)}%)`);
    if (last > data[data.length - 1].open) bullSignals.push('Bullish Candle');
    else bearSignals.push('Bearish Candle');

    // Probability (based on signals)
    const bullProb = Math.round((bullSignals.length / (bullSignals.length + bearSignals.length)) * 100);

    // Support / Resistance from recent data
    const recentHighs = data.slice(-50).map(d => d.high);
    const recentLows = data.slice(-50).map(d => d.low);
    const resistance = Math.max(...recentHighs);
    const support = Math.min(...recentLows);

    // Risk/Reward
    const distToResistance = ((resistance - last) / last * 100).toFixed(2);
    const distToSupport = ((last - support) / last * 100).toFixed(2);

    // Day change
    const dayChange = ((last - prev) / prev * 100).toFixed(2);

    return {
      last, prev, open, sma20, sma50, rsi, atr, volatilityPct, volRatio,
      trendScore, regime, regimeColor, bullSignals, bearSignals, bullProb,
      resistance, support, distToResistance, distToSupport, dayChange,
      avgVol, lastVol
    };
  }, [data]);

  if (collapsed) {
    return (
      <div style={{ background: '#131722', borderLeft: '1px solid #2b313f', width: '36px', display: 'flex', flexDirection: 'column', alignItems: 'center', paddingTop: '12px', cursor: 'pointer' }}
        onClick={() => setCollapsed(false)}>
        <span style={{ writingMode: 'vertical-rl', color: '#787b86', fontSize: '11px', fontWeight: 600, letterSpacing: '1px' }}>AI PANEL</span>
        <span style={{ color: '#2962ff', fontSize: '16px', marginTop: '8px' }}>◀</span>
      </div>
    );
  }

  const s = {
    container: { background: '#0d1117', color: '#d1d4dc', borderLeft: '1px solid #1e222d', width: '340px', display: 'flex', flexDirection: 'column', overflowY: 'auto', fontSize: '12px' },
    header: { padding: '12px 14px', background: '#131722', borderBottom: '1px solid #1e222d', display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
    tabs: { display: 'flex', gap: '2px', background: '#1a1e2e', borderRadius: '6px', padding: '2px', margin: '10px 12px 4px' },
    tab: { flex: 1, padding: '6px 0', textAlign: 'center', fontSize: '10px', fontWeight: 700, borderRadius: '5px', cursor: 'pointer', border: 'none', transition: '0.15s', textTransform: 'uppercase', letterSpacing: '0.5px' },
    section: { margin: '6px 12px', background: '#131722', padding: '10px 12px', borderRadius: '8px', border: '1px solid #1e222d' },
    label: { fontSize: '10px', color: '#565d6e', textTransform: 'uppercase', fontWeight: 700, letterSpacing: '0.5px' },
    val: { fontSize: '13px', fontWeight: 700, color: '#e1e3e8', marginTop: '2px' },
    row: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 0' },
    green: { color: '#00e676' }, red: { color: '#ff1744' }, yellow: { color: '#ff9800' }, blue: { color: '#2979ff' },
    meter: { height: '4px', borderRadius: '2px', background: '#1e222d', overflow: 'hidden', marginTop: '4px' },
    pill: { display: 'inline-block', padding: '2px 6px', borderRadius: '3px', fontSize: '10px', fontWeight: 700 },
  };

  const tabList = [
    { id: 'intelligence', label: '🧠 Intel' },
    { id: 'signals', label: '📡 Signals' },
    { id: 'scenarios', label: '🎯 Trade' },
    ...(mode === 'ADVANCED' ? [{ id: 'quant', label: '📊 Quant' }] : []),
  ];

  return (
    <div style={s.container}>
      {/* Header */}
      <div style={s.header}>
        <div>
          <div style={{ color: '#fff', fontWeight: 800, fontSize: '13px' }}>AI Intelligence</div>
          <div style={{ color: '#565d6e', fontSize: '10px', marginTop: '2px' }}>{symbol?.replace('.NS', '')} · {timeframe}</div>
        </div>
        <span style={{ cursor: 'pointer', color: '#565d6e', fontSize: '16px' }} onClick={() => setCollapsed(true)}>▶</span>
      </div>

      {/* Tabs */}
      <div style={s.tabs}>
        {tabList.map(t => (
          <button key={t.id}
            style={{ ...s.tab, background: activeTab === t.id ? '#2962ff' : 'transparent', color: activeTab === t.id ? '#fff' : '#565d6e' }}
            onClick={() => setActiveTab(t.id)}>
            {t.label}
          </button>
        ))}
      </div>

      {!metrics ? (
        <div style={{ padding: '40px 20px', textAlign: 'center', color: '#565d6e' }}>⏳ Loading data...</div>
      ) : (
        <>
          {/* ════════════ INTELLIGENCE TAB ════════════ */}
          {activeTab === 'intelligence' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
              {/* Regime Card */}
              <div style={{ ...s.section, background: `linear-gradient(135deg, ${metrics.regimeColor}11, #131722)`, border: `1px solid ${metrics.regimeColor}33` }}>
                <div style={s.label}>Market Regime</div>
                <div style={{ fontSize: '16px', fontWeight: 800, color: metrics.regimeColor, marginTop: '4px' }}>{metrics.regime}</div>
                <div style={s.meter}>
                  <div style={{ width: `${metrics.trendScore}%`, height: '100%', borderRadius: '2px', background: `linear-gradient(90deg, #ff1744, #ff9800, #00e676)`, transition: '0.3s' }} />
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '4px' }}>
                  <span style={{ fontSize: '9px', color: '#565d6e' }}>Bearish</span>
                  <span style={{ fontSize: '10px', color: '#e1e3e8', fontWeight: 700 }}>{metrics.trendScore}/100</span>
                  <span style={{ fontSize: '9px', color: '#565d6e' }}>Bullish</span>
                </div>
              </div>

              {/* Key Metrics Grid */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2px', margin: '0 12px' }}>
                {[
                  { label: 'RSI (14)', value: metrics.rsi.toFixed(1), color: metrics.rsi > 70 ? '#ff1744' : metrics.rsi < 30 ? '#00e676' : '#e1e3e8' },
                  { label: 'Volatility', value: `${metrics.volatilityPct.toFixed(2)}%`, color: metrics.volatilityPct > 2 ? '#ff9800' : '#e1e3e8' },
                  { label: 'Vol Ratio', value: `${(metrics.volRatio * 100).toFixed(0)}%`, color: metrics.volRatio > 1.5 ? '#00e676' : '#e1e3e8' },
                  { label: 'Day Chg', value: `${metrics.dayChange > 0 ? '+' : ''}${metrics.dayChange}%`, color: metrics.dayChange > 0 ? '#00e676' : '#ff1744' },
                ].map((m, i) => (
                  <div key={i} style={{ background: '#131722', padding: '8px 10px', borderRadius: '6px', border: '1px solid #1e222d' }}>
                    <div style={s.label}>{m.label}</div>
                    <div style={{ fontSize: '15px', fontWeight: 800, color: m.color, marginTop: '2px' }}>{m.value}</div>
                  </div>
                ))}
              </div>

              {/* Support / Resistance */}
              <div style={s.section}>
                <div style={s.label}>Key Levels</div>
                <div style={{ marginTop: '6px' }}>
                  <div style={s.row}>
                    <span style={{ color: '#ef5350' }}>▲ Resistance</span>
                    <span style={{ fontWeight: 700, color: '#ef5350' }}>₹{metrics.resistance.toFixed(2)} ({metrics.distToResistance}%)</span>
                  </div>
                  <div style={{ height: '1px', background: '#1e222d', margin: '4px 0' }} />
                  <div style={s.row}>
                    <span style={{ color: '#26a69a' }}>▼ Support</span>
                    <span style={{ fontWeight: 700, color: '#26a69a' }}>₹{metrics.support.toFixed(2)} ({metrics.distToSupport}%)</span>
                  </div>
                </div>
              </div>

              {/* Patterns */}
              {patterns && patterns.length > 0 && (
                <div style={s.section}>
                  <div style={s.label}>Recent Patterns</div>
                  {patterns.slice(-4).reverse().map((p, i) => (
                    <div key={i} style={{ ...s.row, marginTop: '4px' }}>
                      <span>{p.type}</span>
                      <span style={{
                        ...s.pill,
                        background: p.signal === 'Bullish' ? '#00e67622' : p.signal === 'Bearish' ? '#ff174422' : '#ff980022',
                        color: p.signal === 'Bullish' ? '#00e676' : p.signal === 'Bearish' ? '#ff1744' : '#ff9800'
                      }}>{p.signal}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* ════════════ SIGNALS TAB ════════════ */}
          {activeTab === 'signals' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
              {/* Probability Meter */}
              <div style={s.section}>
                <div style={s.label}>AI Signal Probability</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '8px' }}>
                  <span style={{ color: '#ff1744', fontWeight: 700, fontSize: '11px' }}>SELL</span>
                  <div style={{ flex: 1, height: '8px', borderRadius: '4px', background: '#1e222d', overflow: 'hidden' }}>
                    <div style={{ width: `${metrics.bullProb}%`, height: '100%', borderRadius: '4px', background: 'linear-gradient(90deg, #ff1744, #ff9800, #00e676)', transition: '0.5s' }} />
                  </div>
                  <span style={{ color: '#00e676', fontWeight: 700, fontSize: '11px' }}>BUY</span>
                </div>
                <div style={{ textAlign: 'center', marginTop: '4px', fontSize: '18px', fontWeight: 800, color: metrics.bullProb >= 60 ? '#00e676' : metrics.bullProb <= 40 ? '#ff1744' : '#ff9800' }}>
                  {metrics.bullProb >= 60 ? '📈 BUY' : metrics.bullProb <= 40 ? '📉 SELL' : '⏸️ WAIT'} ({metrics.bullProb}%)
                </div>
              </div>

              {/* Bull Signals */}
              <div style={s.section}>
                <div style={{ ...s.label, color: '#00e676' }}>✅ Bullish Signals ({metrics.bullSignals.length})</div>
                {metrics.bullSignals.map((sig, i) => (
                  <div key={i} style={{ padding: '4px 0', fontSize: '11px', color: '#69f0ae', display: 'flex', gap: '6px' }}>
                    <span>✓</span> {sig}
                  </div>
                ))}
              </div>

              {/* Bear Signals */}
              <div style={s.section}>
                <div style={{ ...s.label, color: '#ff1744' }}>⚠️ Bearish Signals ({metrics.bearSignals.length})</div>
                {metrics.bearSignals.map((sig, i) => (
                  <div key={i} style={{ padding: '4px 0', fontSize: '11px', color: '#ff8a80', display: 'flex', gap: '6px' }}>
                    <span>✗</span> {sig}
                  </div>
                ))}
              </div>

              {/* Moving Average Table */}
              <div style={s.section}>
                <div style={s.label}>Moving Average Status</div>
                {[
                  { name: 'SMA 20', val: metrics.sma20, above: metrics.last > metrics.sma20 },
                  { name: 'SMA 50', val: metrics.sma50, above: metrics.last > metrics.sma50 },
                ].map((ma, i) => (
                  <div key={i} style={{ ...s.row, marginTop: '4px' }}>
                    <span>{ma.name}: ₹{ma.val.toFixed(2)}</span>
                    <span style={{ ...s.pill, background: ma.above ? '#00e67622' : '#ff174422', color: ma.above ? '#00e676' : '#ff1744' }}>
                      {ma.above ? '▲ Above' : '▼ Below'}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ════════════ TRADE SCENARIOS TAB ════════════ */}
          {activeTab === 'scenarios' && (() => {
            // ATR-based dynamic levels (NOT hardcoded percentages)
            const atrVal = metrics.atr;
            const isBullish = metrics.trendScore >= 50;
            const longEntry = currentPrice + atrVal * 0.2;
            const longT1 = currentPrice + atrVal * 1.5;
            const longT2 = currentPrice + atrVal * 3;
            const longSL = currentPrice - atrVal * 1;
            const longRisk = Math.abs(longEntry - longSL);
            const longReward = Math.abs(longT1 - longEntry);
            const longRR = longRisk > 0 ? (longReward / longRisk).toFixed(1) : '—';
            const shortEntry = currentPrice - atrVal * 0.2;
            const shortT1 = currentPrice - atrVal * 1.5;
            const shortT2 = currentPrice - atrVal * 3;
            const shortSL = currentPrice + atrVal * 1;
            const shortRisk = Math.abs(shortSL - shortEntry);
            const shortReward = Math.abs(shortEntry - shortT1);
            const shortRR = shortRisk > 0 ? (shortReward / shortRisk).toFixed(1) : '—';

            // Backend AI signal (if available)
            const aiAction = aiAnalysis?.action || (isBullish ? 'BUY' : 'SELL');
            const aiConf = aiAnalysis?.confidence ? `${(aiAnalysis.confidence * 100).toFixed(0)}%` : `${metrics.trendScore}%`;

            return (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
              {/* AI Recommendation */}
              {aiAnalysis && (
                <div style={{ ...s.section, background: 'linear-gradient(135deg, #2962ff11, #131722)', border: '1px solid #2962ff33' }}>
                  <div style={s.label}>🤖 Backend AI Signal</div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '6px' }}>
                    <span style={{ fontWeight: 800, fontSize: '16px', color: aiAction === 'BUY' ? '#00e676' : aiAction === 'SELL' ? '#ff1744' : '#ff9800' }}>
                      {aiAction}
                    </span>
                    <span style={{ ...s.pill, background: '#2962ff22', color: '#2979ff' }}>Confidence: {aiConf}</span>
                  </div>
                  {aiAnalysis?.reason && <div style={{ fontSize: '10px', color: '#8a92a5', marginTop: '4px' }}>{aiAnalysis.reason}</div>}
                </div>
              )}

              {/* ATR Info */}
              <div style={{ margin: '0 12px', fontSize: '10px', color: '#565d6e', display: 'flex', justifyContent: 'space-between' }}>
                <span>ATR(14): ₹{atrVal.toFixed(2)}</span>
                <span>Based on real volatility</span>
              </div>

              {/* Long Setup */}
              <div style={{ ...s.section, background: 'linear-gradient(135deg, #00e67609, #131722)', border: '1px solid #00e67633' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontWeight: 800, color: '#00e676', fontSize: '13px' }}>📈 LONG SETUP</span>
                  <span style={{ ...s.pill, background: '#00e676', color: '#000', fontWeight: 800 }}>BUY</span>
                </div>
                <div style={{ marginTop: '10px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                  <div>
                    <div style={s.label}>Entry (ATR×0.2)</div>
                    <div style={{ ...s.val, color: '#fff' }}>₹{longEntry.toFixed(2)}</div>
                  </div>
                  <div>
                    <div style={s.label}>Target 1 (ATR×1.5)</div>
                    <div style={{ ...s.val, color: '#00e676' }}>₹{longT1.toFixed(2)}</div>
                  </div>
                  <div>
                    <div style={s.label}>Target 2 (ATR×3)</div>
                    <div style={{ ...s.val, color: '#69f0ae' }}>₹{longT2.toFixed(2)}</div>
                  </div>
                  <div>
                    <div style={s.label}>Stop Loss (ATR×1)</div>
                    <div style={{ ...s.val, color: '#ff1744' }}>₹{longSL.toFixed(2)}</div>
                  </div>
                </div>
                <div style={{ marginTop: '8px', padding: '6px 8px', background: '#00e67611', borderRadius: '4px' }}>
                  <div style={{ ...s.row }}>
                    <span style={s.label}>Risk:Reward</span>
                    <span style={{ fontWeight: 800, color: '#00e676' }}>1 : {longRR}</span>
                  </div>
                </div>
              </div>

              {/* Short Setup */}
              <div style={{ ...s.section, background: 'linear-gradient(135deg, #ff174409, #131722)', border: '1px solid #ff174433' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontWeight: 800, color: '#ff1744', fontSize: '13px' }}>📉 SHORT SETUP</span>
                  <span style={{ ...s.pill, background: '#ff1744', color: '#fff', fontWeight: 800 }}>SELL</span>
                </div>
                <div style={{ marginTop: '10px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                  <div>
                    <div style={s.label}>Entry (ATR×0.2)</div>
                    <div style={{ ...s.val, color: '#fff' }}>₹{shortEntry.toFixed(2)}</div>
                  </div>
                  <div>
                    <div style={s.label}>Target 1 (ATR×1.5)</div>
                    <div style={{ ...s.val, color: '#ff1744' }}>₹{shortT1.toFixed(2)}</div>
                  </div>
                  <div>
                    <div style={s.label}>Target 2 (ATR×3)</div>
                    <div style={{ ...s.val, color: '#ff8a80' }}>₹{shortT2.toFixed(2)}</div>
                  </div>
                  <div>
                    <div style={s.label}>Stop Loss (ATR×1)</div>
                    <div style={{ ...s.val, color: '#00e676' }}>₹{shortSL.toFixed(2)}</div>
                  </div>
                </div>
                <div style={{ marginTop: '8px', padding: '6px 8px', background: '#ff174411', borderRadius: '4px' }}>
                  <div style={{ ...s.row }}>
                    <span style={s.label}>Risk:Reward</span>
                    <span style={{ fontWeight: 800, color: '#ff1744' }}>1 : {shortRR}</span>
                  </div>
                </div>
              </div>

              <div style={{ margin: '4px 12px', padding: '8px', background: '#1a1e2e', borderRadius: '6px', textAlign: 'center', fontSize: '9px', color: '#565d6e' }}>
                ⚠️ Levels based on ATR(14) volatility. Not guaranteed outcomes.
              </div>
            </div>
            );
          })()}

          {/* ════════════ QUANT TAB (Advanced Only) ════════════ */}
          {activeTab === 'quant' && mode === 'ADVANCED' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
              <div style={s.section}>
                <div style={s.label}>Quantitative Metrics</div>
                {[
                  { label: 'ATR (14)', value: `₹${metrics.atr.toFixed(2)}` },
                  { label: 'Volatility %', value: `${metrics.volatilityPct.toFixed(3)}%` },
                  { label: 'Avg Volume (20)', value: metrics.avgVol > 1e6 ? `${(metrics.avgVol / 1e6).toFixed(2)}M` : `${(metrics.avgVol / 1e3).toFixed(0)}K` },
                  { label: 'Current Volume', value: metrics.lastVol > 1e6 ? `${(metrics.lastVol / 1e6).toFixed(2)}M` : `${(metrics.lastVol / 1e3).toFixed(0)}K` },
                  { label: 'Vol/Avg Ratio', value: `${(metrics.volRatio * 100).toFixed(0)}%` },
                  { label: 'SMA20', value: `₹${metrics.sma20.toFixed(2)}` },
                  { label: 'SMA50', value: `₹${metrics.sma50.toFixed(2)}` },
                  { label: 'RSI (14)', value: metrics.rsi.toFixed(2) },
                  { label: '% from Resistance', value: `${metrics.distToResistance}%` },
                  { label: '% from Support', value: `${metrics.distToSupport}%` },
                ].map((m, i) => (
                  <div key={i} style={{ ...s.row, borderBottom: '1px solid #1a1e2e', padding: '5px 0' }}>
                    <span style={{ color: '#8a92a5' }}>{m.label}</span>
                    <span style={{ fontWeight: 700, color: '#e1e3e8', fontFamily: 'monospace' }}>{m.value}</span>
                  </div>
                ))}
              </div>

              {/* Market Structure */}
              {marketStructure && marketStructure.length > 0 && (
                <div style={s.section}>
                  <div style={s.label}>Market Structure (Last 5)</div>
                  {marketStructure.slice(-5).reverse().map((p, i) => (
                    <div key={i} style={{ ...s.row, marginTop: '3px' }}>
                      <span style={{
                        ...s.pill,
                        background: (p.type === 'HH' || p.type === 'HL') ? '#00e67622' : '#ff174422',
                        color: (p.type === 'HH' || p.type === 'HL') ? '#00e676' : '#ff1744'
                      }}>{p.type}</span>
                      <span style={{ fontFamily: 'monospace', color: '#8a92a5' }}>₹{p.price?.toFixed(2)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default AIMarketIntelligencePanel;
