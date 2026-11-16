import { useState, useEffect, useCallback, useMemo } from 'react';
import { clsx } from '../design-system';
import { Button, Badge, Modal, Switch } from '../components/ui';

// Navigation structure
const NAVIGATION = [
  {
    category: 'Trading',
    icon: '⚡',
    items: [
      { id: 'dashboard', label: 'Dashboard', icon: '📊', component: 'Dashboard' },
      { id: 'command-center', label: 'Command Center', icon: '🎯', component: 'CommandCenter' },
      { id: 'oms', label: 'Order Management', icon: '📋', component: 'OMS' },
      { id: 'positions', label: 'Positions', icon: '📈', component: 'Positions' },
    ],
  },
  {
    category: 'Analysis',
    icon: '🔍',
    items: [
      { id: 'charts', label: 'Advanced Charts', icon: '📉', component: 'AdvancedChart' },
      { id: 'scanner', label: 'Market Scanner', icon: '🔎', component: 'MarketScanner' },
      { id: 'options', label: 'Options Chain', icon: '🎯', component: 'OptionsChain' },
      { id: 'universal', label: 'Universal Screener', icon: '🌐', component: 'UniversalScreener' },
      { id: 'heatmap', label: 'Portfolio Heatmap', icon: '🗺️', component: 'Heatmap' },
    ],
  },
  {
    category: 'Strategy',
    icon: '🧠',
    items: [
      { id: 'strategy-builder', label: 'Strategy Builder', icon: '🔧', component: 'StrategyBuilder' },
      { id: 'backtest', label: 'Backtest Engine', icon: '📊', component: 'BacktestEngine' },
      { id: 'walkforward', label: 'Walk-Forward', icon: '👣', component: 'WalkForward' },
      { id: 'stress-test', label: 'Stress Test', icon: '⚡', component: 'StressTest' },
    ],
  },
  {
    category: 'Risk',
    icon: '🛡️',
    items: [
      { id: 'risk-dashboard', label: 'Risk Dashboard', icon: '📉', component: 'RiskDashboard' },
      { id: 'var', label: 'VaR Analysis', icon: '📐', component: 'VaRAnalysis' },
      { id: 'correlation', label: 'Correlation', icon: '🔗', component: 'Correlation' },
    ],
  },
  {
    category: 'Intelligence',
    icon: '🤖',
    items: [
      { id: 'ai-assistant', label: 'AI Assistant', icon: '🤖', component: 'AIAssistant' },
      { id: 'regime', label: 'Regime Detection', icon: '🌊', component: 'RegimeDetection' },
      { id: 'news', label: 'News & Sentiment', icon: '📰', component: 'NewsSentiment' },
      { id: 'patterns', label: 'Pattern Recognition', icon: '🔍', component: 'PatternRecognition' },
    ],
  },
  {
    category: 'Journal',
    icon: '📓',
    items: [
      { id: 'trade-journal', label: 'Trade Journal', icon: '📝', component: 'TradeJournal' },
      { id: 'psychology', label: 'Psychology', icon: '🧠', component: 'Psychology' },
      { id: 'analytics', label: 'Analytics', icon: '📈', component: 'JournalAnalytics' },
    ],
  },
  {
    category: 'Brokers',
    icon: '🔗',
    items: [
      { id: 'multi-broker', label: 'Multi-Broker', icon: '🔗', component: 'MultiBroker' },
      { id: 'accounts', label: 'Accounts', icon: '👤', component: 'Accounts' },
      { id: 'execution', label: 'Execution Quality', icon: '⚡', component: 'ExecutionQuality' },
    ],
  },
  {
    category: 'System',
    icon: '⚙️',
    items: [
      { id: 'settings', label: 'Settings', icon: '⚙️', component: 'Settings' },
      { id: 'api-keys', label: 'API Keys', icon: '🔑', component: 'ApiKeys' },
      { id: 'notifications', label: 'Notifications', icon: '🔔', component: 'Notifications' },
      { id: 'logs', label: 'System Logs', icon: '📋', component: 'SystemLogs' },
    ],
  },
];

export function AppLayout({
  children,
  token,
  config,
  onLogout,
  onConfigChange,
  className = '',
  style = {},
}) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [activeNav, setActiveNav] = useState('dashboard');
  const [expandedCategories, setExpandedCategories] = useState({});
  const [theme, setTheme] = useState('dark');
  const [notifications, setNotifications] = useState([]);
  const [showNotifications, setShowNotifications] = useState(false);

  // Initialize expanded categories
  useEffect(() => {
    const initial = {};
    NAVIGATION.forEach(cat => { initial[cat.category] = true; });
    setExpandedCategories(initial);
  }, []);

  const toggleCategory = useCallback((category) => {
    setExpandedCategories(prev => ({ ...prev, [category]: !prev[category] }));
  }, []);

  const handleNavClick = useCallback((navId) => {
    setActiveNav(navId);
    // In a real app, this would trigger routing
    console.log('Navigate to:', navId);
  }, []);

  const toggleTheme = useCallback(() => {
    const newTheme = theme === 'dark' ? 'light' : 'dark';
    setTheme(newTheme);
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
  }, [theme]);

  // Load saved theme
  useEffect(() => {
    const saved = localStorage.getItem('theme') || 'dark';
    setTheme(saved);
    document.documentElement.setAttribute('data-theme', saved);
  }, []);

  // Mobile sidebar handling
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth >= 1024) {
        setSidebarOpen(false);
      }
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const isMobile = typeof window !== 'undefined' && window.innerWidth < 1024;

  return (
    <div className={clsx('elco-app-layout', className)} style={{ ...style, minHeight: '100vh', display: 'flex', flexDirection: 'column', background: 'var(--color-surface-base)' }}>
      {/* Top Bar */}
      <header className="elco-topbar" style={{
        height: '56px',
        background: 'var(--color-surface-panel)',
        borderBottom: '1px solid var(--color-surface-border)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 var(--space-4)',
        position: 'sticky',
        top: 0,
        zIndex: 'var(--z-sticky)',
      }}>
        {/* Left - Mobile menu + Brand */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
          {isMobile && (
            <button
              onClick={() => setSidebarOpen(true)}
              style={{ background: 'none', border: 'none', padding: 'var(--space-2)', borderRadius: 'var(--radius-md)', color: 'var(--color-text-secondary)', cursor: 'pointer' }}
              aria-label="Open menu"
            >
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="3" y1="12" x2="21" y2="12" /><line x1="3" y1="6" x2="21" y2="6" /><line x1="3" y1="18" x2="21" y2="18" /></svg>
            </button>
          )}
          <div className="elco-brand" style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
            <div style={{ width: '32px', height: '32px', borderRadius: 'var(--radius-lg)', background: 'var(--color-brand-500)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '16px' }}>📈</div>
            <span style={{ fontWeight: 'var(--font-weight-bold)', fontSize: 'var(--font-size-lg)', color: 'var(--color-text-primary)' }}>
              ELCO <span style={{ color: 'var(--color-brand-500)' }}>TRADER</span>
            </span>
          </div>
        </div>

        {/* Center - Market Status */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4)', flex: 1, justifyContent: 'center' }}>
          <MarketStatusIndicator config={config} />
        </div>

        {/* Right - Actions */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
          {/* Theme Toggle */}
          <button
            onClick={toggleTheme}
            style={{ background: 'var(--color-surface-interactive)', border: '1px solid var(--color-surface-border)', borderRadius: 'var(--radius-md)', padding: 'var(--space-2)', color: 'var(--color-text-secondary)', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
            aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
          >
            {theme === 'dark' ? (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="5" /><line x1="12" y1="1" x2="12" y2="3" /><line x1="12" y1="21" x2="12" y2="23" /><line x1="4.22" y1="4.22" x2="5.64" y2="5.64" /><line x1="18.36" y1="18.36" x2="19.78" y2="19.78" /><line x1="1" y1="12" x2="3" y2="12" /><line x1="21" y1="12" x2="23" y2="12" /><line x1="4.22" y1="19.78" x2="5.64" y2="18.36" /><line x1="18.36" y1="5.64" x2="19.78" y2="4.22" /></svg>
            ) : (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" /></svg>
            )}
          </button>

          {/* Notifications */}
          <button
            onClick={() => setShowNotifications(!showNotifications)}
            style={{ background: 'var(--color-surface-interactive)', border: '1px solid var(--color-surface-border)', borderRadius: 'var(--radius-md)', padding: 'var(--space-2)', color: 'var(--color-text-secondary)', cursor: 'pointer', position: 'relative' }}
            aria-label="Notifications"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" /><path d="M13.73 21a2 2 0 0 1-3.46 0" /></svg>
            {notifications.length > 0 && (
              <span style={{ position: 'absolute', top: '-2px', right: '-2px', background: 'var(--color-market-sell)', color: 'white', fontSize: '10px', fontWeight: 'var(--font-weight-bold)', borderRadius: '9999px', minWidth: '16px', height: '16px', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '0 4px' }}>
                {notifications.length > 9 ? '9+' : notifications.length}
              </span>
            )}
          </button>

          {/* User Menu */}
          <div style={{ position: 'relative' }}>
            <button
              style={{ background: 'var(--color-surface-interactive)', border: '1px solid var(--color-surface-border)', borderRadius: 'var(--radius-md)', padding: 'var(--space-2) var(--space-3)', display: 'flex', alignItems: 'center', gap: 'var(--space-2)', cursor: 'pointer' }}
            >
              <div style={{ width: '32px', height: '32px', borderRadius: '50%', background: 'var(--color-brand-500)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white', fontWeight: 'var(--font-weight-bold)' }}>
                U
              </div>
              <span style={{ fontSize: 'var(--font-size-sm)', fontWeight: 'var(--font-weight-medium)' }}>User</span>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="6 9 12 15 18 9" /></svg>
            </button>
          </div>

          {/* Sidebar Toggle (Desktop) */}
          {!isMobile && (
            <button
              onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
              style={{ background: 'var(--color-surface-interactive)', border: '1px solid var(--color-surface-border)', borderRadius: 'var(--radius-md)', padding: 'var(--space-2)', color: 'var(--color-text-secondary)', cursor: 'pointer' }}
              aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                {sidebarCollapsed ? <polyline points="9 18 15 12 9 6" /> : <polyline points="15 18 9 12 15 6" />}
              </svg>
            </button>
          )}
        </div>
      </header>

      {/* Mobile Sidebar Overlay */}
      {isMobile && sidebarOpen && (
        <div
          className="elco-mobile-overlay"
          onClick={() => setSidebarOpen(false)}
          style={{ position: 'fixed', inset: 0, background: 'var(--color-surface-overlay)', zIndex: 'var(--z-overlay)' }}
        />
      )}

      {/* Main Content Area */}
      <div className="elco-main" style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* Sidebar */}
        <aside
          className={clsx('elco-sidebar', sidebarCollapsed && 'collapsed', isMobile && sidebarOpen && 'open')}
          style={{
            width: sidebarCollapsed ? '72px' : '280px',
            minWidth: sidebarCollapsed ? '72px' : '280px',
            maxWidth: sidebarCollapsed ? '72px' : '280px',
            background: 'var(--color-surface-panel)',
            borderRight: '1px solid var(--color-surface-border)',
            display: 'flex',
            flexDirection: 'column',
            transition: 'width var(--transition-fast), min-width var(--transition-fast), max-width var(--transition-fast)',
            zIndex: isMobile ? 'var(--z-modal)' : 'var(--z-sticky)',
            overflowY: 'auto',
          }}
        >
          {!sidebarCollapsed && (
            <div style={{ padding: 'var(--space-4)', borderBottom: '1px solid var(--color-surface-border)' }}>
              <div style={{ fontSize: 'var(--font-size-xs)', fontWeight: 'var(--font-weight-semibold)', color: 'var(--color-text-tertiary)', textTransform: 'uppercase', letterSpacing: 'var(--letter-spacing-wider)', marginBottom: 'var(--space-3)' }}>
                NAVIGATION
              </div>
              {NAVIGATION.map(category => (
                <NavCategory
                  key={category.category}
                  category={category}
                  expanded={expandedCategories[category.category]}
                  activeNav={activeNav}
                  onToggle={() => toggleCategory(category.category)}
                  onNavClick={handleNavClick}
                />
              ))}
            </div>
          )}

          {sidebarCollapsed && (
            <div style={{ padding: 'var(--space-3)', display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
              {NAVIGATION.flatMap(category => category.items).map(item => (
                <button
                  key={item.id}
                  onClick={() => handleNavClick(item.id)}
                  className={clsx('elco-nav-icon', activeNav === item.id && 'active')}
                  style={{
                    padding: 'var(--space-3)',
                    borderRadius: 'var(--radius-md)',
                    background: activeNav === item.id ? 'var(--color-brand-100)' : 'transparent',
                    border: 'none',
                    color: activeNav === item.id ? 'var(--color-brand-500)' : 'var(--color-text-secondary)',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    transition: 'all var(--transition-fast)',
                  }}
                  title={item.label}
                >
                  <span style={{ fontSize: '20px' }}>{item.icon}</span>
                </button>
              ))}
            </div>
          )}

          {/* Bottom - System Status */}
          <div style={{ marginTop: 'auto', padding: 'var(--space-4)', borderTop: '1px solid var(--color-surface-border)' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)' }}>
              <span>System</span>
              <Badge
                variant={config?.auto_trade === 'active' ? 'success' : config?.auto_trade === 'halted' ? 'danger' : 'default'}
                dot
                size="sm"
              >
                {config?.auto_trade?.toUpperCase() || 'OFF'}
              </Badge>
            </div>
            <Button variant="ghost" size="sm" onClick={onLogout} fullWidth style={{ marginTop: 'var(--space-3)' }}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" /><polyline points="16 17 21 12 16 7" /><line x1="21" y1="12" x2="9" y2="12" /></svg>
              {sidebarCollapsed ? '' : ' Logout'}
            </Button>
          </div>
        </aside>

        {/* Main Content */}
        <main className="elco-content" style={{ flex: 1, overflow: 'auto', background: 'var(--color-surface-base)' }}>
          {children}
        </main>
      </div>

      {/* Notifications Dropdown */}
      {showNotifications && (
        <div
          className="elco-notifications-dropdown"
          style={{
            position: 'fixed',
            top: '64px',
            right: 'var(--space-4)',
            width: '360px',
            maxHeight: '400px',
            background: 'var(--color-surface-panel)',
            border: '1px solid var(--color-surface-border)',
            borderRadius: 'var(--radius-lg)',
            boxShadow: 'var(--shadow-xl)',
            zIndex: 'var(--z-dropdown)',
            overflow: 'hidden',
          }}
        >
          <div style={{ padding: 'var(--space-3) var(--space-4)', borderBottom: '1px solid var(--color-surface-border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 'var(--font-weight-semibold)', margin: 0 }}>Notifications</h3>
            <Button variant="ghost" size="sm" onClick={() => setNotifications([])}>Clear All</Button>
          </div>
          <div style={{ maxHeight: '340px', overflow: 'auto' }}>
            {notifications.length === 0 ? (
              <div style={{ padding: 'var(--space-8)', textAlign: 'center', color: 'var(--color-text-tertiary)' }}>No notifications</div>
            ) : (
              notifications.map((notif, i) => (
                <div key={i} style={{ padding: 'var(--space-3) var(--space-4)', borderBottom: '1px solid var(--color-surface-border)', display: 'flex', gap: 'var(--space-3)' }}>
                  <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: notif.read ? 'var(--color-text-tertiary)' : 'var(--color-brand-500)', marginTop: '6px', flexShrink: 0 }} />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 'var(--font-weight-medium)', fontSize: 'var(--font-size-sm)' }}>{notif.title}</div>
                    <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-tertiary)', marginTop: 'var(--space-1)' }}>{notif.message}</div>
                    <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-tertiary)', marginTop: 'var(--space-1)' }}>{formatters.timeOnly(notif.timestamp)}</div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function NavCategory({ category, expanded, activeNav, onToggle, onNavClick }) {
  return (
    <div style={{ marginBottom: 'var(--space-1)' }}>
      <button
        onClick={onToggle}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: 'var(--space-2) var(--space-3)',
          background: 'transparent',
          border: 'none',
          color: 'var(--color-text-secondary)',
          fontSize: 'var(--font-size-xs)',
          fontWeight: 'var(--font-weight-semibold)',
          textTransform: 'uppercase',
          letterSpacing: 'var(--letter-spacing-wider)',
          cursor: 'pointer',
          textAlign: 'left',
          borderRadius: 'var(--radius-md)',
          transition: 'all var(--transition-fast)',
        }}
        onMouseEnter={(e) => e.target.style.background = 'var(--color-surface-interactive)'}
        onMouseLeave={(e) => e.target.style.background = 'transparent'}
      >
        <span style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
          <span>{category.icon}</span>
          <span>{category.category}</span>
        </span>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ transition: 'transform var(--transition-fast)', transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)' }}>
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>
      {expanded && (
        <div style={{ paddingLeft: 'var(--space-2)', marginTop: 'var(--space-1)', borderLeft: '2px solid var(--color-surface-border)' }}>
          {category.items.map(item => (
            <button
              key={item.id}
              onClick={() => onNavClick(item.id)}
              style={{
                width: '100%',
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--space-2)',
                padding: 'var(--space-2) var(--space-3)',
                background: activeNav === item.id ? 'var(--color-brand-100)' : 'transparent',
                border: 'none',
                color: activeNav === item.id ? 'var(--color-brand-500)' : 'var(--color-text-secondary)',
                fontSize: 'var(--font-size-sm)',
                fontWeight: activeNav === item.id ? 'var(--font-weight-medium)' : 'var(--font-weight-normal)',
                cursor: 'pointer',
                textAlign: 'left',
                borderRadius: 'var(--radius-md)',
                transition: 'all var(--transition-fast)',
              }}
              onMouseEnter={(e) => { if (activeNav !== item.id) e.target.style.background = 'var(--color-surface-interactive)'; }}
              onMouseLeave={(e) => { if (activeNav !== item.id) e.target.style.background = 'transparent'; }}
            >
              <span style={{ fontSize: '16px' }}>{item.icon}</span>
              <span>{item.label}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function MarketStatusIndicator({ config }) {
  const isMarketOpen = () => {
    const now = new Date();
    const day = now.getDay();
    const hours = now.getHours();
    const minutes = now.getMinutes();
    const timeInMinutes = hours * 60 + minutes;
    if (day === 0 || day === 6) return false;
    const marketOpen = 9 * 60 + 15;
    const marketClose = 15 * 60 + 30;
    return timeInMinutes >= marketOpen && timeInMinutes <= marketClose;
  };

  const open = isMarketOpen();

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', fontSize: 'var(--font-size-sm)' }}>
      <Badge variant={open ? 'success' : 'default'} dot size="sm">
        {open ? 'MARKET OPEN' : 'MARKET CLOSED'}
      </Badge>
      {config && (
        <span style={{ color: 'var(--color-text-secondary)' }}>
          Capital: {formatters.price(config.capital || 0)}
        </span>
      )}
    </div>
  );
}

function formatters() {
  return {
    price: (value) => {
      if (value === null || value === undefined || isNaN(value)) return '—';
      return new Intl.NumberFormat('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(value);
    },
    timeOnly: (timestamp) => {
      if (!timestamp) return '—';
      const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp;
      return date.toLocaleTimeString('en-IN', { hour12: false, hour: '2-digit', minute: '2-digit' });
    },
  };
}

export default AppLayout;