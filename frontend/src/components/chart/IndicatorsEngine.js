// IndicatorsEngine.js — High-performance technical indicators library
// All functions accept OHLCV data: [{time, open, high, low, close, value/volume}]

// Helper: normalize volume field (API sends "value", some send "volume")
const vol = (d) => d.volume || d.value || 0;

// ───────────────────────── CORE INDICATORS ─────────────────────────

export const calculateSMA = (data, period) => {
  const sma = [];
  let sum = 0;
  for (let i = 0; i < data.length; i++) {
    sum += data[i].close;
    if (i >= period) sum -= data[i - period].close;
    if (i >= period - 1) {
      sma.push({ time: data[i].time, value: sum / period });
    }
  }
  return sma;
};

export const calculateEMA = (data, period) => {
  const ema = [];
  const k = 2 / (period + 1);
  // Use SMA of first `period` values as seed
  let seed = 0;
  for (let i = 0; i < Math.min(period, data.length); i++) seed += data[i].close;
  let prevEma = seed / Math.min(period, data.length);

  for (let i = 0; i < data.length; i++) {
    prevEma = i === 0 ? data[0].close : (data[i].close - prevEma) * k + prevEma;
    if (i >= period - 1) {
      ema.push({ time: data[i].time, value: prevEma });
    }
  }
  return ema;
};

export const calculateMACD = (data, fast = 12, slow = 26, signal = 9) => {
  const fastEma = calculateEMA(data, fast);
  const slowEma = calculateEMA(data, slow);

  // Build time→value map for O(1) lookup
  const slowMap = new Map();
  for (const s of slowEma) slowMap.set(s.time, s.value);

  const macdLine = [];
  for (const f of fastEma) {
    const sv = slowMap.get(f.time);
    if (sv !== undefined) {
      macdLine.push({ time: f.time, value: f.value - sv, close: f.value - sv });
    }
  }

  // Signal line is EMA of MACD values
  const sigEma = [];
  const kk = 2 / (signal + 1);
  let prev = macdLine.length > 0 ? macdLine[0].value : 0;
  for (let i = 0; i < macdLine.length; i++) {
    prev = i === 0 ? macdLine[0].value : (macdLine[i].value - prev) * kk + prev;
    if (i >= signal - 1) {
      sigEma.push({ time: macdLine[i].time, value: prev });
    }
  }

  return { macdLine, macdSignal: sigEma };
};

export const calculateFVG = (data) => {
  const fvgs = [];
  for (let i = 2; i < data.length; i++) {
    const candle1 = data[i - 2];
    const candle2 = data[i - 1]; // The large candle
    const candle3 = data[i];

    // Bullish FVG: candle1 high < candle3 low
    if (candle1.high < candle3.low && candle2.close > candle2.open) {
      fvgs.push({ time: candle2.time, type: 'bullish', top: candle3.low, bottom: candle1.high });
    }
    // Bearish FVG: candle1 low > candle3 high
    else if (candle1.low > candle3.high && candle2.close < candle2.open) {
      fvgs.push({ time: candle2.time, type: 'bearish', top: candle1.low, bottom: candle3.high });
    }
  }
  return fvgs;
};

export const calculatePOC = (data) => {
  if (!data || data.length === 0) return null;
  const volumeProfile = new Map();
  let maxVol = 0;
  let pocPrice = 0;

  for (const d of data) {
    const price = Math.round(d.close); // Bin by rounded price
    const vol = d.volume || d.value || 1;
    const currentVol = (volumeProfile.get(price) || 0) + vol;
    volumeProfile.set(price, currentVol);

    if (currentVol > maxVol) {
      maxVol = currentVol;
      pocPrice = price;
    }
  }
  return pocPrice;
};

export const calculateRSI = (data, period = 14) => {
  if (data.length < period + 1) return [];
  const rsi = [];

  // Wilder's smoothed RSI
  let gainSum = 0, lossSum = 0;
  for (let i = 1; i <= period; i++) {
    const diff = data[i].close - data[i - 1].close;
    if (diff >= 0) gainSum += diff; else lossSum -= diff;
  }
  let avgGain = gainSum / period;
  let avgLoss = lossSum / period;
  const rs0 = avgLoss === 0 ? 100 : avgGain / avgLoss;
  rsi.push({ time: data[period].time, value: 100 - 100 / (1 + rs0) });

  for (let i = period + 1; i < data.length; i++) {
    const diff = data[i].close - data[i - 1].close;
    const gain = diff >= 0 ? diff : 0;
    const loss = diff < 0 ? -diff : 0;
    avgGain = (avgGain * (period - 1) + gain) / period;
    avgLoss = (avgLoss * (period - 1) + loss) / period;
    const rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
    rsi.push({ time: data[i].time, value: 100 - 100 / (1 + rs) });
  }
  return rsi;
};

export const calculateBB = (data, period = 20, stdDevMultiplier = 2) => {
  const upper = [], lower = [], middle = [];

  let sum = 0;
  for (let i = 0; i < data.length; i++) {
    sum += data[i].close;
    if (i >= period) sum -= data[i - period].close;
    if (i >= period - 1) {
      const mean = sum / period;
      let varianceSum = 0;
      for (let j = 0; j < period; j++) {
        varianceSum += Math.pow(data[i - j].close - mean, 2);
      }
      const stdDev = Math.sqrt(varianceSum / period);
      middle.push({ time: data[i].time, value: mean });
      upper.push({ time: data[i].time, value: mean + stdDev * stdDevMultiplier });
      lower.push({ time: data[i].time, value: mean - stdDev * stdDevMultiplier });
    }
  }
  return { upper, lower, middle };
};

export const calculateVWAP = (data) => {
  const vwap = [];
  let cumTPV = 0, cumVol = 0;

  for (let i = 0; i < data.length; i++) {
    const tp = (data[i].high + data[i].low + data[i].close) / 3;
    const v = vol(data[i]) || 1;
    cumTPV += tp * v;
    cumVol += v;
    vwap.push({ time: data[i].time, value: cumTPV / cumVol });
  }
  return vwap;
};

export const calculateATR = (data, period = 14) => {
  if (data.length < 2) return [];
  const atr = [];

  // True Range array
  const tr = [];
  for (let i = 1; i < data.length; i++) {
    const hl = data[i].high - data[i].low;
    const hpc = Math.abs(data[i].high - data[i - 1].close);
    const lpc = Math.abs(data[i].low - data[i - 1].close);
    tr.push(Math.max(hl, hpc, lpc));
  }

  // First ATR = simple average
  if (tr.length < period) return [];
  let atrVal = 0;
  for (let j = 0; j < period; j++) atrVal += tr[j];
  atrVal /= period;
  atr.push({ time: data[period].time, value: atrVal });

  // Smoothed ATR
  for (let i = period; i < tr.length; i++) {
    atrVal = (atrVal * (period - 1) + tr[i]) / period;
    atr.push({ time: data[i + 1].time, value: atrVal });
  }
  return atr;
};

// ───────────────────────── ADVANCED INDICATORS ─────────────────────────

export const calculateSupertrend = (data, period = 10, multiplier = 3) => {
  const atrData = calculateATR(data, period);
  if (atrData.length === 0) return [];

  const atrMap = new Map();
  for (const a of atrData) atrMap.set(a.time, a.value);

  const supertrend = [];
  let prevUpperFinal = 0, prevLowerFinal = 0, prevTrend = 1;

  for (let i = period; i < data.length; i++) {
    const atr = atrMap.get(data[i].time);
    if (!atr) continue;

    const hl2 = (data[i].high + data[i].low) / 2;
    const upperBasic = hl2 + multiplier * atr;
    const lowerBasic = hl2 - multiplier * atr;
    const prevClose = data[i - 1].close;

    const upperFinal = (upperBasic < prevUpperFinal || prevClose > prevUpperFinal) ? upperBasic : prevUpperFinal;
    const lowerFinal = (lowerBasic > prevLowerFinal || prevClose < prevLowerFinal) ? lowerBasic : prevLowerFinal;

    let trend = prevTrend;
    if (prevTrend === 1 && data[i].close < lowerFinal) trend = -1;
    else if (prevTrend === -1 && data[i].close > upperFinal) trend = 1;

    supertrend.push({ time: data[i].time, value: trend === 1 ? lowerFinal : upperFinal, trend });
    prevUpperFinal = upperFinal;
    prevLowerFinal = lowerFinal;
    prevTrend = trend;
  }
  return supertrend;
};

export const calculateStochRSI = (data, rsiPeriod = 14, stochPeriod = 14, kSmooth = 3, dSmooth = 3) => {
  const rsiData = calculateRSI(data, rsiPeriod);
  if (rsiData.length < stochPeriod) return { k: [], d: [] };

  const kLine = [];
  for (let i = stochPeriod - 1; i < rsiData.length; i++) {
    let minRSI = Infinity, maxRSI = -Infinity;
    for (let j = 0; j < stochPeriod; j++) {
      const v = rsiData[i - j].value;
      if (v < minRSI) minRSI = v;
      if (v > maxRSI) maxRSI = v;
    }
    const range = maxRSI - minRSI;
    const stoch = range === 0 ? 50 : ((rsiData[i].value - minRSI) / range) * 100;
    kLine.push({ time: rsiData[i].time, value: stoch, close: stoch });
  }

  // Smooth %K with SMA
  const kSmoothed = [];
  let kSum = 0;
  for (let i = 0; i < kLine.length; i++) {
    kSum += kLine[i].value;
    if (i >= kSmooth) kSum -= kLine[i - kSmooth].value;
    if (i >= kSmooth - 1) kSmoothed.push({ time: kLine[i].time, value: kSum / kSmooth });
  }

  // %D = SMA of smoothed %K
  const dLine = [];
  let dSum = 0;
  for (let i = 0; i < kSmoothed.length; i++) {
    dSum += kSmoothed[i].value;
    if (i >= dSmooth) dSum -= kSmoothed[i - dSmooth].value;
    if (i >= dSmooth - 1) dLine.push({ time: kSmoothed[i].time, value: dSum / dSmooth });
  }

  return { k: kSmoothed, d: dLine };
};

export const calculateIchimoku = (data, convPeriod = 9, basePeriod = 26, spanBPeriod = 52) => {
  const highLow = (start, end) => {
    let hi = -Infinity, lo = Infinity;
    for (let i = start; i <= end; i++) {
      if (data[i].high > hi) hi = data[i].high;
      if (data[i].low < lo) lo = data[i].low;
    }
    return { hi, lo };
  };

  const tenkan = [], kijun = [], spanA = [], spanB = [];

  for (let i = 0; i < data.length; i++) {
    if (i >= convPeriod - 1) {
      const hl = highLow(i - convPeriod + 1, i);
      tenkan.push({ time: data[i].time, value: (hl.hi + hl.lo) / 2 });
    }
    if (i >= basePeriod - 1) {
      const hl = highLow(i - basePeriod + 1, i);
      kijun.push({ time: data[i].time, value: (hl.hi + hl.lo) / 2 });
    }
    if (i >= spanBPeriod - 1) {
      const hl = highLow(i - spanBPeriod + 1, i);
      spanB.push({ time: data[i].time, value: (hl.hi + hl.lo) / 2 });
    }
  }

  // Span A = avg(tenkan, kijun) shifted forward by basePeriod
  for (let i = 0; i < Math.min(tenkan.length, kijun.length); i++) {
    spanA.push({ time: tenkan[i].time, value: (tenkan[i].value + kijun[i].value) / 2 });
  }

  return { tenkan, kijun, spanA, spanB };
};

// ───────────────── AI SUPER PREDICTOR (20 indicators combined) ─────────────────

export const calculateAIPredictor = (data) => {
  if (data.length < 55) return [];

  // Pre-calculate all indicators
  const sma20 = calculateSMA(data, 20);
  const sma50 = calculateSMA(data, 50);
  const ema9 = calculateEMA(data, 9);
  const ema21 = calculateEMA(data, 21);
  const ema50 = calculateEMA(data, 50);
  const rsi = calculateRSI(data, 14);
  const macd = calculateMACD(data);
  const vwap = calculateVWAP(data);
  const bb = calculateBB(data, 20, 2);
  const atr = calculateATR(data, 14);
  const supertrend = calculateSupertrend(data);
  const stochRSI = calculateStochRSI(data);

  // Build O(1) lookup maps for every indicator
  const maps = {};
  const buildMap = (arr) => { const m = new Map(); for (const d of arr) m.set(d.time, d.value); return m; };

  maps.sma20 = buildMap(sma20);
  maps.sma50 = buildMap(sma50);
  maps.ema9 = buildMap(ema9);
  maps.ema21 = buildMap(ema21);
  maps.ema50 = buildMap(ema50);
  maps.rsi = buildMap(rsi);
  maps.macdLine = buildMap(macd.macdLine);
  maps.macdSig = buildMap(macd.macdSignal);
  maps.vwap = buildMap(vwap);
  maps.bbUpper = buildMap(bb.upper);
  maps.bbLower = buildMap(bb.lower);
  maps.bbMiddle = buildMap(bb.middle);
  maps.atr = buildMap(atr);
  const stMap = new Map();
  for (const s of supertrend) stMap.set(s.time, s);
  maps.stochK = buildMap(stochRSI.k);
  maps.stochD = buildMap(stochRSI.d);

  const predictorLine = [];

  for (let i = 52; i < data.length; i++) {
    const t = data[i].time;
    const c = data[i].close;
    const h = data[i].high;
    const l = data[i].low;
    const prevC = data[i - 1].close;

    let score = 0; // Range: -20 to +20

    // 1. SMA 20 trend
    const s20 = maps.sma20.get(t); if (s20) score += c > s20 ? 1 : -1;
    // 2. SMA 50 trend
    const s50 = maps.sma50.get(t); if (s50) score += c > s50 ? 1 : -1;
    // 3. EMA 9 trend
    const e9 = maps.ema9.get(t); if (e9) score += c > e9 ? 1 : -1;
    // 4. EMA 21 trend
    const e21 = maps.ema21.get(t); if (e21) score += c > e21 ? 1 : -1;
    // 5. EMA 50 trend
    const e50 = maps.ema50.get(t); if (e50) score += c > e50 ? 1 : -1;
    // 6. EMA 9 > EMA 21 (golden cross)
    if (e9 && e21) score += e9 > e21 ? 1 : -1;
    // 7. Price above VWAP
    const vw = maps.vwap.get(t); if (vw) score += c > vw ? 1 : -1;
    // 8. RSI momentum
    const rsiV = maps.rsi.get(t);
    if (rsiV !== undefined) {
      if (rsiV > 60) score += 2;
      else if (rsiV > 50) score += 1;
      else if (rsiV < 40) score -= 2;
      else if (rsiV < 50) score -= 1;
    }
    // 9. MACD above signal
    const ml = maps.macdLine.get(t), ms = maps.macdSig.get(t);
    if (ml !== undefined && ms !== undefined) score += ml > ms ? 1.5 : -1.5;
    // 10. MACD positive
    if (ml !== undefined) score += ml > 0 ? 0.5 : -0.5;
    // 11. Bollinger Band position
    const bbU = maps.bbUpper.get(t), bbL = maps.bbLower.get(t), bbM = maps.bbMiddle.get(t);
    if (bbU && bbL && bbM) {
      if (c > bbM) score += 0.5;
      else score -= 0.5;
      // Near upper band = overbought penalty, near lower = oversold bonus
      const bbRange = bbU - bbL;
      if (bbRange > 0) {
        const pos = (c - bbL) / bbRange;
        if (pos > 0.9) score -= 1; // overbought
        if (pos < 0.1) score += 1; // oversold bounce
      }
    }
    // 12. Supertrend direction
    const st = stMap.get(t);
    if (st) score += st.trend === 1 ? 1.5 : -1.5;
    // 13. Stochastic RSI
    const sk = maps.stochK.get(t), sd = maps.stochD.get(t);
    if (sk !== undefined && sd !== undefined) {
      score += sk > sd ? 0.5 : -0.5;
      if (sk > 80) score -= 0.5; // overbought
      if (sk < 20) score += 0.5; // oversold
    }
    // 14. Price action momentum (breakout)
    if (c > data[i - 1].high) score += 1;
    else if (c < data[i - 1].low) score -= 1;
    // 15. Volume surge
    const curVol = vol(data[i]);
    const prevVol = vol(data[i - 1]);
    if (prevVol > 0 && curVol > prevVol * 1.5) {
      score += c > prevC ? 1 : -1; // volume confirms direction
    }
    // 16. Higher highs / lower lows (3-bar)
    if (i >= 3) {
      if (data[i].high > data[i-1].high && data[i-1].high > data[i-2].high) score += 0.5;
      if (data[i].low < data[i-1].low && data[i-1].low < data[i-2].low) score -= 0.5;
    }
    // 17. Candle body strength
    const bodyRatio = Math.abs(c - data[i].open) / (h - l || 1);
    if (bodyRatio > 0.7) score += c > data[i].open ? 0.5 : -0.5;

    // Normalize score to confidence (max theoretical ~20)
    const maxScore = 20;
    const confidence = Math.min(Math.abs(score) / maxScore, 1);
    const direction = score > 0 ? 1 : -1;

    // Predicted value: current price + (score-weighted volatility projection)
    const atrV = maps.atr.get(t) || Math.abs(h - l);
    const predictedValue = c + (score / maxScore) * atrV * 1.5;

    // Color: strong green/red for high confidence, orange for low
    let color;
    if (confidence > 0.5) color = direction > 0 ? '#00e676' : '#ff1744';
    else if (confidence > 0.25) color = direction > 0 ? '#69f0ae' : '#ff8a80';
    else color = '#ff9800';

    predictorLine.push({ time: t, value: predictedValue, color, score, confidence });
  }

  // Future Projection (5 candles ahead)
  if (predictorLine.length >= 3) {
    const last = data[data.length - 1];
    let lastPrice = last.close;
    let lastTime = last.time;
    const timeStep = data.length > 2 ? data[data.length - 1].time - data[data.length - 2].time : 900;

    // Use average of last 3 scores for smoother projection
    const avgScore = (predictorLine[predictorLine.length - 1].score +
                      predictorLine[predictorLine.length - 2].score +
                      predictorLine[predictorLine.length - 3].score) / 3;
    const atrLast = maps.atr.get(last.time) || Math.abs(last.high - last.low);
    const momentum = (avgScore / 20) * atrLast * 0.4;

    for (let f = 1; f <= 5; f++) {
      lastTime += timeStep;
      lastPrice += momentum * (1 - f * 0.1); // Decay projection
      predictorLine.push({
        time: lastTime,
        value: lastPrice,
        color: '#e040fb', // Purple = future
        score: avgScore,
        confidence: Math.max(0, 0.8 - f * 0.12)
      });
    }
  }

  return predictorLine;
};

// ───────────────── FIBONACCI RETRACEMENT (Auto from recent swing) ─────────────────

export const calculateFibonacci = (data) => {
  if (data.length < 20) return [];
  // Find recent swing high and swing low from last 50 bars
  const lookback = Math.min(50, data.length);
  const slice = data.slice(-lookback);
  let swingHigh = -Infinity, swingLow = Infinity;
  for (const d of slice) {
    if (d.high > swingHigh) swingHigh = d.high;
    if (d.low < swingLow) swingLow = d.low;
  }
  const diff = swingHigh - swingLow;
  if (diff <= 0) return [];

  const levels = [
    { ratio: 0, label: '0%', color: '#787b86' },
    { ratio: 0.236, label: '23.6%', color: '#2196f3' },
    { ratio: 0.382, label: '38.2%', color: '#00bcd4' },
    { ratio: 0.5, label: '50%', color: '#ff9800' },
    { ratio: 0.618, label: '61.8%', color: '#e040fb' },
    { ratio: 0.786, label: '78.6%', color: '#f44336' },
    { ratio: 1, label: '100%', color: '#787b86' },
  ];

  const startTime = data[data.length - lookback]?.time || data[0].time;
  const endTime = data[data.length - 1].time;

  return levels.map(l => ({
    label: l.label,
    value: swingHigh - diff * l.ratio,
    color: l.color,
    data: [{ time: startTime, value: swingHigh - diff * l.ratio }, { time: endTime, value: swingHigh - diff * l.ratio }]
  }));
};

// ───────────────── PIVOT POINTS (Standard Floor Pivots) ─────────────────

export const calculatePivotPoints = (data) => {
  if (data.length < 2) return [];
  // Use previous day's data (or previous bar for intraday)
  const prev = data[data.length - 2];
  const h = prev.high, l = prev.low, c = prev.close;
  const pp = (h + l + c) / 3;
  const r1 = 2 * pp - l;
  const s1 = 2 * pp - h;
  const r2 = pp + (h - l);
  const s2 = pp - (h - l);
  const r3 = h + 2 * (pp - l);
  const s3 = l - 2 * (h - pp);

  const startTime = data[0].time;
  const endTime = data[data.length - 1].time;

  return [
    { label: 'R3', value: r3, color: '#ff1744', data: [{ time: startTime, value: r3 }, { time: endTime, value: r3 }] },
    { label: 'R2', value: r2, color: '#ef5350', data: [{ time: startTime, value: r2 }, { time: endTime, value: r2 }] },
    { label: 'R1', value: r1, color: '#ff8a80', data: [{ time: startTime, value: r1 }, { time: endTime, value: r1 }] },
    { label: 'PP', value: pp, color: '#ff9800', data: [{ time: startTime, value: pp }, { time: endTime, value: pp }] },
    { label: 'S1', value: s1, color: '#69f0ae', data: [{ time: startTime, value: s1 }, { time: endTime, value: s1 }] },
    { label: 'S2', value: s2, color: '#26a69a', data: [{ time: startTime, value: s2 }, { time: endTime, value: s2 }] },
    { label: 'S3', value: s3, color: '#00e676', data: [{ time: startTime, value: s3 }, { time: endTime, value: s3 }] },
  ];
};

// ───────────────── ADX (Average Directional Index) ─────────────────

export const calculateADX = (data, period = 14) => {
  if (data.length < period * 2 + 1) return { adx: [], pdi: [], mdi: [] };

  const tr = [], plusDM = [], minusDM = [];

  for (let i = 1; i < data.length; i++) {
    const hi = data[i].high, lo = data[i].low, pc = data[i - 1].close;
    tr.push(Math.max(hi - lo, Math.abs(hi - pc), Math.abs(lo - pc)));

    const upMove = hi - data[i - 1].high;
    const downMove = data[i - 1].low - lo;
    plusDM.push(upMove > downMove && upMove > 0 ? upMove : 0);
    minusDM.push(downMove > upMove && downMove > 0 ? downMove : 0);
  }

  // Smoothed averages
  const smooth = (arr) => {
    const result = [];
    let sum = 0;
    for (let i = 0; i < arr.length; i++) {
      if (i < period) { sum += arr[i]; if (i === period - 1) result.push(sum); }
      else result.push(result[result.length - 1] - result[result.length - 1] / period + arr[i]);
    }
    return result;
  };

  const sTR = smooth(tr), sPDM = smooth(plusDM), sMDM = smooth(minusDM);

  const pdi = [], mdi = [], dx = [];
  for (let i = 0; i < sTR.length; i++) {
    const pdiVal = sTR[i] > 0 ? (sPDM[i] / sTR[i]) * 100 : 0;
    const mdiVal = sTR[i] > 0 ? (sMDM[i] / sTR[i]) * 100 : 0;
    pdi.push({ time: data[i + period].time, value: pdiVal });
    mdi.push({ time: data[i + period].time, value: mdiVal });
    const sum = pdiVal + mdiVal;
    dx.push(sum > 0 ? Math.abs(pdiVal - mdiVal) / sum * 100 : 0);
  }

  // ADX = smoothed DX
  const adx = [];
  if (dx.length >= period) {
    let adxVal = dx.slice(0, period).reduce((a, b) => a + b, 0) / period;
    adx.push({ time: data[period * 2].time, value: adxVal });
    for (let i = period; i < dx.length; i++) {
      adxVal = (adxVal * (period - 1) + dx[i]) / period;
      if (i + period < data.length) adx.push({ time: data[i + period].time, value: adxVal });
    }
  }

  return { adx, pdi, mdi };
};
