import React, { useState } from 'react';

const WalkForwardUI = ({ globalSymbol }) => {
  const [activeTab, setActiveTab] = useState('walkforward');
  const [inSampleSize, setInSampleSize] = useState(70);
  const [outOfSampleSize, setOutOfSampleSize] = useState(30);
  const [metric, setMetric] = useState('Sharpe Ratio');
  const [mcSimulations, setMcSimulations] = useState(1000);
  const [mcNoise, setMcNoise] = useState(0.5);
  const [isRunning, setIsRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [results, setResults] = useState(null);

  const handleRun = () => {
    setIsRunning(true);
    setProgress(0);
    setResults(null);
    
    // Simulate complex analysis
    let p = 0;
    const interval = setInterval(() => {
      p += 5;
      setProgress(p);
      if (p >= 100) {
        clearInterval(interval);
        setIsRunning(false);
        setResults({
          wf: [
            { window: 1, isReturn: 12.5, oosReturn: 4.2, pass: true },
            { window: 2, isReturn: 10.1, oosReturn: -1.5, pass: false },
            { window: 3, isReturn: 15.3, oosReturn: 6.8, pass: true },
            { window: 4, isReturn: 8.7, oosReturn: 2.1, pass: true },
          ],
          mc: {
            median: 8.5,
            worstCase: -15.2,
            bestCase: 35.4,
            probabilityOfRuin: 2.3
          }
        });
      }
    }, 100);
  };

  const styles = {
    container: {
      fontFamily: 'system-ui, -apple-system, sans-serif',
      maxWidth: '1200px',
      margin: '0 auto',
      padding: '20px',
      backgroundColor: '#f8fafc',
      borderRadius: '8px',
      boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
      color: '#1e293b'
    },
    header: {
      borderBottom: '1px solid #e2e8f0',
      paddingBottom: '16px',
      marginBottom: '24px',
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center'
    },
    title: {
      fontSize: '24px',
      fontWeight: 'bold',
      margin: 0
    },
    tabs: {
      display: 'flex',
      gap: '12px',
      marginBottom: '24px'
    },
    tab: (active) => ({
      padding: '8px 16px',
      borderRadius: '6px',
      border: 'none',
      backgroundColor: active ? '#2563eb' : '#e2e8f0',
      color: active ? '#ffffff' : '#475569',
      cursor: 'pointer',
      fontWeight: '500',
      transition: 'all 0.2s'
    }),
    grid: {
      display: 'grid',
      gridTemplateColumns: '300px 1fr',
      gap: '24px'
    },
    sidebar: {
      backgroundColor: '#ffffff',
      padding: '20px',
      borderRadius: '8px',
      border: '1px solid #e2e8f0'
    },
    formGroup: {
      marginBottom: '16px'
    },
    label: {
      display: 'block',
      fontSize: '14px',
      fontWeight: '500',
      marginBottom: '8px',
      color: '#475569'
    },
    input: {
      width: '100%',
      padding: '8px',
      borderRadius: '4px',
      border: '1px solid #cbd5e1',
      fontSize: '14px',
      boxSizing: 'border-box'
    },
    button: (disabled) => ({
      width: '100%',
      padding: '12px',
      backgroundColor: disabled ? '#94a3b8' : '#10b981',
      color: 'white',
      border: 'none',
      borderRadius: '6px',
      fontWeight: '600',
      cursor: disabled ? 'not-allowed' : 'pointer',
      marginTop: '16px'
    }),
    progressBar: {
      width: '100%',
      height: '8px',
      backgroundColor: '#e2e8f0',
      borderRadius: '4px',
      overflow: 'hidden',
      marginTop: '16px'
    },
    progressFill: (percent) => ({
      width: `${percent}%`,
      height: '100%',
      backgroundColor: '#3b82f6',
      transition: 'width 0.1s linear'
    }),
    main: {
      backgroundColor: '#ffffff',
      padding: '24px',
      borderRadius: '8px',
      border: '1px solid #e2e8f0'
    },
    table: {
      width: '100%',
      borderCollapse: 'collapse',
      marginTop: '16px'
    },
    th: {
      textAlign: 'left',
      padding: '12px',
      backgroundColor: '#f1f5f9',
      borderBottom: '2px solid #e2e8f0',
      fontWeight: '600',
      color: '#475569'
    },
    td: {
      padding: '12px',
      borderBottom: '1px solid #e2e8f0',
      color: '#334155'
    },
    badge: (pass) => ({
      padding: '4px 8px',
      borderRadius: '9999px',
      fontSize: '12px',
      fontWeight: '500',
      backgroundColor: pass ? '#d1fae5' : '#fee2e2',
      color: pass ? '#065f46' : '#991b1b'
    }),
    statsGrid: {
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
      gap: '16px',
      marginTop: '16px'
    },
    statCard: {
      padding: '16px',
      backgroundColor: '#f8fafc',
      borderRadius: '6px',
      border: '1px solid #e2e8f0'
    },
    statValue: (val) => ({
      fontSize: '24px',
      fontWeight: 'bold',
      color: val < 0 ? '#ef4444' : '#10b981',
      marginTop: '8px'
    })
  };

  return (
    <div style={styles.container}>
      <header style={styles.header}>
        <h2 style={styles.title}>Advanced Robustness Analysis</h2>
        <div style={styles.tabs}>
          <button 
            style={styles.tab(activeTab === 'walkforward')} 
            onClick={() => setActiveTab('walkforward')}
          >
            Walk-Forward
          </button>
          <button 
            style={styles.tab(activeTab === 'montecarlo')} 
            onClick={() => setActiveTab('montecarlo')}
          >
            Monte Carlo
          </button>
        </div>
      </header>

      <div style={styles.grid}>
        {/* Sidebar Configuration */}
        <aside style={styles.sidebar}>
          <h3 style={{ marginTop: 0, marginBottom: '20px', color: '#0f172a' }}>Parameters</h3>
          
          {activeTab === 'walkforward' ? (
            <>
              <div style={styles.formGroup}>
                <label style={styles.label}>In-Sample Window (%)</label>
                <input 
                  type="number" 
                  value={inSampleSize} 
                  onChange={(e) => setInSampleSize(e.target.value)}
                  style={styles.input}
                />
              </div>
              <div style={styles.formGroup}>
                <label style={styles.label}>Out-of-Sample Window (%)</label>
                <input 
                  type="number" 
                  value={outOfSampleSize} 
                  onChange={(e) => setOutOfSampleSize(e.target.value)}
                  style={styles.input}
                />
              </div>
              <div style={styles.formGroup}>
                <label style={styles.label}>Optimization Metric</label>
                <select 
                  value={metric} 
                  onChange={(e) => setMetric(e.target.value)}
                  style={styles.input}
                >
                  <option>Net Profit</option>
                  <option>Sharpe Ratio</option>
                  <option>Sortino Ratio</option>
                  <option>Max Drawdown</option>
                </select>
              </div>
            </>
          ) : (
            <>
              <div style={styles.formGroup}>
                <label style={styles.label}>Simulations Count</label>
                <input 
                  type="number" 
                  value={mcSimulations} 
                  onChange={(e) => setMcSimulations(e.target.value)}
                  style={styles.input}
                />
              </div>
              <div style={styles.formGroup}>
                <label style={styles.label}>Noise Level</label>
                <input 
                  type="number" 
                  step="0.1"
                  value={mcNoise} 
                  onChange={(e) => setMcNoise(e.target.value)}
                  style={styles.input}
                />
              </div>
            </>
          )}

          <button 
            style={styles.button(isRunning)} 
            disabled={isRunning}
            onClick={handleRun}
          >
            {isRunning ? 'Analyzing...' : 'Run Analysis'}
          </button>

          {isRunning && (
            <div style={styles.progressBar}>
              <div style={styles.progressFill(progress)} />
            </div>
          )}
        </aside>

        {/* Main Content Area */}
        <main style={styles.main}>
          {!results && !isRunning && (
            <div style={{ textAlign: 'center', color: '#64748b', padding: '40px 0' }}>
              Configure parameters and click "Run Analysis" to view results.
            </div>
          )}

          {results && activeTab === 'walkforward' && (
            <div>
              <h3 style={{ marginTop: 0, color: '#0f172a' }}>Walk-Forward Efficiency</h3>
              <p style={{ color: '#64748b', fontSize: '14px' }}>
                Evaluating strategy robustness across out-of-sample data segments.
              </p>
              
              <table style={styles.table}>
                <thead>
                  <tr>
                    <th style={styles.th}>Window</th>
                    <th style={styles.th}>In-Sample Return</th>
                    <th style={styles.th}>Out-of-Sample Return</th>
                    <th style={styles.th}>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {results.wf.map((row, i) => (
                    <tr key={i}>
                      <td style={styles.td}># {row.window}</td>
                      <td style={styles.td}>{row.isReturn}%</td>
                      <td style={styles.td}>{row.oosReturn}%</td>
                      <td style={styles.td}>
                        <span style={styles.badge(row.pass)}>
                          {row.pass ? 'PASS' : 'FAIL'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {results && activeTab === 'montecarlo' && (
            <div>
              <h3 style={{ marginTop: 0, color: '#0f172a' }}>Monte Carlo Simulation Stats</h3>
              <p style={{ color: '#64748b', fontSize: '14px' }}>
                Statistical distribution of strategy performance over {mcSimulations} iterations.
              </p>

              <div style={styles.statsGrid}>
                <div style={styles.statCard}>
                  <div style={styles.label}>Median Return</div>
                  <div style={styles.statValue(results.mc.median)}>{results.mc.median}%</div>
                </div>
                <div style={styles.statCard}>
                  <div style={styles.label}>Worst Case (99% CI)</div>
                  <div style={styles.statValue(results.mc.worstCase)}>{results.mc.worstCase}%</div>
                </div>
                <div style={styles.statCard}>
                  <div style={styles.label}>Best Case (99% CI)</div>
                  <div style={styles.statValue(results.mc.bestCase)}>{results.mc.bestCase}%</div>
                </div>
                <div style={styles.statCard}>
                  <div style={styles.label}>Probability of Ruin</div>
                  <div style={{ ...styles.statValue(results.mc.probabilityOfRuin * -1), color: '#ef4444' }}>
                    {results.mc.probabilityOfRuin}%
                  </div>
                </div>
              </div>

              {/* Placeholder for a chart */}
              <div style={{ marginTop: '32px', padding: '40px', backgroundColor: '#f1f5f9', borderRadius: '8px', textAlign: 'center', border: '1px dashed #cbd5e1' }}>
                <span style={{ color: '#94a3b8' }}>[ Distribution Chart Visualization Rendered Here ]</span>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
};

export default WalkForwardUI;
