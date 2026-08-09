import React, { useState, useEffect } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area
} from 'recharts';

const styles = {
  container: {
    padding: '32px',
    backgroundColor: '#0f172a',
    color: '#e2e8f0',
    minHeight: '100vh',
    fontFamily: '"Inter", sans-serif',
    boxSizing: 'border-box',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: '32px',
    borderBottom: '1px solid #1e293b',
    paddingBottom: '24px',
  },
  title: {
    fontSize: '32px',
    fontWeight: '800',
    margin: '0 0 8px 0',
    background: 'linear-gradient(90deg, #38bdf8, #818cf8)',
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
    letterSpacing: '-0.025em',
  },
  subtitle: {
    color: '#94a3b8',
    margin: 0,
    fontSize: '16px',
    fontWeight: '400',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: '1fr 2fr',
    gap: '24px',
  },
  card: {
    backgroundColor: '#1e293b',
    borderRadius: '16px',
    padding: '28px',
    boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
    border: '1px solid #334155',
    display: 'flex',
    flexDirection: 'column',
  },
  cardTitle: {
    fontSize: '20px',
    fontWeight: '700',
    margin: '0 0 24px 0',
    color: '#f8fafc',
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  icon: {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '32px',
    height: '32px',
    borderRadius: '8px',
    backgroundColor: '#0f172a',
    fontSize: '18px',
  },
  formGroup: {
    marginBottom: '20px',
  },
  label: {
    display: 'block',
    fontSize: '14px',
    fontWeight: '600',
    marginBottom: '10px',
    color: '#cbd5e1',
  },
  input: {
    width: '100%',
    padding: '12px 16px',
    backgroundColor: '#0f172a',
    border: '1px solid #334155',
    borderRadius: '8px',
    color: '#f8fafc',
    fontSize: '15px',
    outline: 'none',
    boxSizing: 'border-box',
    transition: 'border-color 0.2s',
  },
  runButton: {
    width: '100%',
    padding: '16px',
    backgroundColor: '#818cf8',
    color: '#ffffff',
    border: 'none',
    borderRadius: '12px',
    fontWeight: '700',
    fontSize: '16px',
    cursor: 'pointer',
    transition: 'all 0.2s',
    marginTop: 'auto',
    boxShadow: '0 4px 14px 0 rgba(129, 140, 248, 0.39)',
  },
  metricGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: '16px',
    marginBottom: '24px'
  },
  metricBox: {
    backgroundColor: '#0f172a',
    padding: '20px',
    borderRadius: '12px',
    border: '1px solid #334155',
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'center',
  },
  metricLabel: {
    fontSize: '13px',
    color: '#94a3b8',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    fontWeight: '600',
    marginBottom: '8px',
  },
  metricValue: {
    fontSize: '24px',
    fontWeight: '800',
    color: '#f8fafc',
  },
  chartContainer: {
    flex: 1,
    minHeight: '400px',
    backgroundColor: '#0f172a',
    borderRadius: '12px',
    border: '1px solid #334155',
    padding: '20px',
  },
  emptyState: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    color: '#64748b',
    textAlign: 'center',
    padding: '40px 20px',
  }
};

const StrategyLab = ({ token, globalSymbol }) => {
  const [symbol, setSymbol] = useState(globalSymbol || 'RELIANCE.NS');

  useEffect(() => {
    if (globalSymbol && globalSymbol !== symbol) {
      setSymbol(globalSymbol);
    }
  }, [globalSymbol]);
  const [years, setYears] = useState(5);
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

  const runBacktest = async () => {
    setIsOptimizing(true);
    setError(null);
    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL || ""}/api/backtest/${symbol}?years=${years}`, {
        headers: token ? { 'Authorization': `Bearer ${token}` } : {}
      });
      const data = await res.json();
      
      if (data.summary) {
        const mappedMetrics = {
            total_return: data.summary.net_profit_pct || data.summary.total_return || 0,
            annualized_cagr: data.summary.annualized_cagr || ((data.summary.net_profit_pct || 0) / years).toFixed(2),
            max_drawdown: data.summary.max_drawdown || 0,
            sharpe_ratio: data.summary.sharpe_ratio || 0,
            win_rate: data.summary.win_rate || 0,
            total_trades: data.summary.total_trades || 0,
            final_capital: data.summary.final_capital || 0
        };
        setResults({
          ...data,
          metrics: mappedMetrics
        });
      } else {
        setError(data.error || data.message || 'Backtest failed');
      }
    } catch (err) {
      console.error(err);
      setError('Network error connecting to API');
    }
    setIsOptimizing(false);
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(value);
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div>
          <h1 style={styles.title}>Historical Backtester</h1>
          <p style={styles.subtitle}>Scientific Validation Engine for AI Trading Strategies</p>
        </div>
      </div>

      <div style={styles.grid}>
        {/* Configuration Panel */}
        <div style={styles.card}>
          <h2 style={styles.cardTitle}>
            <span style={{ ...styles.icon, color: '#38bdf8' }}>⚙</span> 
            Configuration
          </h2>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', flex: 1 }}>
            <div style={styles.formGroup}>
              <label style={styles.label}>Stock Symbol (Yahoo Finance Format)</label>
              <input
                type="text"
                value={symbol}
                onChange={(e) => setSymbol(e.target.value)}
                style={styles.input}
                placeholder="e.g. RELIANCE.NS"
              />
            </div>

            <div style={styles.formGroup}>
              <label style={styles.label}>Historical Period (Years)</label>
              <select
                value={years}
                onChange={(e) => setYears(parseInt(e.target.value))}
                style={styles.input}
              >
                <option value={1}>1 Year</option>
                <option value={3}>3 Years</option>
                <option value={5}>5 Years</option>
                <option value={10}>10 Years</option>
              </select>
            </div>
            
            <div style={styles.formGroup}>
              <label style={styles.label}>Starting Capital (INR)</label>
              <input
                type="text"
                value="₹ 10,00,000"
                disabled
                style={{...styles.input, opacity: 0.7, cursor: 'not-allowed'}}
              />
            </div>
          </div>

          {error && (
            <div style={{color: '#f87171', marginBottom: '16px', fontSize: '14px', backgroundColor: '#450a0a', padding: '12px', borderRadius: '8px'}}>
              Error: {error}
            </div>
          )}

          <button 
            style={{ 
              ...styles.runButton, 
              backgroundColor: isOptimizing ? '#475569' : '#818cf8',
              cursor: isOptimizing ? 'not-allowed' : 'pointer',
              opacity: isOptimizing ? 0.7 : 1,
            }}
            onClick={runBacktest}
            disabled={isOptimizing}
          >
            {isOptimizing ? 'Running Backtest...' : 'Execute Backtest'}
          </button>
        </div>

        {/* Results Panel */}
        <div style={styles.card}>
          <h2 style={styles.cardTitle}>
            <span style={{ ...styles.icon, color: '#4ade80' }}>📊</span> 
            Performance Results
          </h2>
          
          {results ? (
            <div style={{ display: 'flex', flexDirection: 'column', flex: 1 }}>
              <div style={styles.metricGrid}>
                <div style={styles.metricBox}>
                  <div style={styles.metricLabel}>Total Return</div>
                  <div style={{ ...styles.metricValue, color: results.metrics.total_return >= 0 ? '#4ade80' : '#f87171' }}>
                    {results.metrics.total_return >= 0 ? '+' : ''}{results.metrics.total_return}%
                  </div>
                </div>
                <div style={styles.metricBox}>
                  <div style={styles.metricLabel}>CAGR</div>
                  <div style={{ ...styles.metricValue, color: results.metrics.annualized_cagr >= 0 ? '#4ade80' : '#f87171' }}>
                    {results.metrics.annualized_cagr >= 0 ? '+' : ''}{results.metrics.annualized_cagr}%
                  </div>
                </div>
                <div style={styles.metricBox}>
                  <div style={styles.metricLabel}>Max Drawdown</div>
                  <div style={{ ...styles.metricValue, color: '#f87171' }}>
                    {results.metrics.max_drawdown}%
                  </div>
                </div>
                <div style={styles.metricBox}>
                  <div style={styles.metricLabel}>Sharpe Ratio</div>
                  <div style={{ ...styles.metricValue, color: results.metrics.sharpe_ratio >= 1 ? '#4ade80' : '#facc15' }}>
                    {results.metrics.sharpe_ratio}
                  </div>
                </div>
                
                <div style={styles.metricBox}>
                  <div style={styles.metricLabel}>Win Rate</div>
                  <div style={{ ...styles.metricValue, color: '#38bdf8' }}>
                    {results.metrics.win_rate}%
                  </div>
                </div>
                <div style={styles.metricBox}>
                  <div style={styles.metricLabel}>Total Trades</div>
                  <div style={{ ...styles.metricValue, color: '#f8fafc' }}>
                    {results.metrics.total_trades}
                  </div>
                </div>
                <div style={{...styles.metricBox, gridColumn: 'span 2'}}>
                  <div style={styles.metricLabel}>Final Capital</div>
                  <div style={{ ...styles.metricValue, color: '#4ade80', fontSize: '28px' }}>
                    {formatCurrency(results.metrics.final_capital)}
                  </div>
                </div>
              </div>
              
              <div style={styles.chartContainer}>
                <h3 style={{fontSize: '14px', color: '#94a3b8', marginTop: 0, marginBottom: '20px'}}>Cumulative Equity Curve</h3>
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={results.equity_curve} margin={{ top: 10, right: 10, left: 20, bottom: 0 }}>
                    <defs>
                      <linearGradient id="colorEquity" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#818cf8" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#818cf8" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                    <XAxis 
                      dataKey="date" 
                      stroke="#94a3b8" 
                      tick={{fill: '#94a3b8', fontSize: 12}}
                      tickFormatter={(tick) => tick.split('-')[0]} // Show only year
                      minTickGap={30}
                    />
                    <YAxis 
                      stroke="#94a3b8" 
                      tick={{fill: '#94a3b8', fontSize: 12}}
                      tickFormatter={(tick) => `₹${(tick/1000).toFixed(0)}k`}
                      domain={['auto', 'auto']}
                    />
                    <Tooltip 
                      contentStyle={{backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px', color: '#f8fafc'}}
                      itemStyle={{color: '#818cf8', fontWeight: 'bold'}}
                      formatter={(value) => [formatCurrency(value), 'Equity']}
                      labelStyle={{color: '#94a3b8', marginBottom: '4px'}}
                    />
                    <Area 
                      type="monotone" 
                      dataKey="value" 
                      stroke="#818cf8" 
                      strokeWidth={2}
                      fillOpacity={1} 
                      fill="url(#colorEquity)" 
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
          ) : (
            <div style={styles.emptyState}>
              <div style={{ fontSize: '48px', marginBottom: '16px', filter: 'grayscale(1)', opacity: 0.5 }}>🧪</div>
              <h3 style={{ color: '#e2e8f0', margin: '0 0 8px 0' }}>Awaiting Configuration</h3>
              <p style={{ margin: 0, maxWidth: '250px' }}>
                Enter a valid stock symbol and select the historical period to run the AI backtest engine.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default StrategyLab;
