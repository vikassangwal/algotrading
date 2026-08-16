import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { createChart, CandlestickSeries, HistogramSeries, LineSeries, createSeriesMarkers } from 'lightweight-charts';
import ChartToolbar from './chart/ChartToolbar';
import AIMarketIntelligencePanel from './chart/AIMarketIntelligencePanel';
import {
  calculateSMA, calculateEMA, calculateMACD, calculateRSI, calculateBB,
  calculateVWAP, calculateATR, calculateSupertrend, calculateAIPredictor,
  calculateStochRSI, calculateIchimoku
} from './chart/IndicatorsEngine';
import { detectCandlePatterns, detectMarketStructure } from './chart/PatternDetection';

const API_URL = (import.meta.env.VITE_API_URL || 'https://elco-backend.onrender.com').replace(/\/$/, '');

// ─── Heikin Ashi helper (pure function, declared before use) ───
const getHeikinAshiData = (sourceData) => {
  if (sourceData.length === 0) return [];
  const haData = [];
  let prevHAOpen = sourceData[0].open;
  let prevHAClose = sourceData[0].close;
  for (let i = 0; i < sourceData.length; i++) {
    const { time, open, high, low, close } = sourceData[i];
    const haClose = (open + high + low + close) / 4;
    const haOpen = i === 0 ? (open + close) / 2 : (prevHAOpen + prevHAClose) / 2;
    haData.push({ time, open: haOpen, high: Math.max(high, haOpen, haClose), low: Math.min(low, haOpen, haClose), close: haClose });
    prevHAOpen = haOpen;
    prevHAClose = haClose;
  }
  return haData;
};

const AdvancedChartEngine = ({ token, globalSymbol }) => {
  const [mode, setMode] = useState('ADVANCED');
  const [activeChartType, setActiveChartType] = useState('candlestick');
  const [symbol, setSymbol] = useState(globalSymbol || 'RELIANCE');
  const [timeframe, setTimeframe] = useState('15m');

  const [indicators, setIndicators] = useState({
    vol: true, rsi: false, macd: false, sma20: false, sma50: false,
    ema9: false, bb: false, sr: false, vwap: false, supertrend: false, atr: false,
    aipredictor: false, stochrsi: false, ichimoku: false
  });

  const [aiAnalysis, setAiAnalysis] = useState(null);
  const [showDomPanel, setShowDomPanel] = useState(false);
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [lastQuote, setLastQuote] = useState(null);

  const chartContainerRef = useRef(null);
  const chartRef = useRef(null);
  const seriesRef = useRef(null);
  const markersRef = useRef(null);
  const volumeSeriesRef = useRef(null);
  const lastCandleRef = useRef(null);

  // Track all indicator series for proper cleanup
  const indRefs = useRef({});

  useEffect(() => {
    if (globalSymbol && globalSymbol !== symbol) setSymbol(globalSymbol);
  }, [globalSymbol]);

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
      if (!res || !res.ok) {
        res = await fetch(`${API_URL}/api/history/${symbol.toUpperCase()}?interval=${timeframe}&period=${period}`, { headers }).catch(() => null);
      }

      if (res && res.ok) {
        const historyData = await res.json();
        // Deduplicate and sort by time
        const seen = new Set();
        const uniqueData = [];
        for (const item of historyData) {
          if (!seen.has(item.time)) {
            seen.add(item.time);
            // Normalize volume field: API sends "value" for volume
            uniqueData.push({
              ...item,
              volume: item.volume || item.value || 0
            });
          }
        }
        uniqueData.sort((a, b) => a.time - b.time);
        setData(uniqueData);
        lastCandleRef.current = uniqueData.length ? { ...uniqueData[uniqueData.length - 1] } : null;
      }
    } catch (err) {
      console.error("Error fetching history:", err);
    }
    setLoading(false);
  }, [symbol, timeframe, token]);

  const fetchAnalysis = useCallback(async () => {
    if (!symbol) return;
    try {
      const res = await fetch(`${API_URL}/analyze/${symbol.toUpperCase().replace('.NS', '')}`);
      if (res.ok) setAiAnalysis(await res.json());
      else setAiAnalysis(null);
    } catch { setAiAnalysis(null); }
  }, [symbol]);

  useEffect(() => {
    fetchHistory();
    fetchAnalysis();
  }, [fetchHistory, fetchAnalysis]);

  // ─── CLEANUP: Remove all indicator series from chart ───
  const cleanupIndicators = useCallback((chart) => {
    if (!chart) return;
    const refs = indRefs.current;
    for (const key of Object.keys(refs)) {
      try {
        if (refs[key]) {
          chart.removeSeries(refs[key]);
        }
      } catch (e) { /* series already removed */ }
      refs[key] = null;
    }
  }, []);

  // ─── MAIN CHART RENDER EFFECT ───
  useEffect(() => {
    if (!chartContainerRef.current || data.length === 0) return;

    // Create chart if not exists
    if (!chartRef.current) {
      chartRef.current = createChart(chartContainerRef.current, {
        layout: { background: { type: 'solid', color: '#131722' }, textColor: '#d1d4dc' },
        grid: { vertLines: { color: '#1e222d' }, horzLines: { color: '#1e222d' } },
        crosshair: { mode: 1 },
        timeScale: { timeVisible: true, secondsVisible: false, borderColor: '#2b313f' },
        rightPriceScale: { borderColor: '#2b313f', autoScale: true },
        leftPriceScale: { visible: false },
      });
    }

    const chart = chartRef.current;

    // Remove old main series + indicators
    if (seriesRef.current) {
      try { chart.removeSeries(seriesRef.current); } catch {}
      seriesRef.current = null;
    }
    cleanupIndicators(chart);

    // Create volume series if needed
    if (!volumeSeriesRef.current) {
      volumeSeriesRef.current = chart.addSeries(HistogramSeries, {
        color: '#26a69a', priceFormat: { type: 'volume' }, priceScaleId: '', scaleMargins: { top: 0.8, bottom: 0 }
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
        time: d.time,
        value: d.volume || d.value || 0,
        color: d.close > d.open ? 'rgba(38,166,154,0.3)' : 'rgba(239,83,80,0.3)'
      })));
    } else {
      volumeSeriesRef.current.setData([]);
    }

    // ─── Helper to add/remove line indicators safely ───
    const addLine = (key, calcFn, opts) => {
      if (mode === 'ADVANCED' || key === 'sr') {
        try {
          indRefs.current[key] = chart.addSeries(LineSeries, opts);
          indRefs.current[key].setData(calcFn());
        } catch (e) { console.warn(`Indicator ${key} failed:`, e); }
      }
    };

    // ─── Overlay Indicators (on price scale) ───
    if (indicators.sma20) addLine('sma20', () => calculateSMA(data, 20), { color: '#ffeb3b', lineWidth: 2, title: 'SMA 20' });
    if (indicators.sma50) addLine('sma50', () => calculateSMA(data, 50), { color: '#ff9800', lineWidth: 2, title: 'SMA 50' });
    if (indicators.ema9) addLine('ema9', () => calculateEMA(data, 9), { color: '#00bcd4', lineWidth: 2, title: 'EMA 9' });
    if (indicators.vwap) addLine('vwap', () => calculateVWAP(data), { color: '#e040fb', lineWidth: 2, title: 'VWAP' });
    if (indicators.atr) addLine('atr', () => calculateATR(data), { color: '#ff5252', lineWidth: 2, priceScaleId: 'left', title: 'ATR' });

    // Bollinger Bands
    if (indicators.bb && mode === 'ADVANCED') {
      const bbData = calculateBB(data, 20, 2);
      addLine('bbUpper', () => bbData.upper, { color: 'rgba(33,150,243,0.5)', lineWidth: 1, title: 'BB Upper' });
      addLine('bbMiddle', () => bbData.middle, { color: 'rgba(33,150,243,0.3)', lineWidth: 1, lineStyle: 2, title: 'BB Mid' });
      addLine('bbLower', () => bbData.lower, { color: 'rgba(33,150,243,0.5)', lineWidth: 1, title: 'BB Lower' });
    }

    // Supertrend
    if (indicators.supertrend && mode === 'ADVANCED') {
      const stData = calculateSupertrend(data);
      if (stData.length > 0) {
        indRefs.current.supertrend = chart.addSeries(LineSeries, { lineWidth: 2, title: 'Supertrend' });
        indRefs.current.supertrend.setData(stData.map(d => ({
          time: d.time, value: d.value,
          color: d.trend === 1 ? '#00e676' : '#ff1744'
        })));
      }
    }

    // AI Predictor
    if (indicators.aipredictor && mode === 'ADVANCED') {
      const aiData = calculateAIPredictor(data);
      if (aiData.length > 0) {
        indRefs.current.aipredictor = chart.addSeries(LineSeries, {
          lineWidth: 3, title: 'AI Predictor', lineStyle: 0
        });
        indRefs.current.aipredictor.setData(aiData.map(d => ({
          time: d.time, value: d.value, color: d.color
        })));
      }
    }

    // RSI
    if (indicators.rsi && mode === 'ADVANCED') {
      addLine('rsi', () => calculateRSI(data), { color: '#9c27b0', lineWidth: 2, priceScaleId: 'left', title: 'RSI' });
    }

    // Stochastic RSI
    if (indicators.stochrsi && mode === 'ADVANCED') {
      const sr = calculateStochRSI(data);
      if (sr.k.length > 0) {
        addLine('stochK', () => sr.k, { color: '#00bcd4', lineWidth: 1, priceScaleId: 'left', title: '%K' });
        addLine('stochD', () => sr.d, { color: '#ff9800', lineWidth: 1, priceScaleId: 'left', title: '%D' });
      }
    }

    // MACD
    if (indicators.macd && mode === 'ADVANCED') {
      const { macdLine, macdSignal } = calculateMACD(data);
      if (macdLine.length > 0) {
        addLine('macdLine', () => macdLine, { color: '#2196f3', lineWidth: 2, priceScaleId: 'left', title: 'MACD' });
        addLine('macdSignal', () => macdSignal, { color: '#f44336', lineWidth: 2, priceScaleId: 'left', title: 'Signal' });
      }
    }

    // Ichimoku
    if (indicators.ichimoku && mode === 'ADVANCED') {
      const ich = calculateIchimoku(data);
      if (ich.tenkan.length > 0) {
        addLine('ichTenkan', () => ich.tenkan, { color: '#2196f3', lineWidth: 1, title: 'Tenkan' });
        addLine('ichKijun', () => ich.kijun, { color: '#ef5350', lineWidth: 1, title: 'Kijun' });
        addLine('ichSpanA', () => ich.spanA, { color: 'rgba(76,175,80,0.4)', lineWidth: 1, title: 'Span A' });
        addLine('ichSpanB', () => ich.spanB, { color: 'rgba(244,67,54,0.4)', lineWidth: 1, title: 'Span B' });
      }
    }

    // Support / Resistance
    if (indicators.sr || mode === 'BEGINNER') {
      const maxHigh = Math.max(...data.map(d => d.high));
      const minLow = Math.min(...data.map(d => d.low));
      addLine('srHigh', () => [{ time: data[0].time, value: maxHigh }, { time: data[data.length - 1].time, value: maxHigh }],
        { color: '#ef5350', lineWidth: 1, lineStyle: 2, title: 'Resistance' });
      addLine('srLow', () => [{ time: data[0].time, value: minLow }, { time: data[data.length - 1].time, value: minLow }],
        { color: '#26a69a', lineWidth: 1, lineStyle: 2, title: 'Support' });
    }

    // ─── Pattern Markers (Advanced only) ───
    const activeMarkers = [];
    if (mode === 'ADVANCED') {
      const patterns = detectCandlePatterns(data);
      for (const p of patterns) {
        activeMarkers.push({
          time: p.time,
          position: p.signal === 'Bullish' ? 'belowBar' : 'aboveBar',
          color: p.signal === 'Bullish' ? '#26a69a' : p.signal === 'Bearish' ? '#ef5350' : '#ff9800',
          shape: p.signal === 'Bullish' ? 'arrowUp' : p.signal === 'Bearish' ? 'arrowDown' : 'circle',
          text: p.type
        });
      }
      const pivots = detectMarketStructure(data);
      for (const p of pivots) {
        activeMarkers.push({
          time: p.time,
          position: (p.type === 'HL' || p.type === 'LL') ? 'belowBar' : 'aboveBar',
          color: '#2196f3', shape: 'circle', text: p.type
        });
      }
    }

    // Deduplicate markers by time
    activeMarkers.sort((a, b) => a.time - b.time);
    const uniqueMarkers = [];
    for (const m of activeMarkers) {
      const last = uniqueMarkers[uniqueMarkers.length - 1];
      if (last && last.time === m.time) {
        last.text += ` | ${m.text}`;
      } else {
        uniqueMarkers.push({ ...m });
      }
    }
    markersRef.current.setMarkers(uniqueMarkers);

    // ─── Resize handler ───
    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({
          width: chartContainerRef.current.clientWidth,
          height: chartContainerRef.current.clientHeight
        });
      }
    };
    window.addEventListener('resize', handleResize);
    handleResize();

    return () => window.removeEventListener('resize', handleResize);
  }, [data, activeChartType, indicators, mode, cleanupIndicators]);

  // ─── Live quote polling ───
  useEffect(() => {
    if (!symbol) return;
    let active = true;
    const poll = async () => {
      try {
        const res = await fetch(`${API_URL}/api/quote/${symbol.toUpperCase().replace('.NS', '')}`);
        if (res.ok && active) {
          const q = await res.json();
          setLastQuote(q);
        }
      } catch {}
    };
    poll();
    const iv = setInterval(poll, 10000);
    return () => { active = false; clearInterval(iv); };
  }, [symbol]);

  // Memoized pattern data for AI panel
  const patternsMemo = useMemo(() => detectCandlePatterns(data), [data]);
  const msMemo = useMemo(() => detectMarketStructure(data), [data]);

  const toggleIndicator = (ind) => setIndicators(p => ({ ...p, [ind]: !p[ind] }));

  const styles = {
    wrapper: { display: 'flex', flexDirection: 'column', height: '80vh', background: '#131722', borderRadius: '8px', overflow: 'hidden', border: '1px solid #2b313f' },
    main: { display: 'flex', flex: 1, overflow: 'hidden' },
    chartArea: { flex: 1, position: 'relative' },
    loading: { position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', color: '#787b86', zIndex: 10, fontSize: '14px' },
    ticker: { position: 'absolute', top: '16px', left: '16px', zIndex: 10, background: 'rgba(19,23,34,0.85)', padding: '8px 14px', borderRadius: '8px', border: '1px solid #2b313f', backdropFilter: 'blur(8px)' }
  };

  return (
    <div style={styles.wrapper}>
      <ChartToolbar
        mode={mode} setMode={setMode}
        symbol={symbol} setSymbol={setSymbol} fetchHistory={fetchHistory}
        timeframe={timeframe} setTimeframe={setTimeframe}
        activeChartType={activeChartType} setActiveChartType={setActiveChartType}
        indicators={indicators} toggleIndicator={toggleIndicator}
        showDomPanel={showDomPanel} setShowDomPanel={setShowDomPanel}
      />

      <div style={styles.main}>
        <div style={styles.chartArea}>
          {loading && data.length === 0 && <div style={styles.loading}>⏳ Loading Chart Data...</div>}

          {lastQuote && (
            <div style={styles.ticker}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <span style={{ color: '#fff', fontWeight: 700, fontSize: '16px' }}>{symbol.toUpperCase().replace('.NS', '')}</span>
                <span style={{ fontWeight: 700, fontSize: '20px', color: (lastQuote.change_pct || 0) >= 0 ? '#26a69a' : '#ef5350' }}>
                  ₹{lastQuote.price?.toFixed(2)}
                </span>
                <span style={{
                  fontSize: '13px', fontWeight: 600,
                  padding: '2px 8px', borderRadius: '4px',
                  background: (lastQuote.change_pct || 0) >= 0 ? 'rgba(38,166,154,0.15)' : 'rgba(239,83,80,0.15)',
                  color: (lastQuote.change_pct || 0) >= 0 ? '#26a69a' : '#ef5350'
                }}>
                  {(lastQuote.change_pct || 0) >= 0 ? '+' : ''}{lastQuote.change_pct}%
                </span>
                {lastQuote.delayed && <span style={{ fontSize: '10px', color: '#787b86', background: '#2b313f', padding: '2px 6px', borderRadius: '3px' }}>DELAYED</span>}
              </div>
            </div>
          )}

          <div ref={chartContainerRef} style={{ width: '100%', height: '100%' }} />
        </div>

        <AIMarketIntelligencePanel
          mode={mode}
          aiAnalysis={aiAnalysis}
          symbol={symbol}
          timeframe={timeframe}
          currentPrice={lastCandleRef.current?.close || lastQuote?.price || 0}
          patterns={patternsMemo}
          marketStructure={msMemo}
        />
      </div>
    </div>
  );
};

export default AdvancedChartEngine;
