import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { clsx, formatters, marketStatus } from '../../design-system';
import { Button, Select, Input, Badge, Table, Card, CardHeader, CardContent } from '../ui';

const SCANNER_TYPES = [
  { value: 'gap_up', label: 'Gap Up', icon: '⬆', color: 'var(--color-market-buy)' },
  { value: 'gap_down', label: 'Gap Down', icon: '⬇', color: 'var(--color-market-sell)' },
  { value: 'breakout', label: 'Breakout', icon: '📈', color: 'var(--color-brand-500)' },
  { value: 'breakdown', label: 'Breakdown', icon: '📉', color: 'var(--color-market-sell)' },
  { value: 'high_volume', label: 'High Volume', icon: '📊', color: 'var(--color-market-info)' },
  { value: 'momentum', label: 'Momentum', icon: '⚡', color: 'var(--color-market-warning)' },
  { value: 'reversal', label: 'Reversal', icon: '🔄', color: 'var(--color-market-neutral)' },
  { value: 'unusual_options', label: 'Unusual Options', icon: '🎯', color: 'var(--color-brand-400)' },
];

const SECTORS = [
  'All', 'NIFTY 50', 'BANK NIFTY', 'IT', 'BANKING', 'PHARMA', 'AUTO', 'FMCG', 'METALS', 'ENERGY', 'REALTY', 'INFRA'
];

const TIMEFRAMES = [
  { value: '1m', label: '1 Min' },
  { value: '5m', label: '5 Min' },
  { value: '15m', label: '15 Min' },
  { value: '30m', label: '30 Min' },
  { value: '1h', label: '1 Hour' },
  { value: '1d', label: 'Daily' },
];

export function MarketScanner({
  token,
  className = '',
  style = {},
  ...props
}) {
  const [activeScanner, setActiveScanner] = useState('gap_up');
  const [selectedSector, setSelectedSector] = useState('All');
  const [timeframe, setTimeframe] = useState('15m');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [refreshInterval, setRefreshInterval] = useState(30); // seconds
  const [filters, setFilters] = useState({
    minPrice: '',
    maxPrice: '',
    minVolume: '',
    minChange: '',
    maxChange: '',
  });
  const [sortConfig, setSortConfig] = useState({ key: 'changePercent', direction: 'desc' });

  const wsRef = useRef(null);
  const intervalRef = useRef(null);
  const API_URL = `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}`;
  const WS_URL = `${import.meta.env.VITE_WS_URL || 'ws://localhost:8000'}`;

  // Connect WebSocket for real-time updates
  const connectWebSocket = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(`${WS_URL}/ws/live?token=${token}&symbols=ALL`);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('Scanner WebSocket connected');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'ticks') {
          // Update real-time prices in results
          setResults(prev => prev.map(row => {
            const tick = data.ticks[row.symbol];
            if (!tick) return row;
            const change = ((tick.ltp - row.prevClose) / row.prevClose) * 100;
            return {
              ...row,
              ltp: tick.ltp,
              change: tick.ltp - row.prevClose,
              changePercent: change,
              volume: tick.volume,
              timestamp: tick.timestamp,
            };
          }));
        }
      } catch (e) {
        console.error('WS message parse error:', e);
      }
    };

    ws.onerror = (err) => {
      console.error('Scanner WebSocket error:', err);
    };

    ws.onclose = () => {
      console.log('Scanner WebSocket closed, reconnecting...');
      setTimeout(connectWebSocket, 5000);
    };
  }, [token, WS_URL]);

  // Fetch scanner results
  const fetchResults = useCallback(async () => {
    if (!token) return;
    setLoading(true);

    try {
      const headers = { 'Authorization': `Bearer ${token}` };
      const params = new URLSearchParams({
        scanner: activeScanner,
        sector: selectedSector,
        timeframe,
        ...Object.fromEntries(Object.entries(filters).filter(([, v]) => v !== '')),
      });

      const res = await fetch(`${API_URL}/api/scanners/${activeScanner}?${params}`, { headers });
      if (!res.ok) throw new Error('Failed to fetch scanner data');
      const data = await res.json();
      setResults(data.results || data);
      setLastUpdate(new Date());
    } catch (err) {
      console.error('Scanner fetch error:', err);
    } finally {
      setLoading(false);
    }
  }, [token, activeScanner, selectedSector, timeframe, filters, API_URL]);

  // Auto-refresh
  useEffect(() => {
    if (autoRefresh) {
      intervalRef.current = setInterval(fetchResults, refreshInterval * 1000);
      return () => clearInterval(intervalRef.current);
    }
  }, [autoRefresh, refreshInterval, fetchResults]);

  // Initial load and WebSocket
  useEffect(() => {
    fetchResults();
    connectWebSocket();
    return () => {
      clearInterval(intervalRef.current);
      wsRef.current?.close();
    };
  }, [fetchResults, connectWebSocket]);

  // Sort handler
  const handleSort = useCallback((key, direction) => {
    setSortConfig({ key, direction });
    setResults(prev => [...prev].sort((a, b) => {
      const aVal = a[key];
      const bVal = b[key];
      if (aVal < bVal) return direction === 'asc' ? -1 : 1;
      if (aVal > bVal) return direction === 'asc' ? 1 : -1;
      return 0;
    }));
  }, []);

  // Filter handler
  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  const handleFilterSubmit = (e) => {
    e.preventDefault();
    fetchResults();
  };

  // Columns based on scanner type
  const columns = useMemo(() => {
    const baseColumns = [
      { key: 'symbol', header: 'Symbol', sortable: true, width: '100px' },
      { key: 'name', header: 'Name', sortable: true, width: '180px' },
      { key: 'ltp', header: 'LTP', sortable: true, align: 'right', format: 'price', width: '100px' },
      { key: 'change', header: 'Change', sortable: true, align: 'right', format: 'price', width: '100px' },
      { key: 'changePercent', header: 'Change %', sortable: true, align: 'right', format: 'percent', width: '100px' },
      { key: 'volume', header: 'Volume', sortable: true, align: 'right', format: 'volume', width: '120px' },
    ];

    const scannerSpecific = {
      gap_up: [
        { key: 'gapPercent', header: 'Gap %', sortable: true, align: 'right', format: 'percent', width: '90px' },
        { key: 'openPrice', header: 'Open', sortable: true, align: 'right', format: 'price', width: '100px' },
      ],
      breakout: [
        { key: 'breakoutLevel', header: 'Level', sortable: true, align: 'right', format: 'price', width: '100px' },
        { key: 'consolidationDays', header: 'Cons. Days', sortable: true, align: 'center', width: '100px' },
      ],
      high_volume: [
        { key: 'volumeRatio', header: 'Vol Ratio', sortable: true, align: 'right', format: (v) => v.toFixed(2) + 'x', width: '100px' },
        { key: 'avgVolume', header: 'Avg Vol', sortable: true, align: 'right', format: 'volume', width: '120px' },
      ],
      momentum: [
        { key: 'rsi', header: 'RSI', sortable: true, align: 'right', format: (v) => v?.toFixed(1), width: '70px' },
        { key: 'macdSignal', header: 'MACD', sortable: true, align: 'right', format: (v) => v?.toFixed(3), width: '80px' },
      ],
      reversal: [
        { key: 'pattern', header: 'Pattern', sortable: true, width: '140px' },
        { key: 'reliability', header: 'Reliability', sortable: true, align: 'right', format: (v) => v + '%', width: '100px' },
      ],
      unusual_options: [
        { key: 'optionType', header: 'Type', sortable: true, align: 'center', width: '70px' },
        { key: 'strike', header: 'Strike', sortable: true, align: 'right', format: 'price', width: '90px' },
        { key: 'oiChange', header: 'OI Change', sortable: true, align: 'right', format: 'percent', width: '100px' },
        { key: 'iv', header: 'IV', sortable: true, align: 'right', format: (v) => v?.toFixed(1) + '%', width: '80px' },
      ],
    };

    return [...baseColumns, ...(scannerSpecific[activeScanner] || [])];
  }, [activeScanner]);

  // Render cell with color coding
  const renderCell = (value, row, column) => {
    if (column.key === 'change' || column.key === 'changePercent') {
      const color = value > 0 ? 'var(--color-market-buy)' : value < 0 ? 'var(--color-market-sell)' : 'var(--color-text-secondary)';
      const sign = value > 0 ? '+' : '';
      return (
        <span style={{ color, fontWeight: 'var(--font-weight-medium)', fontFamily: 'var(--font-family-mono)' }}>
          {sign}{column.format === 'percent' ? formatters.percent(value) : formatters.price(value)}
        </span>
      );
    }
    if (column.key === 'volume' || column.key === 'avgVolume') {
      return <span style={{ fontFamily: 'var(--font-family-mono)' }}>{formatters.volume(value)}</span>;
    }
    if (column.key === 'ltp' || column.key === 'openPrice' || column.key === 'breakoutLevel' || column.key === 'strike') {
      return <span style={{ fontFamily: 'var(--font-family-mono)', fontWeight: 'var(--font-weight-medium)' }}>{formatters.price(value)}</span>;
    }
    if (column.key === 'symbol') {
      return (
        <span style={{ fontWeight: 'var(--font-weight-semibold)', fontFamily: 'var(--font-family-mono)', cursor: 'pointer', color: 'var(--color-brand-400)' }}>
          {value}
        </span>
      );
    }
    if (column.key === 'optionType') {
      return (
        <Badge variant={value === 'CE' ? 'success' : 'danger'} size="sm">
          {value}
        </Badge>
      );
    }
    if (column.key === 'pattern') {
      return <Badge variant="outline" size="sm">{value}</Badge>;
    }
    if (column.format) {
      return <span style={{ fontFamily: 'var(--font-family-mono)' }}>{column.format(value)}</span>;
    }
    return value;
  };

  const marketPhase = marketStatus.getMarketPhase();

  return (
    <div className={clsx('elco-market-scanner', className)} style={{ ...style, height: '100%', display: 'flex', flexDirection: 'column', ...props }}>
      {/* Header Toolbar */}
      <Card variant="outlined" padding="none" style={{ marginBottom: 'var(--space-4)' }}>
        <div style={{ padding: 'var(--space-4)', borderBottom: '1px solid var(--color-surface-border)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4)', flexWrap: 'wrap' }}>
            {/* Market Status */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', padding: 'var(--space-2) var(--space-3)', background: 'var(--color-surface-interactive)', borderRadius: 'var(--radius-md)' }}>
              <StatusBadge status={marketPhase === 'open' ? 'connected' : marketPhase === 'pre_market' ? 'connecting' : 'disconnected'} size="sm" />
              <span style={{ fontSize: 'var(--font-size-sm)', fontWeight: 'var(--font-weight-medium)', textTransform: 'capitalize' }}>
                {marketPhase.replace('_', ' ')}
              </span>
            </div>

            {/* Scanner Type Tabs */}
            <div className="elco-scanner-tabs" style={{ display: 'flex', gap: '2px', background: 'var(--color-surface-interactive)', borderRadius: 'var(--radius-md)', padding: '2px' }}>
              {SCANNER_TYPES.map(scanner => (
                <button
                  key={scanner.value}
                  onClick={() => setActiveScanner(scanner.value)}
                  style={{
                    padding: 'var(--space-2) var(--space-3)',
                    fontSize: 'var(--font-size-xs)',
                    fontWeight: 'var(--font-weight-medium)',
                    color: activeScanner === scanner.value ? 'white' : 'var(--color-text-secondary)',
                    background: activeScanner === scanner.value ? scanner.color : 'transparent',
                    border: 'none',
                    borderRadius: 'var(--radius-sm)',
                    cursor: 'pointer',
                    transition: 'all var(--transition-fast)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 'var(--space-1)',
                    whiteSpace: 'nowrap',
                  }}
                >
                  <span>{scanner.icon}</span>
                  <span>{scanner.label}</span>
                </button>
              ))}
            </div>

            {/* Sector Filter */}
            <Select
              value={selectedSector}
              onChange={(e) => setSelectedSector(e.target.value)}
              options={SECTORS.map(s => ({ value: s, label: s }))}
              size="sm"
              style={{ width: '160px' }}
            />

            {/* Timeframe */}
            <Select
              value={timeframe}
              onChange={(e) => setTimeframe(e.target.value)}
              options={TIMEFRAMES}
              size="sm"
              style={{ width: '120px' }}
            />

            <div style={{ flex: 1 }} />

            {/* Auto Refresh Toggle */}
            <Switch
              checked={autoRefresh}
              onChange={setAutoRefresh}
              label="Auto"
              description={`${refreshInterval}s`}
            />

            <Select
              value={refreshInterval}
              onChange={(e) => setRefreshInterval(parseInt(e.target.value))}
              options={[
                { value: 15, label: '15s' },
                { value: 30, label: '30s' },
                { value: 60, label: '1m' },
                { value: 120, label: '2m' },
                { value: 300, label: '5m' },
              ]}
              size="sm"
              style={{ width: '100px' }}
            />

            <Button variant="ghost" size="sm" onClick={fetchResults} loading={loading} leftIcon={<RefreshIcon />}>
              Refresh
            </Button>
          </div>

          {/* Advanced Filters */}
          <form onSubmit={handleFilterSubmit} style={{ display: 'flex', gap: 'var(--space-3)', padding: 'var(--space-3) var(--space-4)', borderTop: '1px solid var(--color-surface-border)', flexWrap: 'wrap', alignItems: 'flex-end' }}>
            <Input label="Min Price" type="number" placeholder="0" value={filters.minPrice} onChange={(e) => handleFilterChange('minPrice', e.target.value)} size="sm" style={{ width: '120px' }} />
            <Input label="Max Price" type="number" placeholder="∞" value={filters.maxPrice} onChange={(e) => handleFilterChange('maxPrice', e.target.value)} size="sm" style={{ width: '120px' }} />
            <Input label="Min Volume" type="number" placeholder="0" value={filters.minVolume} onChange={(e) => handleFilterChange('minVolume', e.target.value)} size="sm" style={{ width: '140px' }} />
            <Input label="Min Change %" type="number" step="0.1" placeholder="-∞" value={filters.minChange} onChange={(e) => handleFilterChange('minChange', e.target.value)} size="sm" style={{ width: '140px' }} />
            <Input label="Max Change %" type="number" step="0.1" placeholder="∞" value={filters.maxChange} onChange={(e) => handleFilterChange('maxChange', e.target.value)} size="sm" style={{ width: '140px' }} />
            <Button type="submit" variant="primary" size="sm" style={{ marginTop: 'auto' }}>
              <FilterIcon /> Apply
            </Button>
            <Button type="button" variant="ghost" size="sm" onClick={() => setFilters({ minPrice: '', maxPrice: '', minVolume: '', minChange: '', maxChange: '' })} style={{ marginTop: 'auto' }}>
              Clear
            </Button>
          </form>
        </div>
      </Card>

      {/* Results Table */}
      <Card variant="default" padding="none" style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        <Table
          columns={columns}
          data={results}
          keyField="symbol"
          sortable
          sortColumn={sortConfig.key}
          sortDirection={sortConfig.direction}
          onSort={handleSort}
          selectable
          striped
          hoverable
          loading={loading}
          emptyMessage={`No ${SCANNER_TYPES.find(s => s.value === activeScanner)?.label.toLowerCase()} signals found`}
          renderCell={renderCell}
          style={{ flex: 1, overflow: 'auto' }}
        />

        {/* Footer Stats */}
        <div style={{ padding: 'var(--space-3) var(--space-4)', borderTop: '1px solid var(--color-surface-border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)' }}>
          <span>{results.length} results</span>
          <span>Last updated: {lastUpdate ? formatters.timeOnly(lastUpdate) : '—'}</span>
          <span>
            {marketStatus.isMarketOpen() ? (
              <Badge variant="success" size="sm" dot>Live</Badge>
            ) : (
              <Badge variant="default" size="sm" dot>Delayed</Badge>
            )}
          </span>
        </div>
      </Card>
    </div>
  );
}

// Helper icons
function RefreshIcon() {
  return <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M23 4v6h-6" /><path d="M1 20v-6h6" /><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" /></svg>;
}

function FilterIcon() {
  return <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" /></svg>;
}

import { Switch, StatusBadge } from '../ui';

export default MarketScanner;