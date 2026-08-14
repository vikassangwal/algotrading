import React, { useState, useEffect, useRef } from 'react';
import { createChart, CandlestickSeries, HistogramSeries, LineSeries, createSeriesMarkers } from 'lightweight-charts';

const API_URL = (import.meta.env.VITE_API_URL || 'https://elco-backend.onrender.com').replace(/\/$/, '');

const AdvancedChartEngine = ({ token, globalSymbol }) => {
  const [activeChartType, setActiveChartType] = useState('candlestick');
  const [drawingToolsEnabled, setDrawingToolsEnabled] = useState(false);
  const [symbol, setSymbol] = useState(globalSymbol || 'RELIANCE');
  const [timeframe, setTimeframe] = useState('15m');
  
  // Indicators State
  const [indicators, setIndicators] = useState({
    sma20: false,
    sma50: false,
    ema9: false,
    bb: false,
    sr: false
  });
  
  const [aiAnalysis, setAiAnalysis] = useState(null);
  const [showAiPanel, setShowAiPanel] = useState(true);
  const [showDomPanel, setShowDomPanel] = useState(false);
  const [showFullTradingView, setShowFullTradingView] = useState(false);
  const [domData, setDomData] = useState({ bids: [], asks: [] });
  const [tradeQty, setTradeQty] = useState(1);
  const [tradeMsg, setTradeMsg] = useState("");

  const handleQuickTrade = async (action) => {
    try {
      const cleanSym = symbol.replace('.NS', '').replace('.BO', '');
      const hdrs = { 'Content-Type': 'application/json' };
      if (token && token.length > 20) hdrs['Authorization'] = `Bearer ${token}`;
      
      const res = await fetch(`${API_URL}/api/orders`, {
        method: 'POST',
        headers: hdrs,
        body: JSON.stringify({
          symbol: cleanSym,
          action: action,
          qty: parseInt(tradeQty) || 1,
          type: 'MARKET',
          price: null
        })
      });
      
      if (res.ok) {
        setTradeMsg(`✅ ${action} ${tradeQty} ${cleanSym} placed!`);
        setTimeout(() => setTradeMsg(""), 3000);
      } else {
        setTradeMsg(`❌ Failed to place ${action}`);
        setTimeout(() => setTradeMsg(""), 3000);
      }
    } catch (e) {
      setTradeMsg(`❌ Error: ${e.message}`);
      setTimeout(() => setTradeMsg(""), 3000);
    }
  };

  // Simulate Live DOM (Level 2) Data
  useEffect(() => {
    if (!showDomPanel || !lastQuote || !lastQuote.price) return;
    const interval = setInterval(() => {
      const price = lastQuote.price;
      const step = price > 1000 ? 0.5 : 0.05;
      const bids = [];
      const asks = [];
      for (let i = 1; i <= 5; i++) {
        bids.push({ price: price - (i * step), qty: Math.floor(Math.random() * 5000) + 500 });
        asks.push({ price: price + (i * step), qty: Math.floor(Math.random() * 5000) + 500 });
      }
      setDomData({ bids, asks });
    }, 1000);
    return () => clearInterval(interval);
  }, [showDomPanel, lastQuote]);

  useEffect(() => {
    if (globalSymbol && globalSymbol !== symbol) {
      setSymbol(globalSymbol);
    }
  }, [globalSymbol]);

  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [live, setLive] = useState(true);
  const [lastQuote, setLastQuote] = useState(null);
  const [wsLive, setWsLive] = useState(false);
  const [indexTicks, setIndexTicks] = useState({});

  const chartContainerRef = useRef(null);
  const chartRef = useRef(null);
  const seriesRef = useRef(null);
  const markersRef = useRef(null);
  const volumeSeriesRef = useRef(null);
  const lastCandleRef = useRef(null);
  const aiLinesRef = useRef([]);
  
  // Indicator Refs
  const indRefs = useRef({
    sma20: null, sma50: null, ema9: null, bbUpper: null, bbLower: null, bbMiddle: null, srHigh: null, srLow: null
  });

  const chartTypes = [
    { id: 'candlestick', label: 'Candlestick' },
    { id: 'heikin_ashi', label: 'Heikin Ashi' },
    { id: 'renko', label: 'Renko (Line)' },
    { id: 'point_figure', label: 'P&F (Line)' }
  ];
  
  const timeframes = ['1m', '5m', '15m', '1h', '1d', '1wk'];

  const fetchHistory = async () => {
    if (!symbol) return;
    setLoading(true);
    try {
      const headers = token && token.length > 20 ? { 'Authorization': `Bearer ${token}` } : {};
      
      let period = '1mo';
      if (timeframe === '1m' || timeframe === '5m') period = '5d';
      else if (timeframe === '1d') period = '1y';
      else if (timeframe === '1wk') period = '2y';
      
      const res = await fetch(`${API_URL}/api/history/${symbol.toUpperCase()}?interval=${timeframe}&period=${period}`, { headers });
      if (res.ok) {
        const historyData = await res.json();
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
      const res = await fetch(`${API_URL}/analyze/${symbol.toUpperCase()}`);
      if (res.ok) {
        const data = await res.json();
        setAiAnalysis(data);
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

  // Indicator Calculations
  const calculateSMA = (data, period) => {
    const sma = [];
    for (let i = 0; i < data.length; i++) {
      if (i < period - 1) continue;
      let sum = 0;
      for (let j = 0; j < period; j++) {
        sum += data[i - j].close;
      }
      sma.push({ time: data[i].time, value: sum / period });
    }
    return sma;
  };

  const calculateEMA = (data, period) => {
    const ema = [];
    const k = 2 / (period + 1);
    let prevEma = data.length > 0 ? data[0].close : 0;
    
    for (let i = 0; i < data.length; i++) {
      if (i === 0) continue;
      const currentEma = (data[i].close - prevEma) * k + prevEma;
      if (i >= period - 1) {
        ema.push({ time: data[i].time, value: currentEma });
      }
      prevEma = currentEma;
    }
    return ema;
  };

  const calculateBB = (data, period, stdDevMultiplier) => {
    const upper = [];
    const lower = [];
    const middle = [];
    
    for (let i = period - 1; i < data.length; i++) {
      let sum = 0;
      for (let j = 0; j < period; j++) {
        sum += data[i - j].close;
      }
      const mean = sum / period;
      
      let varianceSum = 0;
      for (let j = 0; j < period; j++) {
        varianceSum += Math.pow(data[i - j].close - mean, 2);
      }
      const stdDev = Math.sqrt(varianceSum / period);
      
      middle.push({ time: data[i].time, value: mean });
      upper.push({ time: data[i].time, value: mean + (stdDev * stdDevMultiplier) });
      lower.push({ time: data[i].time, value: mean - (stdDev * stdDevMultiplier) });
    }
    return { upper, lower, middle };
  };

  const getHeikinAshiData = (sourceData) => {
    if (sourceData.length === 0) return [];
    const haData = [];
    let prevHAOpen = sourceData[0].open;
    let prevHAClose = sourceData[0].close;
    for (let i = 0; i < sourceData.length; i++) {
      const { time, open, high, low, close } = sourceData[i];
      const haClose = (open + high + low + close) / 4;
      const haOpen = i === 0 ? (open + close) / 2 : (prevHAOpen + prevHAClose) / 2;
      const haHigh = Math.max(high, haOpen, haClose);
      const haLow = Math.min(low, haOpen, haClose);
      haData.push({ time, open: haOpen, high: haHigh, low: haLow, close: haClose });
      prevHAOpen = haOpen;
      prevHAClose = haClose;
    }
    return haData;
  };

  const getLineData = (sourceData) => {
    return sourceData.map(d => ({ time: d.time, value: d.close }));
  };

  // Manage Chart Instance
  useEffect(() => {
    if (!chartContainerRef.current) return;
    if (data.length === 0) return;

    if (!chartRef.current) {
      chartRef.current = createChart(chartContainerRef.current, {
        layout: { background: { type: 'solid', color: '#1e222d' }, textColor: '#d1d4dc' },
        grid: { vertLines: { color: '#2b313f' }, horzLines: { color: '#2b313f' } },
        timeScale: { timeVisible: true, secondsVisible: false }
      });
      volumeSeriesRef.current = chartRef.current.addSeries(HistogramSeries, {
        color: '#26a69a',
        priceFormat: { type: 'volume' },
        priceScaleId: '',
        scaleMargins: { top: 0.8, bottom: 0 },
      });
    }

    const chart = chartRef.current;

    if (seriesRef.current) {
      chart.removeSeries(seriesRef.current);
    }

    if (activeChartType === 'candlestick') {
      seriesRef.current = chart.addSeries(CandlestickSeries, {
        upColor: '#26a69a', downColor: '#ef5350', borderVisible: false,
        wickUpColor: '#26a69a', wickDownColor: '#ef5350',
      });
      seriesRef.current.setData(data);
    } else if (activeChartType === 'heikin_ashi') {
      seriesRef.current = chart.addSeries(CandlestickSeries, {
        upColor: '#26a69a', downColor: '#ef5350', borderVisible: false,
        wickUpColor: '#26a69a', wickDownColor: '#ef5350',
      });
      seriesRef.current.setData(getHeikinAshiData(data));
    } else {
      seriesRef.current = chart.addSeries(LineSeries, { color: '#2962ff', lineWidth: 2 });
      seriesRef.current.setData(getLineData(data));
    }

    markersRef.current = createSeriesMarkers(seriesRef.current, []);

    if (indicators.vol) {
      const volData = data.map(d => ({ 
        time: d.time, value: d.volume || 0, color: d.close > d.open ? 'rgba(38, 166, 154, 0.3)' : 'rgba(239, 83, 80, 0.3)' 
      }));
      volumeSeriesRef.current.setData(volData);
    } else {
      volumeSeriesRef.current.setData([]);
    }
    
    // Update Indicators
    const updateIndicator = (key, show, createFn, dataFn, options) => {
      if (indRefs.current[key]) {
        chart.removeSeries(indRefs.current[key]);
        indRefs.current[key] = null;
      }
      if (show && data.length > 0) {
        indRefs.current[key] = chart.addSeries(LineSeries, options);
        indRefs.current[key].setData(dataFn());
      }
    };

    updateIndicator('sma20', indicators.sma20, null, () => calculateSMA(data, 20), { color: '#ffeb3b', lineWidth: 2, title: 'SMA 20' });
    updateIndicator('sma50', indicators.sma50, null, () => calculateSMA(data, 50), { color: '#ff9800', lineWidth: 2, title: 'SMA 50' });
    updateIndicator('ema9', indicators.ema9, null, () => calculateEMA(data, 9), { color: '#00bcd4', lineWidth: 2, title: 'EMA 9' });
    if (indicators.rsi) {
        if(!indRefs.current.rsi) indRefs.current.rsi = chart.addSeries(LineSeries, { color: '#9c27b0', lineWidth: 2, priceScaleId: 'left', title: 'RSI' });
        indRefs.current.rsi.setData(calculateRSI(data));
    } else if(indRefs.current.rsi) { chart.removeSeries(indRefs.current.rsi); indRefs.current.rsi = null; }

    if (indicators.macd) {
        if(!indRefs.current.macdLine) {
            indRefs.current.macdLine = chart.addSeries(LineSeries, { color: '#2196f3', lineWidth: 2, priceScaleId: 'left', title: 'MACD' });
            indRefs.current.macdSignal = chart.addSeries(LineSeries, { color: '#f44336', lineWidth: 2, priceScaleId: 'left', title: 'Signal' });
        }
        const { macdLine, macdSignal } = calculateMACD(data);
        indRefs.current.macdLine.setData(macdLine);
        indRefs.current.macdSignal.setData(macdSignal);
    } else if(indRefs.current.macdLine) { chart.removeSeries(indRefs.current.macdLine); chart.removeSeries(indRefs.current.macdSignal); indRefs.current.macdLine = indRefs.current.macdSignal = null; }

    if (indicators.rsi) {
        if(!indRefs.current.rsi) indRefs.current.rsi = chart.addSeries(LineSeries, { color: '#9c27b0', lineWidth: 2, priceScaleId: 'left', title: 'RSI' });
        indRefs.current.rsi.setData(calculateRSI(data));
    } else if(indRefs.current.rsi) { chart.removeSeries(indRefs.current.rsi); indRefs.current.rsi = null; }

    if (indicators.macd) {
        if(!indRefs.current.macdLine) {
            indRefs.current.macdLine = chart.addSeries(LineSeries, { color: '#2196f3', lineWidth: 2, priceScaleId: 'left', title: 'MACD' });
            indRefs.current.macdSignal = chart.addSeries(LineSeries, { color: '#f44336', lineWidth: 2, priceScaleId: 'left', title: 'Signal' });
        }
        const { macdLine, macdSignal } = calculateMACD(data);
        indRefs.current.macdLine.setData(macdLine);
        indRefs.current.macdSignal.setData(macdSignal);
    } else if(indRefs.current.macdLine) { chart.removeSeries(indRefs.current.macdLine); chart.removeSeries(indRefs.current.macdSignal); indRefs.current.macdLine = indRefs.current.macdSignal = null; }

    
    if (indRefs.current.bbUpper) {
      chart.removeSeries(indRefs.current.bbUpper);
      chart.removeSeries(indRefs.current.bbLower);
      chart.removeSeries(indRefs.current.bbMiddle);
      indRefs.current.bbUpper = indRefs.current.bbLower = indRefs.current.bbMiddle = null;
    }
    
    if (indicators.bb && data.length > 0) {
      const bb = calculateBB(data, 20, 2);
      indRefs.current.bbUpper = chart.addSeries(LineSeries, { color: 'rgba(33, 150, 243, 0.5)', lineWidth: 1, title: 'BB Upper' });
      indRefs.current.bbLower = chart.addSeries(LineSeries, { color: 'rgba(33, 150, 243, 0.5)', lineWidth: 1, title: 'BB Lower' });
      indRefs.current.bbMiddle = chart.addSeries(LineSeries, { color: 'rgba(33, 150, 243, 0.8)', lineWidth: 1, title: 'BB Mid' });
      indRefs.current.bbUpper.setData(bb.upper);
      indRefs.current.bbLower.setData(bb.lower);
      indRefs.current.bbMiddle.setData(bb.middle);
    }

    if (indRefs.current.srHigh) {
      chart.removeSeries(indRefs.current.srHigh);
      chart.removeSeries(indRefs.current.srLow);
      indRefs.current.srHigh = indRefs.current.srLow = null;
    }

    if (indicators.sr && data.length > 0) {
      const highs = data.map(d => d.high);
      const lows = data.map(d => d.low);
      const maxHigh = Math.max(...highs);
      const minLow = Math.min(...lows);
      
      const srHighLine = chart.addSeries(LineSeries, { color: '#ef5350', lineWidth: 2, lineStyle: 2, title: 'Resistance' });
      const srLowLine = chart.addSeries(LineSeries, { color: '#26a69a', lineWidth: 2, lineStyle: 2, title: 'Support' });
      
      srHighLine.setData([{ time: data[0].time, value: maxHigh }, { time: data[data.length - 1].time, value: maxHigh }]);
      srLowLine.setData([{ time: data[0].time, value: minLow }, { time: data[data.length - 1].time, value: minLow }]);
      indRefs.current.srHigh = srHighLine;
      indRefs.current.srLow = srLowLine;
    }

    // Plot AI Signal Markers
    if (aiAnalysis && markersRef.current && showAiPanel && data.length > 0) {
      const lastItem = data[data.length - 1];
      const action = aiAnalysis.action;
      if (action === 'STRONG BUY' || action === 'BUY') {
        markersRef.current.setMarkers([{
          time: lastItem.time, position: 'belowBar', color: '#26a69a', shape: 'arrowUp', text: `AI: ${action}`
        }]);
      } else if (action === 'STRONG SELL' || action === 'SELL') {
        markersRef.current.setMarkers([{
          time: lastItem.time, position: 'aboveBar', color: '#ef5350', shape: 'arrowDown', text: `AI: ${action}`
        }]);
      } else {
        markersRef.current.setMarkers([]);
      }
    } else if (markersRef.current) {
        markersRef.current.setMarkers([]);
    }

    // Clear old AI lines
    if (aiLinesRef.current) {
      aiLinesRef.current.forEach(series => chart.removeSeries(series));
      aiLinesRef.current = [];
    }

    // Draw new AI lines
    if (aiAnalysis && showAiPanel && aiAnalysis.reasoning) {
      const jsonReason = aiAnalysis.reasoning.find(r => r.startsWith('JSON_DATA:'));
      if (jsonReason) {
        try {
          const parsed = JSON.parse(jsonReason.replace('JSON_DATA:', ''));
          if (parsed.chart_lines && parsed.chart_lines.length > 0) {
            parsed.chart_lines.forEach(lineObj => {
               if (lineObj && lineObj.points) {
                 const lineSeries = chart.addSeries(LineSeries, {
                   color: lineObj.color || '#e040fb',
                   lineWidth: lineObj.lineWidth || 2,
                   lineStyle: lineObj.lineStyle || 0,
                 });
                 // lightweight-charts needs points sorted by time
                 const sortedPoints = [...lineObj.points].sort((a, b) => a.time - b.time);
                 lineSeries.setData(sortedPoints);
                 aiLinesRef.current.push(lineSeries);
               }
            });
          }
        } catch (e) {
          console.error("Failed to parse AI JSON Data", e);
        }
      }
    }

    chart.timeScale().fitContent();

    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({ width: chartContainerRef.current.clientWidth, height: chartContainerRef.current.clientHeight });
      }
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [data, activeChartType, indicators, aiAnalysis, showAiPanel]);

  useEffect(() => {
    if (data.length > 0) {
      lastCandleRef.current = { ...data[data.length - 1] };
    }
  }, [data]);

  const applyPrice = (price) => {
    const series = seriesRef.current;
    const prev = lastCandleRef.current;
    if (!series || !prev || typeof price !== 'number') return;
    const isLine = activeChartType !== 'candlestick' && activeChartType !== 'heikin_ashi';
    if (isLine) {
      series.update({ time: prev.time, value: price });
      return;
    }
    const updated = {
      time: prev.time, open: prev.open, high: Math.max(prev.high, price),
      low: Math.min(prev.low, price), close: price,
    };
    lastCandleRef.current = updated;
    series.update(updated);
  };
  const applyPriceRef = useRef(applyPrice);
  applyPriceRef.current = applyPrice;

  useEffect(() => {
    if (!live || !token || !symbol) return;
    let ws;
    let alive = true;
    let staleTimer;

    const markStale = () => {
      clearTimeout(staleTimer);
      staleTimer = setTimeout(() => { if (alive) setWsLive(false); }, 15000);
    };

    try {
      const wsBase = API_URL.replace(/^http/, 'ws');
      ws = new WebSocket(`${wsBase}/ws/live?token=${encodeURIComponent(token)}&symbols=${symbol.toUpperCase()},NIFTY,BANKNIFTY`);
      ws.onmessage = (ev) => {
        if (!alive) return;
        try {
          const msg = JSON.parse(ev.data);
          if (msg.type === 'ticks') {
            const sym = symbol.toUpperCase();
            const t = msg.ticks[sym];
            const idx = {};
            if (msg.ticks.NIFTY) idx.NIFTY = msg.ticks.NIFTY;
            if (msg.ticks.BANKNIFTY) idx.BANKNIFTY = msg.ticks.BANKNIFTY;
            if (Object.keys(idx).length) setIndexTicks((p) => ({ ...p, ...idx }));
            if (t && typeof t.ltp === 'number') {
              setWsLive(true);
              markStale();
              setLastQuote({ price: t.ltp, change_pct: t.change_pct ?? 0, delayed: !!t.delayed, source: t.source || 'dhan' });
              applyPriceRef.current(t.ltp);
            }
          }
        } catch { }
      };
      ws.onclose = () => { if (alive) setWsLive(false); };
      ws.onerror = () => { if (alive) setWsLive(false); };
    } catch {
      setWsLive(false);
    }
    return () => {
      alive = false;
      clearTimeout(staleTimer);
      try { if (ws) ws.close(); } catch { }
    };
  }, [live, token, symbol]);

  useEffect(() => {
    if (!live || !symbol || wsLive) return;
    let cancelled = false;
    const poll = async () => {
      try {
        const headers = token && token.length > 20 ? { 'Authorization': `Bearer ${token}` } : {};
        const res = await fetch(`${API_URL}/api/quote/${symbol.toUpperCase()}`, { headers });
        if (!res.ok || cancelled) return;
        const q = await res.json();
        if (cancelled || typeof q.price !== 'number') return;
        setLastQuote(q);
        applyPriceRef.current(q.price);
      } catch { }
    };
    poll();
    const id = setInterval(poll, 30000);
    return () => { cancelled = true; clearInterval(id); };
  }, [live, token, symbol, wsLive, activeChartType]);

  useEffect(() => {
    return () => {
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
      }
    };
  }, []);
  
  const toggleIndicator = (ind) => {
    setIndicators(p => ({ ...p, [ind]: !p[ind] }));
  };

  // Render AI Panel Overlay
  const renderAiPanel = () => {
    if (!showAiPanel || !aiAnalysis) return null;
    
    // Extract top 3 reasons, skipping JSON_DATA
    const cleanReasons = (aiAnalysis.reasoning || []).filter(r => !r.startsWith('JSON_DATA:'));
    const reasons = cleanReasons.slice(0, 3);
    
    // Estimate Confidence based on scores
    let highestConf = 0;
    if (aiAnalysis.contributions) {
        Object.values(aiAnalysis.contributions).forEach(v => {
            if (v.confidence > highestConf) highestConf = v.confidence;
        });
    }
    const confidencePct = Math.round((highestConf || 0.75) * 100);
    
    let actionColor = '#b2b5be';
    if (aiAnalysis.action?.includes('BUY')) actionColor = '#26a69a';
    if (aiAnalysis.action?.includes('SELL')) actionColor = '#ef5350';

    return (
      <div style={styles.aiPanel}>
        <div style={styles.aiHeader}>
          <span>🤖 AI Trade Intelligence</span>
          <button style={styles.closeBtn} onClick={() => setShowAiPanel(false)}>×</button>
        </div>
        <div style={styles.aiContent}>
          <div style={{...styles.aiAction, color: actionColor}}>
            {aiAnalysis.action || 'NEUTRAL'}
          </div>
          <div style={styles.aiConfidence}>
            Accuracy / Confidence: <strong>{confidencePct}%</strong>
          </div>
          <div style={styles.aiReasonsTitle}>Key Drivers:</div>
          <ul style={styles.aiReasonsList}>
            {reasons.map((r, idx) => (
              <li key={idx} style={styles.aiReasonItem}>{r}</li>
            ))}
          </ul>
        </div>
      </div>
    );
  };

  const renderDomPanel = () => {
    if (!showDomPanel) return null;
    return (
      <div style={styles.domPanel}>
        <div style={styles.domHeader}>
          <span>📊 Level 2 DOM (Order Flow)</span>
          <button style={styles.closeBtn} onClick={() => setShowDomPanel(false)}>×</button>
        </div>
        <div style={styles.domContent}>
          <div style={{ display: 'flex', justifyContent: 'space-between', color: '#b2b5be', fontSize: '11px', marginBottom: '4px' }}>
            <span>BID QTY</span><span>PRICE</span><span>ASK QTY</span>
          </div>
          {domData.asks.slice().reverse().map((ask, i) => (
            <div key={`ask-${i}`} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', padding: '2px 0' }}>
              <span style={{ width: '33%', textAlign: 'left' }}>-</span>
              <span style={{ width: '34%', textAlign: 'center', color: '#ef5350' }}>{ask.price.toFixed(2)}</span>
              <span style={{ width: '33%', textAlign: 'right', color: '#ef5350' }}>{ask.qty}</span>
            </div>
          ))}
          <div style={{ display: 'flex', justifyContent: 'center', fontSize: '14px', fontWeight: 'bold', margin: '6px 0', color: '#d1d4dc' }}>
            {lastQuote?.price?.toFixed(2) || '---'}
          </div>
          {domData.bids.map((bid, i) => (
            <div key={`bid-${i}`} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', padding: '2px 0' }}>
              <span style={{ width: '33%', textAlign: 'left', color: '#26a69a' }}>{bid.qty}</span>
              <span style={{ width: '34%', textAlign: 'center', color: '#26a69a' }}>{bid.price.toFixed(2)}</span>
              <span style={{ width: '33%', textAlign: 'right' }}>-</span>
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div style={styles.container}>
      <div style={styles.toolbar}>
        <div style={{ display: 'flex', gap: '16px', alignItems: 'center', flexWrap: 'wrap' }}>
          <div style={styles.symbolInputContainer}>
            <input 
              type="text" 
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              onBlur={fetchHistory}
              onKeyDown={(e) => e.key === 'Enter' && fetchHistory()}
              style={styles.symbolInput}
              placeholder="Symbol"
            />
            <div style={{display: 'flex', gap: '4px', marginLeft: '8px'}}>
              <button style={{...styles.button, padding: '4px 6px'}} onClick={() => setSymbol('RELIANCE.NS')}>REL</button>
              <button style={{...styles.button, padding: '4px 6px'}} onClick={() => setSymbol('^NSEI')}>NIFTY</button>
              <button style={{...styles.button, padding: '4px 6px'}} onClick={() => setSymbol('^NSEBANK')}>BANK</button>
            </div>
          </div>
          
          <div style={styles.timeframeSelector}>
            {timeframes.map(tf => (
              <button key={tf} style={{...styles.button, ...(timeframe === tf ? styles.activeButton : {})}} onClick={() => setTimeframe(tf)}>
                {tf}
              </button>
            ))}
          </div>

          <div style={styles.chartTypeSelector}>
            <select 
              value={activeChartType} 
              onChange={(e) => setActiveChartType(e.target.value)}
              style={styles.selectInput}
            >
              {chartTypes.map(t => <option key={t.id} value={t.id}>{t.label}</option>)}
            </select>
          </div>
          
          {/* Indicators Toggle */}
          <div style={styles.indicatorSelector}>
            <button style={{...styles.button, ...(indicators.vol ? styles.activeButton : {})}} onClick={() => toggleIndicator('vol')}>Volume</button>
            <button style={{...styles.button, ...(indicators.rsi ? styles.activeButton : {})}} onClick={() => toggleIndicator('rsi')}>RSI</button>
            <button style={{...styles.button, ...(indicators.macd ? styles.activeButton : {})}} onClick={() => toggleIndicator('macd')}>MACD</button>
            <button style={{...styles.button, ...(indicators.sma20 ? styles.activeButton : {})}} onClick={() => toggleIndicator('sma20')}>SMA 20</button>
            <button style={{...styles.button, ...(indicators.sma50 ? styles.activeButton : {})}} onClick={() => toggleIndicator('sma50')}>SMA 50</button>
            <button style={{...styles.button, ...(indicators.ema9 ? styles.activeButton : {})}} onClick={() => toggleIndicator('ema9')}>EMA 9</button>
            <button style={{...styles.button, ...(indicators.bb ? styles.activeButton : {})}} onClick={() => toggleIndicator('bb')}>BB Bands</button>
            <button style={{...styles.button, ...(indicators.sr ? styles.activeButton : {})}} onClick={() => toggleIndicator('sr')}>Supp/Res</button>
            
            <button style={{...styles.button, ...(showDomPanel ? styles.activeDomButton : styles.domButton)}} onClick={() => setShowDomPanel(!showDomPanel)}>
              📊 Order Book
            </button>
            <button style={{...styles.button, ...(showAiPanel ? styles.activeAiButton : styles.aiButton)}} onClick={() => setShowAiPanel(!showAiPanel)}>
              🤖 AI Panel
            </button>
            
            {/* Quick Trade Panel */}
            <div style={{display: 'flex', alignItems: 'center', gap: '4px', marginLeft: '8px', borderLeft: '1px solid #2b313f', paddingLeft: '8px'}}>
              <input 
                type="number" 
                value={tradeQty} 
                onChange={(e) => setTradeQty(e.target.value)}
                style={{...styles.symbolInput, width: '50px'}}
                min="1"
                title="Quantity"
              />
              <button 
                style={{...styles.button, backgroundColor: 'rgba(38, 166, 154, 0.2)', color: '#26a69a', borderColor: '#26a69a', fontWeight: 'bold'}}
                onClick={() => handleQuickTrade('BUY')}
              >
                BUY
              </button>
              <button 
                style={{...styles.button, backgroundColor: 'rgba(239, 83, 80, 0.2)', color: '#ef5350', borderColor: '#ef5350', fontWeight: 'bold'}}
                onClick={() => handleQuickTrade('SELL')}
              >
                SELL
              </button>
              {tradeMsg && <span style={{fontSize: '12px', marginLeft: '4px', color: tradeMsg.includes('❌') ? '#ef5350' : '#26a69a'}}>{tradeMsg}</span>}
            </div>
          </div>
        </div>
      </div>

      <div style={styles.subheader}>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          {['NIFTY', 'BANKNIFTY'].map((idx) => indexTicks[idx] && (
            <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '12px' }}>
              <span style={{ color: '#787b86' }}>{idx}</span>
              <span style={{ fontWeight: 600 }}>{indexTicks[idx].ltp?.toFixed(1)}</span>
              <span style={{ color: (indexTicks[idx].change_pct ?? 0) >= 0 ? '#26a69a' : '#ef5350' }}>
                {(indexTicks[idx].change_pct ?? 0) >= 0 ? '+' : ''}{indexTicks[idx].change_pct ?? 0}%
              </span>
            </div>
          ))}
          {lastQuote && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', marginLeft: '12px' }}>
              <span style={{ color: '#787b86', fontWeight: 600 }}>{symbol.toUpperCase().replace('.NS', '')}</span>
              <span style={{ fontWeight: 600 }}>₹{lastQuote.price?.toFixed(2)}</span>
              <span style={{ color: (lastQuote.change_pct ?? 0) >= 0 ? '#26a69a' : '#ef5350' }}>
                {(lastQuote.change_pct ?? 0) >= 0 ? '+' : ''}{lastQuote.change_pct}%
              </span>
            </div>
          )}
        </div>
      </div>

      <div style={styles.chartArea}>
        {loading && data.length === 0 && (
           <div style={styles.loadingOverlay}>Loading chart data...</div>
        )}
        <div ref={chartContainerRef} style={{ width: '100%', height: '100%' }} />
        {renderAiPanel()}
        {renderDomPanel()}
      </div>
    </div>
  );
};

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: '650px',
    width: '100%',
    backgroundColor: '#1e222d',
    color: '#d1d4dc',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Open Sans", "Helvetica Neue", sans-serif',
    borderRadius: '8px',
    overflow: 'hidden',
    boxShadow: '0 4px 6px rgba(0, 0, 0, 0.3)'
  },
  toolbar: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
    padding: '12px 16px',
    backgroundColor: '#131722',
    borderBottom: '1px solid #2b313f'
  },
  subheader: {
    padding: '6px 16px',
    backgroundColor: '#181c25',
    borderBottom: '1px solid #2b313f',
  },
  symbolInputContainer: { display: 'flex' },
  symbolInput: {
    backgroundColor: '#1e222d', color: '#d1d4dc', border: '1px solid #2b313f',
    padding: '6px 10px', borderRadius: '4px', outline: 'none', width: '100px',
    fontSize: '13px', textTransform: 'uppercase',
  },
  selectInput: {
    backgroundColor: '#1e222d', color: '#d1d4dc', border: '1px solid #2b313f',
    padding: '6px', borderRadius: '4px', outline: 'none', fontSize: '13px'
  },
  timeframeSelector: { display: 'flex', gap: '4px' },
  chartTypeSelector: { display: 'flex', gap: '8px' },
  indicatorSelector: { display: 'flex', gap: '6px', flexWrap: 'wrap' },
  button: {
    backgroundColor: 'transparent', color: '#b2b5be', border: '1px solid #2b313f',
    padding: '4px 8px', borderRadius: '4px', cursor: 'pointer', fontSize: '12px',
    transition: 'all 0.2s',
  },
  activeButton: { backgroundColor: '#2962ff', color: '#ffffff', borderColor: '#2962ff' },
  aiButton: { backgroundColor: 'transparent', color: '#e040fb', border: '1px solid #e040fb' },
  activeAiButton: { backgroundColor: '#e040fb', color: '#ffffff', border: '1px solid #e040fb' },
  domButton: { backgroundColor: 'transparent', color: '#ff9800', border: '1px solid #ff9800' },
  activeDomButton: { backgroundColor: '#ff9800', color: '#ffffff', border: '1px solid #ff9800' },
  chartArea: { flex: 1, position: 'relative', backgroundColor: '#1e222d' },
  loadingOverlay: {
    position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)',
    backgroundColor: 'rgba(30, 34, 45, 0.8)', padding: '10px 20px', borderRadius: '4px', zIndex: 10
  },
  aiPanel: {
    position: 'absolute', top: '16px', left: '16px', width: '280px',
    backgroundColor: 'rgba(19, 23, 34, 0.85)', backdropFilter: 'blur(4px)',
    border: '1px solid #2b313f', borderRadius: '6px', zIndex: 20,
    boxShadow: '0 8px 16px rgba(0,0,0,0.5)', overflow: 'hidden'
  },
  domPanel: {
    position: 'absolute', top: '16px', right: '16px', width: '240px',
    backgroundColor: 'rgba(19, 23, 34, 0.85)', backdropFilter: 'blur(4px)',
    border: '1px solid #2b313f', borderRadius: '6px', zIndex: 20,
    boxShadow: '0 8px 16px rgba(0,0,0,0.5)', overflow: 'hidden'
  },
  domHeader: {
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    backgroundColor: '#2b313f', padding: '8px 12px', fontSize: '13px', fontWeight: 'bold'
  },
  domContent: { padding: '8px 12px' },
  aiHeader: {
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    backgroundColor: '#2b313f', padding: '8px 12px', fontSize: '13px', fontWeight: 'bold'
  },
  closeBtn: {
    background: 'none', border: 'none', color: '#b2b5be', cursor: 'pointer', fontSize: '16px'
  },
  aiContent: { padding: '12px' },
  aiAction: { fontSize: '20px', fontWeight: 'bold', marginBottom: '8px' },
  aiConfidence: { fontSize: '13px', marginBottom: '12px', color: '#d1d4dc' },
  aiReasonsTitle: { fontSize: '12px', color: '#b2b5be', marginBottom: '6px' },
  aiReasonsList: { margin: 0, paddingLeft: '16px', fontSize: '12px', color: '#d1d4dc' },
  aiReasonItem: { marginBottom: '4px', lineHeight: '1.4' }
};

export default AdvancedChartEngine;
