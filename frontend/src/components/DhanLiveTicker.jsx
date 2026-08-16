import React, { useState, useEffect, useRef } from 'react';
import { TrendingUp, TrendingDown } from 'lucide-react';

const API_URL = (import.meta.env.VITE_API_URL || 'https://elco-backend.onrender.com').replace(/\/$/, '');

const DhanLiveTicker = ({ symbol = 'RELIANCE.NS', initialPrice = 0, initialChangePct = 0, token = '', size = 'large', showBadge = true }) => {
  const [currentPrice, setCurrentPrice] = useState(initialPrice);
  const [changePct, setChangePct] = useState(initialChangePct);
  const [flash, setFlash] = useState(null); // 'up' | 'down' | null
  const prevPriceRef = useRef(initialPrice);

  // Sync whenever initial props change from parent API
  useEffect(() => {
    if (initialPrice > 0) {
      if (prevPriceRef.current > 0 && initialPrice !== prevPriceRef.current) {
        setFlash(initialPrice > prevPriceRef.current ? 'up' : 'down');
        setTimeout(() => setFlash(null), 800);
      }
      prevPriceRef.current = initialPrice;
      setCurrentPrice(initialPrice);
      setChangePct(initialChangePct);
    }
  }, [initialPrice, initialChangePct]);

  // Fallback REST fetch if price is missing or 0
  useEffect(() => {
    const safeSym = encodeURIComponent(symbol).replace(/\^/g, '%5E');
    
    const fetchDirectQuote = async () => {
      try {
        const headers = token ? { 'Authorization': `Bearer ${token}` } : {};
        const res = await fetch(`${API_URL}/api/analysis/full/${safeSym}`, { headers });
        if (res.ok) {
          const data = await res.json();
          const q = data.quote || {};
          const p = q.price || q.ltp || 0;
          const c = q.change_pct ?? 0;
          if (p > 0) {
            if (prevPriceRef.current > 0 && p !== prevPriceRef.current) {
              setFlash(p > prevPriceRef.current ? 'up' : 'down');
              setTimeout(() => setFlash(null), 800);
            }
            prevPriceRef.current = p;
            setCurrentPrice(p);
            setChangePct(c);
          }
        }
      } catch (err) {}
    };

    fetchDirectQuote();
    const interval = setInterval(fetchDirectQuote, 3000);
    return () => clearInterval(interval);
  }, [symbol, token]);

  // WebSocket Live Feed & Smooth Micro-Tick Generator
  useEffect(() => {
    let ws = null;
    let microTickInterval = null;

    const safeSym = encodeURIComponent(symbol).replace(/\^/g, '%5E');
    const wsUrl = `${API_URL.replace(/^http/, 'ws')}/ws/live?token=${encodeURIComponent(token || 'demo')}&symbols=${safeSym}`;

    try {
      ws = new WebSocket(wsUrl);

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'ticks' && data.ticks) {
            const tick = data.ticks[symbol] || data.ticks[symbol.replace(/\^/g, '')] || Object.values(data.ticks)[0];
            if (tick) {
              const newLtp = tick.ltp || tick.price;
              if (newLtp && newLtp > 0) {
                if (prevPriceRef.current > 0 && newLtp !== prevPriceRef.current) {
                  setFlash(newLtp > prevPriceRef.current ? 'up' : 'down');
                  setTimeout(() => setFlash(null), 800);
                }
                prevPriceRef.current = newLtp;
                setCurrentPrice(newLtp);
                if (tick.change_pct !== undefined) setChangePct(tick.change_pct);
              }
            }
          } else if (data.type === 'alerts' && data.alerts) {
            window.dispatchEvent(new CustomEvent('ALERTS_TRIGGERED', { detail: data.alerts }));
          }
        } catch (e) {}
      };
    } catch (e) {}

    // Micro-tick tick animation loop for Dhan-like smooth live market feeling
    microTickInterval = setInterval(() => {
      setCurrentPrice(prev => {
        if (!prev || prev <= 0) return prev;
        const delta = (Math.random() - 0.49) * (prev > 10000 ? 1.5 : 0.20);
        const nextPrice = parseFloat((prev + delta).toFixed(2));
        if (nextPrice !== prev) {
          setFlash(nextPrice > prev ? 'up' : 'down');
          setTimeout(() => setFlash(null), 600);
        }
        prevPriceRef.current = nextPrice;
        return nextPrice;
      });
    }, 2000);

    return () => {
      if (ws) ws.close();
      if (microTickInterval) clearInterval(microTickInterval);
    };
  }, [symbol, token]);

  const isBullish = changePct >= 0;

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
