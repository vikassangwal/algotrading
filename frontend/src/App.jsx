import { useState, useEffect } from 'react';
import { LayoutDashboard, Activity, Settings, TrendingUp, AlertTriangle, Play, Square, Pause, BookOpen, BarChart2, ListFilter, Layers, PieChart, ShoppingCart, Grid, BellRing, BrainCircuit, Bot, Video, ShieldAlert, Key, Users, CheckCircle, Route, Crosshair, ChevronDown, ChevronRight, Zap, Plug } from 'lucide-react';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar } from 'recharts';
import './index.css'; // Uses our custom Vanilla CSS theme

import AdvancedChartEngine from './components/AdvancedChartEngine';
import ScannerView from './components/ScannerView';
import OptionChain from './components/OptionChain';
import ReportsView from './components/ReportsView';
import OMSView from './components/OMSView';
import CommandCenter from './components/CommandCenter';
import BrokerPanel from './components/BrokerPanel';
import PortfolioHeatmap from './components/PortfolioHeatmap';
import SmartAlerts from './components/SmartAlerts';
import TradeDiary from './components/TradeDiary';
import TradeJournal from './components/TradeJournal';
import NewsRiskRadar from './components/NewsRiskRadar';
import AIAssistant from './components/AIAssistant';
import ExecutionReplay from './components/ExecutionReplay';
import StrategyLab from './components/StrategyLab';
import StressTest from './components/StressTest';
import SSOSettings from './components/SSOSettings';
import TenantDashboard from './components/TenantDashboard';
import WorkflowApprovals from './components/WorkflowApprovals';
import AuthViews from './components/AuthViews';
import SystemDashboard from './components/SystemDashboard';
import StrategyBuilderLayout from './components/StrategyBuilder/StrategyBuilderLayout';
import WalkForwardUI from './components/WalkForwardUI';
import AdvancedScannerUI from './components/AdvancedScannerUI';
import UltimateDashboard from './components/UltimateDashboard';
import TradingPathways from './components/TradingPathways';
import UniversalScreener from './components/UniversalScreener';
import StockProfile from './components/StockProfile';
import GlobalSearch from './components/GlobalSearch';

const API_URL = (import.meta.env.VITE_API_URL || 'https://elco-backend.onrender.com').replace(/\/$/, '');

// Tabs whose UI shipped without any backend — pure demo screens. We label them
// honestly instead of letting sample data pass for real engine output.
const DEMO_TABS = [];

export default function App() {
  const getSafeToken = () => {
    try {
      return localStorage.getItem('elco_token') || 'guest_mode_active';
    } catch (e) {
      return 'guest_mode_active';
    }
  };

  const setSafeToken = (t) => {
    try {
      if (t) localStorage.setItem('elco_token', t);
      else localStorage.removeItem('elco_token');
    } catch (e) {}
  };

  const [activeTab, setActiveTab] = useState('dashboard');
  const [globalSymbol, setGlobalSymbol] = useState('RELIANCE.NS');
  const [config, setConfig] = useState(null);
  const [token, setToken] = useState(getSafeToken);
  const [loginError, setLoginError] = useState('');
  const [expandedCategories, setExpandedCategories] = useState({
    trading: true,
    analysis: true,
    strategy: false,
    risk: false,
    admin: false
  });
  
  const toggleCategory = (cat) => {
    setExpandedCategories(prev => ({ ...prev, [cat]: !prev[cat] }));
  };
  
  const headers = token ? { 'Authorization': `Bearer ${token}` } : {};
  
  const [tickers, setTickers] = useState([
    { symbol: 'NIFTY 50', val: '---', change: '0.0%', up: true },
    { symbol: 'BANKNIFTY', val: '---', change: '0.0%', up: true }
  ]);

  useEffect(() => {
    const ensureToken = async () => {
      const savedToken = getSafeToken();
      if (!savedToken || savedToken === 'guest_mode_active' || savedToken.length < 20) {
        try {
          const res = await fetch(`${API_URL}/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ password: 'admin' })
          });
          if (res.ok) {
            const data = await res.json();
            if (data.token) {
              setSafeToken(data.token);
              setToken(data.token);
            }
          }
        } catch (e) {
          console.error("Auto-login error:", e);
        }
      }
    };
    ensureToken();
  }, []);

  useEffect(() => {
    fetchConfig();
    fetchTickers();
    const interval = setInterval(fetchTickers, 60000);
    return () => clearInterval(interval);
  }, [token]);

  const fetchTickers = async () => {
    try {
      const res = await fetch(`${API_URL}/api/market-indices`, { headers });
      if (res.ok) {
        const data = await res.json();
        if (data.length > 0) setTickers(data);
      }
    } catch (err) {
      console.error("Failed to fetch tickers:", err);
    }
  };

  const fetchConfig = async () => {
    try {
      const res = await fetch(`${API_URL}/config`, { headers });
      if (!res.ok) return;
      const data = await res.json();
      setConfig(data);
    } catch (err) {
      console.error("Failed to fetch config:", err);
    }
  };

  const updateConfig = async (updates) => {
    try {
      const res = await fetch(`${API_URL}/config`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', ...headers },
        body: JSON.stringify(updates)
      });
      if (res.ok) {
        const data = await res.json();
        setConfig(data.config);
      } else {
        console.error("Backend error when updating config", await res.text());
        // Fallback to local state update if backend fails
        setConfig(prev => ({ ...prev, ...updates }));
      }
    } catch (err) {
      console.error("Failed to update config:", err);
      // Fallback
      setConfig(prev => ({ ...prev, ...updates }));
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('elco_token');
    setToken(null);
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    const password = e.target.password.value;
    try {
      const res = await fetch(`${API_URL}/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password })
      });
      if (res.ok) {
        const data = await res.json();
        localStorage.setItem('elco_token', data.token);
        setToken(data.token);
        setLoginError('');
      } else {
        setLoginError('Invalid password');
      }
    } catch (err) {
      setLoginError('Server error');
    }
  };

  if (!token) {
    return <AuthViews setToken={setToken} />;
  }

  return (
    <>
      {/* Ticker Strip */}
      <div className="ticker-strip">
        <div style={{display: 'flex', animation: 'marquee 30s linear infinite'}}>
          {tickers.map(t => (
            <div key={t.symbol} className="ticker-item">
              <span>{t.symbol}</span>
              <span className="ticker-val">{t.val}</span>
              <span className={`ticker-change ${t.up ? 'up' : 'down'}`}>{t.change}</span>
            </div>
          ))}
          {/* Duplicate for seamless marquee effect */}
          {tickers.map(t => (
            <div key={t.symbol + '-dup'} className="ticker-item">
              <span>{t.symbol}</span>
              <span className="ticker-val">{t.val}</span>
              <span className={`ticker-change ${t.up ? 'up' : 'down'}`}>{t.change}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="app-container">
        {/* Sidebar */}
        <div className="sidebar">
          <div className="brand">
            ELCO <span>TRADER</span>
          </div>
          <div className="nav-links" style={{ overflowY: 'auto', flex: 1 }}>
            
            <div className="sidebar-category" onClick={() => toggleCategory('trading')}>
              <span>Trading & Core</span>
              {expandedCategories.trading ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
            </div>
            {expandedCategories.trading && (
              <div className="category-items">
                <div className={`nav-item ${activeTab === 'command-center' ? 'active' : ''}`} onClick={() => setActiveTab('command-center')}><Zap size={20} /> Command Center</div>
                <div className={`nav-item ${activeTab === 'ultimate-dashboard' ? 'active' : ''}`} onClick={() => setActiveTab('ultimate-dashboard')}><LayoutDashboard size={20} /> Ultimate Command Center</div>
                <div className={`nav-item ${activeTab === 'dashboard' ? 'active' : ''}`} onClick={() => setActiveTab('dashboard')}><LayoutDashboard size={20} /> Regular Dashboard</div>
                <div className={`nav-item ${activeTab === 'oms' ? 'active' : ''}`} onClick={() => setActiveTab('oms')}><ShoppingCart size={20} /> Order Management</div>
                <div className={`nav-item ${activeTab === 'charts' ? 'active' : ''}`} onClick={() => setActiveTab('charts')}><BarChart2 size={20} /> Pro Charts</div>
              </div>
            )}

            <div className="sidebar-category" onClick={() => toggleCategory('analysis')}>
              <span>Analysis & Scanners</span>
              {expandedCategories.analysis ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
            </div>
            {(expandedCategories.analysis ?? true) && (
              <div className="category-items">
                <div className={`nav-item ${activeTab === 'scalping' ? 'active' : ''}`} onClick={() => setActiveTab('scalping')} style={{ color: '#ef4444', fontWeight: 'bold' }}><Zap size={20} /> ⚡ 1-Min Scalping Radar</div>
                <div className={`nav-item ${activeTab === 'universal' ? 'active' : ''}`} onClick={() => setActiveTab('universal')}><Crosshair size={20} /> Universal Screener (4800+ Stocks)</div>
                <div className={`nav-item ${activeTab === 'scanner' ? 'active' : ''}`} onClick={() => setActiveTab('scanner')}><ListFilter size={20} /> Technical Scanners</div>
                <div className={`nav-item ${activeTab === 'market-scanner' ? 'active' : ''}`} onClick={() => setActiveTab('market-scanner')}><ListFilter size={20} /> AI Technical Scanners</div>
                <div className={`nav-item ${activeTab === 'options' ? 'active' : ''}`} onClick={() => setActiveTab('options')}><Layers size={20} /> Option Chain</div>
                <div className={`nav-item ${activeTab === 'profile' ? 'active' : ''}`} onClick={() => setActiveTab('profile')}><BookOpen size={20} /> Stock Biodata</div>
                <div className={`nav-item ${activeTab === 'heatmap' ? 'active' : ''}`} onClick={() => setActiveTab('heatmap')}><Grid size={20} /> Portfolio Heatmap</div>
                <div className={`nav-item ${activeTab === 'radar' ? 'active' : ''}`} onClick={() => setActiveTab('radar')}><ShieldAlert size={20} /> Crash-Risk Radar</div>
              </div>
            )}

            <div className="sidebar-category" onClick={() => toggleCategory('strategy')}>
              <span>Strategy & Backtest</span>
              {expandedCategories.strategy ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
            </div>
            {expandedCategories.strategy && (
              <div className="category-items">
                <div className={`nav-item ${activeTab === 'strategy-lab' ? 'active' : ''}`} onClick={() => setActiveTab('strategy-lab')}><BrainCircuit size={20} /> Strategy Lab</div>
                <div className={`nav-item ${activeTab === 'strategy-canvas' ? 'active' : ''}`} onClick={() => setActiveTab('strategy-canvas')}><Grid size={20} /> Strategy Canvas</div>
                <div className={`nav-item ${activeTab === 'walk-forward' ? 'active' : ''}`} onClick={() => setActiveTab('walk-forward')}><Layers size={20} /> Walk Forward UI</div>
                <div className={`nav-item ${activeTab === 'stress-test' ? 'active' : ''}`} onClick={() => setActiveTab('stress-test')}><AlertTriangle size={20} /> Stress Test</div>
                <div className={`nav-item ${activeTab === 'execution-replay' ? 'active' : ''}`} onClick={() => setActiveTab('execution-replay')}><Play size={20} /> Execution Replay</div>
              </div>
            )}

            <div className="sidebar-category" onClick={() => toggleCategory('risk')}>
              <span>Risk & Intelligence</span>
              {expandedCategories.risk ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
            </div>
            {expandedCategories.risk && (
              <div className="category-items">
                <div className={`nav-item ${activeTab === 'journal' ? 'active' : ''}`} onClick={() => setActiveTab('journal')}><BookOpen size={20} /> Trade Journal</div>
                <div className={`nav-item ${activeTab === 'diary' ? 'active' : ''}`} onClick={() => setActiveTab('diary')}><BrainCircuit size={20} /> Trading Psychology</div>
                <div className={`nav-item ${activeTab === 'pathways' ? 'active' : ''}`} onClick={() => setActiveTab('pathways')}><Route size={20} /> Syllabus Matrix</div>
                <div className={`nav-item ${activeTab === 'ai' ? 'active' : ''}`} onClick={() => setActiveTab('ai')}><Bot size={20} /> AI Assistant</div>
                <div className={`nav-item ${activeTab === 'reports' ? 'active' : ''}`} onClick={() => setActiveTab('reports')}><PieChart size={20} /> Analytics & Reports</div>
              </div>
            )}

            <div className="sidebar-category" onClick={() => toggleCategory('admin')}>
              <span>System & Admin</span>
              {expandedCategories.admin ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
            </div>
            {(expandedCategories.admin ?? true) && (
              <div className="category-items">
                <div className={`nav-item ${activeTab === 'broker' ? 'active' : ''}`} onClick={() => setActiveTab('broker')}><Plug size={20} /> Broker API Keys</div>
                <div className={`nav-item ${activeTab === 'system-dashboard' ? 'active' : ''}`} onClick={() => setActiveTab('system-dashboard')}><Activity size={20} /> System Dashboard</div>
                <div className={`nav-item ${activeTab === 'config' ? 'active' : ''}`} onClick={() => setActiveTab('config')}><Settings size={20} /> App Config</div>
                <div className={`nav-item ${activeTab === 'sso' ? 'active' : ''}`} onClick={() => setActiveTab('sso')}><Key size={20} /> Security (SSO/MFA)</div>
                <div className={`nav-item ${activeTab === 'tenant' ? 'active' : ''}`} onClick={() => setActiveTab('tenant')}><Users size={20} /> Tenant Admin</div>
                <div className={`nav-item ${activeTab === 'workflow' ? 'active' : ''}`} onClick={() => setActiveTab('workflow')}><CheckCircle size={20} /> Workflow Approvals</div>
                <div className={`nav-item ${activeTab === 'alerts' ? 'active' : ''}`} onClick={() => setActiveTab('alerts')}><BellRing size={20} /> Smart Alerts</div>
              </div>
            )}

          </div>
          
          <div style={{padding: '1.5rem', borderTop: '1px solid var(--border-color)', fontSize: '0.8rem', color: 'var(--text-secondary)'}}>
            System Status: 
            <span style={{color: config?.auto_trade === 'active' ? 'var(--signal-buy)' : 
                          config?.auto_trade === 'halted' ? 'var(--signal-sell)' : 'var(--text-secondary)', marginLeft: '8px', fontWeight: 'bold', textTransform: 'uppercase'}}>
              {config?.auto_trade || 'OFF'}
            </span>
          </div>
          
          <div style={{padding: '0 1.5rem 1.5rem'}}>
            <button className="btn" onClick={handleLogout} style={{width: '100%', padding: '0.5rem', backgroundColor: '#374151'}}>Logout</button>
          </div>
        </div>

        {/* Main Content */}
        <div className="main-content">
          <div className="header" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '1rem', flexWrap: 'nowrap' }}>
            <div className="header-title" style={{ whiteSpace: 'nowrap', minWidth: 'fit-content' }}>
              {activeTab === 'dashboard' && 'Market Overview'}
              {activeTab === 'profile' && 'Stock Biodata'}
              {activeTab === 'command-center' && 'AI Command Center'}
              {activeTab === 'ultimate-dashboard' && 'Ultimate Command Center'}
              {activeTab === 'oms' && 'Order Management System'}
              {activeTab === 'charts' && 'Pro Candlestick Charts'}
              {activeTab === 'scanner' && 'Real-time Scanners'}
              {activeTab === 'options' && 'Advanced Option Chain'}
              {activeTab === 'reports' && 'End of Day Reports'}
              {activeTab === 'scalping' && '⚡ 1-Min High-Momentum Scalping Radar'}
              {activeTab === 'universal' && 'Global Universal Market Radar'}
              {activeTab === 'heatmap' && 'Portfolio Intelligence'}
              {activeTab === 'alerts' && 'Smart Alerts Center'}
              {activeTab === 'radar' && 'Crash-Risk Radar'}
              {activeTab === 'journal' && 'Execution Trade Journal'}
              {activeTab === 'pathways' && 'Syllabus Matrix'}
              {activeTab === 'diary' && 'Trading Psychology & Discipline'}
              {activeTab === 'ai' && 'AI Market Intelligence'}
              {activeTab === 'market-scanner' && 'Advanced Market Scanners'}
              {activeTab === 'system-dashboard' && 'System Analytics'}
              {activeTab === 'strategy-canvas' && 'Strategy Canvas'}
              {activeTab === 'walk-forward' && 'Walk Forward Analysis'}
              {activeTab === 'strategy-lab' && 'Quantitative Strategy Lab'}
              {activeTab === 'execution-replay' && 'Historical Execution Replay'}
              {activeTab === 'stress-test' && 'Portfolio Stress Scenarios'}
              {activeTab === 'workflow' && '4-Eyes Operational Approvals'}
              {activeTab === 'sso' && 'Enterprise Security Settings'}
              {activeTab === 'tenant' && 'SaaS Tenant Management'}
              {activeTab === 'config' && 'System Configuration'}
            </div>
            <div style={{ flex: 1, display: 'flex', justifyContent: 'center' }}>
              <GlobalSearch token={token} onSelect={(sym) => {
                const cleanSym = sym.includes('.NS') || sym.includes('.BO') || sym.includes('=') ? sym : `${sym}.NS`;
                setGlobalSymbol(cleanSym);
                setActiveTab('ultimate-dashboard');
              }} />
            </div>
            <div style={{ whiteSpace: 'nowrap' }}>
              <span style={{marginRight: '0.5rem', fontSize: '0.85rem', color: 'var(--text-secondary)'}}>Capital:</span>
              <span style={{fontWeight: 600}}>₹ {config?.capital != null ? config.capital.toLocaleString() : '---'}</span>
            </div>
          </div>
          
          <div className="content-body">
            {DEMO_TABS.includes(activeTab) && (
              <div style={{ background: '#7c2d12', border: '1px solid #f97316', color: '#ffedd5',
                padding: '10px 16px', borderRadius: 8, marginBottom: 14, fontSize: 14 }}>
                ⚠️ <b>DEMO SCREEN</b> — ye tab abhi trading engine se juda <b>nahi</b> hai.
                Isme dikhne wala data sample hai, asli nahi. (Asli tabs: Command Center,
                Pro Charts, Market Scanner, Option Chain, Order Mgmt, Portfolio, Journal, Config.)
              </div>
            )}
            {activeTab === 'command-center' && (
              <CommandCenter globalSymbol={globalSymbol} />
            )}
            {activeTab === 'ultimate-dashboard' && (
              <UltimateDashboard token={token} globalSymbol={globalSymbol} />
            )}
            {activeTab === 'dashboard' && (
              <DashboardView config={config} token={token} />
            )}
            {activeTab === 'oms' && (
              <OMSView token={token} globalSymbol={globalSymbol} />
            )}
            {activeTab === 'charts' && (
              <AdvancedChartEngine token={token} globalSymbol={globalSymbol} />
            )}
            {activeTab === 'scanner' && (
              <ScannerView token={token} globalSymbol={globalSymbol} />
            )}
            {activeTab === 'scalping' && (
              <UniversalScreener token={token} globalSymbol={globalSymbol} initialFilter="⚡ SCALPING (1-5 MIN)" onSelectSymbol={(sym, targetTab) => {
                const cleanSym = sym.includes('.NS') || sym.includes('.BO') || sym.includes('=') ? sym : `${sym}.NS`;
                setGlobalSymbol(cleanSym);
                setActiveTab(targetTab || 'ultimate-dashboard');
              }} />
            )}
            {activeTab === 'universal' && (
              <UniversalScreener token={token} globalSymbol={globalSymbol} onSelectSymbol={(sym, targetTab) => {
                const cleanSym = sym.includes('.NS') || sym.includes('.BO') || sym.includes('=') ? sym : `${sym}.NS`;
                setGlobalSymbol(cleanSym);
                setActiveTab(targetTab || 'ultimate-dashboard');
              }} />
            )}
            {activeTab === 'profile' && (
              <StockProfile token={token} globalSymbol={globalSymbol} />
            )}
            {activeTab === 'options' && (
              <OptionChain token={token} globalSymbol={globalSymbol} />
            )}
            {activeTab === 'reports' && (
              <ReportsView token={token} globalSymbol={globalSymbol} />
            )}
            {activeTab === 'heatmap' && (
              <PortfolioHeatmap token={token} globalSymbol={globalSymbol} />
            )}
            {activeTab === 'alerts' && (
              <SmartAlerts token={token} globalSymbol={globalSymbol} />
            )}
            {activeTab === 'radar' && (
              <NewsRiskRadar token={token} globalSymbol={globalSymbol} />
            )}
            {activeTab === 'journal' && (
              <TradeJournal token={token} />
            )}
            {activeTab === 'diary' && (
              <TradeDiary token={token} />
            )}
            {activeTab === 'pathways' && (
              <TradingPathways token={token} />
            )}
            {activeTab === 'ai' && (
              <AIAssistant token={token} globalSymbol={globalSymbol} />
            )}
            {activeTab === 'strategy-lab' && (
              <StrategyLab token={token} globalSymbol={globalSymbol} />
            )}
            {activeTab === 'execution-replay' && (
              <ExecutionReplay token={token} globalSymbol={globalSymbol} />
            )}
            {activeTab === 'stress-test' && (
              <StressTest token={token} globalSymbol={globalSymbol} />
            )}
            {activeTab === 'workflow' && (
              <WorkflowApprovals token={token} />
            )}
            {activeTab === 'sso' && (
              <SSOSettings token={token} />
            )}
            {activeTab === 'broker' && (
              <BrokerPanel />
            )}
            {activeTab === 'tenant' && (
              <TenantDashboard token={token} />
            )}
            {activeTab === 'config' && (
              config ? (
                <AdminPanel config={config} updateConfig={updateConfig} />
              ) : (
                <div style={{padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)'}}>
                  <h3>Failed to load configuration from backend</h3>
                  <button onClick={fetchConfig} className="btn" style={{marginTop: '1rem', backgroundColor: 'var(--signal-buy)'}}>Retry Connection</button>
                </div>
              )
            )}
            {activeTab === 'market-scanner' && (
              <AdvancedScannerUI token={token} globalSymbol={globalSymbol} />
            )}
            {activeTab === 'system-dashboard' && (
              <SystemDashboard token={token} />
            )}
            {activeTab === 'strategy-canvas' && (
              <StrategyBuilderLayout token={token} globalSymbol={globalSymbol} />
            )}
            {activeTab === 'walk-forward' && (
              <WalkForwardUI token={token} globalSymbol={globalSymbol} />
            )}
          </div>
        </div>
      </div>
      
      <style dangerouslySetInnerHTML={{__html: `
        @keyframes marquee { 0% { transform: translateX(0); } 100% { transform: translateX(-50%); } }
      `}} />
    </>
  );
}

function StrategyBuilder({ config, updateConfig }) {
  const [newRule, setNewRule] = useState({
    name: '', indicator: 'LTP', operator: '>', value: 0, action: 'BUY'
  });

  const handleAddRule = () => {
    if (!newRule.name) return alert("Please enter a rule name");
    const updatedStrategies = [...(config.custom_strategies || []), { ...newRule, id: Date.now().toString() }];
    updateConfig({ custom_strategies: updatedStrategies });
    setNewRule({ name: '', indicator: 'LTP', operator: '>', value: 0, action: 'BUY' });
  };

  const handleRemoveRule = (id) => {
    const updatedStrategies = (config.custom_strategies || []).filter(s => s.id !== id);
    updateConfig({ custom_strategies: updatedStrategies });
  };

  return (
    <div className="dashboard-grid">
      <div className="panel" style={{gridColumn: '1 / -1'}}>
        <div className="panel-header">Create Custom Strategy Rule</div>
        <div style={{display: 'flex', gap: '1rem', alignItems: 'flex-end', flexWrap: 'wrap', marginBottom: '1rem'}}>
          <div style={{flex: 1, minWidth: '200px'}}>
            <label style={{display: 'block', fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.5rem'}}>Rule Name</label>
            <input type="text" value={newRule.name} onChange={e => setNewRule({...newRule, name: e.target.value})} 
                   style={{width: '100%', padding: '0.75rem', backgroundColor: '#1F2937', color: 'white', border: '1px solid var(--border-color)', borderRadius: '4px'}} placeholder="e.g. Trend Breakout" />
          </div>
          <div style={{flex: 1}}>
            <label style={{display: 'block', fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.5rem'}}>Indicator</label>
            <select value={newRule.indicator} onChange={e => setNewRule({...newRule, indicator: e.target.value})}
                    style={{width: '100%', padding: '0.75rem', backgroundColor: '#1F2937', color: 'white', border: '1px solid var(--border-color)', borderRadius: '4px'}}>
              <option value="LTP">LTP (Price)</option>
              <option value="RSI">RSI</option>
              <option value="MACD">MACD</option>
              <option value="VOLUME">Volume</option>
            </select>
          </div>
          <div style={{flex: 1}}>
            <label style={{display: 'block', fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.5rem'}}>Operator</label>
            <select value={newRule.operator} onChange={e => setNewRule({...newRule, operator: e.target.value})}
                    style={{width: '100%', padding: '0.75rem', backgroundColor: '#1F2937', color: 'white', border: '1px solid var(--border-color)', borderRadius: '4px'}}>
              <option value=">">Greater Than (&gt;)</option>
              <option value="<">Less Than (&lt;)</option>
              <option value="==">Equals (==)</option>
            </select>
          </div>
          <div style={{flex: 1}}>
            <label style={{display: 'block', fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.5rem'}}>Value</label>
            <input type="number" value={newRule.value} onChange={e => setNewRule({...newRule, value: parseFloat(e.target.value)})} 
                   style={{width: '100%', padding: '0.75rem', backgroundColor: '#1F2937', color: 'white', border: '1px solid var(--border-color)', borderRadius: '4px'}} />
          </div>
          <div style={{flex: 1}}>
            <label style={{display: 'block', fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.5rem'}}>Action</label>
            <select value={newRule.action} onChange={e => setNewRule({...newRule, action: e.target.value})}
                    style={{width: '100%', padding: '0.75rem', backgroundColor: '#1F2937', color: 'white', border: '1px solid var(--border-color)', borderRadius: '4px', color: newRule.action === 'BUY' ? 'var(--signal-buy)' : 'var(--signal-sell)', fontWeight: 'bold'}}>
              <option value="BUY">BUY</option>
              <option value="SELL">SELL</option>
            </select>
          </div>
          <button className="btn" onClick={handleAddRule} style={{backgroundColor: 'var(--accent)', padding: '0.75rem 1.5rem'}}>Add Rule</button>
        </div>
      </div>

      <div className="panel" style={{gridColumn: '1 / -1'}}>
        <div className="panel-header">Active Custom Strategies</div>
        <table style={{width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem'}}>
          <thead>
            <tr style={{borderBottom: '1px solid var(--border-color)', color: 'var(--text-secondary)', textAlign: 'left'}}>
              <th style={{padding: '0.5rem'}}>Rule Name</th>
              <th style={{padding: '0.5rem'}}>Condition</th>
              <th style={{padding: '0.5rem'}}>Action</th>
              <th style={{padding: '0.5rem', textAlign: 'right'}}>Manage</th>
            </tr>
          </thead>
          <tbody>
            {!config.custom_strategies || config.custom_strategies.length === 0 ? (
              <tr><td colSpan="4" style={{padding: '1rem 0.5rem', color: 'var(--text-secondary)'}}>No custom rules active.</td></tr>
            ) : (
              config.custom_strategies.map(rule => (
                <tr key={rule.id} style={{borderTop: '1px solid var(--border-color)'}}>
                  <td style={{padding: '1rem 0.5rem', fontWeight: 600}}>{rule.name}</td>
                  <td style={{padding: '1rem 0.5rem', fontFamily: 'monospace'}}>
                    IF <span style={{color: '#60a5fa'}}>{rule.indicator}</span> {rule.operator} <span style={{color: '#f472b6'}}>{rule.value}</span>
                  </td>
                  <td style={{padding: '1rem 0.5rem', color: rule.action === 'BUY' ? 'var(--signal-buy)' : 'var(--signal-sell)', fontWeight: 'bold'}}>
                    THEN {rule.action}
                  </td>
                  <td style={{padding: '1rem 0.5rem', textAlign: 'right'}}>
                    <button onClick={() => handleRemoveRule(rule.id)} style={{background: 'transparent', border: 'none', color: 'var(--signal-sell)', cursor: 'pointer'}}>Remove</button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function AdminPanel({ config, updateConfig }) {
  const safeConfig = config || {};
  const risk = safeConfig.risk || {
    max_position_pct: 10,
    max_portfolio_exposure_pct: 50,
    daily_loss_limit_pct: 2.0,
    crash_risk_halt_threshold: 75
  };
  const modulesEnabled = safeConfig.modules_enabled || {
    technical: true, fundamental: true, promoter: true, ratio: true,
    options_flow: true, quant: true, news_risk: true, sentiment: true
  };

  return (
    <div className="dashboard-grid">
      <div className="panel">
        <div className="panel-header">Execution Settings</div>
        
        <div style={{display: 'flex', gap: '1rem', marginBottom: '1.5rem'}}>
          <button className="btn" style={{backgroundColor: safeConfig.auto_trade === 'active' ? 'var(--signal-buy)' : '#374151', display: 'flex', alignItems: 'center', gap: '0.5rem'}}
                  onClick={() => updateConfig({auto_trade: 'active'})}>
            <Play size={16}/> Active
          </button>
          <button className="btn" style={{backgroundColor: safeConfig.auto_trade === 'halted' ? 'var(--signal-sell)' : '#374151', display: 'flex', alignItems: 'center', gap: '0.5rem'}}
                  onClick={() => updateConfig({auto_trade: 'halted'})}>
            <Pause size={16}/> Halted
          </button>
          <button className="btn" style={{backgroundColor: safeConfig.auto_trade === 'off' ? '#6b7280' : '#374151', display: 'flex', alignItems: 'center', gap: '0.5rem'}}
                  onClick={() => updateConfig({auto_trade: 'off'})}>
            <Square size={16}/> Off
          </button>
        </div>

        <div style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem', paddingBottom: '1rem', borderBottom: '1px solid var(--border-color)'}}>
          <div>
            <div style={{fontWeight: 500}}>Paper Trading Mode</div>
            <div style={{fontSize: '0.8rem', color: 'var(--text-secondary)'}}>Execute trades via mock broker</div>
          </div>
          <label className="toggle-switch">
            <input type="checkbox" checked={!!safeConfig.paper_mode} onChange={(e) => updateConfig({paper_mode: e.target.checked})} />
            <span className="slider"></span>
          </label>
        </div>

        <div className="form-group">
          <label>Starting Capital (INR)</label>
          <input type="number" className="form-control" value={safeConfig.capital ?? 1000000} onChange={(e) => updateConfig({capital: parseFloat(e.target.value)})} />
        </div>
      </div>

      <div className="panel">
        <div className="panel-header">Risk Limits</div>
        <div className="form-group">
          <label>Max Position Size (% of Capital)</label>
          <div style={{display: 'flex', alignItems: 'center', gap: '1rem'}}>
            <input type="range" min="1" max="100" value={risk.max_position_pct ?? 10} className="form-control" style={{flexGrow: 1}} readOnly/>
            <span>{risk.max_position_pct ?? 10}%</span>
          </div>
        </div>
        <div className="form-group">
          <label>Max Portfolio Exposure (%)</label>
          <div style={{display: 'flex', alignItems: 'center', gap: '1rem'}}>
            <input type="range" min="1" max="100" value={risk.max_portfolio_exposure_pct ?? 50} className="form-control" style={{flexGrow: 1}} readOnly/>
            <span>{risk.max_portfolio_exposure_pct ?? 50}%</span>
          </div>
        </div>
        <div className="form-group">
          <label>Daily Loss Limit (%) - Auto Stop</label>
          <div style={{display: 'flex', alignItems: 'center', gap: '1rem'}}>
            <input type="range" min="0.1" max="10" step="0.1" value={risk.daily_loss_limit_pct ?? 2.0} className="form-control" style={{flexGrow: 1}} readOnly/>
            <span className="text-sell">{risk.daily_loss_limit_pct ?? 2.0}%</span>
          </div>
        </div>
        <div className="form-group">
          <label>Crash Risk Halt Threshold</label>
          <div style={{display: 'flex', alignItems: 'center', gap: '1rem'}}>
            <input type="range" min="0" max="100" value={risk.crash_risk_halt_threshold ?? 75} className="form-control" style={{flexGrow: 1}} readOnly/>
            <span className="text-neutral">{risk.crash_risk_halt_threshold ?? 75}</span>
          </div>
        </div>
      </div>

      <div className="panel">
        <div className="panel-header">Analysis Modules</div>
        {Object.entries(modulesEnabled).map(([modName, isEnabled]) => (
          <div key={modName} style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem'}}>
            <span style={{textTransform: 'capitalize', fontSize: '0.9rem'}}>{modName.replace('_', ' ')}</span>
            <label className="toggle-switch" style={{transform: 'scale(0.8)'}}>
              <input type="checkbox" checked={!!isEnabled} readOnly />
              <span className="slider"></span>
            </label>
          </div>
        ))}
      </div>

      <div className="panel" style={{gridColumn: '1 / -1'}}>
        <div className="panel-header" style={{borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
          <span>API Credentials & Broker Integration</span>
          <span style={{fontSize: '0.8rem', color: 'var(--signal-buy)', fontWeight: 600}}>✓ Active Provider: {(safeConfig?.broker_name || 'dhan').toUpperCase()}</span>
        </div>
        <div style={{display: 'flex', gap: '2rem', marginTop: '1rem', flexWrap: 'wrap'}}>
          <div style={{flex: 1, minWidth: '220px'}}>
            <label style={{display: 'block', fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.5rem'}}>Active Broker</label>
            <select
              value={safeConfig?.broker_name || 'dhan'}
              onChange={e => updateConfig({ broker_name: e.target.value })}
              style={{width: '100%', padding: '0.75rem', backgroundColor: '#1F2937', color: 'white', border: '1px solid var(--border-color)', borderRadius: '4px', outline: 'none', marginBottom: '1rem'}}
            >
              <option value="dhan">Dhan (DhanHQ API)</option>
              <option value="mock">Mock Provider (Paper Simulator)</option>
              <option value="zerodha">Zerodha (Kite Connect)</option>
              <option value="upstox">Upstox API</option>
              <option value="angelone">Angel One SmartAPI</option>
              <option value="fyers">Fyers API v3</option>
            </select>
          </div>
          <div style={{flex: 1, minWidth: '220px'}}>
            <label style={{display: 'block', fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.5rem'}}>
              {safeConfig?.broker_name === 'dhan' ? 'Dhan Client ID' : 'API Key / Client ID'}
            </label>
            <input 
              type="text" 
              value={
                (safeConfig?.api_key || '').startsWith('eyJ') 
                  ? '1105713827 (Attached)' 
                  : (safeConfig?.api_key || '')
              } 
              onChange={e => updateConfig({ api_key: e.target.value })}
              placeholder="e.g. 1105713827"
              style={{width: '100%', padding: '0.75rem', backgroundColor: '#1F2937', color: 'white', border: '1px solid var(--border-color)', borderRadius: '4px', outline: 'none', marginBottom: '1rem'}}
            />
          </div>
          <div style={{flex: 1, minWidth: '220px'}}>
            <label style={{display: 'block', fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.5rem'}}>
              {safeConfig?.broker_name === 'dhan' ? 'Dhan Access Token (Masked)' : 'API Secret'}
            </label>
            <input 
              type="password" 
              value={safeConfig?.api_secret || (safeConfig?.api_key?.startsWith('eyJ') ? safeConfig.api_key : '')} 
              onChange={e => updateConfig({ api_secret: e.target.value })}
              placeholder="••••••••••••••••"
              style={{width: '100%', padding: '0.75rem', backgroundColor: '#1F2937', color: 'white', border: '1px solid var(--border-color)', borderRadius: '4px', outline: 'none', marginBottom: '1rem'}}
            />
          </div>
        </div>
        <div style={{fontSize: '0.8rem', color: '#93c5fd', background: 'rgba(59, 130, 246, 0.1)', padding: '8px 12px', borderRadius: '6px', border: '1px solid rgba(59, 130, 246, 0.2)'}}>
          🔒 Dhan Access Token safely stored & masked. Use <b>Broker API Keys</b> tab in sidebar to test live connectivity.
        </div>
      </div>
    </div>
  );
}

function JournalView({ token }) {
  const [journal, setJournal] = useState([]);

  useEffect(() => {
    const fetchJournal = async () => {
      try {
        const res = await fetch(`${API_URL}/journal`, { headers: { 'Authorization': `Bearer ${token}` } });
        if (res.ok) {
          const data = await res.json();
          setJournal(Array.isArray(data) ? data : []);
        }
      } catch (e) {
        console.error(e);
      }
    };
    fetchJournal();
    const interval = setInterval(fetchJournal, 60000);
    return () => clearInterval(interval);
  }, []);

  const safeJournal = Array.isArray(journal) ? journal : [];

  return (
    <div className="panel" style={{gridColumn: '1 / -1'}}>
      <div className="panel-header">Trade Journal (Ledger)</div>
      
      {/* Equity Curve */}
      <div style={{width: '100%', height: '250px', marginBottom: '2rem'}}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={[...safeJournal].reverse().map((t, i, arr) => ({
             trade_id: t.trade_id,
             equity: arr.slice(0, i + 1).reduce((sum, item) => sum + (item.pnl || 0), 0)
          }))}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis dataKey="trade_id" stroke="#9ca3af" fontSize={10} />
            <YAxis stroke="#9ca3af" fontSize={10} />
            <Tooltip contentStyle={{backgroundColor: '#1F2937', borderColor: '#374151', color: '#fff'}} />
            <Line type="monotone" dataKey="equity" stroke="#10B981" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <table style={{width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem'}}>
        <thead>
          <tr style={{borderBottom: '1px solid var(--border-color)', color: 'var(--text-secondary)', textAlign: 'left'}}>
            <th style={{padding: '0.5rem'}}>Trade ID</th>
            <th style={{padding: '0.5rem'}}>Time</th>
            <th style={{padding: '0.5rem'}}>Symbol</th>
            <th style={{padding: '0.5rem'}}>Action</th>
            <th style={{padding: '0.5rem'}}>Qty</th>
            <th style={{padding: '0.5rem'}}>Entry</th>
            <th style={{padding: '0.5rem'}}>Status</th>
            <th style={{padding: '0.5rem'}}>Reasons (Log)</th>
          </tr>
        </thead>
        <tbody>
          {safeJournal.length === 0 ? (
            <tr><td colSpan="8" style={{padding: '1rem 0.5rem'}}>No trades executed yet.</td></tr>
          ) : (
            safeJournal.map(trade => {
              let color = 'var(--signal-neutral)';
              if (trade.action === 'BUY') color = 'var(--signal-buy)';
              if (trade.action === 'SELL') color = 'var(--signal-sell)';
              
              return (
                <tr key={trade.trade_id || Math.random()} style={{borderTop: '1px solid var(--border-color)', verticalAlign: 'top'}}>
                  <td style={{padding: '1rem 0.5rem', fontFamily: 'monospace'}}>{trade.trade_id}</td>
                  <td style={{padding: '1rem 0.5rem'}}>{trade.timestamp ? new Date(trade.timestamp).toLocaleString() : 'N/A'}</td>
                  <td style={{padding: '1rem 0.5rem', fontWeight: 600}}>{trade.symbol}</td>
                  <td style={{padding: '1rem 0.5rem', color: color, fontWeight: 600}}>{trade.action}</td>
                  <td style={{padding: '1rem 0.5rem'}}>{trade.qty}</td>
                  <td style={{padding: '1rem 0.5rem'}}>{(trade.entry_price ?? 0).toFixed(2)}</td>
                  <td style={{padding: '1rem 0.5rem'}}>{trade.status}</td>
                  <td style={{padding: '1rem 0.5rem', fontSize: '0.8rem', color: 'var(--text-secondary)'}}>
                    <ul style={{paddingLeft: '1rem', margin: 0}}>
                      {(trade.reasons || []).map((r, i) => <li key={i}>{r}</li>)}
                    </ul>
                  </td>
                </tr>
              )
            })
          )}
        </tbody>
      </table>
    </div>
  );
}

function RadarView({ token }) {
  const [radar, setRadar] = useState(null);

  useEffect(() => {
    const fetchRadar = async () => {
      try {
        const res = await fetch(`${API_URL}/radar`, { headers: { 'Authorization': `Bearer ${token}` } });
        if (res.ok) {
          const data = await res.json();
          setRadar(data);
        }
      } catch (e) {
        console.error(e);
      }
    };
    fetchRadar();
    const interval = setInterval(fetchRadar, 60000);
    return () => clearInterval(interval);
  }, []);

  if (!radar) return <div className="panel" style={{padding: '2rem'}}>Loading NLP Data...</div>;

  let statusColor = 'var(--signal-neutral)';
  if (radar.overall_status === 'BULLISH') statusColor = 'var(--signal-buy)';
  if (radar.overall_status === 'BEARISH') statusColor = 'var(--signal-sell)';

  const newsItems = Array.isArray(radar?.news) ? radar.news : [];

  return (
    <div style={{display: 'flex', flexDirection: 'column', gap: '1.5rem'}}>
      <div className="panel" style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
        <div>
          <div className="panel-header">Market NLP Sentiment (VADER)</div>
          <div style={{fontSize: '0.9rem', color: 'var(--text-secondary)'}}>
            Aggregated real-time headline sentiment scoring.
          </div>
        </div>
        <div style={{textAlign: 'right'}}>
          <div style={{fontSize: '2rem', fontWeight: 'bold', color: statusColor}}>
            {radar.overall_status || 'NEUTRAL'}
          </div>
          <div style={{fontSize: '0.9rem', color: 'var(--text-secondary)'}}>
            Avg Compound Score: {(radar.avg_compound ?? 0).toFixed(3)}
          </div>
        </div>
      </div>
      
      <div className="panel">
        <div className="panel-header">Latest Headlines</div>
        <table style={{width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem'}}>
          <thead>
            <tr style={{borderBottom: '1px solid var(--border-color)', color: 'var(--text-secondary)', textAlign: 'left'}}>
              <th style={{padding: '0.5rem'}}>Headline</th>
              <th style={{padding: '0.5rem'}}>VADER Score</th>
              <th style={{padding: '0.5rem'}}>Impact</th>
            </tr>
          </thead>
          <tbody>
            {newsItems.map((item, idx) => {
              let color = 'var(--signal-neutral)';
              let bg = 'bg-neutral';
              if (item.status === 'BULLISH') { color = 'var(--signal-buy)'; bg = 'bg-buy'; }
              if (item.status === 'BEARISH') { color = 'var(--signal-sell)'; bg = 'bg-sell'; }
              
              return (
                <tr key={idx} style={{borderTop: '1px solid var(--border-color)'}}>
                  <td style={{padding: '1rem 0.5rem', fontWeight: 500}}>{item.headline}</td>
                  <td style={{padding: '1rem 0.5rem'}}>{(item.compound ?? 0).toFixed(3)}</td>
                  <td style={{padding: '1rem 0.5rem'}}>
                    <span className={bg} style={{padding: '4px 8px', borderRadius: '4px', color: color, fontSize: '0.8rem', fontWeight: 600}}>
                      {item.status || 'NEUTRAL'}
                    </span>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function DashboardView({ config, token }) {
  const [analysis, setAnalysis] = useState({});
  const [portfolio, setPortfolio] = useState(null);
  const [segment, setSegment] = useState('EQUITY');
  
  const assetMap = {
    EQUITY: ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'NIFTY'],
    COMMODITY: ['GOLD', 'SILVER', 'CRUDEOIL'],
    CURRENCY: ['USDINR', 'EURINR', 'GBPINR']
  };
  
  const symbols = assetMap[segment];
  const [selectedSymbol, setSelectedSymbol] = useState(symbols[0]);

  useEffect(() => {
    setSelectedSymbol(assetMap[segment][0]);
  }, [segment]);

  useEffect(() => {
    const headers = { 'Authorization': `Bearer ${token}` };
    const fetchAll = async () => {
        const results = {};
        await Promise.all(symbols.map(async (sym) => {
          let querySym = sym;
          if (segment === 'EQUITY') querySym = sym === 'NIFTY' ? '^NSEI' : sym + '.NS';
          if (segment === 'COMMODITY') querySym = sym === 'CRUDEOIL' ? 'CL=F' : sym === 'GOLD' ? 'GC=F' : 'SI=F';
          if (segment === 'CURRENCY') querySym = sym + '=X';
          
          try {
            const res = await fetch(`${API_URL}/api/analyze/${querySym}`, { headers });
            if (res.ok) {
              results[sym] = await res.json();
            }
          } catch (e) {
            console.error(`Failed to fetch ${sym}:`, e);
          }
        }));
        setAnalysis(prev => ({ ...prev, ...results }));
      };
  
      const fetchPortfolio = async () => {
        try {
          const res = await fetch(`${API_URL}/portfolio`, { headers });
          if (res.ok) {
            setPortfolio(await res.json());
          }
        } catch(e) {}
      };
  
      fetchAll();
      fetchPortfolio();
      const interval = setInterval(() => { fetchAll(); fetchPortfolio(); }, 60000); // 60s to prevent spam
      return () => clearInterval(interval);
  }, [segment, token]);

  const ALL_MODULES = ['technical', 'fundamental', 'options_flow', 'quant', 'news_risk', 'sentiment'];
  
  // Always return array so RadarChart draws the grid even when empty
  const radarData = ALL_MODULES.map(mod => {
    const modData = analysis[selectedSymbol]?.contributions?.[mod];
    return {
      module: mod,
      score: modData ? modData.score * 100 : 0
    };
  });

  const confidenceData = symbols.map(sym => ({
    name: sym,
    confidence: analysis[sym] ? (analysis[sym].overall_confidence ?? 0) * 100 : 0
  }));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      
      {/* Segment Selector */}
      <div style={{ display: 'flex', gap: '10px', backgroundColor: '#1e293b', padding: '10px', borderRadius: '8px', border: '1px solid #334155' }}>
        {Object.keys(assetMap).map(s => (
          <button 
            key={s} 
            onClick={() => setSegment(s)}
            style={{
              padding: '8px 16px',
              backgroundColor: segment === s ? '#8b5cf6' : 'transparent',
              color: segment === s ? 'white' : '#cbd5e1',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontWeight: segment === s ? 'bold' : 'normal'
            }}
          >
            {s}
          </button>
        ))}
      </div>

      <div className="dashboard-grid">
        <div className="panel" style={{gridColumn: '1 / span 2'}}>
          <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
            <div className="panel-header" style={{borderBottom: 'none'}}>AI Module Radar (Spider Chart)</div>
            <select value={selectedSymbol} onChange={e => setSelectedSymbol(e.target.value)} 
                    style={{padding: '0.5rem', backgroundColor: '#374151', color: 'white', border: '1px solid var(--border-color)', borderRadius: '4px'}}>
              {symbols.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
        <div style={{width: '100%', height: '300px'}}>
          <ResponsiveContainer width="100%" height="100%">
            <RadarChart cx="50%" cy="50%" outerRadius="80%" data={radarData}>
              <PolarGrid stroke="#374151" />
              <PolarAngleAxis dataKey="module" stroke="#9ca3af" fontSize={11} />
              <PolarRadiusAxis angle={30} domain={[-100, 100]} stroke="#4b5563" />
              <Radar name="Module Score" dataKey="score" stroke="#8b5cf6" fill="#8b5cf6" fillOpacity={0.4} />
              <Tooltip contentStyle={{backgroundColor: '#1F2937', borderColor: '#374151'}} />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="panel">
        <div className="panel-header">Watchlist Confidence</div>
        <div style={{width: '100%', height: '300px'}}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={confidenceData} layout="vertical" margin={{top: 5, right: 30, left: 20, bottom: 5}}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" horizontal={false} />
              <XAxis type="number" domain={[0, 100]} stroke="#9ca3af" />
              <YAxis dataKey="name" type="category" stroke="#9ca3af" fontSize={11} width={80} />
              <Tooltip contentStyle={{backgroundColor: '#1F2937', borderColor: '#374151'}} />
              <Bar dataKey="confidence" fill="#3b82f6" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="panel" style={{gridColumn: '1 / -1'}}>
        <div className="panel-header">Open Positions</div>
        <table style={{width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem'}}>
          <thead>
            <tr style={{borderBottom: '1px solid var(--border-color)', color: 'var(--text-secondary)', textAlign: 'left'}}>
              <th style={{padding: '0.5rem'}}>Symbol</th>
              <th style={{padding: '0.5rem'}}>Action</th>
              <th style={{padding: '0.5rem'}}>Qty</th>
              <th style={{padding: '0.5rem'}}>Entry Price</th>
              <th style={{padding: '0.5rem'}}>Current Price (LTP)</th>
              <th style={{padding: '0.5rem'}}>Unrealized P&L</th>
            </tr>
          </thead>
          <tbody>
            {Array.isArray(portfolio?.open_positions) && portfolio.open_positions.length > 0 ? (
              portfolio.open_positions.map((pos, idx) => (
                <tr key={idx} style={{borderTop: '1px solid var(--border-color)'}}>
                  <td style={{padding: '1rem 0.5rem', fontWeight: 600}}>{pos.symbol}</td>
                  <td style={{padding: '1rem 0.5rem', color: pos.action === 'BUY' ? 'var(--signal-buy)' : 'var(--signal-sell)'}}>{pos.action}</td>
                  <td style={{padding: '1rem 0.5rem'}}>{pos.qty}</td>
                  <td style={{padding: '1rem 0.5rem'}}>{(pos.entry_price ?? 0).toFixed(2)}</td>
                  <td style={{padding: '1rem 0.5rem'}}>{(pos.ltp ?? 0).toFixed(2)}</td>
                  <td style={{padding: '1rem 0.5rem', color: (pos.unrealized_pnl ?? 0) >= 0 ? 'var(--signal-buy)' : 'var(--signal-sell)', fontWeight: 'bold'}}>
                    {(pos.unrealized_pnl ?? 0) >= 0 ? '+' : ''}{(pos.unrealized_pnl ?? 0).toFixed(2)}
                  </td>
                </tr>
              ))
            ) : (
              <tr><td colSpan="6" style={{padding: '1rem 0.5rem', textAlign: 'center', color: 'var(--text-secondary)'}}>No open positions</td></tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="panel" style={{gridColumn: '1 / -1'}}>
        <div className="panel-header">Watchlist Analysis (Live - Intraday)</div>
        <table style={{width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem'}}>
          <thead>
            <tr style={{borderBottom: '1px solid var(--border-color)', color: 'var(--text-secondary)', textAlign: 'left'}}>
              <th style={{padding: '0.5rem'}}>Symbol</th>
              <th style={{padding: '0.5rem'}}>Action</th>
              <th style={{padding: '0.5rem'}}>Confidence</th>
              <th style={{padding: '0.5rem'}}>Score</th>
              <th style={{padding: '0.5rem'}}>Execution</th>
              <th style={{padding: '0.5rem'}}>Module Signals Log</th>
            </tr>
          </thead>
          <tbody>
            {symbols.map(sym => {
              const data = analysis[sym];
              if (!data) return <tr key={sym}><td colSpan="6" style={{padding: '1rem 0.5rem'}}>Loading {sym}...</td></tr>;
              
              let actionClass = "bg-neutral";
              let actionColor = "var(--signal-neutral)";
              if (data.action === "BUY") { actionClass = "bg-buy"; actionColor = "var(--signal-buy)"; }
              if (data.action === "SELL") { actionClass = "bg-sell"; actionColor = "var(--signal-sell)"; }

              return (
                <tr key={sym} style={{borderTop: '1px solid var(--border-color)'}}>
                  <td style={{padding: '1rem 0.5rem', fontWeight: 600}}>{data.symbol || sym}</td>
                  <td style={{padding: '1rem 0.5rem'}}>
                    <span className={actionClass} style={{padding: '4px 8px', borderRadius: '4px', color: actionColor, fontSize: '0.8rem', fontWeight: 600}}>
                      {data.action || 'NEUTRAL'}
                    </span>
                  </td>
                  <td style={{padding: '1rem 0.5rem'}}>{((data.overall_confidence ?? 0) * 100).toFixed(1)}%</td>
                  <td style={{padding: '1rem 0.5rem'}}>{(data.overall_score ?? 0).toFixed(2)}</td>
                  <td style={{padding: '1rem 0.5rem', verticalAlign: 'top'}}>
                    {data.executed ? 
                      <span style={{color: 'var(--signal-buy)', fontWeight: 'bold'}}>Executed</span> :
                      data.risk_check_passed ? 
                        <span style={{color: 'var(--text-secondary)'}}>Safe to execute (Neutral)</span> : 
                        <span style={{color: 'var(--signal-sell)'}}>Blocked by Risk Manager</span>
                    }
                  </td>
                  <td style={{padding: '1rem 0.5rem', fontSize: '0.8rem', color: 'var(--text-secondary)'}}>
                    <ul style={{paddingLeft: '1rem', margin: 0}}>
                      {Array.isArray(data.reasons) && data.reasons.map((r, i) => <li key={i}>{r}</li>)}
                    </ul>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      
      <div className="panel">
        <div className="panel-header">Unrealized P&L</div>
        <div className="value" style={{fontSize: '2rem', fontWeight: 600, color: (Number(portfolio?.pnl?.total_pnl) || 0) >= 0 ? 'var(--signal-buy)' : 'var(--signal-sell)'}}>
          {(Number(portfolio?.pnl?.total_pnl) || 0) >= 0 ? '+' : ''} ₹ {(Number(portfolio?.pnl?.total_pnl) || 0).toLocaleString()}
        </div>
        <div style={{fontSize: '0.85rem', color: 'var(--text-secondary)'}}>
          {config?.paper_mode ? 'Paper Trading Mode Active' : 'Live Mode Active'}
        </div>
      </div>
      
      <div className="panel">
        <div className="panel-header">Portfolio Exposure</div>
        <div style={{fontSize: '2rem', fontWeight: 600, marginBottom: '0.5rem'}}>{portfolio?.exposure_pct?.toFixed(1) || 0}%</div>
        <div style={{width: '100%', height: '6px', backgroundColor: '#374151', borderRadius: '3px', marginTop: '1rem'}}>
          <div style={{width: `${portfolio?.exposure_pct || 0}%`, height: '100%', backgroundColor: 'var(--accent)', borderRadius: '3px', transition: 'width 0.5s'}}></div>
        </div>
      </div>
      </div>
    </div>
  );
}
