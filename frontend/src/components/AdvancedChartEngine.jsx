import React, { useState, useEffect, useRef, useMemo } from 'react';
import { createChart, CandlestickSeries, HistogramSeries, LineSeries, createSeriesMarkers } from 'lightweight-charts';
import ChartToolbar from './chart/ChartToolbar';
import AIMarketIntelligencePanel from './chart/AIMarketIntelligencePanel';
import { 
  calculateSMA, calculateEMA, calculateMACD, calculateRSI, calculateBB, 
  calculateVWAP, calculateATR, calculateSupertrend, calculateAIPredictor
} from './chart/IndicatorsEngine';
import { detectCandlePatterns, detectMarketStructure } from './chart/PatternDetection';

const API_URL = (import.meta.env.VITE_API_URL || 'https://elco-backend.onrender.com').replace(/\/$/, '');

const AdvancedChartEngine = ({ token, globalSymbol }) => {
  const [mode, setMode] = useState('ADVANCED'); // BEGINNER or ADVANCED
  const [activeChartType, setActiveChartType] = useState('candlestick');
  const [symbol, setSymbol] = useState(globalSymbol || 'RELIANCE');
  const [timeframe, setTimeframe] = useState('15m');
  
  // Indicators State
  const [indicators, setIndicators] = useState({
    vol: true, rsi: false, macd: false, sma20: false, sma50: false, 
    ema9: false, bb: false, sr: false, vwap: false, supertrend: false, atr: false,
    aipredictor: false
  });
  
  const [aiAnalysis, setAiAnalysis] = useState(null);
  const [showDomPanel, setShowDomPanel] = useState(false);
  const [tradeQty, setTradeQty] = useState(1);
  const [tradeMsg, setTradeMsg] = useState("");

  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [live, setLive] = useState(true);
  const [lastQuote, setLastQuote] = useState(null);
  const [wsLive, setWsLive] = useState(false);

  const chartContainerRef = useRef(null);
  const chartRef = useRef(null);
  const seriesRef = useRef(null);
  const markersRef = useRef(null);
  const volumeSeriesRef = useRef(null);
  const lastCandleRef = useRef(null);
  const aiLinesRef = useRef([]);
  
  const indRefs = useRef({
    sma20: null, sma50: null, ema9: null, bbUpper: null, bbLower: null, bbMiddle: null, srHigh: null, srLow: null,
    rsi: null, macdLine: null, macdSignal: null, vwap: null, supertrend: null, atr: null, aipredictor: null,
    patterns: []
  });

  useEffect(() => {
    if (globalSymbol && globalSymbol !== symbol) {
      setSymbol(globalSymbol);
    }
  }, [globalSymbol]);

  const fetchHistory = async () => {
    if (!symbol) return;
    setLoading(true);
    try {
      const headers = token && token.length > 20 ? { 'Authorization': `Bearer ${token}` } : {};
      let period = '1mo';
      if (timeframe === '1m' || timeframe === '5m') period = '5d';
      else if (timeframe === '1d') period = '1y';
      else if (timeframe === '1wk') period = '2y';
      
      const res = await fetch(`${API_URL}/api/history/${symbol.toUpperCase().replace('.NS', '')}.NS?interval=${timeframe}&period=${period}`, { headers }).catch(() => null);
      // Fallback if .NS fails
      let finalRes = res;
      if (!res || !res.ok) {
        finalRes = await fetch(`${API_URL}/api/history/${symbol.toUpperCase()}?interval=${timeframe}&period=${period}`, { headers });
      }
      
      if (finalRes && finalRes.ok) {
        const historyData = await finalRes.json();
        const uniqueData = [];
        let lastTime = 0;
        for (const item of historyData) {
          if (item.time > lastTime) {
            uniqueData.push(item);
            lastTime = item.time;
          }
        }
        setData(uniqueData);
        lastCandleRef.current = uniqueData.length ? { ...uniqueData[uniqueData.length - 1] } : null;
      }
    } catch (err) {
      console.error("Error fetching history:", err);
    }
    setLoading(false);
  };

  const fetchAnalysis = async () => {
    if (!symbol) return;
    try {
      const res = await fetch(`${API_URL}/analyze/${symbol.toUpperCase().replace('.NS', '')}`);
      if (res.ok) {
        const d = await res.json();
        setAiAnalysis(d);
      } else {
        setAiAnalysis(null);
      }
    } catch (err) {
      setAiAnalysis(null);
    }
  };

  useEffect(() => {
    fetchHistory();
    fetchAnalysis();
  }, [symbol, timeframe]);

  // Handle Chart Lifecycle & Indicators
  useEffect(() => {
    if (!chartContainerRef.current) return;
    if (data.length === 0) return;

    if (!chartRef.current) {
      chartRef.current = createChart(chartContainerRef.current, {
        layout: { background: { type: 'solid', color: '#131722' }, textColor: '#d1d4dc' },
        grid: { vertLines: { color: '#2b313f' }, horzLines: { color: '#2b313f' } },
        crosshair: { mode: 1 },
        timeScale: { timeVisible: true, secondsVisible: false, borderColor: '#2b313f' },
        rightPriceScale: { borderColor: '#2b313f', autoScale: true },
        leftPriceScale: { visible: false },
      });
      volumeSeriesRef.current = chartRef.current.addSeries(HistogramSeries, {
        color: '#26a69a', priceFormat: { type: 'volume' }, priceScaleId: '', scaleMargins: { top: 0.8, bottom: 0 }
      });
    }

    const chart = chartRef.current;

    // Series logic
    if (seriesRef.current) {
      chart.removeSeries(seriesRef.current);
      seriesRef.current = null;
    }

    if (activeChartType === 'candlestick') {
      seriesRef.current = chart.addSeries(CandlestickSeries, { upColor: '#26a69a', downColor: '#ef5350', borderVisible: false, wickUpColor: '#26a69a', wickDownColor: '#ef5350' });
      seriesRef.current.setData(data);
    } else if (activeChartType === 'heikin_ashi') {
      seriesRef.current = chart.addSeries(CandlestickSeries, { upColor: '#26a69a', downColor: '#ef5350', borderVisible: false, wickUpColor: '#26a69a', wickDownColor: '#ef5350' });
      const haData = getHeikinAshiData(data);
      seriesRef.current.setData(haData);
    } else {
      seriesRef.current = chart.addSeries(LineSeries, { color: '#2962FF', lineWidth: 2 });
      seriesRef.current.setData(data.map(d => ({ time: d.time, value: d.close })));
    }

    markersRef.current = createSeriesMarkers(seriesRef.current, []);

    // Indicators logic
    if (indicators.vol || mode === 'BEGINNER') {
      volumeSeriesRef.current.setData(data.map(d => ({ 
        time: d.time, value: d.volume || 0, color: d.close > d.open ? 'rgba(38, 166, 154, 0.3)' : 'rgba(239, 83, 80, 0.3)' 
      })));
    } else {
      volumeSeriesRef.current.setData([]);
    }

    const updateLineIndicator = (key, show, calcFn, options) => {
      if (show && mode === 'ADVANCED') {
        if (!indRefs.current[key]) indRefs.current[key] = chart.addSeries(LineSeries, options);
        indRefs.current[key].setData(calcFn());
      } else if (indRefs.current[key]) {
        chart.removeSeries(indRefs.current[key]);
        indRefs.current[key] = null;
      }
    };

    updateLineIndicator('sma20', indicators.sma20, () => calculateSMA(data, 20), { color: '#ffeb3b', lineWidth: 2, title: 'SMA 20' });
    updateLineIndicator('sma50', indicators.sma50, () => calculateSMA(data, 50), { color: '#ff9800', lineWidth: 2, title: 'SMA 50' });
    updateLineIndicator('ema9', indicators.ema9, () => calculateEMA(data, 9), { color: '#00bcd4', lineWidth: 2, title: 'EMA 9' });
    updateLineIndicator('vwap', indicators.vwap, () => calculateVWAP(data), { color: '#e040fb', lineWidth: 2, title: 'VWAP' });
    updateLineIndicator('atr', indicators.atr, () => calculateATR(data), { color: '#ff5252', lineWidth: 2, priceScaleId: 'left', title: 'ATR' });

    // AI Super Predictor
    if (indicators.aipredictor && mode === 'ADVANCED') {
      if(!indRefs.current.aipredictor) indRefs.current.aipredictor = chart.addSeries(LineSeries, { lineWidth: 3, title: 'AI Predictor (Future)', lineStyle: 0 });
      const aiData = calculateAIPredictor(data);
      // We use baseColor logic inside lightweight-charts to apply segment colors if possible, but for simplicity we will set the whole line to a distinct color, or map colors per segment.
      indRefs.current.aipredictor.setData(aiData.map(d => ({ time: d.time, value: d.value, color: d.color })));
    } else if (indRefs.current.aipredictor) { chart.removeSeries(indRefs.current.aipredictor); indRefs.current.aipredictor = null; }

    // Supertrend
    if (indicators.supertrend && mode === 'ADVANCED') {
      if(!indRefs.current.supertrend) indRefs.current.supertrend = chart.addSeries(LineSeries, { color: '#00e676', lineWidth: 2, title: 'Supertrend' });
      const stData = calculateSupertrend(data);
      indRefs.current.supertrend.setData(stData.map(d => ({ time: d.time, value: d.value, color: d.trend === 1 ? '#00e676' : '#ff1744' })));
    } else if (indRefs.current.supertrend) { chart.removeSeries(indRefs.current.supertrend); indRefs.current.supertrend = null; }

    // RSI
    if (indicators.rsi && mode === 'ADVANCED') {
        if(!indRefs.current.rsi) indRefs.current.rsi = chart.addSeries(LineSeries, { color: '#9c27b0', lineWidth: 2, priceScaleId: 'left', title: 'RSI' });
        indRefs.current.rsi.setData(calculateRSI(data));
    } else if(indRefs.current.rsi) { chart.removeSeries(indRefs.current.rsi); indRefs.current.rsi = null; }

    // MACD
    if (indicators.macd && mode === 'ADVANCED') {
        if(!indRefs.current.macdLine) {
            indRefs.current.macdLine = chart.addSeries(LineSeries, { color: '#2196f3', lineWidth: 2, priceScaleId: 'left', title: 'MACD' });
            indRefs.current.macdSignal = chart.addSeries(LineSeries, { color: '#f44336', lineWidth: 2, priceScaleId: 'left', title: 'Signal' });
        }
        const { macdLine, macdSignal } = calculateMACD(data);
        indRefs.current.macdLine.setData(macdLine);
        indRefs.current.macdSignal.setData(macdSignal);
    } else if(indRefs.current.macdLine) { chart.removeSeries(indRefs.current.macdLine); chart.removeSeries(indRefs.current.macdSignal); indRefs.current.macdLine = indRefs.current.macdSignal = null; }

    // Support / Resistance (simplified)
    if (indicators.sr || mode === 'BEGINNER') {
      const maxHigh = Math.max(...data.map(d => d.high));
      const minLow = Math.min(...data.map(d => d.low));
      if(!indRefs.current.srHigh) {
        indRefs.current.srHigh = chart.addSeries(LineSeries, { color: '#ef5350', lineWidth: 1, lineStyle: 2, title: 'Resistance' });
        indRefs.current.srLow = chart.addSeries(LineSeries, { color: '#26a69a', lineWidth: 1, lineStyle: 2, title: 'Support' });
      }
      indRefs.current.srHigh.setData([{ time: data[0].time, value: maxHigh }, { time: data[data.length - 1].time, value: maxHigh }]);
      indRefs.current.srLow.setData([{ time: data[0].time, value: minLow }, { time: data[data.length - 1].time, value: minLow }]);
    } else if (indRefs.current.srHigh) {
      chart.removeSeries(indRefs.current.srHigh);
      chart.removeSeries(indRefs.current.srLow);
      indRefs.current.srHigh = indRefs.current.srLow = null;
    }
    
    // Pattern Markers (Only in Advanced)
    const activeMarkers = [];
    if (mode === 'ADVANCED') {
      const patterns = detectCandlePatterns(data);
      patterns.forEach(p => {
        activeMarkers.push({
          time: p.time,
          position: p.signal === 'Bullish' ? 'belowBar' : 'aboveBar',
          color: p.signal === 'Bullish' ? '#26a69a' : p.signal === 'Bearish' ? '#ef5350' : '#ff9800',
          shape: p.signal === 'Bullish' ? 'arrowUp' : p.signal === 'Bearish' ? 'arrowDown' : 'circle',
          text: p.type
        });
      });
      // Market Structure
      const pivots = detectMarketStructure(data);
      pivots.forEach(p => {
        activeMarkers.push({
          time: p.time,
          position: (p.type === 'HL' || p.type === 'LL') ? 'belowBar' : 'aboveBar',
          color: '#2196f3',
          shape: 'circle',
          text: p.type
        });
      });
    }
    
    // Group markers by time to prevent lightweight-charts crash on duplicate times
    activeMarkers.sort((a, b) => a.time - b.time);
    const uniqueMarkers = [];
    for (const m of activeMarkers) {
      if (uniqueMarkers.length > 0 && uniqueMarkers[uniqueMarkers.length - 1].time === m.time) {
        uniqueMarkers[uniqueMarkers.length - 1].text += ` | ${m.text}`;
      } else {
        uniqueMarkers.push(m);
      }
    }
    
    markersRef.current.setMarkers(uniqueMarkers);

    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({ width: chartContainerRef.current.clientWidth, height: chartContainerRef.current.clientHeight });
      }
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [data, activeChartType, indicators, mode]);

  // Derived metrics for AI Panel
  const patternsMemo = useMemo(() => detectCandlePatterns(data), [data]);
  const msMemo = useMemo(() => detectMarketStructure(data), [data]);

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
      prevHAOpen = haOpen; prevHAClose = haClose;
    }
    return haData;
  };

  const toggleIndicator = (ind) => setIndicators(p => ({ ...p, [ind]: !p[ind] }));

  const styles = {
    wrapper: { display: 'flex', flexDirection: 'column', height: '80vh', background: '#131722', borderRadius: '8px', overflow: 'hidden', border: '1px solid #2b313f' },
    main: { display: 'flex', flex: 1, overflow: 'hidden' },
    chartArea: { flex: 1, position: 'relative' },
    loading: { position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', color: '#787b86', zIndex: 10 },
    ticker: { position: 'absolute', top: '16px', left: '16px', zIndex: 10, background: 'rgba(19, 23, 34, 0.8)', padding: '6px 12px', borderRadius: '6px', border: '1px solid #2b313f' }
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
          {loading && data.length === 0 && <div style={styles.loading}>Loading Institutional Data...</div>}
          
          {lastQuote && (
            <div style={styles.ticker}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <span style={{ color: '#fff', fontWeight: 600, fontSize: '16px' }}>{symbol.toUpperCase().replace('.NS', '')}</span>
                <span style={{ fontWeight: 600, fontSize: '18px', color: (lastQuote.change_pct || 0) >= 0 ? '#26a69a' : '#ef5350' }}>
                  ₹{lastQuote.price?.toFixed(2)}
                </span>
                <span style={{ fontSize: '13px', color: (lastQuote.change_pct || 0) >= 0 ? '#26a69a' : '#ef5350' }}>
                  {(lastQuote.change_pct || 0) >= 0 ? '+' : ''}{lastQuote.change_pct}%
                </span>
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
