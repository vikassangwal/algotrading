import React, { useEffect, useRef } from 'react';
import { createChart } from 'lightweight-charts';

const CandlestickChart = ({ data, width = '100%', height = 400 }) => {
  const chartContainerRef = useRef(null);
  const chartRef = useRef(null);
  const seriesRef = useRef(null);

  useEffect(() => {
    if (!chartContainerRef.current) return;

    // Create chart
    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: height,
      layout: {
        background: { type: 'solid', color: '#1E222D' },
        textColor: '#D9D9D9',
      },
      grid: {
        vertLines: { color: '#2B2B43' },
        horzLines: { color: '#2B2B43' },
      },
      crosshair: { mode: 1 },
      rightPriceScale: { borderColor: '#2B2B43' },
      timeScale: { borderColor: '#2B2B43', timeVisible: true, secondsVisible: false },
    });
    
    chartRef.current = chart;

    const candlestickSeries = chart.addCandlestickSeries({
      upColor: '#26a69a',
      downColor: '#ef5350',
      borderVisible: false,
      wickUpColor: '#26a69a',
      wickDownColor: '#ef5350',
    });
    
    seriesRef.current = candlestickSeries;

    // Generate some initial historical data if none is provided
    let initialData = data;
    if (!initialData || initialData.length === 0) {
      initialData = [];
      let basePrice = 24500; // BankNifty style price
      let time = Math.floor(Date.now() / 1000) - 100 * 60; // 100 minutes ago
      
      for (let i = 0; i < 100; i++) {
        const open = basePrice;
        const close = open + (Math.random() - 0.5) * 20;
        const high = Math.max(open, close) + Math.random() * 10;
        const low = Math.min(open, close) - Math.random() * 10;
        
        initialData.push({ time, open, high, low, close });
        
        basePrice = close;
        time += 60; // 1 minute interval
      }
    }

    candlestickSeries.setData(initialData);

    const handleResize = () => {
      chart.applyOptions({ width: chartContainerRef.current.clientWidth });
    };

    window.addEventListener('resize', handleResize);

    // Simulate Live Ticks every 500ms for a very "live" feel
    let lastCandle = {...initialData[initialData.length - 1]};
    const liveTickInterval = setInterval(() => {
      const now = Math.floor(Date.now() / 1000);
      
      // Every 60 seconds create a new candle, else update the current one
      if (now - lastCandle.time >= 60) {
        lastCandle = {
          time: now, // Ensure time is strictly greater
          open: lastCandle.close,
          high: lastCandle.close,
          low: lastCandle.close,
          close: lastCandle.close
        };
      }
      
      // Simulate price jump
      const diff = (Math.random() - 0.5) * 6;
      lastCandle.close += diff;
      lastCandle.high = Math.max(lastCandle.high, lastCandle.close);
      lastCandle.low = Math.min(lastCandle.low, lastCandle.close);
      
      candlestickSeries.update(lastCandle);
    }, 500);

    return () => {
      clearInterval(liveTickInterval);
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [data, height]);

  return (
    <div className="candlestick-chart-wrapper" style={{ width, height, position: 'relative' }}>
      <div 
        ref={chartContainerRef} 
        className="candlestick-chart-container"
        style={{ width: '100%', height: '100%', borderRadius: '8px', overflow: 'hidden', border: '1px solid #2B2B43' }}
      />
    </div>
  );
};

export default CandlestickChart;
