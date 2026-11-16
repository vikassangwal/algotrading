import { useState, useEffect, useMemo, useCallback } from 'react';
import { clsx, formatters } from '../../design-system';
import { Button, Select, Input, Card, CardHeader, CardContent, Badge, Table, Tabs, Tab } from '../ui';
import { AdvancedChart } from '../charts/AdvancedChart';

const EXPIRIES = [
  { value: 'weekly', label: 'Weekly', days: 7 },
  { value: 'monthly', label: 'Monthly', days: 30 },
  { value: 'quarterly', label: 'Quarterly', days: 90 },
];

export function OptionsChainAnalyzer({
  token,
  className = '',
  style = {},
  ...props
}) {
  const [symbol, setSymbol] = useState('NIFTY');
  const [expiry, setExpiry] = useState('weekly');
  const [strikeRange, setStrikeRange] = useState(10); // ±10 strikes
  const [chainData, setChainData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [spotPrice, setSpotPrice] = useState(0);
  const [pcr, setPcr] = useState(0);
  const [maxPain, setMaxPain] = useState(0);
  const [ivSurface, setIvSurface] = useState([]);
  const [greeksView, setGreeksView] = useState('delta'); // delta, gamma, theta, vega, iv
  const [selectedStrike, setSelectedStrike] = useState(null);

  const API_URL = `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}`;

  const fetchChain = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const headers = { 'Authorization': `Bearer ${token}` };
      const res = await fetch(`${API_URL}/api/options-chain?symbol=${symbol}&expiry=${expiry}&range=${strikeRange}`, { headers });
      if (res.ok) {
        const data = await res.json();
        setChainData(data.chain);
        setSpotPrice(data.spot);
        setPcr(data.pcr);
        setMaxPain(data.max_pain);
        setIvSurface(data.iv_surface || []);
      }
    } catch (err) {
      console.error('Fetch options chain error:', err);
    } finally {
      setLoading(false);
    }
  }, [token, symbol, expiry, strikeRange, API_URL]);

  useEffect(() => {
    fetchChain();
  }, [fetchChain]);

  // Auto-refresh during market hours
  useEffect(() => {
    const interval = setInterval(fetchChain, 60000);
    return () => clearInterval(interval);
  }, [fetchChain]);

  const columns = useMemo(() => [
    // Put side (left)
    { key: 'put_oi', header: 'Put OI', align: 'right', format: 'quantity', width: '90px' },
    { key: 'put_oi_change', header: 'OI Chg', align: 'right', format: (v) => (v >= 0 ? '+' : '') + formatters.percent(v), width: '80px' },
    { key: 'put_iv', header: 'Put IV', align: 'right', format: (v) => v.toFixed(1) + '%', width: '70px' },
    { key: 'put_greek', header: `Put ${greeksView.toUpperCase()}`, align: 'right', format: (v) => v.toFixed(4), width: '80px' },
    { key: 'put_ltp', header: 'Put LTP', align: 'right', format: 'price', width: '80px' },

    // Strike (center)
    { key: 'strike', header: 'STRIKE', align: 'center', width: '80px', sticky: true },

    // Call side (right)
    { key: 'call_ltp', header: 'Call LTP', align: 'right', format: 'price', width: '80px' },
    { key: 'call_greek', header: `Call ${greeksView.toUpperCase()}`, align: 'right', format: (v) => v.toFixed(4), width: '80px' },
    { key: 'call_iv', header: 'Call IV', align: 'right', format: (v) => v.toFixed(1) + '%', width: '70px' },
    { key: 'call_oi_change', header: 'OI Chg', align: 'right', format: (v) => (v >= 0 ? '+' : '') + formatters.percent(v), width: '80px' },
    { key: 'call_oi', header: 'Call OI', align: 'right', format: 'quantity', width: '90px' },
  ], [greeksView]);

  const renderCell = (value, row, column) => {
    const isATM = Math.abs(row.strike - spotPrice) < 50;
    const isSelected = selectedStrike === row.strike;

    if (column.key === 'strike') {
      return (
        <div
          style={{
            fontWeight: isATM ? 'var(--font-weight-bold)' : 'var(--font-weight-medium)',
            color: isATM ? 'var(--color-brand-500)' : 'var(--color-text-primary)',
            background: isATM ? 'var(--color-brand-100)' : isSelected ? 'var(--color-surface-interactive)' : 'transparent',
            padding: 'var(--space-1) var(--space-2)',
            borderRadius: 'var(--radius-md)',
            cursor: 'pointer',
            fontFamily: 'var(--font-family-mono)',
            fontSize: 'var(--font-size-sm)',
            transition: 'all var(--transition-fast)',
          }}
          onClick={() => setSelectedStrike(row.strike)}
        >
          {row.strike}
        </div>
      );
    }

    if (column.key.includes('oi_change')) {
      const color = value > 0 ? 'var(--color-market-buy)' : value < 0 ? 'var(--color-market-sell)' : 'var(--color-text-tertiary)';
      return <span style={{ color, fontWeight: 'var(--font-weight-medium)', fontFamily: 'var(--font-family-mono)', fontSize: 'var(--font-size-xs)' }}>{value >= 0 ? '+' : ''}{formatters.percent(value)}</span>;
    }

    if (column.key.includes('iv')) {
      const color = value > 30 ? 'var(--color-market-sell)' : value > 20 ? 'var(--color-market-warning)' : 'var(--color-market-buy)';
      return <span style={{ color, fontWeight: 'var(--font-weight-medium)', fontFamily: 'var(--font-family-mono)' }}>{column.format(value)}</span>;
    }

    if (column.key.includes('greek')) {
      const color = value > 0 ? 'var(--color-market-buy)' : value < 0 ? 'var(--color-market-sell)' : 'var(--color-text-tertiary)';
      return <span style={{ color, fontWeight: 'var(--font-weight-medium)', fontFamily: 'var(--font-family-mono)', fontSize: 'var(--font-size-sm)' }}>{column.format(value)}</span>;
    }

    if (column.key.includes('ltp')) {
      return <span style={{ fontFamily: 'var(--font-family-mono)', fontWeight: 'var(--font-weight-medium)' }}>{formatters.price(value)}</span>;
    }

    if (column.key.includes('oi')) {
      return <span style={{ fontFamily: 'var(--font-family-mono)', fontSize: 'var(--font-size-sm)' }}>{formatters.volume(value)}</span>;
    }

    return column.format ? column.format(value) : value;
  };

  // Summary cards
  const summaryStats = useMemo(() => [
    { label: 'Spot Price', value: formatters.price(spotPrice), trend: 'neutral' },
    { label: 'PCR', value: pcr.toFixed(2), trend: pcr > 1.2 ? 'down' : pcr < 0.8 ? 'up' : 'neutral' },
    { label: 'Max Pain', value: formatters.price(maxPain), trend: maxPain > spotPrice ? 'down' : 'up' },
    { label: 'ATM IV', value: `${chainData?.find(c => Math.abs(c.strike - spotPrice) < 50)?.call_iv?.toFixed(1) || '—'}%`, trend: 'neutral' },
    { label: 'Total Call OI', value: formatters.volume(chainData?.reduce((sum, c) => sum + (c.call_oi || 0), 0) || 0), trend: 'neutral' },
    { label: 'Total Put OI', value: formatters.volume(chainData?.reduce((sum, c) => sum + (c.put_oi || 0), 0) || 0), trend: 'neutral' },
  ], [spotPrice, pcr, maxPain, chainData]);

  return (
    <div className={clsx('elco-options-chain', className)} style={{ ...style, height: '100%', display: 'flex', flexDirection: 'column', ...props }}>
      {/* Header Toolbar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', padding: 'var(--space-3) var(--space-4)', background: 'var(--color-surface-panel)', borderBottom: '1px solid var(--color-surface-border)', flexWrap: 'wrap' }}>
        <Select
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
          options={[
            { value: 'NIFTY', label: 'NIFTY 50' },
            { value: 'BANKNIFTY', label: 'BANK NIFTY' },
            { value: 'FINNIFTY', label: 'FIN NIFTY' },
            { value: 'MIDCPNIFTY', label: 'MIDCP NIFTY' },
          ]}
          size="sm"
          style={{ width: '160px' }}
        />
        <Select
          value={expiry}
          onChange={(e) => setExpiry(e.target.value)}
          options={EXPIRIES}
          size="sm"
          style={{ width: '140px' }}
        />
        <Input
          label="Strike Range (±)"
          type="number"
          min="5"
          max="50"
          value={strikeRange}
          onChange={(e) => setStrikeRange(parseInt(e.target.value) || 10)}
          size="sm"
          style={{ width: '160px' }}
        />

        <div style={{ flex: 1 }} />

        <div style={{ display: 'flex', gap: 'var(--space-1)', background: 'var(--color-surface-interactive)', borderRadius: 'var(--radius-md)', padding: '2px' }}>
          {['delta', 'gamma', 'theta', 'vega', 'iv'].map(g => (
            <Button
              key={g}
              variant={greeksView === g ? 'primary' : 'ghost'}
              size="sm"
              onClick={() => setGreeksView(g)}
              style={{ padding: '4px 10px', fontSize: 'var(--font-size-xs)', textTransform: 'uppercase' }}
            >
              {g.toUpperCase()}
            </Button>
          ))}
        </div>

        <Button variant="ghost" size="sm" onClick={fetchChain} loading={loading} leftIcon={<RefreshIcon />}>Refresh</Button>
      </div>

      {/* Summary Stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 'var(--space-3)', padding: 'var(--space-3) var(--space-4)', background: 'var(--color-surface-base)', borderBottom: '1px solid var(--color-surface-border)' }}>
        {summaryStats.map((stat, i) => (
          <StatCard key={i} label={stat.label} value={stat.value} trend={stat.trend} />
        ))}
      </div>

      {/* Main Content */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {/* Options Chain Table */}
        <div style={{ width: '100%', overflow: 'auto', padding: 'var(--space-4)' }}>
          {loading && !chainData ? (
            <div style={{ textAlign: 'center', padding: 'var(--space-8)', color: 'var(--color-text-tertiary)' }}>
              <div className="elco-spinner" style={{ width: '32px', height: '32px', border: '3px solid var(--color-surface-border)', borderTopColor: 'var(--color-brand-500)', borderRadius: '50%', animation: 'spin 0.8s linear infinite', margin: '0 auto var(--space-4)' }} />
              <style jsx>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
              Loading options chain...
            </div>
          ) : chainData ? (
            <Table
              columns={columns}
              data={chainData}
              keyField="strike"
              sortable
              striped
              hoverable
              renderCell={renderCell}
              emptyMessage="No options data available"
            />
          ) : (
            <div style={{ textAlign: 'center', padding: 'var(--space-8)', color: 'var(--color-text-tertiary)' }}>
              No options chain data loaded
            </div>
          )}
        </div>
      </div>

      {/* Footer - Key Levels */}
      <div style={{ padding: 'var(--space-3) var(--space-4)', background: 'var(--color-surface-panel)', borderTop: '1px solid var(--color-surface-border)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4)', flexWrap: 'wrap', fontSize: 'var(--font-size-sm)' }}>
          <span style={{ color: 'var(--color-text-secondary)' }}>Key Levels:</span>
          <span style={{ color: 'var(--color-market-sell)', fontWeight: 'var(--font-weight-medium)', fontFamily: 'var(--font-family-mono)' }}>Resistance: {formatters.price(spotPrice * 1.02)}</span>
          <span style={{ color: 'var(--color-market-buy)', fontWeight: 'var(--font-weight-medium)', fontFamily: 'var(--font-family-mono)' }}>Support: {formatters.price(spotPrice * 0.98)}</span>
          <span style={{ color: 'var(--color-brand-500)', fontWeight: 'var(--font-weight-medium)', fontFamily: 'var(--font-family-mono)' }}>Max Pain: {formatters.price(maxPain)}</span>
          <span style={{ marginLeft: 'auto', color: 'var(--color-text-tertiary)' }}>Last updated: {formatters.timeOnly(new Date())}</span>
        </div>
      </div>
    </div>
  );
}

function RefreshIcon() { return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M23 4v6h-6" /><path d="M1 20v-6h6" /><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" /></svg>; }
function StatCard({ label, value, trend }) { return (<div style={{ padding: 'var(--space-3)', background: 'var(--color-surface-panel)', border: '1px solid var(--color-surface-border)', borderRadius: 'var(--radius-md)' }}><div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: 'var(--letter-spacing-wider)', marginBottom: 'var(--space-1)' }}>{label}</div><div style={{ fontSize: 'var(--font-size-lg)', fontWeight: 'var(--font-weight-bold)', color: trend === 'up' ? 'var(--color-market-buy)' : trend === 'down' ? 'var(--color-market-sell)' : 'var(--color-text-primary)', fontFamily: 'var(--font-family-mono)' }}>{value}</div></div>); }

export default OptionsChainAnalyzer;