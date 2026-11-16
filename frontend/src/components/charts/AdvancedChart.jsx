import { useRef, useEffect, useState, useMemo, useCallback } from 'react';
import { createChart, IChartApi, ISeriesApi, ChartOptions, Time, BarData, HistogramData, LineData, DeepPartial } from 'lightweight-charts';
import { clsx, formatters } from '../../design-system';

const CHART_COLORS = {
  background: '#0a0c10',
  grid: '#1e2430',
  text: '#9aa3b2',
  up: '#10b981',
  down: '#ef4444',
  volumeUp: 'rgba(16, 185, 129, 0.5)',
  volumeDown: 'rgba(239, 68, 68, 0.5)',
  crosshair: '#2d3444',
  watermark: 'rgba(99, 102, 241, 0.15)',
};

const INDICATOR_COLORS = {
  sma20: '#6366f1',
  sma50: '#f59e0b',
  sma200: '#ef4444',
  ema9: '#0ea5e9',
  ema21: '#a855f7',
  bbUpper: '#ef4444',
  bbLower: '#10b981',
  bbMiddle: '#6366f1',
  rsi: '#a855f7',
  macd: '#0ea5e9',
  signal: '#f59e0b',
  histogramPos: '#10b981',
  histogramNeg: '#ef4444',
  vwap: '#f59e0b',
};

const TIMEFRAMES = [
  { value: '1m', label: '1m', seconds: 60 },
  { value: '5m', label: '5m', seconds: 300 },
  { value: '15m', label: '15m', seconds: 900 },
  { value: '30m', label: '30m', seconds: 1800 },
  { value: '1h', label: '1h', seconds: 3600 },
  { value: '4h', label: '4h', seconds: 14400 },
  { value: '1d', label: '1D', seconds: 86400 },
  { value: '1w', label: '1W', seconds: 604800 },
  { value: '1M', label: '1M', seconds: 2592000 },
];

export function AdvancedChart({
  symbol,
  token,
  initialTimeframe = '15m',
  height = 600,
  showVolume = true,
  showIndicators = true,
  indicators = ['sma20', 'sma50', 'vwap'],
  onTimeframeChange,
  onSymbolChange,
  className = '',
  style = {},
  ...props
}) {
  const containerRef = useRef(null);
  const chartRef = useRef(null);
  const candleSeriesRef = useRef(null);
  const volumeSeriesRef = useRef(null);
  const indicatorSeriesRef = useRef({});
  const [timeframe, setTimeframe] = useState(initialTimeframe);
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [crosshairInfo, setCrosshairInfo] = useState(null);
  const [priceScale, setPriceScale] = useState('regular'); // 'regular' | 'log' | 'percentage'
  const [chartType, setChartType] = useState('candle'); // 'candle' | 'line' | 'area' | 'heikin' | 'renko'

  const API_URL = `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}`;

  // Initialize chart
  useEffect(() => {
    if (!containerRef.current) return;

    const chartOptions: DeepPartial<ChartOptions> = {
      layout: {
        background: { color: CHART_COLORS.background },
        textColor: CHART_COLORS.text,
        fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        fontSize: 11,
        attributionLogo: false,
      },
      grid: {
        vertLines: { color: CHART_COLORS.grid, style: 2 },
        horzLines: { color: CHART_COLORS.grid, style: 2 },
      },
      crosshair: {
        mode: 1, // Normal
        vertLine: { color: CHART_COLORS.crosshair, width: 1, style: 2, labelBackgroundColor: CHART_COLORS.background },
        horzLine: { color: CHART_COLORS.crosshair, width: 1, style: 2, labelBackgroundColor: CHART_COLORS.background },
      },
      rightPriceScale: {
        borderColor: CHART_COLORS.grid,
        scaleMargins: { top: 0.1, bottom: showVolume ? 0.3 : 0.1 },
        mode: 0, // Regular
        autoScale: true,
      },
      timeScale: {
        borderColor: CHART_COLORS.grid,
        timeVisible: true,
        secondsVisible: false,
        fixLeftEdge: false,
        fixRightEdge: false,
        rightOffset: 12,
        barSpacing: 8,
        minBarSpacing: 4,
      },
      localization: {
        locale: 'en-IN',
        timeFormatter: (time) => {
          const date = new Date(time * 1000);
          return date.toLocaleString('en-IN', {
            hour12: false,
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
          });
        },
      },
      handleScroll: { mouseWheel: true, pressedMouseMove: true, horzTouchDrag: true, vertTouchDrag: true },
      handleScale: { axisPressedMouseMove: { time: true, price: true }, mouseWheel: true, pinch: true },
      autoSize: true,
    };

    const chart = createChart(containerRef.current, chartOptions);
    chartRef.current = chart;

    // Candle series
    const candleSeries = chart.addCandlestickSeries({
      upColor: CHART_COLORS.up,
      downColor: CHART_COLORS.down,
      borderUpColor: CHART_COLORS.up,
      borderDownColor: CHART_COLORS.down,
      wickUpColor: CHART_COLORS.up,
      wickDownColor: CHART_COLORS.down,
      priceLineVisible: true,
      priceLineColor: CHART_COLORS.text,
      priceLineWidth: 1,
      priceFormat: { type: 'price', precision: 2, minMove: 0.01 },
      lastValueVisible: true,
    });
    candleSeriesRef.current = candleSeries;

    // Volume series
    if (showVolume) {
      const volumeSeries = chart.addHistogramSeries({
        color: CHART_COLORS.volumeUp,
        priceFormat: { type: 'volume' },
        priceScaleId: 'volume',
        base: 0,
      });
      volumeSeriesRef.current = volumeSeries;

      chart.priceScale('volume').applyOptions({
        scaleMargins: { top: 0.7, bottom: 0 },
        borderVisible: false,
        visible: true,
        height: '30%',
      });
    }

    // Crosshair listener
    chart.subscribeCrosshairMove((param) => {
      if (param.time && param.seriesData) {
        const candleData = param.seriesData.get(candleSeries);
        const volumeData = volumeSeriesRef.current && param.seriesData.get(volumeSeriesRef.current);
        if (candleData) {
          setCrosshairInfo({
            time: param.time,
            open: candleData.open,
            high: candleData.high,
            low: candleData.low,
            close: candleData.close,
            volume: volumeData?.value,
          });
        }
      } else {
        setCrosshairInfo(null);
      }
    });

    // Cleanup
    return () => {
      chart.unsubscribeCrosshairMove();
      chart.remove();
      chartRef.current = null;
    };
  }, [showVolume]);

  // Fetch data
  const fetchData = useCallback(async () => {
    if (!symbol) return;
    setLoading(true);
    setError(null);

    try {
      const headers = { 'Authorization': `Bearer ${token}` };
      const res = await fetch(`${API_URL}/api/history/${symbol}?interval=${timeframe}&period=60d`, { headers });
      if (!res.ok) throw new Error('Failed to fetch data');
      const result = await res.json();
      setData(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [symbol, timeframe, token, API_URL]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Update chart when data changes
  useEffect(() => {
    if (!chartRef.current || !candleSeriesRef.current || !data.length) return;

    const candleData: BarData[] = data.map(d => ({
      time: d.time as Time,
      open: d.open,
      high: d.high,
      low: d.low,
      close: d.close,
    }));

    candleSeriesRef.current.setData(candleData);

    if (volumeSeriesRef.current) {
      const volumeData: HistogramData[] = data.map(d => ({
        time: d.time as Time,
        value: d.value,
        color: d.close >= d.open ? CHART_COLORS.volumeUp : CHART_COLORS.volumeDown,
      }));
      volumeSeriesRef.current.setData(volumeData);
    }

    // Update indicators
    if (showIndicators && indicators.length) {
      updateIndicators(data);
    }

    chartRef.current.timeScale().fitContent();
  }, [data, showIndicators, indicators]);

  // Calculate and update indicators
  const updateIndicators = useCallback((chartData) => {
    if (!chartRef.current) return;

    indicators.forEach(indicator => {
      let series = indicatorSeriesRef.current[indicator];
      const values = calculateIndicator(chartData, indicator);

      if (!series) {
        const color = INDICATOR_COLORS[indicator] || '#818cf8';
        series = chartRef.current.addLineSeries({
          color,
          lineWidth: indicator.includes('sma') || indicator.includes('ema') ? 1.5 : 1,
          priceLineVisible: false,
          lastValueVisible: true,
          title: indicator.toUpperCase(),
        });
        indicatorSeriesRef.current[indicator] = series;
      }

      if (values.length) {
        series.setData(values);
      }
    });

    // Remove indicators not in list
    Object.keys(indicatorSeriesRef.current).forEach(key => {
      if (!indicators.includes(key)) {
        chartRef.current.removeSeries(indicatorSeriesRef.current[key]);
        delete indicatorSeriesRef.current[key];
      }
    });
  }, [indicators]);

  // Calculate indicator values
  const calculateIndicator = (data, indicator) => {
    if (!data.length) return [];

    const closes = data.map(d => d.close);
    const highs = data.map(d => d.high);
    const lows = data.map(d => d.low);
    const volumes = data.map(d => d.value);

    switch (indicator) {
      case 'sma20': return calculateSMA(data, closes, 20);
      case 'sma50': return calculateSMA(data, closes, 50);
      case 'sma200': return calculateSMA(data, closes, 200);
      case 'ema9': return calculateEMA(data, closes, 9);
      case 'ema21': return calculateEMA(data, closes, 21);
      case 'vwap': return calculateVWAP(data);
      case 'bb': return calculateBollingerBands(data, closes, 20, 2);
      default: return [];
    }
  };

  // Helper functions for indicators
  const calculateSMA = (data, values, period) => {
    const result = [];
    for (let i = period - 1; i < data.length; i++) {
      const sum = values.slice(i - period + 1, i + 1).reduce((a, b) => a + b, 0);
      result.push({ time: data[i].time, value: sum / period });
    }
    return result;
  };

  const calculateEMA = (data, values, period) => {
    const result = [];
    const multiplier = 2 / (period + 1);
    let ema = values.slice(0, period).reduce((a, b) => a + b, 0) / period;
    result.push({ time: data[period - 1].time, value: ema });
    for (let i = period; i < data.length; i++) {
      ema = (values[i] - ema) * multiplier + ema;
      result.push({ time: data[i].time, value: ema });
    }
    return result;
  };

  const calculateVWAP = (data) => {
    const result = [];
    let cumulativePV = 0;
    let cumulativeV = 0;
    data.forEach((d, i) => {
      const typical = (d.high + d.low + d.close) / 3;
      cumulativePV += typical * d.value;
      cumulativeV += d.value;
      if (cumulativeV > 0) {
        result.push({ time: d.time, value: cumulativePV / cumulativeV });
      }
    });
    return result;
  };

  const calculateBollingerBands = (data, closes, period, stdDev) => {
    // Returns upper, middle, lower - for now just middle (SMA)
    return calculateSMA(data, closes, period);
  };

  // Toolbar
  const toolbarItems = useMemo(() => [
    { type: 'timeframe', value: timeframe, options: TIMEFRAMES },
    { type: 'chartType', value: chartType, options: ['candle', 'line', 'area', 'heikin'] },
    { type: 'priceScale', value: priceScale, options: ['regular', 'log', 'percentage'] },
    { type: 'indicators', value: indicators },
    { type: 'divider' },
    { type: 'actions', items: [
      { label: 'Reset Zoom', action: () => chartRef.current?.timeScale().fitContent() },
      { label: 'Screenshot', action: () => chartRef.current?.chartElement()?.toBlob?.(b => { const url = URL.createObjectURL(b); const a = document.createElement('a'); a.href = url; a.download = `${symbol}-${timeframe}.png`; a.click(); }) },
    ]},
  ], [timeframe, chartType, priceScale, indicators, symbol]);

  if (loading) {
    return (
      <div className={clsx('elco-chart-loading', className)} style={{ ...style, height, display: 'flex', alignItems: 'center', justifyContent: 'center', background: CHART_COLORS.background, borderRadius: 'var(--radius-lg)', border: '1px solid var(--color-surface-border)' }}>
        <div className="elco-spinner" style={{ width: '40px', height: '40px', border: '3px solid var(--color-surface-border)', borderTopColor: 'var(--color-brand-500)', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
        <style jsx>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  if (error) {
    return (
      <div className={clsx('elco-chart-error', className)} style={{ ...style, height, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', background: CHART_COLORS.background, borderRadius: 'var(--radius-lg)', border: '1px solid var(--color-surface-border)', padding: 'var(--space-6)', textAlign: 'center' }}>
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--color-market-sell)" strokeWidth="1.5" style={{ marginBottom: 'var(--space-4)' }}>
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="8" x2="12" y2="12" />
          <line x1="12" y1="16" x2="12.01" y2="16" />
        </svg>
        <p style={{ color: 'var(--color-text-secondary)', marginBottom: 'var(--space-4)' }}>Failed to load chart</p>
        <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-tertiary)', marginBottom: 'var(--space-4)' }}>{error}</p>
        <Button variant="outline" size="sm" onClick={fetchData}>Retry</Button>
      </div>
    );
  }

  return (
    <div className={clsx('elco-advanced-chart', className)} style={{ ...style, height, position: 'relative', background: CHART_COLORS.background, borderRadius: 'var(--radius-lg)', border: '1px solid var(--color-surface-border)', overflow: 'hidden' }}>
      {/* Toolbar */}
      <div className="elco-chart-toolbar" style={{
        position: 'absolute',
        top: 'var(--space-3)',
        left: 'var(--space-3)',
        right: 'var(--space-3)',
        zIndex: 10,
        display: 'flex',
        alignItems: 'center',
        gap: 'var(--space-2)',
        flexWrap: 'wrap',
        background: 'rgba(17, 20, 26, 0.95)',
        backdropFilter: 'blur(8px)',
        padding: 'var(--space-2) var(--space-3)',
        borderRadius: 'var(--radius-md)',
        border: '1px solid var(--color-surface-border)',
      }}>
        {/* Symbol */}
        <Select
          value={symbol}
          onChange={(e) => onSymbolChange?.(e.target.value)}
          options={[
            { value: 'RELIANCE', label: 'RELIANCE' },
            { value: 'TCS', label: 'TCS' },
            { value: 'INFY', label: 'INFY' },
            { value: 'HDFCBANK', label: 'HDFCBANK' },
            { value: 'ICICIBANK', label: 'ICICIBANK' },
            { value: 'NIFTY', label: 'NIFTY 50' },
            { value: 'BANKNIFTY', label: 'BANK NIFTY' },
          ]}
          size="sm"
          style={{ width: '140px', minWidth: '140px' }}
        />

        {/* Timeframe */}
        <div className="elco-timeframe-picker" style={{ display: 'flex', gap: '2px', background: 'var(--color-surface-interactive)', borderRadius: 'var(--radius-sm)', padding: '2px' }}>
          {TIMEFRAMES.map(tf => (
            <button
              key={tf.value}
              onClick={() => { setTimeframe(tf.value); onTimeframeChange?.(tf.value); }}
              style={{
                padding: '4px 10px',
                fontSize: 'var(--font-size-xs)',
                fontWeight: 'var(--font-weight-medium)',
                color: timeframe === tf.value ? 'var(--color-text-primary)' : 'var(--color-text-secondary)',
                background: timeframe === tf.value ? 'var(--color-brand-500)' : 'transparent',
                border: 'none',
                borderRadius: 'var(--radius-sm)',
                cursor: 'pointer',
                transition: 'all var(--transition-fast)',
                whiteSpace: 'nowrap',
              }}
            >
              {tf.label}
            </button>
          ))}
        </div>

        {/* Chart Type */}
        <Select
          value={chartType}
          onChange={(e) => setChartType(e.target.value)}
          options={[
            { value: 'candle', label: 'Candle' },
            { value: 'line', label: 'Line' },
            { value: 'area', label: 'Area' },
            { value: 'heikin', label: 'Heikin Ashi' },
          ]}
          size="sm"
          style={{ width: '120px' }}
        />

        {/* Price Scale */}
        <Select
          value={priceScale}
          onChange={(e) => {
            const newScale = e.target.value;
            setPriceScale(newScale);
            if (chartRef.current) {
              chartRef.current.priceScale('right').applyOptions({ mode: newScale === 'log' ? 1 : newScale === 'percentage' ? 2 : 0 });
            }
          }}
          options={[
            { value: 'regular', label: 'Linear' },
            { value: 'log', label: 'Log' },
            { value: 'percentage', label: '%' },
          ]}
          size="sm"
          style={{ width: '100px' }}
        />

        <div style={{ flex: 1 }} />

        {/* Indicator Toggle */}
        <div style={{ display: 'flex', gap: 'var(--space-1)' }}>
          {['sma20', 'sma50', 'vwap', 'ema9', 'ema21', 'bb'].map(ind => (
            <ToggleButton
              key={ind}
              pressed={indicators.includes(ind)}
              variant="outline"
              size="sm"
              onClick={() => {
                const newIndicators = indicators.includes(ind)
                  ? indicators.filter(i => i !== ind)
                  : [...indicators, ind];
                // We'd need to lift this state up or use a callback
              }}
              style={{ fontSize: 'var(--font-size-xs)', textTransform: 'uppercase' }}
            >
              {ind.toUpperCase()}
            </ToggleButton>
          ))}
        </div>
      </div>

      {/* Crosshair Info Panel */}
      {crosshairInfo && (
        <div className="elco-crosshair-info" style={{
          position: 'absolute',
          top: '56px',
          right: 'var(--space-3)',
          zIndex: 10,
          background: 'rgba(17, 20, 26, 0.95)',
          backdropFilter: 'blur(8px)',
          padding: 'var(--space-3)',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--color-surface-border)',
          fontSize: 'var(--font-size-xs)',
          fontFamily: 'var(--font-family-mono)',
          minWidth: '200px',
        }}>
          <div style={{ color: 'var(--color-text-secondary)', marginBottom: 'var(--space-2)', fontFamily: 'var(--font-family-sans)' }}>
            {new Date(crosshairInfo.time * 1000).toLocaleString('en-IN', { hour12: false, month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: 'var(--space-2) var(--space-4)' }}>
            <span style={{ color: 'var(--color-text-tertiary)' }}>O</span>
            <span style={{ color: 'var(--color-text-primary)' }}>{formatters.price(crosshairInfo.open)}</span>
            <span style={{ color: 'var(--color-text-tertiary)' }}>H</span>
            <span style={{ color: 'var(--color-market-buy)' }}>{formatters.price(crosshairInfo.high)}</span>
            <span style={{ color: 'var(--color-text-tertiary)' }}>L</span>
            <span style={{ color: 'var(--color-market-sell)' }}>{formatters.price(crosshairInfo.low)}</span>
            <span style={{ color: 'var(--color-text-tertiary)' }}>C</span>
            <span style={{ color: 'var(--color-text-primary)', fontWeight: 'var(--font-weight-semibold)' }}>{formatters.price(crosshairInfo.close)}</span>
            {crosshairInfo.volume && (
              <>
                <span style={{ color: 'var(--color-text-tertiary)' }}>V</span>
                <span style={{ color: 'var(--color-text-secondary)' }}>{formatters.volume(crosshairInfo.volume)}</span>
              </>
            )}
          </div>
        </div>
      )}

      {/* Watermark */}
      <div className="elco-chart-watermark" style={{
        position: 'absolute',
        bottom: 'var(--space-4)',
        left: 'var(--space-4)',
        right: 'var(--space-4)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-end',
        pointerEvents: 'none',
        zIndex: 5,
      }}>
        <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-tertiary)', opacity: 0.6 }}>
          {symbol} • {timeframe} • {formatters.price(data[data.length - 1]?.close)}
        </div>
        <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-brand-500)', opacity: 0.8 }}>
          ELCO Trader
        </div>
      </div>

      {/* Chart Container */}
      <div ref={containerRef} style={{ width: '100%', height: '100%' }} {...props} />
    </div>
  );
}

import { Button, Select, ToggleButton } from '../ui';
import { clsx, formatters } from '../../design-system';

export default AdvancedChart;