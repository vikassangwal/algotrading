import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { clsx, formatters } from '../../design-system';
import { Button, Select, Input, Card, CardHeader, CardContent, Table, Badge, Modal, Tabs, Tab } from '../ui';
import { AdvancedChart } from '../charts/AdvancedChart';

const STRATEGY_TEMPLATES = [
  { id: 'sma_crossover', name: 'SMA Crossover', description: 'Buy when SMA 20 crosses above SMA 50', category: 'Trend' },
  { id: 'rsi_mean_reversion', name: 'RSI Mean Reversion', description: 'Buy when RSI < 30, Sell when RSI > 70', category: 'Mean Reversion' },
  { id: 'bollinger_breakout', name: 'Bollinger Breakout', description: 'Buy on upper band break, sell on lower band break', category: 'Volatility' },
  { id: 'macd_signal', name: 'MACD Signal', description: 'Trade MACD crossovers with histogram confirmation', category: 'Momentum' },
  { id: 'vwap_reclaim', name: 'VWAP Reclaim', description: 'Intraday VWAP reclaim strategy', category: 'Intraday' },
  { id: 'custom', name: 'Custom Strategy', description: 'Build your own strategy in the Strategy Builder', category: 'Custom' },
];

const TIMEFRAMES = [
  { value: '1m', label: '1 Minute' },
  { value: '5m', label: '5 Minutes' },
  { value: '15m', label: '15 Minutes' },
  { value: '30m', label: '30 Minutes' },
  { value: '1h', label: '1 Hour' },
  { value: '4h', label: '4 Hours' },
  { value: '1d', label: 'Daily' },
];

export function BacktestEngine({
  token,
  className = '',
  style = {},
  ...props
}) {
  const [activeTab, setActiveTab] = useState('configure');
  const [strategy, setStrategy] = useState(STRATEGY_TEMPLATES[0].id);
  const [symbol, setSymbol] = useState('NIFTY');
  const [timeframe, setTimeframe] = useState('15m');
  const [period, setPeriod] = useState('6mo');
  const [initialCapital, setInitialCapital] = useState(1000000);
  const [positionSize, setPositionSize] = useState(10); // % of capital
  const [commission, setCommission] = useState(0.03); // %
  const [slippage, setSlippage] = useState(0.01); // %
  const [strategyParams, setStrategyParams] = useState({});

  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [results, setResults] = useState(null);
  const [trades, setTrades] = useState([]);
  const [equityCurve, setEquityCurve] = useState([]);
  const [drawdownCurve, setDrawdownCurve] = useState([]);
  const [monthlyReturns, setMonthlyReturns] = useState([]);
  const [error, setError] = useState(null);

  const API_URL = `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}`;

  // Strategy parameter configs
  const strategyConfig = useMemo(() => ({
    sma_crossover: {
      fastPeriod: { label: 'Fast SMA Period', type: 'number', default: 20, min: 5, max: 50 },
      slowPeriod: { label: 'Slow SMA Period', type: 'number', default: 50, min: 20, max: 200 },
    },
    rsi_mean_reversion: {
      period: { label: 'RSI Period', type: 'number', default: 14, min: 7, max: 30 },
      oversold: { label: 'Oversold Level', type: 'number', default: 30, min: 10, max: 40 },
      overbought: { label: 'Overbought Level', type: 'number', default: 70, min: 60, max: 90 },
    },
    bollinger_breakout: {
      period: { label: 'BB Period', type: 'number', default: 20, min: 10, max: 50 },
      stdDev: { label: 'Std Dev', type: 'number', default: 2, min: 1, max: 3, step: 0.1 },
    },
    macd_signal: {
      fast: { label: 'Fast EMA', type: 'number', default: 12, min: 5, max: 20 },
      slow: { label: 'Slow EMA', type: 'number', default: 26, min: 20, max: 50 },
      signal: { label: 'Signal Period', type: 'number', default: 9, min: 5, max: 20 },
    },
    vwap_reclaim: {
      lookback: { label: 'Lookback Periods', type: 'number', default: 5, min: 1, max: 20 },
      volumeThreshold: { label: 'Volume Threshold', type: 'number', default: 1.5, min: 1, max: 5, step: 0.1 },
    },
  }), []);

  const currentConfig = strategyConfig[strategy] || {};

  const runBacktest = useCallback(async () => {
    if (!token) return;

    setRunning(true);
    setProgress(0);
    setError(null);
    setResults(null);
    setTrades([]);
    setEquityCurve([]);
    setDrawdownCurve([]);
    setMonthlyReturns([]);

    try {
      const headers = { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' };
      const body = {
        strategy,
        symbol,
        timeframe,
        period,
        initial_capital: initialCapital,
        position_size_pct: positionSize,
        commission_pct: commission,
        slippage_pct: slippage,
        params: strategyParams,
      };

      // Simulate progress updates
      const progressInterval = setInterval(() => {
        setProgress(p => Math.min(p + Math.random() * 10, 90));
      }, 500);

      const res = await fetch(`${API_URL}/api/backtest/run`, {
        method: 'POST',
        headers,
        body: JSON.stringify(body),
      });

      clearInterval(progressInterval);

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Backtest failed');
      }

      const data = await res.json();
      setResults(data.summary);
      setTrades(data.trades || []);
      setEquityCurve(data.equity_curve || []);
      setDrawdownCurve(data.drawdown_curve || []);
      setMonthlyReturns(data.monthly_returns || []);
      setProgress(100);
      setActiveTab('results');
    } catch (err) {
      setError(err.message);
      setProgress(0);
    } finally {
      setRunning(false);
    }
  }, [token, strategy, symbol, timeframe, period, initialCapital, positionSize, commission, slippage, strategyParams, API_URL]);

  const runWalkForward = useCallback(async () => {
    // Walk-forward analysis implementation
    setRunning(true);
    setProgress(0);
    // ... implementation
    setRunning(false);
  }, [token]);

  const runMonteCarlo = useCallback(async () => {
    // Monte Carlo simulation implementation
    setRunning(true);
    setProgress(0);
    // ... implementation
    setRunning(false);
  }, [token]);

  const exportResults = useCallback(() => {
    if (!results) return;
    const data = {
      summary: results,
      trades,
      equity_curve: equityCurve,
      drawdown_curve: drawdownCurve,
      monthly_returns: monthlyReturns,
      config: { strategy, symbol, timeframe, period, initialCapital, positionSize, commission, slippage, strategyParams },
    };
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `backtest-${strategy}-${symbol}-${timeframe}-${Date.now()}.json`;
    a.click();
  }, [results, trades, equityCurve, drawdownCurve, monthlyReturns, strategy, symbol, timeframe, period, initialCapital, positionSize, commission, slippage, strategyParams]);

  if (activeTab === 'configure') {
    return (
      <div className={clsx('elco-backtest-configure', className)} style={{ ...style, height: '100%', display: 'flex', flexDirection: 'column', ...props }}>
        <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
          {/* Left Panel - Configuration */}
          <div style={{ width: '420px', background: 'var(--color-surface-panel)', borderRight: '1px solid var(--color-surface-border)', overflow: 'auto', padding: 'var(--space-4)', display: 'flex', flexDirection: 'column' }}>
            <Card variant="outlined" style={{ marginBottom: 'var(--space-4)' }}>
              <CardHeader title="Strategy Selection" />
              <CardContent>
                <Select
                  value={strategy}
                  onChange={(e) => { setStrategy(e.target.value); setStrategyParams({}); }}
                  options={STRATEGY_TEMPLATES.map(s => ({ value: s.id, label: s.name }))}
                  size="sm"
                />
                <p style={{ marginTop: 'var(--space-2)', fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)' }}>
                  {STRATEGY_TEMPLATES.find(s => s.id === strategy)?.description}
                </p>
              </CardContent>
            </Card>

            <Card variant="outlined" style={{ marginBottom: 'var(--space-4)' }}>
              <CardHeader title="Market Data" />
              <CardContent style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
                <Select
                  label="Symbol"
                  value={symbol}
                  onChange={(e) => setSymbol(e.target.value)}
                  options={[
                    { value: 'NIFTY', label: 'NIFTY 50' },
                    { value: 'BANKNIFTY', label: 'BANK NIFTY' },
                    { value: 'RELIANCE', label: 'RELIANCE' },
                    { value: 'TCS', label: 'TCS' },
                    { value: 'INFY', label: 'INFY' },
                    { value: 'HDFCBANK', label: 'HDFC BANK' },
                    { value: 'ICICIBANK', label: 'ICICI BANK' },
                  ]}
                  size="sm"
                />
                <Select
                  label="Timeframe"
                  value={timeframe}
                  onChange={(e) => setTimeframe(e.target.value)}
                  options={TIMEFRAMES}
                  size="sm"
                />
                <Select
                  label="Period"
                  value={period}
                  onChange={(e) => setPeriod(e.target.value)}
                  options={[
                    { value: '1mo', label: '1 Month' },
                    { value: '3mo', label: '3 Months' },
                    { value: '6mo', label: '6 Months' },
                    { value: '1y', label: '1 Year' },
                    { value: '2y', label: '2 Years' },
                    { value: '5y', label: '5 Years' },
                  ]}
                  size="sm"
                />
              </CardContent>
            </Card>

            <Card variant="outlined" style={{ marginBottom: 'var(--space-4)' }}>
              <CardHeader title="Capital & Risk" />
              <CardContent style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
                <Input
                  label="Initial Capital (₹)"
                  type="number"
                  value={initialCapital}
                  onChange={(e) => setInitialCapital(parseInt(e.target.value) || 0)}
                  size="sm"
                />
                <Input
                  label="Position Size (%)"
                  type="number"
                  step="0.1"
                  min="0.1"
                  max="100"
                  value={positionSize}
                  onChange={(e) => setPositionSize(parseFloat(e.target.value) || 0)}
                  size="sm"
                />
                <Input
                  label="Commission (%)"
                  type="number"
                  step="0.001"
                  min="0"
                  max="1"
                  value={commission}
                  onChange={(e) => setCommission(parseFloat(e.target.value) || 0)}
                  size="sm"
                />
                <Input
                  label="Slippage (%)"
                  type="number"
                  step="0.001"
                  min="0"
                  max="1"
                  value={slippage}
                  onChange={(e) => setSlippage(parseFloat(e.target.value) || 0)}
                  size="sm"
                />
              </CardContent>
            </Card>

            {Object.keys(currentConfig).length > 0 && (
              <Card variant="outlined" style={{ marginBottom: 'var(--space-4)' }}>
                <CardHeader title="Strategy Parameters" />
                <CardContent style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
                  {Object.entries(currentConfig).map(([key, config]) => (
                    <Input
                      key={key}
                      label={config.label}
                      type="number"
                      value={strategyParams[key] ?? config.default}
                      onChange={(e) => setStrategyParams(prev => ({ ...prev, [key]: config.type === 'number' ? (parseFloat(e.target.value) ?? config.default) : e.target.value }))}
                      size="sm"
                      min={config.min}
                      max={config.max}
                      step={config.step}
                    />
                  ))}
                </CardContent>
              </Card>
            )}

            <div style={{ marginTop: 'auto', display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
              <Button variant="primary" size="lg" onClick={runBacktest} loading={running} fullWidth leftIcon={<PlayIcon />}>
                Run Backtest
              </Button>
              <Button variant="outline" size="sm" onClick={runWalkForward} loading={running} fullWidth>
                Walk-Forward Analysis
              </Button>
              <Button variant="outline" size="sm" onClick={runMonteCarlo} loading={running} fullWidth>
                Monte Carlo Simulation
              </Button>
            </div>
          </div>

          {/* Right Panel - Preview/Progress */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            {running ? (
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 'var(--space-8)' }}>
                <div style={{ width: '80px', height: '80px', border: '4px solid var(--color-surface-border)', borderTopColor: 'var(--color-brand-500)', borderRadius: '50%', animation: 'spin 1s linear infinite', marginBottom: 'var(--space-6)' }} />
                <style jsx>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
                <h3 style={{ fontSize: 'var(--font-size-xl)', fontWeight: 'var(--font-weight-semibold)', marginBottom: 'var(--space-2)' }}>Running Backtest...</h3>
                <p style={{ color: 'var(--color-text-secondary)', marginBottom: 'var(--space-6)' }}>{strategy} on {symbol} {timeframe}</p>
                <div style={{ width: '100%', maxWidth: '400px', height: '8px', background: 'var(--color-surface-interactive)', borderRadius: 'var(--radius-full)', overflow: 'hidden' }}>
                  <div style={{ width: `${progress}%`, height: '100%', background: 'var(--color-brand-500)', borderRadius: 'var(--radius-full)', transition: 'width 0.3s ease' }} />
                </div>
                <p style={{ marginTop: 'var(--space-3)', fontSize: 'var(--font-size-sm)', color: 'var(--color-text-tertiary)', fontFamily: 'var(--font-family-mono)' }}>{Math.round(progress)}%</p>
              </div>
            ) : results ? (
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'auto', padding: 'var(--space-4)' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-4)' }}>
                  <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 'var(--font-weight-semibold)' }}>Backtest Complete</h3>
                  <Button variant="outline" size="sm" onClick={exportResults} leftIcon={<DownloadIcon />}>Export JSON</Button>
                </div>
                <ResultsSummary results={results} />
              </div>
            ) : (
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: 'var(--color-text-tertiary)', padding: 'var(--space-8)' }}>
                <svg width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" style={{ marginBottom: 'var(--space-4)', opacity: 0.3 }}>
                  <line x1="18" y1="20" x2="18" y2="10" />
                  <line x1="12" y1="20" x2="12" y2="4" />
                  <line x1="6" y1="20" x2="6" y2="14" />
                </svg>
                <h3 style={{ fontSize: 'var(--font-size-xl)', fontWeight: 'var(--font-weight-semibold)', marginBottom: 'var(--space-2)', color: 'var(--color-text-secondary)' }}>Ready to Backtest</h3>
                <p style={{ textAlign: 'center', maxWidth: '300px' }}>Configure your strategy and parameters on the left, then click "Run Backtest" to see results.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Results Tab View
  return (
    <div className={clsx('elco-backtest-results', className)} style={{ ...style, height: '100%', display: 'flex', flexDirection: 'column', ...props }}>
      <Tabs activeTab={activeTab} onChange={setActiveTab} style={{ borderBottom: '1px solid var(--color-surface-border)' }}>
        <Tab id="summary" label="Summary" />
        <Tab id="equity" label="Equity Curve" />
        <Tab id="drawdown" label="Drawdown" />
        <Tab id="trades" label="Trades" />
        <Tab id="monthly" label="Monthly Returns" />
        <Tab id="metrics" label="Metrics" />
        <Tab id="monte_carlo" label="Monte Carlo" />
      </Tabs>

      <div style={{ flex: 1, overflow: 'auto', padding: 'var(--space-4)' }}>
        {activeTab === 'summary' && <ResultsSummary results={results} />}
        {activeTab === 'equity' && <EquityCurveChart data={equityCurve} />}
        {activeTab === 'drawdown' && <DrawdownChart data={drawdownCurve} />}
        {activeTab === 'trades' && <TradesTable trades={trades} />}
        {activeTab === 'monthly' && <MonthlyReturnsHeatmap data={monthlyReturns} />}
        {activeTab === 'metrics' && <MetricsTable results={results} />}
        {activeTab === 'monte_carlo' && <MonteCarloResults />}
      </div>

      {error && (
        <div className="elco-error-toast" style={{
          position: 'fixed', bottom: 'var(--space-4)', right: 'var(--space-4)',
          background: 'var(--color-market-sell-bg)', border: '1px solid var(--color-market-sell-border)',
          borderRadius: 'var(--radius-lg)', padding: 'var(--space-4)', zIndex: 100,
          display: 'flex', alignItems: 'center', gap: 'var(--space-3)', maxWidth: '400px',
        }}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--color-market-sell)" strokeWidth="2"><circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" /></svg>
          <span style={{ color: 'var(--color-market-sell)', flex: 1 }}>{error}</span>
          <button onClick={() => setError(null)} style={{ background: 'none', border: 'none', color: 'var(--color-market-sell)', cursor: 'pointer', padding: 'var(--space-1)' }}><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg></button>
        </div>
      )}
    </div>
  );
}

// Sub-components
function ResultsSummary({ results }) {
  if (!results) return null;

  const stats = [
    { label: 'Total Return', value: formatters.percent(results.total_return_pct || 0), trend: results.total_return_pct >= 0 ? 'up' : 'down' },
    { label: 'CAGR', value: formatters.percent(results.cagr_pct || 0), trend: results.cagr_pct >= 0 ? 'up' : 'down' },
    { label: 'Sharpe Ratio', value: (results.sharpe_ratio || 0).toFixed(2), trend: results.sharpe_ratio >= 1 ? 'up' : 'neutral' },
    { label: 'Sortino Ratio', value: (results.sortino_ratio || 0).toFixed(2), trend: results.sortino_ratio >= 1 ? 'up' : 'neutral' },
    { label: 'Max Drawdown', value: formatters.percent(results.max_drawdown_pct || 0), trend: 'down' },
    { label: 'Win Rate', value: formatters.percent(results.win_rate_pct || 0), trend: results.win_rate_pct >= 50 ? 'up' : 'down' },
    { label: 'Profit Factor', value: (results.profit_factor || 0).toFixed(2), trend: results.profit_factor >= 1.5 ? 'up' : results.profit_factor >= 1 ? 'neutral' : 'down' },
    { label: 'Total Trades', value: formatters.quantity(results.total_trades || 0), trend: 'neutral' },
    { label: 'Avg Trade', value: formatters.price(results.avg_trade || 0), trend: results.avg_trade >= 0 ? 'up' : 'down' },
    { label: 'Best Trade', value: formatters.price(results.best_trade || 0), trend: 'up' },
    { label: 'Worst Trade', value: formatters.price(results.worst_trade || 0), trend: 'down' },
    { label: 'Avg Hold (bars)', value: (results.avg_hold_bars || 0).toFixed(1), trend: 'neutral' },
  ];

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 'var(--space-4)' }}>
      {stats.map((stat, i) => (
        <Card key={i} variant="default">
          <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: 'var(--letter-spacing-wider)', marginBottom: 'var(--space-1)' }}>
            {stat.label}
          </div>
          <div style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 'var(--font-weight-bold)', color: stat.trend === 'up' ? 'var(--color-market-buy)' : stat.trend === 'down' ? 'var(--color-market-sell)' : 'var(--color-text-primary)', fontFamily: 'var(--font-family-mono)' }}>
            {stat.value}
          </div>
        </Card>
      ))}
    </div>
  );
}

function EquityCurveChart({ data }) {
  return (
    <Card variant="default" style={{ height: '100%' }}>
      <CardHeader title="Equity Curve" action={<span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-tertiary)' }}>{data.length} points</span>} />
      <CardContent style={{ height: 'calc(100% - 60px)' }}>
        {data.length > 0 ? (
          <div style={{ height: '100%' }}>
            {/* Would integrate with lightweight-charts or recharts */}
            <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--color-text-tertiary)' }}>
              Equity Curve Chart - {data.length} data points
            </div>
          </div>
        ) : (
          <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--color-text-tertiary)' }}>
            No equity curve data
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function DrawdownChart({ data }) {
  return (
    <Card variant="default" style={{ height: '100%' }}>
      <CardHeader title="Drawdown" action={<span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-tertiary)' }}>{data.length} points</span>} />
      <CardContent style={{ height: 'calc(100% - 60px)' }}>
        <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--color-text-tertiary)' }}>
          Drawdown Chart - {data.length} data points
        </div>
      </CardContent>
    </Card>
  );
}

function TradesTable({ trades }) {
  const columns = [
    { key: 'entry_time', header: 'Entry Time', width: '140px' },
    { key: 'exit_time', header: 'Exit Time', width: '140px' },
    { key: 'symbol', header: 'Symbol', width: '100px' },
    { key: 'side', header: 'Side', width: '80px' },
    { key: 'qty', header: 'Qty', align: 'right', width: '80px' },
    { key: 'entry_price', header: 'Entry', align: 'right', format: 'price', width: '100px' },
    { key: 'exit_price', header: 'Exit', align: 'right', format: 'price', width: '100px' },
    { key: 'pnl', header: 'P&L', align: 'right', format: 'price', width: '100px' },
    { key: 'pnl_pct', header: 'P&L %', align: 'right', format: 'percent', width: '100px' },
    { key: 'hold_bars', header: 'Hold', align: 'center', width: '70px' },
  ];

  return (
    <Card variant="default" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <CardHeader title="Trade List" action={<span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-tertiary)' }}>{trades.length} trades</span>} />
      <CardContent style={{ flex: 1, overflow: 'auto' }}>
        <Table
          columns={columns}
          data={trades}
          keyField="id"
          sortable
          striped
          hoverable
          emptyMessage="No trades executed"
        />
      </CardContent>
    </Card>
  );
}

function MonthlyReturnsHeatmap({ data }) {
  return (
    <Card variant="default" style={{ height: '100%' }}>
      <CardHeader title="Monthly Returns Heatmap" />
      <CardContent style={{ height: 'calc(100% - 60px)', overflow: 'auto' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--color-text-tertiary)' }}>
          Monthly Returns Heatmap - {data.length} months
        </div>
      </CardContent>
    </Card>
  );
}

function MetricsTable({ results }) {
  if (!results) return null;

  const metrics = [
    { category: 'Returns', items: [
      { name: 'Total Return', value: formatters.percent(results.total_return_pct || 0) },
      { name: 'Annualized Return (CAGR)', value: formatters.percent(results.cagr_pct || 0) },
      { name: 'Avg Monthly Return', value: formatters.percent(results.avg_monthly_return_pct || 0) },
      { name: 'Best Month', value: formatters.percent(results.best_month_pct || 0) },
      { name: 'Worst Month', value: formatters.percent(results.worst_month_pct || 0) },
      { name: 'Positive Months %', value: formatters.percent(results.positive_months_pct || 0) },
    ]},
    { category: 'Risk', items: [
      { name: 'Max Drawdown', value: formatters.percent(results.max_drawdown_pct || 0) },
      { name: 'Max Drawdown Duration', value: `${results.max_dd_duration || 0} bars` },
      { name: 'Volatility (Annualized)', value: formatters.percent(results.volatility_pct || 0) },
      { name: 'VaR (95%)', value: formatters.percent(results.var_95_pct || 0) },
      { name: 'CVaR (95%)', value: formatters.percent(results.cvar_95_pct || 0) },
      { name: 'Ulcer Index', value: (results.ulcer_index || 0).toFixed(4) },
    ]},
    { category: 'Risk-Adjusted', items: [
      { name: 'Sharpe Ratio', value: (results.sharpe_ratio || 0).toFixed(2) },
      { name: 'Sortino Ratio', value: (results.sortino_ratio || 0).toFixed(2) },
      { name: 'Calmar Ratio', value: (results.calmar_ratio || 0).toFixed(2) },
      { name: 'Omega Ratio', value: (results.omega_ratio || 0).toFixed(2) },
      { name: 'K-Ratio', value: (results.k_ratio || 0).toFixed(2) },
    ]},
    { category: 'Trade Stats', items: [
      { name: 'Total Trades', value: formatters.quantity(results.total_trades || 0) },
      { name: 'Win Rate', value: formatters.percent(results.win_rate_pct || 0) },
      { name: 'Profit Factor', value: (results.profit_factor || 0).toFixed(2) },
      { name: 'Expectancy', value: formatters.price(results.expectancy || 0) },
      { name: 'Avg Win', value: formatters.price(results.avg_win || 0) },
      { name: 'Avg Loss', value: formatters.price(results.avg_loss || 0) },
      { name: 'Avg Win/Loss Ratio', value: (results.avg_win_loss_ratio || 0).toFixed(2) },
      { name: 'Largest Win', value: formatters.price(results.largest_win || 0) },
      { name: 'Largest Loss', value: formatters.price(results.largest_loss || 0) },
      { name: 'Avg Hold Time', value: `${results.avg_hold_bars || 0} bars` },
      { name: 'Consecutive Wins', value: formatters.quantity(results.max_consecutive_wins || 0) },
      { name: 'Consecutive Losses', value: formatters.quantity(results.max_consecutive_losses || 0) },
    ]},
  ];

  return (
    <Card variant="default" style={{ height: '100%', overflow: 'auto' }}>
      <CardHeader title="Detailed Metrics" />
      <CardContent>
        {metrics.map((cat, i) => (
          <div key={i} style={{ marginBottom: 'var(--space-6)' }}>
            <h4 style={{ fontSize: 'var(--font-size-sm)', fontWeight: 'var(--font-weight-semibold)', color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: 'var(--letter-spacing-wider)', marginBottom: 'var(--space-3)', paddingBottom: 'var(--space-2)', borderBottom: '1px solid var(--color-surface-border)' }}>
              {cat.category}
            </h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: 'var(--space-2)' }}>
              {cat.items.map((item, j) => (
                <div key={j} style={{ display: 'flex', justifyContent: 'space-between', padding: 'var(--space-2)', background: 'var(--color-surface-interactive)', borderRadius: 'var(--radius-md)', fontSize: 'var(--font-size-sm)' }}>
                  <span style={{ color: 'var(--color-text-secondary)' }}>{item.name}</span>
                  <span style={{ fontWeight: 'var(--font-weight-medium)', fontFamily: 'var(--font-family-mono)', color: 'var(--color-text-primary)' }}>{item.value}</span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function MonteCarloResults() {
  return (
    <Card variant="default" style={{ height: '100%' }}>
      <CardHeader title="Monte Carlo Simulation" />
      <CardContent style={{ height: 'calc(100% - 60px)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--color-text-tertiary)' }}>
        Run Monte Carlo simulation from the Configure tab to see results here.
      </CardContent>
    </Card>
  );
}

function PlayIcon() { return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="5 3 19 12 5 21 5 3" /></svg>; }
function DownloadIcon() { return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" /></svg>; }

export default BacktestEngine;