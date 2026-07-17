import React, { useState } from 'react';

const StressTest = () => {
  const [portfolio, setPortfolio] = useState({
    equities: 60,
    bonds: 20,
    crypto: 10,
    realEstate: 10,
  });

  const [activeScenario, setActiveScenario] = useState(null);
  const [isSimulating, setIsSimulating] = useState(false);
  const [results, setResults] = useState(null);

  const scenarios = [
    { id: '2008', name: '2008 Financial Crisis', description: 'Severe global economic downturn', impacts: { equities: -45, bonds: 5, crypto: -80, realEstate: -30 } },
    { id: 'covid', name: 'COVID-19 Crash (2020)', description: 'Rapid market sell-off due to pandemic', impacts: { equities: -30, bonds: 2, crypto: -50, realEstate: -10 } },
    { id: 'tech', name: 'Tech Bubble Burst', description: 'Collapse of high-growth tech valuations', impacts: { equities: -25, bonds: 8, crypto: -60, realEstate: -5 } },
    { id: 'rates', name: 'Aggressive Rate Hikes', description: 'Central banks rapidly increase interest rates', impacts: { equities: -15, bonds: -10, crypto: -35, realEstate: -15 } }
  ];

  const handleAllocationChange = (asset, value) => {
    setPortfolio({ ...portfolio, [asset]: Number(value) });
  };

  const runSimulation = (scenario) => {
    setActiveScenario(scenario.id);
    setIsSimulating(true);
    setResults(null);
    
    setTimeout(() => {
      let totalImpact = 0;
      const breakdown = {};
      
      Object.keys(portfolio).forEach(asset => {
        const weight = portfolio[asset] / 100;
        const impact = scenario.impacts[asset] || 0;
        const weightedImpact = weight * impact;
        totalImpact += weightedImpact;
        breakdown[asset] = weightedImpact;
      });
      
      setResults({
        totalImpact: totalImpact.toFixed(2),
        breakdown,
        scenarioName: scenario.name
      });
      setIsSimulating(false);
    }, 1500);
  };

  const totalAllocation = Object.values(portfolio).reduce((a, b) => a + b, 0);

  return (
    <div className="stress-test-container">
      <style>{`
        .stress-test-container {
          font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
          background: linear-gradient(145deg, #0f172a, #1e293b);
          color: #f8fafc;
          padding: 2rem;
          border-radius: 16px;
          box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
          max-width: 900px;
          margin: 0 auto;
        }
        .header {
          text-align: center;
          margin-bottom: 2.5rem;
        }
        .header h2 {
          font-size: 2.25rem;
          font-weight: 800;
          background: -webkit-linear-gradient(45deg, #60a5fa, #a78bfa);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          margin: 0 0 0.5rem 0;
        }
        .header p {
          color: #94a3b8;
          margin: 0;
          font-size: 1.1rem;
        }
        .grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 2rem;
        }
        @media (max-width: 768px) {
          .grid {
            grid-template-columns: 1fr;
          }
        }
        .panel {
          background: rgba(255, 255, 255, 0.03);
          border: 1px solid rgba(255, 255, 255, 0.05);
          border-radius: 16px;
          padding: 1.75rem;
          backdrop-filter: blur(12px);
          box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }
        .panel h3 {
          margin-top: 0;
          font-size: 1.25rem;
          color: #e2e8f0;
          border-bottom: 1px solid rgba(255,255,255,0.1);
          padding-bottom: 0.75rem;
          margin-bottom: 1.5rem;
        }
        .allocation-group {
          margin-bottom: 1.25rem;
        }
        .allocation-group label {
          display: flex;
          justify-content: space-between;
          margin-bottom: 0.5rem;
          color: #cbd5e1;
          font-weight: 500;
          font-size: 0.95rem;
        }
        .allocation-slider {
          width: 100%;
          appearance: none;
          height: 6px;
          border-radius: 3px;
          background: #334155;
          outline: none;
        }
        .allocation-slider::-webkit-slider-thumb {
          appearance: none;
          width: 18px;
          height: 18px;
          border-radius: 50%;
          background: #60a5fa;
          cursor: pointer;
          transition: transform 0.15s ease, background 0.15s ease;
          box-shadow: 0 0 10px rgba(96, 165, 250, 0.5);
        }
        .allocation-slider::-webkit-slider-thumb:hover {
          transform: scale(1.2);
          background: #93c5fd;
        }
        .total-allocation {
          text-align: right;
          font-size: 0.9rem;
          font-weight: 600;
          margin-top: 1.5rem;
          color: ${totalAllocation === 100 ? '#4ade80' : '#f87171'};
        }
        .scenarios-list {
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }
        .scenario-card {
          background: rgba(15, 23, 42, 0.4);
          border: 1px solid rgba(255,255,255,0.05);
          padding: 1.25rem;
          border-radius: 12px;
          cursor: pointer;
          transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
          display: flex;
          justify-content: space-between;
          align-items: center;
        }
        .scenario-card:hover {
          background: rgba(30, 41, 59, 0.8);
          border-color: rgba(96, 165, 250, 0.5);
          transform: translateY(-2px);
          box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.2);
        }
        .scenario-card.active {
          border-color: #a78bfa;
          background: rgba(139, 92, 246, 0.15);
        }
        .scenario-info h4 {
          margin: 0 0 0.35rem 0;
          color: #f8fafc;
          font-size: 1.05rem;
        }
        .scenario-info p {
          margin: 0;
          font-size: 0.85rem;
          color: #94a3b8;
          line-height: 1.4;
        }
        .simulate-btn {
          background: linear-gradient(135deg, #3b82f6, #8b5cf6);
          border: none;
          color: white;
          padding: 0.6rem 1.2rem;
          border-radius: 8px;
          font-weight: 600;
          font-size: 0.9rem;
          cursor: pointer;
          transition: all 0.2s;
          box-shadow: 0 4px 6px -1px rgba(96, 165, 250, 0.4);
        }
        .simulate-btn:hover:not(:disabled) {
          opacity: 0.9;
          transform: translateY(-1px);
          box-shadow: 0 6px 8px -1px rgba(96, 165, 250, 0.5);
        }
        .simulate-btn:disabled {
          background: #334155;
          color: #94a3b8;
          box-shadow: none;
          cursor: not-allowed;
        }
        .results-panel {
          margin-top: 2rem;
          padding: 2.5rem;
          background: rgba(0,0,0,0.25);
          border: 1px solid rgba(255,255,255,0.05);
          border-radius: 16px;
          text-align: center;
          animation: slideUp 0.5s cubic-bezier(0.16, 1, 0.3, 1);
        }
        .impact-value {
          font-size: 4.5rem;
          font-weight: 800;
          margin: 1.5rem 0;
          line-height: 1;
          text-shadow: 0 10px 30px rgba(0,0,0,0.5);
        }
        .impact-negative {
          color: #f87171;
        }
        .impact-positive {
          color: #4ade80;
        }
        .loader {
          display: inline-block;
          width: 48px;
          height: 48px;
          border: 4px solid rgba(255,255,255,0.1);
          border-radius: 50%;
          border-top-color: #a78bfa;
          animation: spin 1s cubic-bezier(0.55, 0.055, 0.675, 0.19) infinite;
          margin: 3rem auto 1rem auto;
        }
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
        @keyframes slideUp {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .breakdown-grid {
          display: flex;
          justify-content: center;
          gap: 2.5rem;
          margin-top: 1.5rem;
          flex-wrap: wrap;
          background: rgba(255,255,255,0.02);
          padding: 1.5rem;
          border-radius: 12px;
        }
      `}</style>

      <div className="header">
        <h2>Portfolio Stress Test</h2>
        <p>Simulate extreme market scenarios to evaluate your portfolio's resilience</p>
      </div>

      <div className="grid">
        <div className="panel">
          <h3>Asset Allocation (%)</h3>
          {Object.keys(portfolio).map(asset => (
            <div className="allocation-group" key={asset}>
              <label>
                <span style={{ textTransform: 'capitalize' }}>{asset.replace(/([A-Z])/g, ' $1').trim()}</span>
                <span>{portfolio[asset]}%</span>
              </label>
              <input 
                type="range" 
                className="allocation-slider"
                min="0" 
                max="100" 
                value={portfolio[asset]}
                onChange={(e) => handleAllocationChange(asset, e.target.value)}
              />
            </div>
          ))}
          <div className="total-allocation">
            Total: {totalAllocation}% {totalAllocation !== 100 && <span style={{display: 'block', fontSize: '0.8rem', marginTop: '0.25rem', opacity: 0.8}}>(Adjust to equal 100%)</span>}
          </div>
        </div>

        <div className="panel">
          <h3>Macro Scenarios</h3>
          <div className="scenarios-list">
            {scenarios.map(scenario => (
              <div 
                key={scenario.id} 
                className={`scenario-card ${activeScenario === scenario.id ? 'active' : ''}`}
                onClick={() => totalAllocation === 100 && runSimulation(scenario)}
              >
                <div className="scenario-info">
                  <h4>{scenario.name}</h4>
                  <p>{scenario.description}</p>
                </div>
                <button 
                  className="simulate-btn"
                  disabled={totalAllocation !== 100 || isSimulating}
                  onClick={(e) => { e.stopPropagation(); runSimulation(scenario); }}
                >
                  Simulate
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>

      {isSimulating && (
        <div style={{ textAlign: 'center' }}>
          <div className="loader"></div>
          <p style={{ color: '#94a3b8', fontSize: '1.1rem', fontWeight: 500 }}>Running Monte Carlo simulations...</p>
        </div>
      )}

      {results && !isSimulating && (
        <div className="results-panel">
          <h3 style={{ margin: '0 0 0.5rem 0', color: '#94a3b8', fontSize: '1.2rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Estimated Portfolio Impact</h3>
          <p style={{ margin: 0, color: '#e2e8f0', fontSize: '1.1rem' }}>Scenario: <strong>{results.scenarioName}</strong></p>
          
          <div className={`impact-value ${Number(results.totalImpact) < 0 ? 'impact-negative' : 'impact-positive'}`}>
            {Number(results.totalImpact) > 0 ? '+' : ''}{results.totalImpact}%
          </div>
          
          <div className="breakdown-grid">
             {Object.keys(results.breakdown).map(asset => (
                <div key={asset} style={{ textAlign: 'center' }}>
                  <div style={{ color: '#94a3b8', fontSize: '0.9rem', textTransform: 'capitalize', marginBottom: '0.4rem', fontWeight: 500 }}>
                    {asset.replace(/([A-Z])/g, ' $1').trim()}
                  </div>
                  <div style={{ color: results.breakdown[asset] < 0 ? '#f87171' : '#4ade80', fontWeight: '700', fontSize: '1.2rem' }}>
                    {results.breakdown[asset] > 0 ? '+' : ''}{results.breakdown[asset].toFixed(1)}%
                  </div>
                </div>
             ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default StressTest;
