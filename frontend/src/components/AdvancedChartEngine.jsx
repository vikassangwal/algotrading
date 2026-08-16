import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { createChart, CandlestickSeries, HistogramSeries, LineSeries, createSeriesMarkers } from 'lightweight-charts';
import ChartToolbar from './chart/ChartToolbar';
import AIMarketIntelligencePanel from './chart/AIMarketIntelligencePanel';
import Watchlist from './chart/Watchlist';
import QuickTradePanel from './chart/QuickTradePanel';
import {
  calculateSMA, calculateEMA, calculateMACD, calculateRSI, calculateBB,
  calculateVWAP, calculateATR, calculateSupertrend, calculateAIPredictor,
  calculateStochRSI, calculateIchimoku, calculateFibonacci, calculatePivotPoints, calculateADX
} from './chart/IndicatorsEngine';
import { detectCandlePatterns, detectMarketStructure } from './chart/PatternDetection';

const API_URL = (import.meta.env.VITE_API_URL || 'https://elco-backend.onrender.com').replace(/\/$/, '');

// ─── Heikin Ashi helper ───
const getHeikinAshiData = (src) => {
  if (!src.length) return [];
  const ha = [];
  let pO = src[0].open, pC = src[0].close;
  for (let i = 0; i < src.length; i++) {
    const { time, open, high, low, close } = src[i];
    const hC = (open + high + low + close) / 4;
    const hO = i === 0 ? (open + close) / 2 : (pO + pC) / 2;
    ha.push({ time, open: hO, high: Math.max(high, hO, hC), low: Math.min(low, hO, hC), close: hC });
    pO = hO; pC = hC;
  }
  return ha;
};

const AdvancedChartEngine = ({ token, globalSymbol }) => {
  const [mode, setMode] = useState('ADVANCED');
  const [activeChartType, setActiveChartType] = useState('candlestick');
  const [symbol, setSymbol] = useState(globalSymbol || 'RELIANCE');
  const [timeframe, setTimeframe] = useState('15m');
  const [isFullscreen, setIsFullscreen] = useState(false);

  const [indicators, setIndicators] = useState({
    vol: true, rsi: false, macd: false, sma20: false, sma50: false,
    ema9: false, bb: false, sr: false, vwap: false, supertrend: false, atr: false,
    aipredictor: false, stochrsi: false, ichimoku: false,
    fibonacci: false, pivots: false, adx: false
  });

  const [aiAnalysis, setAiAnalysis] = useState(null);
  const [showDomPanel, setShowDomPanel] = useState(false);
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [lastQuote, setLastQuote] = useState(null);
  const [crosshairData, setCrosshairData] = useState(null);

  const chartContainerRef = useRef(null);
  const chartRef = useRef(null);
  const seriesRef = useRef(null);
  const markersRef = useRef(null);
  const volumeSeriesRef = useRef(null);
  const lastCandleRef = useRef(null);
  const indRefs = useRef({});
  const wrapperRef = useRef(null);

  useEffect(() => {
    if (globalSymbol && globalSymbol !== symbol) setSymbol(globalSymbol);
  }, [globalSymbol]);

  // ─── Fetch history ───
  const fetchHistory = useCallback(async () => {
    if (!symbol) return;
    setLoading(true);
    try {
      const headers = token && token.length > 20 ? { 'Authorization': `Bearer ${token}` } : {};
      let period = '1mo';
      if (timeframe === '1m' || timeframe === '5m') period = '5d';
      else if (timeframe === '1d') period = '1y';
      else if (timeframe === '1wk') period = '2y';

      const sym = symbol.toUpperCase().replace('.NS', '');
      let res = await fetch(`${API_URL}/api/history/${sym}.NS?interval=${timeframe}&period=${period}`, { headers }).catch(() => null);
      if (!res || !res.ok) res = await fetch(`${API_URL}/api/history/${symbol.toUpperCase()}?interval=${timeframe}&period=${period}`, { headers }).catch(() => null);

      if (res && res.ok) {
        const raw = await res.json();
        const seen = new Set();
        const unique = [];
        for (const item of raw) {
          if (!seen.has(item.time)) {
            seen.add(item.time);
            unique.push({ ...item, volume: item.volume || item.value || 0 });
          }
        }
        unique.sort((a, b) => a.time - b.time);
        setData(unique);
        lastCandleRef.current = unique.length ? { ...unique[unique.length - 1] } : null;
      }
    } catch (err) { console.error("History fetch error:", err); }
    setLoading(false);
  }, [symbol, timeframe, token]);

  const fetchAnalysis = useCallback(async () => {
    if (!symbol) return;
    try {
      const res = await fetch(`${API_URL}/analyze/${symbol.toUpperCase().replace('.NS', '')}`);
      if (res.ok) setAiAnalysis(await res.json()); else setAiAnalysis(null);
    } catch { setAiAnalysis(null); }
  }, [symbol]);

  useEffect(() => { fetchHistory(); fetchAnalysis(); }, [fetchHistory, fetchAnalysis]);

  // ─── Keyboard shortcuts ───
  useEffect(() => {
    const handler = (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;
      const key = e.key.toLowerCase();
      const tfMap = { '1': '1m', '2': '5m', '3': '15m', '4': '1h', '5': '1d', '6': '1wk' };
      if (tfMap[key]) { setTimeframe(tfMap[key]); e.preventDefault(); }
      if (key === 'f') { setIsFullscreen(p => !p); e.preventDefault(); }
      if (key === 'b') { setMode(p => p === 'BEGINNER' ? 'ADVANCED' : 'BEGINNER'); e.preventDefault(); }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  // ─── Cleanup indicator series ───
  const cleanupIndicators = useCallback((chart) => {
    if (!chart) return;
    for (const key of Object.keys(indRefs.current)) {
      try { if (indRefs.current[key]) chart.removeSeries(indRefs.current[key]); } catch {}
      indRefs.current[key] = null;
    }
  }, []);

  // ─── MAIN CHART RENDER ───
  useEffect(() => {
    if (!chartContainerRef.current || data.length === 0) return;

    if (!chartRef.current) {
      chartRef.current = createChart(chartContainerRef.current, {
        layout: { background: { type: 'solid', color: '#0a0e17' }, textColor: '#787b86', fontSize: 11 },
        grid: { vertLines: { color: '#141820' }, horzLines: { color: '#141820' } },
        crosshair: { mode: 0, vertLine: { color: '#2962ff44', width: 1, style: 0, labelBackgroundColor: '#2962ff' }, horzLine: { color: '#2962ff44', width: 1, style: 0, labelBackgroundColor: '#2962ff' } },
        timeScale: { timeVisible: true, secondsVisible: false, borderColor: '#1e222d', rightOffset: 12 },
        rightPriceScale: { borderColor: '#1e222d', autoScale: true },
        leftPriceScale: { visible: false },
        watermark: { visible: true, text: symbol.toUpperCase().replace('.NS', ''), color: '#ffffff08', fontSize: 80, fontFamily: 'Arial', fontWeight: 'bold', horzAlign: 'center', vertAlign: 'center' },
      });

      // Crosshair move handler for OHLCV legend
      chartRef.current.subscribeCrosshairMove((param) => {
        if (!param || !param.time) { setCrosshairData(null); return; }
        const bar = data.find(d => d.time === param.time);
        if (bar) setCrosshairData(bar);
      });
    }

    const chart = chartRef.current;

    // Update watermark on symbol change
    chart.applyOptions({
      watermark: { text: symbol.toUpperCase().replace('.NS', ''), visible: true, color: '#ffffff08', fontSize: 80, fontFamily: 'Arial', fontWeight: 'bold', horzAlign: 'center', vertAlign: 'center' },
    });

    // Remove old series
    if (seriesRef.current) { try { chart.removeSeries(seriesRef.current); } catch {} seriesRef.current = null; }
    cleanupIndicators(chart);
    if (!volumeSeriesRef.current) {
      volumeSeriesRef.current = chart.addSeries(HistogramSeries, {
        color: '#26a69a', priceFormat: { type: 'volume' }, priceScaleId: '', scaleMargins: { top: 0.82, bottom: 0 }
      });
    }

    // ─── Main Series ───
    if (activeChartType === 'candlestick') {
      seriesRef.current = chart.addSeries(CandlestickSeries, {
        upColor: '#26a69a', downColor: '#ef5350', borderVisible: false,
        wickUpColor: '#26a69a', wickDownColor: '#ef5350'
      });
      seriesRef.current.setData(data);
    } else if (activeChartType === 'heikin_ashi') {
      seriesRef.current = chart.addSeries(CandlestickSeries, {
        upColor: '#26a69a', downColor: '#ef5350', borderVisible: false,
        wickUpColor: '#26a69a', wickDownColor: '#ef5350'
      });
      seriesRef.current.setData(getHeikinAshiData(data));
    } else {
      seriesRef.current = chart.addSeries(LineSeries, { color: '#2962FF', lineWidth: 2 });
      seriesRef.current.setData(data.map(d => ({ time: d.time, value: d.close })));
    }

    markersRef.current = createSeriesMarkers(seriesRef.current, []);

    // ─── Volume ───
    if (indicators.vol) {
      volumeSeriesRef.current.setData(data.map(d => ({
        time: d.time, value: d.volume || d.value || 0,
        color: d.close > d.open ? 'rgba(38,166,154,0.25)' : 'rgba(239,83,80,0.25)'
      })));
    } else { volumeSeriesRef.current.setData([]); }

    // ─── Add line indicator helper ───
    const addLine = (key, calcFn, opts) => {
      try {
        indRefs.current[key] = chart.addSeries(LineSeries, opts);
        indRefs.current[key].setData(calcFn());
      } catch (e) { console.warn(`Indicator ${key}:`, e); }
    };

    const adv = mode === 'ADVANCED';

    // Overlays
    if (indicators.sma20 && adv) addLine('sma20', () => calculateSMA(data, 20), { color: '#ffeb3b', lineWidth: 1, title: 'SMA 20' });
    if (indicators.sma50 && adv) addLine('sma50', () => calculateSMA(data, 50), { color: '#ff9800', lineWidth: 1, title: 'SMA 50' });
    if (indicators.ema9 && adv) addLine('ema9', () => calculateEMA(data, 9), { color: '#00bcd4', lineWidth: 1, title: 'EMA 9' });
    if (indicators.vwap && adv) addLine('vwap', () => calculateVWAP(data), { color: '#e040fb', lineWidth: 2, title: 'VWAP', lineStyle: 2 });
    if (indicators.atr && adv) addLine('atr', () => calculateATR(data), { color: '#ff5252', lineWidth: 1, priceScaleId: 'left', title: 'ATR' });

    // Bollinger Bands
    if (indicators.bb && adv) {
      const bb = calculateBB(data, 20, 2);
      addLine('bbU', () => bb.upper, { color: 'rgba(33,150,243,0.5)', lineWidth: 1, title: 'BB↑' });
      addLine('bbM', () => bb.middle, { color: 'rgba(33,150,243,0.3)', lineWidth: 1, lineStyle: 2, title: 'BB' });
      addLine('bbL', () => bb.lower, { color: 'rgba(33,150,243,0.5)', lineWidth: 1, title: 'BB↓' });
    }

    // Supertrend
    if (indicators.supertrend && adv) {
      const st = calculateSupertrend(data);
      if (st.length) {
        indRefs.current.supertrend = chart.addSeries(LineSeries, { lineWidth: 2, title: 'ST' });
        indRefs.current.supertrend.setData(st.map(d => ({ time: d.time, value: d.value, color: d.trend === 1 ? '#00e676' : '#ff1744' })));
      }
    }

    // AI Predictor
    if (indicators.aipredictor && adv) {
      const ai = calculateAIPredictor(data);
      if (ai.length) {
        indRefs.current.aipredictor = chart.addSeries(LineSeries, { lineWidth: 3, title: '🧠 AI', lineStyle: 0 });
        indRefs.current.aipredictor.setData(ai.map(d => ({ time: d.time, value: d.value, color: d.color })));
      }
    }

    // RSI
    if (indicators.rsi && adv) addLine('rsi', () => calculateRSI(data), { color: '#9c27b0', lineWidth: 1, priceScaleId: 'left', title: 'RSI' });

    // Stochastic RSI
    if (indicators.stochrsi && adv) {
      const sr = calculateStochRSI(data);
      if (sr.k.length) {
        addLine('stK', () => sr.k, { color: '#00bcd4', lineWidth: 1, priceScaleId: 'left', title: '%K' });
        addLine('stD', () => sr.d, { color: '#ff9800', lineWidth: 1, priceScaleId: 'left', title: '%D' });
      }
    }

    // MACD
    if (indicators.macd && adv) {
      const m = calculateMACD(data);
      if (m.macdLine.length) {
        addLine('macdL', () => m.macdLine, { color: '#2196f3', lineWidth: 1, priceScaleId: 'left', title: 'MACD' });
        addLine('macdS', () => m.macdSignal, { color: '#f44336', lineWidth: 1, priceScaleId: 'left', title: 'Sig' });
      }
    }

    // Ichimoku
    if (indicators.ichimoku && adv) {
      const ich = calculateIchimoku(data);
      if (ich.tenkan.length) {
        addLine('ichT', () => ich.tenkan, { color: '#2196f3', lineWidth: 1, title: 'Tenkan' });
        addLine('ichK', () => ich.kijun, { color: '#ef5350', lineWidth: 1, title: 'Kijun' });
        addLine('ichA', () => ich.spanA, { color: 'rgba(76,175,80,0.35)', lineWidth: 1, title: 'SpanA' });
        addLine('ichB', () => ich.spanB, { color: 'rgba(244,67,54,0.35)', lineWidth: 1, title: 'SpanB' });
      }
    }

    // Fibonacci Retracement
    if (indicators.fibonacci && adv) {
      const fibs = calculateFibonacci(data);
      fibs.forEach((f, i) => {
        addLine(`fib${i}`, () => f.data, { color: f.color, lineWidth: 1, lineStyle: 2, title: `Fib ${f.label}` });
      });
    }

    // Pivot Points
    if (indicators.pivots && adv) {
      const pvts = calculatePivotPoints(data);
      pvts.forEach((p, i) => {
        addLine(`pvt${i}`, () => p.data, { color: p.color, lineWidth: 1, lineStyle: 1, title: p.label });
      });
    }

    // ADX
    if (indicators.adx && adv) {
      const adxData = calculateADX(data);
      if (adxData.adx.length) {
        addLine('adxLine', () => adxData.adx, { color: '#ff9800', lineWidth: 2, priceScaleId: 'left', title: 'ADX' });
        addLine('pdi', () => adxData.pdi, { color: '#00e676', lineWidth: 1, priceScaleId: 'left', title: '+DI' });
        addLine('mdi', () => adxData.mdi, { color: '#ff1744', lineWidth: 1, priceScaleId: 'left', title: '-DI' });
      }
    }

    // Support / Resistance
    if (indicators.sr || mode === 'BEGINNER') {
      const hi = Math.max(...data.map(d => d.high));
      const lo = Math.min(...data.map(d => d.low));
      addLine('srH', () => [{ time: data[0].time, value: hi }, { time: data[data.length - 1].time, value: hi }], { color: '#ef5350', lineWidth: 1, lineStyle: 2, title: 'R' });
      addLine('srL', () => [{ time: data[0].time, value: lo }, { time: data[data.length - 1].time, value: lo }], { color: '#26a69a', lineWidth: 1, lineStyle: 2, title: 'S' });
    }

    // ─── Pattern Markers ───
    const markers = [];
    if (adv) {
      for (const p of detectCandlePatterns(data)) {
        markers.push({ time: p.time, position: p.signal === 'Bullish' ? 'belowBar' : 'aboveBar', color: p.signal === 'Bullish' ? '#26a69a' : p.signal === 'Bearish' ? '#ef5350' : '#ff9800', shape: p.signal === 'Bullish' ? 'arrowUp' : p.signal === 'Bearish' ? 'arrowDown' : 'circle', text: p.type });
      }
      for (const p of detectMarketStructure(data)) {
        markers.push({ time: p.time, position: (p.type === 'HL' || p.type === 'LL') ? 'belowBar' : 'aboveBar', color: '#2196f3', shape: 'circle', text: p.type });
      }
    }
    // Deduplicate
    markers.sort((a, b) => a.time - b.time);
    const uMarkers = [];
    for (const m of markers) {
      const last = uMarkers[uMarkers.length - 1];
      if (last && last.time === m.time) last.text += ` | ${m.text}`;
      else uMarkers.push({ ...m });
    }
    markersRef.current.setMarkers(uMarkers);

    // Resize
    const onResize = () => {
      if (chartContainerRef.current) chart.applyOptions({ width: chartContainerRef.current.clientWidth, height: chartContainerRef.current.clientHeight });
    };
    window.addEventListener('resize', onResize);
    onResize();
    return () => window.removeEventListener('resize', onResize);
  }, [data, activeChartType, indicators, mode, cleanupIndicators, symbol]);

  // ─── Live quote polling ───
  useEffect(() => {
    if (!symbol) return;
    let active = true;
    const poll = async () => {
      try {
        const r = await fetch(`${API_URL}/api/quote/${symbol.toUpperCase().replace('.NS', '')}`);
        if (r.ok && active) setLastQuote(await r.json());
      } catch {}
    };
    poll();
    const iv = setInterval(poll, 8000);
    return () => { active = false; clearInterval(iv); };
  }, [symbol]);

  const patternsMemo = useMemo(() => detectCandlePatterns(data), [data]);
  const msMemo = useMemo(() => detectMarketStructure(data), [data]);
  const toggleIndicator = (ind) => setIndicators(p => ({ ...p, [ind]: !p[ind] }));

  // Display bar (crosshair or last candle)
  const displayBar = crosshairData || (data.length ? data[data.length - 1] : null);

  const st = {
    wrapper: {
      display: 'flex', flexDirection: 'column',
      height: isFullscreen ? '100vh' : '82vh',
      background: '#0a0e17', borderRadius: isFullscreen ? 0 : '10px',
      overflow: 'hidden', border: isFullscreen ? 'none' : '1px solid #1e222d',
      position: isFullscreen ? 'fixed' : 'relative',
      top: isFullscreen ? 0 : 'auto', left: isFullscreen ? 0 : 'auto',
      width: isFullscreen ? '100vw' : 'auto',
      zIndex: isFullscreen ? 9999 : 'auto',
    },
    main: { display: 'flex', flex: 1, overflow: 'hidden' },
    chartArea: { flex: 1, position: 'relative', background: '#0a0e17' },
    loading: { position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%,-50%)', color: '#787b86', zIndex: 10, fontSize: '14px' },
    legend: {
      position: 'absolute', top: '8px', left: '12px', zIndex: 10,
      background: 'rgba(10,14,23,0.85)', padding: '8px 12px', borderRadius: '8px',
      border: '1px solid #1e222d', backdropFilter: 'blur(12px)',
      display: 'flex', flexDirection: 'column', gap: '4px',
    },
    legendRow: { display: 'flex', alignItems: 'center', gap: '12px', fontSize: '12px' },
    ohlcLabel: { color: '#565d6e', fontSize: '10px', fontWeight: 600 },
    fullscreenBtn: {
      position: 'absolute', top: '8px', right: '12px', zIndex: 10,
      background: 'rgba(10,14,23,0.85)', color: '#787b86', border: '1px solid #1e222d',
      padding: '6px 10px', borderRadius: '6px', cursor: 'pointer', fontSize: '14px',
      backdropFilter: 'blur(8px)',
    },
    shortcutHint: {
      position: 'absolute', bottom: '8px', left: '12px', zIndex: 10,
      fontSize: '9px', color: '#363c4e',
    }
  };

  // Screenshot function
  const takeScreenshot = () => {
    if (!chartContainerRef.current) return;
    const canvas = chartContainerRef.current.querySelector('canvas');
    if (canvas) {
      const link = document.createElement('a');
      link.download = `${symbol.replace('.NS','')}_${timeframe}_${new Date().toISOString().slice(0,10)}.png`;
      link.href = canvas.toDataURL('image/png');
      link.click();
    }
  };

  return (
    <div style={st.wrapper} ref={wrapperRef}>
      <ChartToolbar
        mode={mode} setMode={setMode}
        symbol={symbol} setSymbol={setSymbol} fetchHistory={fetchHistory}
        timeframe={timeframe} setTimeframe={setTimeframe}
        activeChartType={activeChartType} setActiveChartType={setActiveChartType}
        indicators={indicators} toggleIndicator={toggleIndicator}
        showDomPanel={showDomPanel} setShowDomPanel={setShowDomPanel}
      />

      <div style={st.main}>
        {/* Watchlist Sidebar */}
        <Watchlist onSymbolClick={(s) => { setSymbol(s); setTimeout(fetchHistory, 100); }} currentSymbol={symbol} />

        <div style={st.chartArea}>
          {loading && data.length === 0 && <div style={st.loading}>⏳ Loading...</div>}

          {/* OHLCV Legend */}
          {displayBar && (
            <div style={st.legend}>
              <div style={st.legendRow}>
                <span style={{ color: '#fff', fontWeight: 800, fontSize: '15px' }}>
                  {symbol.toUpperCase().replace('.NS', '')}
                </span>
                <span style={{ color: '#565d6e', fontSize: '10px' }}>{timeframe.toUpperCase()}</span>
                {lastQuote && (
                  <span style={{
                    fontSize: '11px', fontWeight: 700, padding: '1px 6px', borderRadius: '3px',
                    background: (lastQuote.change_pct || 0) >= 0 ? 'rgba(38,166,154,0.15)' : 'rgba(239,83,80,0.15)',
                    color: (lastQuote.change_pct || 0) >= 0 ? '#26a69a' : '#ef5350'
                  }}>
                    {(lastQuote.change_pct || 0) >= 0 ? '+' : ''}{lastQuote.change_pct}%
                  </span>
                )}
                {lastQuote?.delayed && <span style={{ fontSize: '8px', color: '#565d6e', background: '#1e222d', padding: '1px 4px', borderRadius: '2px' }}>DELAYED</span>}
              </div>
              <div style={st.legendRow}>
                <span style={st.ohlcLabel}>O</span>
                <span style={{ color: displayBar.close >= displayBar.open ? '#26a69a' : '#ef5350', fontWeight: 600, fontFamily: 'monospace' }}>{displayBar.open?.toFixed(2)}</span>
                <span style={st.ohlcLabel}>H</span>
                <span style={{ color: displayBar.close >= displayBar.open ? '#26a69a' : '#ef5350', fontWeight: 600, fontFamily: 'monospace' }}>{displayBar.high?.toFixed(2)}</span>
                <span style={st.ohlcLabel}>L</span>
                <span style={{ color: displayBar.close >= displayBar.open ? '#26a69a' : '#ef5350', fontWeight: 600, fontFamily: 'monospace' }}>{displayBar.low?.toFixed(2)}</span>
                <span style={st.ohlcLabel}>C</span>
                <span style={{ color: displayBar.close >= displayBar.open ? '#26a69a' : '#ef5350', fontWeight: 800, fontFamily: 'monospace', fontSize: '14px' }}>{displayBar.close?.toFixed(2)}</span>
                <span style={st.ohlcLabel}>V</span>
                <span style={{ color: '#787b86', fontFamily: 'monospace' }}>
                  {(displayBar.volume || displayBar.value || 0) > 1e6 ? `${((displayBar.volume || displayBar.value || 0) / 1e6).toFixed(2)}M` : `${((displayBar.volume || displayBar.value || 0) / 1e3).toFixed(0)}K`}
                </span>
              </div>
            </div>
          )}

          {/* Top-right buttons */}
          <div style={{ position: 'absolute', top: '8px', right: '12px', zIndex: 10, display: 'flex', gap: '4px' }}>
            <button style={st.fullscreenBtn} onClick={takeScreenshot} title="Screenshot (S)">📷</button>
            <button style={st.fullscreenBtn} onClick={() => setIsFullscreen(p => !p)} title="Fullscreen (F)">
              {isFullscreen ? '⊡' : '⛶'}
            </button>
          </div>

          <div ref={chartContainerRef} style={{ width: '100%', height: '100%' }} />

          <div style={st.shortcutHint}>
            1-6: Timeframe · F: Fullscreen · B: Mode · S: Screenshot
          </div>
        </div>

        <AIMarketIntelligencePanel
          mode={mode}
          aiAnalysis={aiAnalysis}
          symbol={symbol}
          timeframe={timeframe}
          currentPrice={lastCandleRef.current?.close || lastQuote?.price || 0}
          data={data}
          patterns={patternsMemo}
          marketStructure={msMemo}
          indicators={indicators}
        />
      </div>

      {/* Quick Trade Panel at bottom */}
      <QuickTradePanel
        symbol={symbol}
        currentPrice={lastCandleRef.current?.close || lastQuote?.price || 0}
        token={token}
        atr={data.length > 0 ? (calculateATR(data).slice(-1)[0]?.value || 0) : null}
      />
    </div>
  );
};

export default AdvancedChartEngine;
