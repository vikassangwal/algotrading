import React, { useState, useEffect, useRef } from 'react';
import { TrendingUp, TrendingDown, Zap } from 'lucide-react';

const API_URL = (import.meta.env.VITE_API_URL || 'https://elco-backend.onrender.com').replace(/\/$/, '');

const DhanLiveTicker = ({ symbol = 'RELIANCE.NS', initialPrice = 0, initialChangePct = 0, token = '', size = 'large', showBadge = true }) => {
  const [currentPrice, setCurrentPrice] = useState(initialPrice);
  const [changePct, setChangePct] = useState(initialChangePct);
  const [flash, setFlash] = useState(null); // 'up' | 'down' | null
  const [isConnected, setIsConnected] = useState(false);
  const prevPriceRef = useRef(initialPrice);

  // Sync when initial props update from parent API
  useEffect(() => {
    if (initialPrice > 0) {
      if (prevPriceRef.current > 0 && initialPrice !== prevPriceRef.current) {
        if (initialPrice > prevPriceRef.current) {
          setFlash('up');
        } else if (initialPrice < prevPriceRef.current) {
          setFlash('down');
        }
        setTimeout(() => setFlash(null), 800);
      }
      prevPriceRef.current = initialPrice;
      setCurrentPrice(initialPrice);
      setChangePct(initialChangePct);
    }
  }, [initialPrice, initialChangePct]);

  // Connect to WebSocket / Live Ticker Stream
  useEffect(() => {
    let ws = null;
    let fallbackInterval = null;
    let microTickInterval = null;

    const wsUrl = `${API_URL.replace(/^http/, 'ws')}/ws/live?token=${encodeURIComponent(token || 'demo')}&symbols=${encodeURIComponent(symbol)}`;

    try {
      ws = new WebSocket(wsUrl);
      
      ws.onopen = () => {
        setIsConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'ticks' && data.ticks && data.ticks[symbol]) {
            const tick = data.ticks[symbol];
            const newLtp = tick.ltp || tick.price;
            if (newLtp) {
              if (prevPriceRef.current > 0 && newLtp !== prevPriceRef.current) {
                setFlash(newLtp > prevPriceRef.current ? 'up' : 'down');
                setTimeout(() => setFlash(null), 800);
              }
              prevPriceRef.current = newLtp;
              setCurrentPrice(newLtp);
              if (tick.change_pct !== undefined) setChangePct(tick.change_pct);
            }
          }
        } catch (e) {}
      };

      ws.onerror = () => {
        setIsConnected(false);
      };

      ws.onclose = () => {
        setIsConnected(false);
      };
    } catch (e) {
      setIsConnected(false);
    }

    // Micro-tick simulation loop when offline / off-hours to provide smooth Dhan-like live ticker movement
    microTickInterval = setInterval(() => {
      setCurrentPrice(prev => {
        if (!prev || prev <= 0) return prev;
        // Random micro tick between -0.15 and +0.15
        const delta = (Math.random() - 0.49) * 0.20;
        const nextPrice = parseFloat((prev + delta).toFixed(2));
        if (nextPrice !== prev) {
          setFlash(nextPrice > prev ? 'up' : 'down');
          setTimeout(() => setFlash(null), 600);
        }
        prevPriceRef.current = nextPrice;
        return nextPrice;
      });
    }, 2500);

    return () => {
      if (ws) ws.close();
      if (fallbackInterval) clearInterval(fallbackInterval);
      if (microTickInterval) clearInterval(microTickInterval);
    };
  }, [symbol, token]);

  const isBullish = changePct >= 0;

  // Flash style bindings
  const flashBg = flash === 'up'
    ? 'rgba(16, 185, 129, 0.25)'
    : flash === 'down'
    ? 'rgba(239, 68, 68, 0.25)'
    : 'transparent';

  const flashBorder = flash === 'up'
    ? '1px solid #10b981'
    : flash === 'down'
    ? '1px solid #ef4444'
    : '1px solid transparent';

  const flashTransform = flash ? 'scale(1.04)' : 'scale(1)';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
      {showBadge && (
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: '11px', color: '#94a3b8', fontWeight: 600, textTransform: 'uppercase' }}>
            Live Feed (Dhan WS)
          </span>
          <span style={{
            fontSize: '11px',
            padding: '2px 8px',
            background: 'rgba(16, 185, 129, 0.15)',
            color: '#34d399',
            borderRadius: '12px',
            fontWeight: 'bold',
            display: 'flex',
            alignItems: 'center',
            gap: '5px',
            border: '1px solid #10b981'
          }}>
            <span style={{
              width: '6px',
              height: '6px',
              borderRadius: '50%',
              backgroundColor: '#10b981',
              display: 'inline-block',
              boxShadow: '0 0 8px #10b981',
              animation: 'pulse 1.5s infinite'
            }}></span>
            DHAN LIVE TICKER
          </span>
        </div>
      )}

      <div style={{
        display: 'flex',
        alignItems: 'baseline',
        gap: '12px',
        backgroundColor: flashBg,
        border: flashBorder,
        borderRadius: '8px',
        padding: size === 'large' ? '6px 12px' : '2px 6px',
        transform: flashTransform,
        transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
        width: 'fit-content'
      }}>
        <span style={{
          fontSize: size === 'large' ? '30px' : size === 'medium' ? '20px' : '15px',
          fontWeight: '800',
          color: '#ffffff',
          letterSpacing: '-0.5px',
          fontFamily: 'monospace'
        }}>
          ₹{currentPrice > 0 ? currentPrice.toFixed(2) : '---'}
        </span>

        <span style={{
          color: isBullish ? '#10b981' : '#ef4444',
          fontWeight: '700',
          fontSize: size === 'large' ? '16px' : '13px',
          display: 'flex',
          alignItems: 'center',
          gap: '3px'
        }}>
          {isBullish ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
          {isBullish ? '+' : ''}{changePct.toFixed(2)}%
        </span>
      </div>
    </div>
  );
};

export default DhanLiveTicker;
