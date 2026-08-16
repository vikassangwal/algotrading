import React, { useState, useEffect } from 'react';

const OrderBookPanel = ({ symbol, currentPrice }) => {
  const [bids, setBids] = useState([]);
  const [asks, setAsks] = useState([]);

  // Simulate Level 2 DOM centered around currentPrice
  useEffect(() => {
    if (!currentPrice) return;
    
    const generateDOM = () => {
      const newBids = [];
      const newAsks = [];
      let totalBidQty = 0;
      let totalAskQty = 0;
      
      const spread = currentPrice > 1000 ? 0.5 : 0.05;
      
      // Generate 10 levels of Bids (below price) and Asks (above price)
      for (let i = 1; i <= 10; i++) {
        // Asks (Sellers)
        const askPrice = currentPrice + (i * spread) + (Math.random() * spread);
        const askQty = Math.floor(Math.random() * 5000) + 100;
        totalAskQty += askQty;
        newAsks.push({ price: askPrice, qty: askQty, total: totalAskQty });
        
        // Bids (Buyers)
        const bidPrice = currentPrice - (i * spread) - (Math.random() * spread);
        const bidQty = Math.floor(Math.random() * 5000) + 100;
        totalBidQty += bidQty;
        newBids.push({ price: bidPrice, qty: bidQty, total: totalBidQty });
      }
      
      setAsks(newAsks.reverse()); // Highest ask at top, closest ask at bottom
      setBids(newBids); // Closest bid at top, lowest bid at bottom
    };

    generateDOM();
    const interval = setInterval(generateDOM, 1500); // Refresh DOM every 1.5s
    return () => clearInterval(interval);
  }, [currentPrice]);

  const maxQty = Math.max(
    ...(bids.length ? bids.map(b => b.qty) : [1]),
    ...(asks.length ? asks.map(a => a.qty) : [1])
  );

  const st = {
    panel: {
      width: '320px',
      background: '#0d1117',
      borderLeft: '1px solid #1e222d',
      display: 'flex',
      flexDirection: 'column',
      fontSize: '11px',
      color: '#b0b8c8',
      height: '100%',
      fontFamily: 'monospace'
    },
    header: { padding: '10px 12px', borderBottom: '1px solid #1e222d', fontWeight: 800, color: '#e1e3e8' },
    row: { display: 'flex', justifyContent: 'space-between', padding: '4px 12px', position: 'relative' },
    bar: { position: 'absolute', top: 0, bottom: 0, opacity: 0.15, zIndex: 0 },
    text: { position: 'relative', zIndex: 1, fontWeight: 600 }
  };

  return (
    <div style={st.panel}>
      <div style={st.header}>📊 Market Depth (DOM)</div>
      
      <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 12px', color: '#565d6e', fontSize: '10px' }}>
        <span>ASK QTY</span>
        <span>PRICE</span>
      </div>
      
      {/* Asks */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'flex-end' }}>
        {asks.map((a, i) => (
          <div key={`ask-${i}`} style={st.row}>
            <div style={{ ...st.bar, left: 0, width: `${(a.qty / maxQty) * 100}%`, background: '#ff1744' }} />
            <span style={st.text}>{a.qty}</span>
            <span style={{ ...st.text, color: '#ff1744' }}>{a.price.toFixed(2)}</span>
          </div>
        ))}
      </div>
      
      {/* Spread / Current Price */}
      <div style={{ padding: '8px 12px', textAlign: 'center', background: '#131722', fontWeight: 800, color: '#fff', borderTop: '1px solid #1e222d', borderBottom: '1px solid #1e222d' }}>
        LTP: {currentPrice?.toFixed(2)}
      </div>

      {/* Bids */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        {bids.map((b, i) => (
          <div key={`bid-${i}`} style={st.row}>
            <div style={{ ...st.bar, right: 0, width: `${(b.qty / maxQty) * 100}%`, background: '#00e676' }} />
            <span style={st.text}>{b.qty}</span>
            <span style={{ ...st.text, color: '#00e676' }}>{b.price.toFixed(2)}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default OrderBookPanel;
