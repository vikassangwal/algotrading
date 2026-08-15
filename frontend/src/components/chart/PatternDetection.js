// Detects common candlestick patterns and basic market structure

export const detectCandlePatterns = (data) => {
  const patterns = [];
  
  for (let i = 1; i < data.length; i++) {
    const prev = data[i - 1];
    const curr = data[i];
    
    const body = Math.abs(curr.open - curr.close);
    const range = curr.high - curr.low;
    
    // Doji
    if (body <= (range * 0.1) && range > 0) {
      patterns.push({ time: curr.time, type: 'Doji', signal: 'Neutral', price: curr.high });
    }
    
    // Bullish Engulfing
    if (prev.close < prev.open && curr.close > curr.open) {
      if (curr.open <= prev.close && curr.close >= prev.open) {
        patterns.push({ time: curr.time, type: 'Bullish Engulfing', signal: 'Bullish', price: curr.low });
      }
    }
    
    // Bearish Engulfing
    if (prev.close > prev.open && curr.close < curr.open) {
      if (curr.open >= prev.close && curr.close <= prev.open) {
        patterns.push({ time: curr.time, type: 'Bearish Engulfing', signal: 'Bearish', price: curr.high });
      }
    }
    
    // Hammer
    const lowerWick = curr.close > curr.open ? curr.open - curr.low : curr.close - curr.low;
    const upperWick = curr.close > curr.open ? curr.high - curr.close : curr.high - curr.open;
    if (lowerWick >= (body * 2) && upperWick <= (body * 0.2)) {
       patterns.push({ time: curr.time, type: 'Hammer', signal: 'Bullish', price: curr.low });
    }
    
    // Shooting Star
    if (upperWick >= (body * 2) && lowerWick <= (body * 0.2)) {
       patterns.push({ time: curr.time, type: 'Shooting Star', signal: 'Bearish', price: curr.high });
    }
  }
  return patterns;
};

// Simplified Pivot High / Low detection for Market Structure (BOS/CHoCH)
export const detectMarketStructure = (data, leftBars = 3, rightBars = 3) => {
  const pivots = []; // { time, type: 'HH'|'HL'|'LH'|'LL', price }
  const highs = [];
  const lows = [];
  
  // Find raw pivots
  for (let i = leftBars; i < data.length - rightBars; i++) {
    let isHigh = true;
    let isLow = true;
    
    for (let j = 1; j <= leftBars; j++) {
      if (data[i - j].high > data[i].high) isHigh = false;
      if (data[i - j].low < data[i].low) isLow = false;
    }
    for (let j = 1; j <= rightBars; j++) {
      if (data[i + j].high > data[i].high) isHigh = false;
      if (data[i + j].low < data[i].low) isLow = false;
    }
    
    if (isHigh) highs.push({ time: data[i].time, price: data[i].high });
    if (isLow) lows.push({ time: data[i].time, price: data[i].low });
  }
  
  // Tag HH/LH/HL/LL
  let lastHigh = null;
  for (let h of highs) {
    const type = !lastHigh ? 'HH' : (h.price > lastHigh.price ? 'HH' : 'LH');
    pivots.push({ ...h, type });
    lastHigh = h;
  }
  
  let lastLow = null;
  for (let l of lows) {
    const type = !lastLow ? 'LL' : (l.price > lastLow.price ? 'HL' : 'LL');
    pivots.push({ ...l, type });
    lastLow = l;
  }
  
  return pivots.sort((a, b) => a.time - b.time);
};
