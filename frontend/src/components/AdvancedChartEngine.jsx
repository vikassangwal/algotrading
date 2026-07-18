import React, { useState, useEffect, useRef } from 'react';
import { createChart } from 'lightweight-charts';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const AdvancedChartEngine = ({ token }) => {
  const [activeChartType, setActiveChartType] = useState('candlestick');
  const [drawingToolsEnabled, setDrawingToolsEnabled] = useState(false);
  const [symbol, setSymbol] = useState('RELIANCE'); // Default symbol
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [live, setLive] = useState(true);
  const [lastQuote, setLastQuote] = useState(null); // { price, change_pct, delayed }
  const [wsLive, setWsLive] = useState(false);      // true only while REAL Dhan ticks arrive
  const [indexTicks, setIndexTicks] = useState({}); // { NIFTY: tick, BANKNIFTY: tick }

  const chartContainerRef = useRef(null);
  const chartRef = useRef(null);
  const seriesRef = useRef(null);
  const volumeSeriesRef = useRef(null);
  const lastCandleRef = useRef(null);

  const chartTypes = [
    { id: 'candlestick', label: 'Candlestick' },
    { id: 'heikin_ashi', label: 'Heikin Ashi' },
    { id: 'renko', label: 'Renko (Line)' },
    { id: 'point_figure', label: 'P&F (Line)' }
  ];

  const fetchHistory = async () => {
    if (!token || !symbol) return;
    setLoading(true);
    try {
      const headers = { 'Authorization': `Bearer ${token}` };
      const res = await fetch(`${API_URL}/api/history/${symbol.toUpperCase()}`, { headers });
      if (res.ok) {
        const historyData = await res.json();
        // Remove duplicate times (lightweight-charts requires strictly increasing times)
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

  // Load once on mount. Symbol changes load on Enter/blur only — NOT on every
  // keystroke (each fetch is a full yfinance download server-side).
  useEffect(() => {
    fetchHistory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Transform to Heikin Ashi
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

  // Convert to Line Data
  const getLineData = (sourceData) => {
    return sourceData.map(d => ({ time: d.time, value: d.close }));
  };

  useEffect(() => {
    if (!chartContainerRef.current) return;
    if (data.length === 0) return;

    // Create chart if it doesn't exist
    if (!chartRef.current) {
      chartRef.current = createChart(chartContainerRef.current, {
        layout: {
          background: { type: 'solid', color: '#1e222d' },
          textColor: '#d1d4dc',
        },
        grid: {
          vertLines: { color: '#2b313f' },
          horzLines: { color: '#2b313f' },
        },
        timeScale: {
          timeVisible: true,
          secondsVisible: false,
        }
      });
      
      volumeSeriesRef.current = chartRef.current.addHistogramSeries({
        color: '#26a69a',
        priceFormat: {
          type: 'volume',
        },
        priceScaleId: '', // set as an overlay
        scaleMargins: {
          top: 0.8, // highest point of the series will be at 80% of the chart's height
          bottom: 0,
        },
      });
    }

    const chart = chartRef.current;

    // Remove existing series to swap chart types
    if (seriesRef.current) {
      chart.removeSeries(seriesRef.current);
    }

    if (activeChartType === 'candlestick') {
      seriesRef.current = chart.addCandlestickSeries({
        upColor: '#26a69a',
        downColor: '#ef5350',
        borderVisible: false,
        wickUpColor: '#26a69a',
        wickDownColor: '#ef5350',
      });
      seriesRef.current.setData(data);
    } else if (activeChartType === 'heikin_ashi') {
      seriesRef.current = chart.addCandlestickSeries({
        upColor: '#26a69a',
        downColor: '#ef5350',
        borderVisible: false,
        wickUpColor: '#26a69a',
        wickDownColor: '#ef5350',
      });
      seriesRef.current.setData(getHeikinAshiData(data));
    } else {
      // For Renko / P&F, fallback to Line chart for now
      seriesRef.current = chart.addLineSeries({
        color: '#2962ff',
        lineWidth: 2,
      });
      seriesRef.current.setData(getLineData(data));
    }

    // Set volume data
    const volData = data.map(d => ({ 
      time: d.time, 
      value: d.value, 
      color: d.close > d.open ? 'rgba(38, 166, 154, 0.3)' : 'rgba(239, 83, 80, 0.3)' 
    }));
    volumeSeriesRef.current.setData(volData);

    chart.timeScale().fitContent();

    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({
          width: chartContainerRef.current.clientWidth,
          height: chartContainerRef.current.clientHeight
        });
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
    };

  }, [data, activeChartType]);

  // Track the most recent candle so live quotes can extend it.
  useEffect(() => {
    if (data.length > 0) {
      lastCandleRef.current = { ...data[data.length - 1] };
    }
  }, [data]);

  // Apply a real price to the chart's forming candle (shared by WS + polling).
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
      time: prev.time,
      open: prev.open,
      high: Math.max(prev.high, price),
      low: Math.min(prev.low, price),
      close: price,
    };
    lastCandleRef.current = updated;
    series.update(updated);
  };
  const applyPriceRef = useRef(applyPrice);
  applyPriceRef.current = applyPrice;

  // TIER 1 — REAL-TIME: Dhan WebSocket ticks (sub-second, exchange feed).
  // Connects to /ws/live; on real ticks, marks the feed live and updates the
  // candle instantly. If the feed can't deliver (no/expired creds, market
  // closed), wsLive stays false and Tier 2 polling covers with delayed data.
  useEffect(() => {
    if (!live || !token || !symbol) return;
    let ws;
    let alive = true;
    let staleTimer;

    const markStale = () => {
      // No real tick for 15s → let the delayed poller take over the badge.
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
            // Index ticks for the header bar.
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
        } catch { /* ignore malformed frame */ }
      };
      ws.onclose = () => { if (alive) setWsLive(false); };
      ws.onerror = () => { if (alive) setWsLive(false); };
    } catch {
      setWsLive(false);
    }

    return () => {
      alive = false;
      clearTimeout(staleTimer);
      try { if (ws) ws.close(); } catch { /* already closed */ }
    };
  }, [live, token, symbol]);

  // TIER 2 — FALLBACK: poll the delayed (~15m) yfinance quote. Only touches
  // the chart when the real-time WS is NOT delivering, and is always labeled
  // delayed. Never fabricates movement.
  useEffect(() => {
    if (!live || !token || !symbol || wsLive) return;
    let cancelled = false;

    const poll = async () => {
      try {
        const headers = { 'Authorization': `Bearer ${token}` };
        const res = await fetch(`${API_URL}/api/quote/${symbol.toUpperCase()}`, { headers });
        if (!res.ok || cancelled) return;
        const q = await res.json();
        if (cancelled || typeof q.price !== 'number') return;
        setLastQuote(q);
        applyPriceRef.current(q.price);
      } catch {
        // Network hiccup — skip this tick, keep polling.
      }
    };

    poll();
    const id = setInterval(poll, 5000); // 5s cadence; data is delayed anyway
    return () => { cancelled = true; clearInterval(id); };
  }, [live, token, symbol, wsLive, activeChartType]);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
      }
    };
  }, []);

  return (
    <div style={styles.container}>
      <div style={styles.toolbar}>
        <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
          <div style={styles.symbolInputContainer}>
            <input 
              type="text" 
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              onBlur={fetchHistory}
              onKeyDown={(e) => e.key === 'Enter' && fetchHistory()}
              style={styles.symbolInput}
              placeholder="Enter Symbol"
            />
          </div>
          <div style={styles.chartTypeSelector}>
            {chartTypes.map(type => (
              <button
                key={type.id}
                style={{
                  ...styles.button,
                  ...(activeChartType === type.id ? styles.activeButton : {})
                }}
                onClick={() => setActiveChartType(type.id)}
              >
                {type.label}
              </button>
            ))}
          </div>
        </div>
        
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
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px' }}>
              <span style={{ fontWeight: 600 }}>₹{lastQuote.price?.toFixed(2)}</span>
              <span style={{ color: (lastQuote.change_pct ?? 0) >= 0 ? '#26a69a' : '#ef5350' }}>
                {(lastQuote.change_pct ?? 0) >= 0 ? '+' : ''}{lastQuote.change_pct}%
              </span>
              {wsLive ? (
                <span style={{ color: '#26a69a', fontSize: '11px', fontWeight: 600 }} title="Real-time exchange feed via Dhan WebSocket">
                  REAL-TIME
                </span>
              ) : lastQuote.delayed ? (
                <span style={{ color: '#b2b5be', fontSize: '11px' }} title="yfinance quotes are delayed ~15 min; real-time needs a valid Dhan token">
                  delayed ~15m
                </span>
              ) : null}
            </div>
          )}
          <button
            style={{
              ...styles.button,
              ...(live ? styles.activeButton : {})
            }}
            onClick={() => setLive(!live)}
            title="Real-time via Dhan WebSocket when available; otherwise 5s polling of delayed data"
          >
            {live ? (wsLive ? '🟢 LIVE (real-time)' : '🟡 LIVE (delayed)') : '⏸ LIVE OFF'}
          </button>
          <button
            style={{
              ...styles.button,
              ...(drawingToolsEnabled ? styles.activeButton : {})
            }}
            onClick={() => setDrawingToolsEnabled(!drawingToolsEnabled)}
          >
            {drawingToolsEnabled ? '✏️ Drawing Tools: ON' : '✏️ Drawing Tools: OFF'}
          </button>
        </div>
      </div>

      <div style={styles.chartArea}>
        {loading && data.length === 0 && (
           <div style={styles.loadingOverlay}>Loading chart data...</div>
        )}
        <div ref={chartContainerRef} style={{ width: '100%', height: '100%' }} />
      </div>
    </div>
  );
};

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: '600px',
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
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '12px 16px',
    backgroundColor: '#131722',
    borderBottom: '1px solid #2b313f'
  },
  symbolInputContainer: {
    display: 'flex',
  },
  symbolInput: {
    backgroundColor: '#1e222d',
    color: '#d1d4dc',
    border: '1px solid #2b313f',
    padding: '6px 12px',
    borderRadius: '4px',
    outline: 'none',
    width: '120px',
    fontSize: '14px',
    textTransform: 'uppercase',
  },
  chartTypeSelector: {
    display: 'flex',
    gap: '8px'
  },
  drawingToolsSelector: {
    display: 'flex'
  },
  button: {
    backgroundColor: 'transparent',
    color: '#b2b5be',
    border: '1px solid transparent',
    padding: '6px 12px',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '14px',
    transition: 'all 0.2s',
  },
  activeButton: {
    backgroundColor: '#2962ff',
    color: '#ffffff',
    borderColor: '#2962ff'
  },
  chartArea: {
    flex: 1,
    position: 'relative',
    backgroundColor: '#1e222d'
  },
  loadingOverlay: {
    position: 'absolute',
    top: '50%',
    left: '50%',
    transform: 'translate(-50%, -50%)',
    backgroundColor: 'rgba(30, 34, 45, 0.8)',
    padding: '10px 20px',
    borderRadius: '4px',
    zIndex: 10
  }
};

export default AdvancedChartEngine;
