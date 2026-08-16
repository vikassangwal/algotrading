import re

with open('frontend/src/components/AdvancedChartEngine.jsx', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Update Indicators State
code = code.replace(
"""    const [indicators, setIndicators] = useState({
      sma20: false,
      sma50: false,
      ema9: false,
      bb: false,
      sr: false
    });""",
"""    const [indicators, setIndicators] = useState({
      vol: true,
      rsi: false,
      macd: false,
      sma20: false,
      sma50: false,
      ema9: false,
      bb: false,
      sr: false
    });"""
)

# 2. Add RSI and MACD functions
ema_func_end = """      }
      return ema;
    };"""

new_funcs = ema_func_end + """
  
    const calculateRSI = (data, period = 14) => {
      const rsi = [];
      let gains = 0;
      let losses = 0;
      for (let i = 1; i < data.length; i++) {
        const diff = data[i].close - data[i - 1].close;
        if (diff >= 0) gains += diff;
        else losses -= diff;
        if (i >= period) {
          const avgGain = gains / period;
          const avgLoss = losses / period;
          const rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
          rsi.push({ time: data[i].time, value: 100 - (100 / (1 + rs)) });
          const prevDiff = data[i - period + 1].close - data[i - period].close;
          if (prevDiff >= 0) gains -= prevDiff;
          else losses += prevDiff;
        }
      }
      return rsi;
    };

    const calculateMACD = (data, fast = 12, slow = 26, signal = 9) => {
      const fastEma = calculateEMA(data, fast);
      const slowEma = calculateEMA(data, slow);
      const macdLine = [];
      for (let i = 0; i < fastEma.length; i++) {
        const slowVal = slowEma.find(e => e.time === fastEma[i].time);
        if (slowVal) macdLine.push({ time: fastEma[i].time, value: fastEma[i].value - slowVal.value });
      }
      const macdSignal = calculateEMA(macdLine, signal);
      return { macdLine, macdSignal };
    };
"""
code = code.replace(ema_func_end, new_funcs)

# 3. Update Chart Initialization for Volume/RSI/MACD scales
init_chart_old = """      const chart = createChart(chartContainerRef.current, {
        layout: { background: { type: 'solid', color: '#1e222d' }, textColor: '#d1d4dc' },
        grid: { vertLines: { color: '#2b313f' }, horzLines: { color: '#2b313f' } },
        crosshair: { mode: 1 },
        timeScale: { timeVisible: true, secondsVisible: false, borderColor: '#2b313f' },
        rightPriceScale: { borderColor: '#2b313f', autoScale: true },"""

init_chart_new = init_chart_old + """
        leftPriceScale: { visible: false },
"""

code = code.replace(init_chart_old, init_chart_new)

# Add indRefs
code = code.replace(
"""    const indRefs = useRef({
      sma20: null, sma50: null, ema9: null, bbUpper: null, bbLower: null, bbMiddle: null, srHigh: null, srLow: null
    });""",
"""    const indRefs = useRef({
      sma20: null, sma50: null, ema9: null, bbUpper: null, bbLower: null, bbMiddle: null, srHigh: null, srLow: null,
      rsi: null, macdLine: null, macdSignal: null
    });"""
)

# 4. Remove showFullTradingView early return
code = code.replace(
"""  useEffect(() => {
    if (showFullTradingView) return;
    if (!chartContainerRef.current) return;""",
"""  useEffect(() => {
    if (!chartContainerRef.current) return;"""
)

# 5. Fix indicators plotting logic for RSI and MACD
update_ind_old = """    updateIndicator('sma20', indicators.sma20, null, () => calculateSMA(data, 20), { color: '#ffeb3b', lineWidth: 2, title: 'SMA 20' });
    updateIndicator('sma50', indicators.sma50, null, () => calculateSMA(data, 50), { color: '#ff9800', lineWidth: 2, title: 'SMA 50' });
    updateIndicator('ema9', indicators.ema9, null, () => calculateEMA(data, 9), { color: '#00bcd4', lineWidth: 2, title: 'EMA 9' });"""

update_ind_new = update_ind_old + """
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
"""
code = code.replace(update_ind_old, update_ind_new)

# Hide/Show Volume based on indicators.vol
vol_old = """    const volData = data.map(d => ({ 
      time: d.time, value: d.volume || 0, color: d.close > d.open ? 'rgba(38, 166, 154, 0.3)' : 'rgba(239, 83, 80, 0.3)' 
    }));
    volumeSeriesRef.current.setData(volData);"""

vol_new = """    if (indicators.vol) {
      const volData = data.map(d => ({ 
        time: d.time, value: d.volume || 0, color: d.close > d.open ? 'rgba(38, 166, 154, 0.3)' : 'rgba(239, 83, 80, 0.3)' 
      }));
      volumeSeriesRef.current.setData(volData);
    } else {
      volumeSeriesRef.current.setData([]);
    }"""
code = code.replace(vol_old, vol_new)

# Fix resize hook deps
code = code.replace(
"""  }, [data, activeChartType, indicators, aiAnalysis, showAiPanel, showFullTradingView]);""",
"""  }, [data, activeChartType, indicators, aiAnalysis, showAiPanel]);"""
)

# 6. Update Toolbar Buttons
toolbar_old = """            <button 
              style={{...styles.button, ...(showFullTradingView ? styles.activeButton : {})}} 
              onClick={() => setShowFullTradingView(!showFullTradingView)}
            >
              📊 Full TV (All Indicators)
            </button>
            
            {!showFullTradingView && (
              <>
                <button style={{...styles.button, ...(indicators.sma20 ? styles.activeButton : {})}} onClick={() => toggleIndicator('sma20')}>SMA 20</button>
                <button style={{...styles.button, ...(indicators.sma50 ? styles.activeButton : {})}} onClick={() => toggleIndicator('sma50')}>SMA 50</button>
                <button style={{...styles.button, ...(indicators.ema9 ? styles.activeButton : {})}} onClick={() => toggleIndicator('ema9')}>EMA 9</button>
                <button style={{...styles.button, ...(indicators.bb ? styles.activeButton : {})}} onClick={() => toggleIndicator('bb')}>BB Bands</button>
                <button style={{...styles.button, ...(indicators.sr ? styles.activeButton : {})}} onClick={() => toggleIndicator('sr')}>Supp/Res</button>
              </>
            )}"""

toolbar_new = """            <button style={{...styles.button, ...(indicators.vol ? styles.activeButton : {})}} onClick={() => toggleIndicator('vol')}>Volume</button>
            <button style={{...styles.button, ...(indicators.rsi ? styles.activeButton : {})}} onClick={() => toggleIndicator('rsi')}>RSI</button>
            <button style={{...styles.button, ...(indicators.macd ? styles.activeButton : {})}} onClick={() => toggleIndicator('macd')}>MACD</button>
            <button style={{...styles.button, ...(indicators.sma20 ? styles.activeButton : {})}} onClick={() => toggleIndicator('sma20')}>SMA 20</button>
            <button style={{...styles.button, ...(indicators.sma50 ? styles.activeButton : {})}} onClick={() => toggleIndicator('sma50')}>SMA 50</button>
            <button style={{...styles.button, ...(indicators.ema9 ? styles.activeButton : {})}} onClick={() => toggleIndicator('ema9')}>EMA 9</button>
            <button style={{...styles.button, ...(indicators.bb ? styles.activeButton : {})}} onClick={() => toggleIndicator('bb')}>BB Bands</button>
            <button style={{...styles.button, ...(indicators.sr ? styles.activeButton : {})}} onClick={() => toggleIndicator('sr')}>Supp/Res</button>"""
code = code.replace(toolbar_old, toolbar_new)

# Also remove showFullTradingView state completely
code = code.replace("    const [showFullTradingView, setShowFullTradingView] = useState(false);\n", "")

with open('frontend/src/components/AdvancedChartEngine.jsx', 'w', encoding='utf-8') as f:
    f.write(code)

print("Patch applied successfully.")
