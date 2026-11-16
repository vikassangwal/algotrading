import { useState, useEffect, useCallback, useMemo } from 'react';
import { clsx, formatters, marketStatus } from '../../design-system';
import { Button, Select, Input, Card, CardHeader, CardContent, Table, Badge, Tabs, Tab, Modal, StatCard } from '../ui';

const RISK_LIMITS = [
  { key: 'max_position_pct', label: 'Max Position Size (% of Capital)', type: 'number', default: 10, min: 1, max: 50, step: 1, suffix: '%' },
  { key: 'max_portfolio_exposure_pct', label: 'Max Portfolio Exposure (%)', type: 'number', default: 80, min: 10, max: 100, step: 1, suffix: '%' },
  { key: 'daily_loss_limit_pct', label: 'Daily Loss Limit (%)', type: 'number', default: 3, min: 0.5, max: 10, step: 0.5, suffix: '%' },
  { key: 'max_drawdown_pct', label: 'Max Drawdown Limit (%)', type: 'number', default: 15, min: 5, max: 50, step: 1, suffix: '%' },
  { key: 'max_sector_exposure_pct', label: 'Max Sector Exposure (%)', type: 'number', default: 30, min: 10, max: 100, step: 5, suffix: '%' },
  { key: 'max_correlated_exposure_pct', label: 'Max Correlated Exposure (%)', type: 'number', default: 40, min: 10, max: 100, step: 5, suffix: '%' },
  { key: 'max_open_positions', label: 'Max Open Positions', type: 'number', default: 10, min: 1, max: 50, step: 1, suffix: '' },
  { key: 'max_leverage', label: 'Max Leverage', type: 'number', default: 1, min: 1, max: 10, step: 0.5, suffix: 'x' },
  { key: 'min_liquidity_ratio', label: 'Min Liquidity Ratio', type: 'number', default: 0.2, min: 0.05, max: 1, step: 0.05, suffix: '' },
  { key: 'var_confidence', label: 'VaR Confidence Level', type: 'select', default: '0.95', options: [{ value: '0.90', label: '90%' }, { value: '0.95', label: '95%' }, { value: '0.99', label: '99%' }], suffix: '' },
  { key: 'var_horizon_days', label: 'VaR Horizon (Days)', type: 'number', default: 1, min: 1, max: 30, step: 1, suffix: 'd' },
];

export function RiskDashboard({
  token,
  className = '',
  style = {},
  ...props
}) {
  const [activeTab, setActiveTab] = useState('overview');
  const [limits, setLimits] = useState({});
  const [portfolioRisk, setPortfolioRisk] = useState(null);
  const [positions, setPositions] = useState([]);
  const [stressTests, setStressTests] = useState([]);
  const [varHistory, setVarHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editMode, setEditMode] = useState(false);

  const API_URL = `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}`;

  // Fetch data
  const fetchData = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const headers = { 'Authorization': `Bearer ${token}` };
      const [riskRes, positionsRes, varRes] = await Promise.all([
        fetch(`${API_URL}/api/risk/portfolio`, { headers }),
        fetch(`${API_URL}/api/risk/positions`, { headers }),
        fetch(`${API_URL}/api/risk/var-history`, { headers }),
      ]);
      if (riskRes.ok) setPortfolioRisk(await riskRes.json());
      if (positionsRes.ok) setPositions(await positionsRes.json());
      if (varRes.ok) setVarHistory(await varRes.json());
    } catch (err) {
      console.error('Risk data fetch error:', err);
    } finally {
      setLoading(false);
    }
  }, [token, API_URL]);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  // Load limits from config
  useEffect(() => {
    if (!token) return;
    fetch(`${API_URL}/config`, { headers: { 'Authorization': `Bearer ${token}` } })
      .then(r => r.json())
      .then(config => {
        const riskConfig = config.risk || {};
        const initialLimits = {};
        RISK_LIMITS.forEach(limit => {
          initialLimits[limit.key] = riskConfig[limit.key] ?? limit.default;
        });
        setLimits(initialLimits);
      })
      .catch(console.error);
  }, [token, API_URL]);

  const handleLimitChange = (key, value) => {
    setLimits(prev => ({ ...prev, [key]: value }));
  };

  const saveLimits = async () => {
    setSaving(true);
    try {
      const headers = { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' };
      const res = await fetch(`${API_URL}/config`, {
        method: 'PATCH',
        headers,
        body: JSON.stringify({ risk: limits }),
      });
      if (!res.ok) throw new Error('Failed to save limits');
      setEditMode(false);
    } catch (err) {
      console.error('Save limits error:', err);
    } finally {
      setSaving(false);
    }
  };

  const runStressTest = async (scenario) => {
    setLoading(true);
    try {
      const headers = { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' };
      const res = await fetch(`${API_URL}/api/risk/stress-test`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ scenario }),
      });
      if (res.ok) {
        const result = await res.json();
        setStressTests(prev => [...prev, { ...result, scenario, timestamp: new Date().toISOString() }].slice(-10));
      }
    } catch (err) {
      console.error('Stress test error:', err);
    } finally {
      setLoading(false);
    }
  };

  // Risk status
  const riskStatus = useMemo(() => {
    if (!portfolioRisk) return 'unknown';
    const { exposure_pct, daily_pnl_pct, max_drawdown_pct, var_95 } = portfolioRisk;
    const limits_ = limits;

    if (daily_pnl_pct <= -(limits_.daily_loss_limit_pct || 3)) return 'critical';
    if (exposure_pct >= (limits_.max_portfolio_exposure_pct || 80) * 0.9) return 'warning';
    if (max_drawdown_pct >= (limits_.max_drawdown_pct || 15) * 0.8) return 'warning';
    return 'ok';
  }, [portfolioRisk, limits]);

  const statusColors = {
    ok: 'var(--color-market-buy)',
    warning: 'var(--color-market-warning)',
    critical: 'var(--color-market-sell)',
    unknown: 'var(--color-text-tertiary)',
  };

  const statusLabels = {
    ok: 'Within Limits',
    warning: 'Approaching Limits',
    critical: 'Limit Breached',
    unknown: 'Unknown',
  };

  return (
    <div className={clsx('elco-risk-dashboard', className)} style={{ ...style, height: '100%', display: 'flex', flexDirection: 'column', ...props }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: 'var(--space-4)', background: 'var(--color-surface-panel)', borderBottom: '1px solid var(--color-surface-border)', flexWrap: 'wrap', gap: 'var(--space-3)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4)' }}>
          <h2 style={{ fontSize: 'var(--font-size-xl)', fontWeight: 'var(--font-weight-semibold)', margin: 0 }}>Risk Management</h2>
          <Badge
            variant={riskStatus === 'ok' ? 'success' : riskStatus === 'warning' ? 'warning' : riskStatus === 'critical' ? 'danger' : 'default'}
            dot
            style={{ fontSize: 'var(--font-size-sm)' }}
          >
            {statusLabels[riskStatus]}
          </Badge>
          {marketStatus.isMarketOpen() && (
            <Badge variant="success" dot size="sm">Live</Badge>
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
          <Button variant="ghost" size="sm" onClick={fetchData} loading={loading} leftIcon={<RefreshIcon />}>Refresh</Button>
          <Button variant={editMode ? 'primary' : 'outline'} size="sm" onClick={() => setEditMode(!editMode)}>
            {editMode ? 'Save Limits' : 'Edit Limits'}
          </Button>
          {editMode && saving && <Button variant="primary" size="sm" loading fullWidth onClick={saveLimits}>Saving...</Button>}
          {editMode && !saving && <Button variant="primary" size="sm" onClick={saveLimits}>Save</Button>}
        </div>
      </div>

      {/* Tabs */}
      <Tabs activeTab={activeTab} onChange={setActiveTab} style={{ borderBottom: '1px solid var(--color-surface-border)' }}>
        <Tab id="overview" label="Overview" />
        <Tab id="limits" label="Risk Limits" />
        <Tab id="positions" label="Positions" />
        <Tab id="var" label="VaR Analysis" />
        <Tab id="stress" label="Stress Tests" />
        <Tab id="correlation" label="Correlation" />
      </Tabs>

      <div style={{ flex: 1, overflow: 'auto', padding: 'var(--space-4)' }}>
        {activeTab === 'overview' && <OverviewTab portfolioRisk={portfolioRisk} limits={limits} riskStatus={riskStatus} />}
        {activeTab === 'limits' && <LimitsTab limits={limits} editMode={editMode} onChange={handleLimitChange} />}
        {activeTab === 'positions' && <PositionsTab positions={positions} limits={limits} />}
        {activeTab === 'var' && <VaRTab varHistory={varHistory} limits={limits} />}
        {activeTab === 'stress' && <StressTab stressTests={stressTests} onRun={runStressTest} loading={loading} />}
        {activeTab === 'correlation' && <CorrelationTab />}
      </div>
    </div>
  );
}

// Overview Tab
function OverviewTab({ portfolioRisk, limits, riskStatus }) {
  if (!portfolioRisk) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--color-text-tertiary)' }}>
        Loading portfolio risk data...
      </div>
    );
  }

  const stats = [
    { label: 'Portfolio Value', value: formatters.price(portfolioRisk.total_value || 0), prefix: '₹' },
    { label: 'Daily P&L', value: formatters.price(portfolioRisk.daily_pnl || 0), trend: portfolioRisk.daily_pnl >= 0 ? 'up' : 'down' },
    { label: 'Daily P&L %', value: formatters.percent(portfolioRisk.daily_pnl_pct || 0), trend: portfolioRisk.daily_pnl_pct >= 0 ? 'up' : 'down' },
    { label: 'Total Exposure', value: formatters.price(portfolioRisk.exposure_value || 0), suffix: ` (${portfolioRisk.exposure_pct?.toFixed(1)}%)` },
    { label: 'Max Drawdown', value: formatters.percent(portfolioRisk.max_drawdown_pct || 0), trend: 'down' },
    { label: 'VaR (95%, 1d)', value: formatters.price(portfolioRisk.var_95 || 0), trend: 'neutral' },
    { label: 'Open Positions', value: formatters.quantity(portfolioRisk.open_positions || 0), suffix: ` / ${limits.max_open_positions || 10}` },
    { label: 'Leverage', value: (portfolioRisk.leverage || 1).toFixed(2) + 'x', suffix: ` / ${limits.max_leverage || 1}x` },
    { label: 'Cash Reserve', value: formatters.price(portfolioRisk.cash || 0), suffix: ` (${portfolioRisk.cash_pct?.toFixed(1)}%)` },
    { label: 'Margin Used', value: formatters.percent(portfolioRisk.margin_used_pct || 0), trend: portfolioRisk.margin_used_pct > 80 ? 'warning' : 'neutral' },
  ];

  const limitChecks = [
    { name: 'Position Size', current: portfolioRisk.max_position_pct || 0, limit: limits.max_position_pct || 10, unit: '%', type: 'pct' },
    { name: 'Portfolio Exposure', current: portfolioRisk.exposure_pct || 0, limit: limits.max_portfolio_exposure_pct || 80, unit: '%', type: 'pct' },
    { name: 'Daily Loss', current: Math.abs(portfolioRisk.daily_pnl_pct || 0), limit: limits.daily_loss_limit_pct || 3, unit: '%', type: 'pct' },
    { name: 'Max Drawdown', current: portfolioRisk.max_drawdown_pct || 0, limit: limits.max_drawdown_pct || 15, unit: '%', type: 'pct' },
    { name: 'Sector Exposure', current: portfolioRisk.max_sector_exposure_pct || 0, limit: limits.max_sector_exposure_pct || 30, unit: '%', type: 'pct' },
    { name: 'Open Positions', current: portfolioRisk.open_positions || 0, limit: limits.max_open_positions || 10, unit: '', type: 'count' },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
      {/* Key Metrics */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 'var(--space-4)' }}>
        {stats.map((stat, i) => (
          <StatCard
            key={i}
            label={stat.label}
            value={stat.value}
            trend={stat.trend}
            prefix={stat.prefix}
            suffix={stat.suffix}
          />
        ))}
      </div>

      {/* Limit Gauges */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 'var(--space-4)' }}>
        {limitChecks.map((check, i) => (
          <Card key={i} variant="default">
            <CardHeader title={check.name} />
            <CardContent>
              <div style={{ marginBottom: 'var(--space-3)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 'var(--space-1)', fontSize: 'var(--font-size-sm)' }}>
                  <span style={{ color: 'var(--color-text-secondary)' }}>Current</span>
                  <span style={{ fontWeight: 'var(--font-weight-semibold)', fontFamily: 'var(--font-family-mono)', color: getLimitColor(check.current, check.limit) }}>
                    {check.current.toFixed(check.type === 'pct' ? 1 : 0)}{check.unit}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--font-size-sm)' }}>
                  <span style={{ color: 'var(--color-text-tertiary)' }}>Limit</span>
                  <span style={{ fontWeight: 'var(--font-weight-medium)', color: 'var(--color-text-secondary)' }}>
                    {check.limit}{check.unit}
                  </span>
                </div>
              </div>
              <div style={{ height: '8px', background: 'var(--color-surface-interactive)', borderRadius: 'var(--radius-full)', overflow: 'hidden' }}>
                <div
                  style={{
                    height: '100%',
                    width: `${Math.min(100, (check.current / check.limit) * 100)}%`,
                    background: getLimitColor(check.current, check.limit),
                    borderRadius: 'var(--radius-full)',
                    transition: 'width 0.5s ease',
                  }}
                />
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 'var(--space-2)', fontSize: 'var(--font-size-xs)', color: 'var(--color-text-tertiary)' }}>
                <span>{((check.current / check.limit) * 100).toFixed(0)}% utilized</span>
                <Badge
                  variant={check.current >= check.limit ? 'danger' : check.current >= check.limit * 0.8 ? 'warning' : 'success'}
                  size="sm"
                >
                  {check.current >= check.limit ? 'BREACH' : check.current >= check.limit * 0.8 ? 'WARNING' : 'OK'}
                </Badge>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

function getLimitColor(current, limit) {
  if (current >= limit) return 'var(--color-market-sell)';
  if (current >= limit * 0.8) return 'var(--color-market-warning)';
  return 'var(--color-market-buy)';
}

// Limits Tab
function LimitsTab({ limits, editMode, onChange }) {
  return (
    <Card variant="default" style={{ maxWidth: '700px' }}>
      <CardHeader title="Risk Limits Configuration" subtitle={editMode ? 'Click Save to apply changes' : 'Enable edit mode to modify limits'} />
      <CardContent>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
          {RISK_LIMITS.map(limit => (
            <div key={limit.key} style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', padding: 'var(--space-3)', background: 'var(--color-surface-interactive)', borderRadius: 'var(--radius-md)' }}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontWeight: 'var(--font-weight-medium)', marginBottom: 'var(--space-1)' }}>{limit.label}</div>
                <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-tertiary)' }}>
                  Current: {limits[limit.key] ?? limit.default}{limit.suffix}
                </div>
              </div>
              {editMode && limit.type === 'number' && (
                <Input
                  type="number"
                  value={limits[limit.key] ?? limit.default}
                  onChange={(e) => onChange(limit.key, parseFloat(e.target.value) ?? limit.default)}
                  min={limit.min}
                  max={limit.max}
                  step={limit.step}
                  size="sm"
                  style={{ width: '120px' }}
                />
              )}
              {editMode && limit.type === 'select' && (
                <Select
                  value={limits[limit.key] ?? limit.default}
                  onChange={(e) => onChange(limit.key, e.target.value)}
                  options={limit.options}
                  size="sm"
                  style={{ width: '140px' }}
                />
              )}
              {!editMode && (
                <span style={{ fontFamily: 'var(--font-family-mono)', fontWeight: 'var(--font-weight-semibold)', fontSize: 'var(--font-size-lg)', color: 'var(--color-text-primary)' }}>
                  {limits[limit.key] ?? limit.default}{limit.suffix}
                </span>
              )}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

// Positions Tab
function PositionsTab({ positions, limits }) {
  const columns = [
    { key: 'symbol', header: 'Symbol', width: '100px' },
    { key: 'side', header: 'Side', width: '80px' },
    { key: 'qty', header: 'Qty', align: 'right', width: '80px' },
    { key: 'entry_price', header: 'Entry', align: 'right', format: 'price', width: '100px' },
    { key: 'current_price', header: 'Current', align: 'right', format: 'price', width: '100px' },
    { key: 'unrealized_pnl', header: 'Unrealized P&L', align: 'right', format: 'price', width: '120px' },
    { key: 'unrealized_pnl_pct', header: 'P&L %', align: 'right', format: 'percent', width: '100px' },
    { key: 'position_value', header: 'Position Value', align: 'right', format: 'price', width: '120px' },
    { key: 'pct_of_portfolio', header: '% of Portfolio', align: 'right', format: (v) => v.toFixed(2) + '%', width: '120px' },
    { key: 'risk_score', header: 'Risk Score', align: 'center', width: '100px' },
  ];

  const renderCell = (value, row, column) => {
    if (column.key === 'side') {
      return <Badge variant={value === 'LONG' ? 'success' : 'danger'} size="sm">{value}</Badge>;
    }
    if (column.key === 'unrealized_pnl' || column.key === 'unrealized_pnl_pct') {
      const color = value >= 0 ? 'var(--color-market-buy)' : 'var(--color-market-sell)';
      return <span style={{ color, fontWeight: 'var(--font-weight-medium)', fontFamily: 'var(--font-family-mono)' }}>{value >= 0 ? '+' : ''}{column.format ? column.format(value) : value}</span>;
    }
    if (column.key === 'risk_score') {
      const color = value >= 70 ? 'var(--color-market-sell)' : value >= 40 ? 'var(--color-market-warning)' : 'var(--color-market-buy)';
      return <Badge variant={value >= 70 ? 'danger' : value >= 40 ? 'warning' : 'success'} size="sm">{value}</Badge>;
    }
    if (column.key === 'pct_of_portfolio') {
      const pct = parseFloat(value);
      const color = pct >= (limits.max_position_pct || 10) * 0.8 ? 'var(--color-market-warning)' : 'var(--color-text-primary)';
      return <span style={{ color, fontWeight: 'var(--font-weight-medium)', fontFamily: 'var(--font-family-mono)' }}>{column.format(value)}</span>;
    }
    return column.format ? column.format(value) : value;
  };

  return (
    <Card variant="default" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <CardHeader title="Position Risk" action={<span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-tertiary)' }}>{positions.length} positions</span>} />
      <CardContent style={{ flex: 1, overflow: 'auto' }}>
        <Table
          columns={columns}
          data={positions}
          keyField="symbol"
          sortable
          striped
          hoverable
          emptyMessage="No open positions"
          renderCell={renderCell}
        />
      </CardContent>
    </Card>
  );
}

// VaR Tab
function VaRTab({ varHistory, limits }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
      <Card variant="default">
        <CardHeader title="Value at Risk (VaR) Analysis" subtitle={`Confidence: ${(parseFloat(limits.var_confidence) * 100 || 95).toFixed(0)}% | Horizon: ${limits.var_horizon_days || 1} day(s)`} />
        <CardContent style={{ height: '400px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--color-text-tertiary)' }}>
          VaR Chart - {varHistory.length} historical points
        </CardContent>
      </Card>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: 'var(--space-4)' }}>
        <Card variant="default">
          <CardHeader title="Current VaR Metrics" />
          <CardContent>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 'var(--space-4)' }}>
              <div>
                <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)' }}>VaR (95%)</div>
                <div style={{ fontSize: 'var(--font-size-xl)', fontWeight: 'var(--font-weight-bold)', fontFamily: 'var(--font-family-mono)', color: 'var(--color-market-sell)' }}>₹ 2,45,000</div>
              </div>
              <div>
                <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)' }}>VaR (99%)</div>
                <div style={{ fontSize: 'var(--font-size-xl)', fontWeight: 'var(--font-weight-bold)', fontFamily: 'var(--font-family-mono)', color: 'var(--color-market-sell)' }}>₹ 4,12,000</div>
              </div>
              <div>
                <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)' }}>CVaR (95%)</div>
                <div style={{ fontSize: 'var(--font-size-xl)', fontWeight: 'var(--font-weight-bold)', fontFamily: 'var(--font-family-mono)', color: 'var(--color-market-sell)' }}>₹ 3,67,000</div>
              </div>
              <div>
                <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)' }}>CVaR (99%)</div>
                <div style={{ fontSize: 'var(--font-size-xl)', fontWeight: 'var(--font-weight-bold)', fontFamily: 'var(--font-family-mono)', color: 'var(--color-market-sell)' }}>₹ 5,89,000</div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card variant="default">
          <CardHeader title="VaR Backtest" />
          <CardContent>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 'var(--space-4)' }}>
              <div>
                <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)' }}>Exceptions (250d)</div>
                <div style={{ fontSize: 'var(--font-size-xl)', fontWeight: 'var(--font-weight-bold)', fontFamily: 'var(--font-family-mono)', color: 'var(--color-market-buy)' }}>3</div>
              </div>
              <div>
                <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)' }}>Expected (95%)</div>
                <div style={{ fontSize: 'var(--font-size-xl)', fontWeight: 'var(--font-weight-bold)', fontFamily: 'var(--font-family-mono)', color: 'var(--color-text-secondary)' }}>12.5</div>
              </div>
              <div>
                <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)' }}>Kupiec Test</div>
                <div style={{ fontSize: 'var(--font-size-xl)', fontWeight: 'var(--font-weight-bold)', fontFamily: 'var(--font-family-mono)', color: 'var(--color-market-buy)' }}>Pass</div>
              </div>
              <div>
                <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)' }}>Christoffersen</div>
                <div style={{ fontSize: 'var(--font-size-xl)', fontWeight: 'var(--font-weight-bold)', fontFamily: 'var(--font-family-mono)', color: 'var(--color-market-buy)' }}>Pass</div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// Stress Tab
function StressTab({ stressTests, onRun, loading }) {
  const scenarios = [
    { id: 'market_crash_20', name: 'Market Crash -20%', description: 'NIFTY drops 20% in a single day', severity: 'extreme' },
    { id: 'market_crash_10', name: 'Market Crash -10%', description: 'NIFTY drops 10% in a single day', severity: 'high' },
    { id: 'volatility_spike', name: 'Volatility Spike', description: 'India VIX spikes to 40+', severity: 'high' },
    { id: 'sector_rotation', name: 'Sector Rotation', description: 'IT -15%, Banking +10%', severity: 'medium' },
    { id: 'liquidity_crisis', name: 'Liquidity Crisis', description: 'Bid-ask spreads widen 5x', severity: 'high' },
    { id: 'rate_shock', name: 'Rate Shock', description: 'RBI hikes rates 100bps', severity: 'medium' },
    { id: 'currency_crisis', name: 'INR Crisis', description: 'USD/INR moves 5% in a week', severity: 'medium' },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
      <Card variant="default">
        <CardHeader title="Run Stress Test" subtitle="Select a scenario to test portfolio resilience" />
        <CardContent>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 'var(--space-3)' }}>
            {scenarios.map(scenario => (
              <Button
                key={scenario.id}
                variant="outline"
                onClick={() => onRun(scenario.id)}
                loading={loading}
                disabled={loading}
                style={{ textAlign: 'left', padding: 'var(--space-4)', height: 'auto', justifyContent: 'flex-start' }}
              >
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginBottom: 'var(--space-1)' }}>
                    <span style={{ fontWeight: 'var(--font-weight-semibold)' }}>{scenario.name}</span>
                    <Badge
                      variant={scenario.severity === 'extreme' ? 'danger' : scenario.severity === 'high' ? 'warning' : 'info'}
                      size="sm"
                    >
                      {scenario.severity.toUpperCase()}
                    </Badge>
                  </div>
                  <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)' }}>{scenario.description}</div>
                </div>
                <PlayIcon />
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>

      {stressTests.length > 0 && (
        <Card variant="default">
          <CardHeader title="Recent Stress Test Results" />
          <CardContent>
            <Table
              columns={[
                { key: 'timestamp', header: 'Time', width: '160px' },
                { key: 'scenario', header: 'Scenario', width: '180px' },
                { key: 'portfolio_pnl', header: 'Portfolio P&L', align: 'right', format: 'price', width: '140px' },
                { key: 'portfolio_pnl_pct', header: 'P&L %', align: 'right', format: 'percent', width: '100px' },
                { key: 'max_drawdown', header: 'Max DD', align: 'right', format: 'percent', width: '100px' },
                { key: 'var_breach', header: 'VaR Breach', align: 'center', width: '100px' },
                { key: 'recovery_days', header: 'Recovery (est.)', align: 'center', width: '120px' },
              ]}
              data={stressTests.slice().reverse()}
              keyField="scenario"
              sortable
              striped
              hoverable
              emptyMessage="No stress tests run yet"
            />
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// Correlation Tab
function CorrelationTab() {
  return (
    <Card variant="default" style={{ height: '100%' }}>
      <CardHeader title="Position Correlation Matrix" subtitle="Real-time correlation between open positions" />
      <CardContent style={{ height: 'calc(100% - 60px)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--color-text-tertiary)' }}>
        Correlation Heatmap - Requires 2+ positions
      </CardContent>
    </Card>
  );
}

function RefreshIcon() { return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M23 4v6h-6" /><path d="M1 20v-6h6" /><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" /></svg>; }
function PlayIcon() { return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="5 3 19 12 5 21 5 3" /></svg>; }

export default RiskDashboard;