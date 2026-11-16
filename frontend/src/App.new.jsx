import { useState, useEffect, useCallback, useMemo, Suspense, lazy } from 'react';
import { LayoutDashboard, Activity, Settings, TrendingUp, AlertTriangle, Play, Square, Pause, BookOpen, BarChart2, ListFilter, Layers, PieChart, ShoppingCart, Grid, BellRing, BrainCircuit, Bot, Video, ShieldAlert, Key, Users, CheckCircle, Route, Crosshair, ChevronDown, ChevronRight, Zap, Terminal, Database, Globe, Shield, FlaskConical, ClipboardList, LineChart, HardDrive, Network, GitBranch, Eye, Mic, Heart, Crown, Anchor, Compass, Box, Laptop, Smartphone, Tablet, Monitor, Server, Cloud, Wifi, Lock, Unlock, Key as KeyIcon, User, Users as UsersIcon, LogOut, Menu, X, ChevronLeft, ChevronRight as ChevronRightIcon, MoreHorizontal, Search, Filter, Download, Upload, RefreshCw, RotateCcw, Home, Activity as ActivityIcon, Settings as SettingsIcon, TrendingUp as TrendingUpIcon } from 'lucide-react';
import './design-system/variables.css';
import './index.css';

// Lazy load heavy components
const AdvancedChart = lazy(() => import('./components/charts/AdvancedChart').then(m => ({ default: m.AdvancedChart })));
const MarketScanner = lazy(() => import('./components/scanner/MarketScanner').then(m => ({ default: m.MarketScanner })));
const OptionsChain = lazy(() => import('./components/options/OptionsChainAnalyzer').then(m => ({ default: m.OptionsChainAnalyzer })));
const VisualStrategyBuilder = lazy(() => import('./components/strategy/VisualStrategyBuilder').then(m => ({ default: m.VisualStrategyBuilder })));
const BacktestEngine = lazy(() => import('./components/backtest/BacktestEngine').then(m => ({ default: m.BacktestEngine })));
const RiskDashboard = lazy(() => import('./components/risk/RiskDashboard').then(m => ({ default: m.RiskDashboard })));
const AIAssistant = lazy(() => import('./components/ai/AIAssistant').then(m => ({ default: m.AIAssistant })));
const MultiBrokerPanel = lazy(() => import('./components/broker/MultiBrokerPanel').then(m => ({ default: m.MultiBrokerPanel })));
const TradeJournal = lazy(() => import('./components/journal/TradeJournalAdvanced').then(m => ({ default: m.TradeJournalAdvanced })));

// Import existing components
import CommandCenter from './components/CommandCenter';
import BrokerPanel from './components/BrokerPanel';
import PortfolioHeatmap from './components/PortfolioHeatmap';
import SmartAlerts from './components/SmartAlerts';
import TradeDiary from './components/TradeDiary';
import ReportsView from './components/ReportsView';
import OMSView from './components/OMSView';
import ScannerView from './components/ScannerView';
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
import ExecutionReplay from './components/ExecutionReplay';

import AppLayout from './layout/AppLayout';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [config, setConfig] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('elco_token'));
  const [loginError, setLoginError] = useState('');
  const [expandedCategories, setExpandedCategories] = useState({
    Trading: true,
    Analysis: true,
    Strategy: false,
    Risk: false,
    Intelligence: false,
    Journal: false,
    Brokers: false,
    System: false,
  });
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [tickers, setTickers] = useState([
    { symbol: 'NIFTY 50', val: '---', change: '0.0%', up: true },
    { symbol: 'BANKNIFTY', val: '---', change: '0.0%', up: true },
  ]);

  const toggleCategory = useCallback((cat) => {
    setExpandedCategories(prev => ({ ...prev, [cat]: !prev[cat] }));
  }, []);

  const headers = token ? { 'Authorization': `Bearer ${token}` } : {};

  const fetchTickers = useCallback(async () => {
    if (!token) return;
    try {
      const res = await fetch(`${API_URL}/api/market-indices`, { headers });
      if (res.ok) {
        const data = await res.json();
        if (data.length > 0) setTickers(data);
      }
    } catch (err) {
      console.error("Failed to fetch tickers:", err);
    }
  }, [token, API_URL, headers]);

  const fetchConfig = useCallback(async () => {
    if (!token) return;
    try {
      const res = await fetch(`${API_URL}/config`, { headers });
      if (res.status === 401) return handleLogout();
      const data = await res.json();
      setConfig(data);
    } catch (err) {
      console.error("Failed to fetch config:", err);
    }
  }, [token, API_URL, headers]);

  const updateConfig = useCallback(async (updates) => {
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
        setConfig(prev => ({ ...prev, ...updates }));
      }
    } catch (err) {
      console.error("Failed to update config:", err);
      setConfig(prev => ({ ...prev, ...updates }));
    }
  }, [headers, API_URL]);

  const handleLogout = useCallback(() => {
    localStorage.removeItem('elco_token');
    setToken(null);
    setConfig(null);
  }, []);

  const handleLogin = useCallback(async (e) => {
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
  }, [API_URL]);

  useEffect(() => {
    fetchConfig();
    fetchTickers();
    const interval = setInterval(fetchTickers, 60000);
    return () => clearInterval(interval);
  }, [fetchConfig, fetchTickers]);

  if (!token) {
    return <AuthViews setToken={setToken} />;
  }

  // Render content based on active tab
  const renderContent = useCallback(() => {
    switch (activeTab) {
      case 'dashboard':
        return <DashboardView config={config} token={token} />;
      case 'oms':
        return <OMSView token={token} />;
      case 'charts':
        return (
          <Suspense fallback={<div style={{ padding: 'var(--space-8)', textAlign: 'center', color: 'var(--color-text-tertiary)' }}>Loading Advanced Charts...</div>}>
            <AdvancedChart token={token} height={700} />
          </Suspense>
        );
      case 'scanner':
        return (
          <Suspense fallback={<div style={{ padding: 'var(--space-8)', textAlign: 'center', color: 'var(--color-text-tertiary)' }}>Loading Market Scanner...</div>}>
            <MarketScanner token={token} />
          </Suspense>
        );
      case 'universal':
        return <UniversalScreener token={token} />;
      case 'options':
        return (
          <Suspense fallback={<div style={{ padding: 'var(--space-8)', textAlign: 'center', color: 'var(--color-text-tertiary)' }}>Loading Options Chain...</div>}>
            <OptionsChain token={token} />
          </Suspense>
        );
      case 'reports':
        return <ReportsView token={token} />;
      case 'heatmap':
        return <PortfolioHeatmap token={token} />;
      case 'alerts':
        return <SmartAlerts token={token} />;
      case 'radar':
        return <CommandCenter token={token} />; // NewsRiskRadar
      case 'journal':
        return <TradeDiary token={token} />;
      case 'diary':
        return <TradeDiary token={token} />;
      case 'pathways':
        return <TradingPathways token={token} />;
      case 'ai':
        return (
          <Suspense fallback={<div style={{ padding: 'var(--space-8)', textAlign: 'center', color: 'var(--color-text-tertiary)' }}>Loading AI Assistant...</div>}>
            <AIAssistant token={token} />
          </Suspense>
        );
      case 'strategy-lab':
        return <StrategyLab token={token} />;
      case 'execution-replay':
        return <ExecutionReplay token={token} />;
      case 'stress-test':
        return <StressTest token={token} />;
      case 'workflow':
        return <WorkflowApprovals token={token} />;
      case 'sso':
        return <SSOSettings token={token} />;
      case 'tenant':
        return <TenantDashboard token={token} />;
      case 'config':
        return config ? (
          <AdminPanel config={config} updateConfig={updateConfig} />
        ) : (
          <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
            <h3>Failed to load configuration from backend</h3>
            <button onClick={fetchConfig} className="btn" style={{ marginTop: '1rem', backgroundColor: 'var(--signal-buy)' }}>Retry Connection</button>
          </div>
        );
      case 'market-scanner':
        return <AdvancedScannerUI token={token} />;
      case 'system-dashboard':
        return <SystemDashboard token={token} />;
      case 'strategy-canvas':
        return <StrategyBuilderLayout token={token} />;
      case 'walk-forward':
        return <WalkForwardUI token={token} />
      case 'command-center':
        return <CommandCenter token={token} />;
      case 'strategy-builder':
        return (
          <Suspense fallback={<div style={{ padding: 'var(--space-8)', textAlign: 'center', color: 'var(--color-text-tertiary)' }}>Loading Strategy Builder...</div>}>
            <VisualStrategyBuilder token={token} />
          </Suspense>
        );
      case 'backtest':
        return (
          <Suspense fallback={<div style={{ padding: 'var(--space-8)', textAlign: 'center', color: 'var(--color-text-tertiary)' }}>Loading Backtest Engine...</div>}>
            <BacktestEngine token={token} />
          </Suspense>
        );
      case 'risk-dashboard':
        return (
          <Suspense fallback={<div style={{ padding: 'var(--space-8)', textAlign: 'center', color: 'var(--color-text-tertiary)' }}>Loading Risk Dashboard...</div>}>
            <RiskDashboard token={token} />
          </Suspense>
        );
      case 'multi-broker':
        return (
          <Suspense fallback={<div style={{ padding: 'var(--space-8)', textAlign: 'center', color: 'var(--color-text-tertiary)' }}>Loading Multi-Broker Panel...</div>}>
            <MultiBrokerPanel token={token} />
          </Suspense>
        );
      case 'trade-journal':
        return (
          <Suspense fallback={<div style={{ padding: 'var(--space-8)', textAlign: 'center', color: 'var(--color-text-tertiary)' }}>Loading Trade Journal...</div>}>
            <TradeJournal token={token} />
          </Suspense>
        );
      default:
        return <DashboardView config={config} token={token} />;
    }
  }, [activeTab, config, token]);

  return (
    <AppLayout
      token={token}
      config={config}
      onLogout={handleLogout}
      onConfigChange={updateConfig}
    >
      {/* Ticker Strip */}
      <div className="ticker-strip">
        <div style={{ display: 'flex', animation: 'marquee 30s linear infinite' }}>
          {tickers.map(t => (
            <div key={t.symbol} className="ticker-item">
              <span>{t.symbol}</span>
              <span className="ticker-val">{t.val}</span>
              <span className={`ticker-change ${t.up ? 'up' : 'down'}`}>{t.change}</span>
            </div>
          ))}
          {tickers.map(t => (
            <div key={t.symbol + '-dup'} className="ticker-item">
              <span>{t.symbol}</span>
              <span className="ticker-val">{t.val}</span>
              <span className={`ticker-change ${t.up ? 'up' : 'down'}`}>{t.change}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Main Content */}
      <main className="elco-main-content" style={{ flex: 1, overflow: 'auto', padding: 'var(--space-4)' }}>
        {renderContent()}
      </main>

      <style dangerouslySetInnerHTML={{ __html: `
        @keyframes marquee { 0% { transform: translateX(0); } 100% { transform: translateX(-50%); } }
      `}} />
    </AppLayout>
  );
}

// Dashboard View Component
function DashboardView({ config, token }) {
  const [analysis, setAnalysis] = useState({});
  const [portfolio, setPortfolio] = useState(null);
  const [segment, setSegment] = useState('EQUITY');
  const [selectedSymbol, setSelectedSymbol] = useState('NIFTY');

  const assetMap = {
    EQUITY: ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK', 'NIFTY', 'BANKNIFTY'],
    COMMODITY: ['GOLD', 'SILVER', 'CRUDEOIL', 'COPPER', 'NATURALGAS'],
    CURRENCY: ['USDINR', 'EURINR', 'GBPINR', 'JPYINR'],
  };

  const symbols = assetMap[segment];

  useEffect(() => {
    setSelectedSymbol(symbols[0]);
  }, [segment]);

  useEffect(() => {
    const headers = { 'Authorization': `Bearer ${token}` };
    const fetchAll = async () => {
      const results = {};
      await Promise.all(symbols.map(async (sym) => {
        let querySym = sym;
        if (segment === 'EQUITY') querySym = sym === 'NIFTY' ? '^NSEI' : sym === 'BANKNIFTY' ? '^NSEBANK' : sym + '.NS';
        if (segment === 'COMMODITY') querySym = sym === 'GOLD' ? 'GC=F' : sym === 'SILVER' ? 'SI=F' : sym === 'CRUDEOIL' ? 'CL=F' : sym + '=F';
        if (segment === 'CURRENCY') querySym = sym + '=X';

        try {
          const res = await fetch(`${API_URL}/api/analyze/${querySym}`, { headers });
          if (res.ok) results[sym] = await res.json();
        } catch (e) {
          console.error(`Failed to fetch ${sym}:`, e);
        }
      }));
      setAnalysis(prev => ({ ...prev, ...results }));
    };

    const fetchPortfolio = async () => {
      try {
        const res = await fetch(`${API_URL}/portfolio`, { headers });
        if (res.ok) setPortfolio(await res.json());
      } catch (e) {}
    };

    fetchAll();
    fetchPortfolio();
    const interval = setInterval(() => { fetchAll(); fetchPortfolio(); }, 60000);
    return () => clearInterval(interval);
  }, [segment, token]);

  const ALL_MODULES = ['technical', 'fundamental', 'options_flow', 'quant', 'news_risk', 'sentiment'];

  const radarData = ALL_MODULES.map(mod => {
    const modData = analysis[selectedSymbol]?.contributions?.[mod];
    return { module: mod, score: modData ? modData.score * 100 : 0 };
  });

  const confidenceData = symbols.map(sym => ({
    name: sym,
    confidence: analysis[sym] ? analysis[sym].analytical_score * 100 : 0
  }));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
      {/* Segment Selector */}
      <div style={{ display: 'flex', gap: 'var(--space-2)', background: 'var(--color-surface-panel)', padding: 'var(--space-2)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--color-surface-border)' }}>
        {Object.keys(assetMap).map(s => (
          <button
            key={s}
            onClick={() => setSegment(s)}
            style={{
              padding: 'var(--space-2) var(--space-4)',
              backgroundColor: segment === s ? 'var(--color-brand-500)' : 'transparent',
              color: segment === s ? 'white' : 'var(--color-text-secondary)',
              border: 'none',
              borderRadius: 'var(--radius-md)',
              cursor: 'pointer',
              fontWeight: segment === s ? 'var(--font-weight-semibold)' : 'var(--font-weight-normal)',
              fontSize: 'var(--font-size-sm)',
              transition: 'all var(--transition-fast)',
            }}
          >
            {s}
          </button>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 'var(--space-4)' }}>
        {/* AI Module Radar */}
        <div style={{ background: 'var(--color-surface-panel)', border: '1px solid var(--color-surface-border)', borderRadius: 'var(--radius-lg)', padding: 'var(--space-4)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-4)' }}>
            <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 'var(--font-weight-semibold)', margin: 0 }}>AI Module Radar</h3>
            <select
              value={selectedSymbol}
              onChange={e => setSelectedSymbol(e.target.value)}
              style={{ padding: 'var(--space-1) var(--space-2)', background: 'var(--color-surface-interactive)', border: '1px solid var(--color-surface-border)', borderRadius: 'var(--radius-md)', color: 'var(--color-text-primary)', fontSize: 'var(--font-size-sm)' }}
            >
              {symbols.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          <div style={{ width: '100%', height: '280px' }}>
            <RadarChartComponent data={radarData} />
          </div>
        </div>

        {/* Watchlist Confidence */}
        <div style={{ background: 'var(--color-surface-panel)', border: '1px solid var(--color-surface-border)', borderRadius: 'var(--radius-lg)', padding: 'var(--space-4)' }}>
          <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 'var(--font-weight-semibold)', marginBottom: 'var(--space-4)' }}>Watchlist Confidence</h3>
          <div style={{ width: '100%', height: '280px' }}>
            <BarChartComponent data={confidenceData} />
          </div>
        </div>
      </div>

      {/* Open Positions & Watchlist Analysis */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: 'var(--space-4)' }}>
        {/* Open Positions */}
        <div style={{ background: 'var(--color-surface-panel)', border: '1px solid var(--color-surface-border)', borderRadius: 'var(--radius-lg)', padding: 'var(--space-4)' }}>
          <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 'var(--font-weight-semibold)', marginBottom: 'var(--space-4)' }}>Open Positions</h3>
          <PositionsTable portfolio={portfolio} />
        </div>

        {/* Watchlist Analysis */}
        <div style={{ background: 'var(--color-surface-panel)', border: '1px solid var(--color-surface-border)', borderRadius: 'var(--radius-lg)', padding: 'var(--space-4)' }}>
          <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 'var(--font-weight-semibold)', marginBottom: 'var(--space-4)' }}>Watchlist Analysis</h3>
          <WatchlistTable analysis={analysis} symbols={symbols} config={config} />
        </div>
      </div>

      {/* P&L Summary */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 'var(--space-4)' }}>
        <div style={{ background: 'var(--color-surface-panel)', border: '1px solid var(--color-surface-border)', borderRadius: 'var(--radius-lg)', padding: 'var(--space-4)' }}>
          <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: 'var(--letter-spacing-wider)', marginBottom: 'var(--space-2)' }}>Unrealized P&L</div>
          <div style={{ fontSize: 'var(--font-size-3xl)', fontWeight: 'var(--font-weight-bold)', color: (portfolio?.pnl?.total_pnl || 0) >= 0 ? 'var(--color-market-buy)' : 'var(--color-market-sell)', fontFamily: 'var(--font-family-mono)' }}>
            {(portfolio?.pnl?.total_pnl || 0) >= 0 ? '+' : ''} ₹ {(portfolio?.pnl?.total_pnl || 0).toLocaleString()}
          </div>
          <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-tertiary)', marginTop: 'var(--space-2)' }}>
            {config?.paper_mode ? 'Paper Trading Mode' : 'Live Mode'}
          </div>
        </div>

        <div style={{ background: 'var(--color-surface-panel)', border: '1px solid var(--color-surface-border)', borderRadius: 'var(--radius-lg)', padding: 'var(--space-4)' }}>
          <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: 'var(--letter-spacing-wider)', marginBottom: 'var(--space-2)' }}>Portfolio Exposure</div>
          <div style={{ fontSize: 'var(--font-size-3xl)', fontWeight: 'var(--font-weight-bold)', marginBottom: 'var(--space-2)' }}>{portfolio?.exposure_pct?.toFixed(1) || 0}%</div>
          <div style={{ width: '100%', height: '8px', background: 'var(--color-surface-interactive)', borderRadius: 'var(--radius-full)', overflow: 'hidden' }}>
            <div style={{ width: `${portfolio?.exposure_pct || 0}%`, height: '100%', background: 'var(--color-brand-500)', borderRadius: 'var(--radius-full)', transition: 'width 0.5s ease' }} />
          </div>
        </div>
      </div>
    </div>
  );
}

// Radar Chart Component
function RadarChartComponent({ data }) {
  return (
    <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--color-text-tertiary)' }}>
      Radar Chart - {data.length} modules
    </div>
  );
}

// Bar Chart Component
function BarChartComponent({ data }) {
  return (
    <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--color-text-tertiary)' }}>
      Bar Chart - {data.length} symbols
    </div>
  );
}

// Positions Table
function PositionsTable({ portfolio }) {
  const positions = portfolio?.open_positions || [];

  if (positions.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: 'var(--space-8)', color: 'var(--color-text-tertiary)' }}>
        No open positions
      </div>
    );
  }

  return (
    <div style={{ overflow: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 'var(--font-size-sm)' }}>
        <thead>
          <tr style={{ borderBottom: '1px solid var(--color-surface-border)', color: 'var(--color-text-secondary)' }}>
            <th style={{ padding: 'var(--space-2)', textAlign: 'left' }}>Symbol</th>
            <th style={{ padding: 'var(--space-2)', textAlign: 'left' }}>Side</th>
            <th style={{ padding: 'var(--space-2)', textAlign: 'right' }}>Qty</th>
            <th style={{ padding: 'var(--space-2)', textAlign: 'right' }}>Entry</th>
            <th style={{ padding: 'var(--space-2)', textAlign: 'right' }}>Current</th>
            <th style={{ padding: 'var(--space-2)', textAlign: 'right' }}>P&L</th>
          </tr>
        </thead>
        <tbody>
          {positions.map((pos, idx) => (
            <tr key={idx} style={{ borderTop: '1px solid var(--color-surface-border)' }}>
              <td style={{ padding: 'var(--space-2)', fontWeight: 'var(--font-weight-semibold)' }}>{pos.symbol}</td>
              <td style={{ padding: 'var(--space-2)', color: pos.action === 'BUY' ? 'var(--color-market-buy)' : 'var(--color-market-sell)' }}>{pos.action}</td>
              <td style={{ padding: 'var(--space-2)', textAlign: 'right', fontFamily: 'var(--font-family-mono)' }}>{pos.qty}</td>
              <td style={{ padding: 'var(--space-2)', textAlign: 'right', fontFamily: 'var(--font-family-mono)' }}>{pos.entry_price?.toFixed(2)}</td>
              <td style={{ padding: 'var(--space-2)', textAlign: 'right', fontFamily: 'var(--font-family-mono)' }}>{pos.ltp?.toFixed(2)}</td>
              <td style={{ padding: 'var(--space-2)', textAlign: 'right', fontFamily: 'var(--font-family-mono)', color: pos.unrealized_pnl >= 0 ? 'var(--color-market-buy)' : 'var(--color-market-sell)', fontWeight: 'var(--font-weight-semibold)' }}>
                {pos.unrealized_pnl >= 0 ? '+' : ''}{pos.unrealized_pnl?.toFixed(2)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// Watchlist Table
function WatchlistTable({ analysis, symbols, config }) {
  return (
    <div style={{ overflow: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 'var(--font-size-sm)' }}>
        <thead>
          <tr style={{ borderBottom: '1px solid var(--color-surface-border)', color: 'var(--color-text-secondary)' }}>
            <th style={{ padding: 'var(--space-2)', textAlign: 'left' }}>Symbol</th>
            <th style={{ padding: 'var(--space-2)', textAlign: 'left' }}>Action</th>
            <th style={{ padding: 'var(--space-2)', textAlign: 'right' }}>Confidence</th>
            <th style={{ padding: 'var(--space-2)', textAlign: 'right' }}>Score</th>
            <th style={{ padding: 'var(--space-2)', textAlign: 'left' }}>Status</th>
          </tr>
        </thead>
        <tbody>
          {symbols.map(sym => {
            const data = analysis[sym];
            if (!data) return <tr key={sym}><td colSpan="5" style={{ padding: 'var(--space-2)' }}>Loading {sym}...</td></tr>;

            let actionColor = 'var(--color-text-secondary)';
            let actionBg = 'var(--color-surface-interactive)';
            if (data.action === "BUY") { actionColor = 'var(--color-market-buy)'; actionBg = 'var(--color-market-buy-bg)'; }
            if (data.action === "SELL") { actionColor = 'var(--color-market-sell)'; actionBg = 'var(--color-market-sell-bg)'; }

            return (
              <tr key={sym} style={{ borderTop: '1px solid var(--color-surface-border)' }}>
                <td style={{ padding: 'var(--space-2)', fontWeight: 'var(--font-weight-semibold)' }}>{data.symbol}</td>
                <td style={{ padding: 'var(--space-2)' }}>
                  <span style={{ padding: '2px 8px', borderRadius: 'var(--radius-sm)', background: actionBg, color: actionColor, fontSize: 'var(--font-size-xs)', fontWeight: 'var(--font-weight-semibold)' }}>
                    {data.action}
                  </span>
                </td>
                <td style={{ padding: 'var(--space-2)', textAlign: 'right', fontFamily: 'var(--font-family-mono)' }}>{(data.overall_confidence * 100).toFixed(1)}%</td>
                <td style={{ padding: 'var(--space-2)', textAlign: 'right', fontFamily: 'var(--font-family-mono)' }}>{data.overall_score.toFixed(2)}</td>
                <td style={{ padding: 'var(--space-2)', fontSize: 'var(--font-size-xs)', color: 'var(--color-text-tertiary)' }}>
                  {data.executed ?
                    <span style={{ color: 'var(--color-market-buy)', fontWeight: 'var(--font-weight-semibold)' }}>Executed</span> :
                    data.risk_check_passed ?
                      <span>Safe to execute</span> :
                      <span style={{ color: 'var(--color-market-sell)' }}>Blocked by Risk</span>
                  }
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// Admin Panel
function AdminPanel({ config, updateConfig }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: 'var(--space-4)' }}>
      <div style={{ background: 'var(--color-surface-panel)', border: '1px solid var(--color-surface-border)', borderRadius: 'var(--radius-lg)', padding: 'var(--space-4)' }}>
        <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 'var(--font-weight-semibold)', marginBottom: 'var(--space-4)' }}>Execution Settings</h3>

        <div style={{ display: 'flex', gap: 'var(--space-2)', marginBottom: 'var(--space-4)' }}>
          <button className="btn" style={{ backgroundColor: config.auto_trade === 'active' ? 'var(--color-market-buy)' : 'var(--color-surface-interactive)', display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }} onClick={() => updateConfig({ auto_trade: 'active' })}>
            <Play size={16} /> Active
          </button>
          <button className="btn" style={{ backgroundColor: config.auto_trade === 'halted' ? 'var(--color-market-sell)' : 'var(--color-surface-interactive)', display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }} onClick={() => updateConfig({ auto_trade: 'halted' })}>
            <Pause size={16} /> Halted
          </button>
          <button className="btn" style={{ backgroundColor: config.auto_trade === 'off' ? 'var(--color-text-tertiary)' : 'var(--color-surface-interactive)', display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }} onClick={() => updateConfig({ auto_trade: 'off' })}>
            <Square size={16} /> Off
          </button>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-4)' }}>
          <div>
            <div style={{ fontWeight: 'var(--font-weight-medium)' }}>Paper Trading Mode</div>
            <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)' }}>Execute trades via mock broker</div>
          </div>
          <label style={{ position: 'relative', width: '44px', height: '24px', display: 'inline-block' }}>
            <input type="checkbox" checked={config.paper_mode} onChange={(e) => updateConfig({ paper_mode: e.target.checked })} style={{ opacity: 0, width: 0, height: 0 }} />
            <span style={{ position: 'absolute', cursor: 'pointer', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: config.paper_mode ? 'var(--color-brand-500)' : '#374151', transition: '.4s', borderRadius: '34px' }} />
          </label>
        </div>

        <div style={{ marginBottom: 'var(--space-4)' }}>
          <label style={{ display: 'block', fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)', marginBottom: 'var(--space-1)' }}>Starting Capital (INR)</label>
          <input type="number" className="form-control" value={config.capital} onChange={(e) => updateConfig({ capital: parseFloat(e.target.value) })} style={{ width: '100%', padding: 'var(--space-2)', background: 'var(--color-surface-interactive)', border: '1px solid var(--color-surface-border)', borderRadius: 'var(--radius-md)', color: 'var(--color-text-primary)' }} />
        </div>
      </div>

      <div style={{ background: 'var(--color-surface-panel)', border: '1px solid var(--color-surface-border)', borderRadius: 'var(--radius-lg)', padding: 'var(--space-4)' }}>
        <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 'var(--font-weight-semibold)', marginBottom: 'var(--space-4)' }}>Risk Limits</h3>

        {[
          { key: 'max_position_pct', label: 'Max Position Size (% of Capital)', value: config.risk?.max_position_pct || 10 },
          { key: 'max_portfolio_exposure_pct', label: 'Max Portfolio Exposure (%)', value: config.risk?.max_portfolio_exposure_pct || 80 },
          { key: 'daily_loss_limit_pct', label: 'Daily Loss Limit (%)', value: config.risk?.daily_loss_limit_pct || 3 },
          { key: 'crash_risk_halt_threshold', label: 'Crash Risk Halt Threshold', value: config.risk?.crash_risk_halt_threshold || 50 },
        ].map(item => (
          <div key={item.key} style={{ marginBottom: 'var(--space-4)' }}>
            <label style={{ display: 'block', fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)', marginBottom: 'var(--space-1)' }}>{item.label}</label>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
              <input type="range" min="1" max="100" value={item.value} style={{ flexGrow: 1 }} readOnly />
              <span>{item.value}%</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}