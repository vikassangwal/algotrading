import { useState, useEffect, useMemo, useCallback } from 'react';
import { clsx, formatters } from '../../design-system';
import { Button, Select, Input, Card, CardHeader, CardContent, Badge, Table, Modal, Tabs, Tab, Textarea } from '../ui';

export function TradeJournalAdvanced({
  token,
  className = '',
  style = {},
  ...props
}) {
  const [activeTab, setActiveTab] = useState('journal');
  const [trades, setTrades] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState({
    symbol: '',
    side: '',
    strategy: '',
    dateFrom: '',
    dateTo: '',
    outcome: '',
  });
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingTrade, setEditingTrade] = useState(null);
  const [newTrade, setNewTrade] = useState({
    symbol: '',
    side: 'BUY',
    quantity: 1,
    entry_price: 0,
    exit_price: 0,
    entry_time: new Date().toISOString().slice(0, 16),
    exit_time: '',
    strategy: '',
    tags: [],
    notes: '',
    commission: 0,
    slippage: 0,
  });

  const [psychologyMetrics, setPsychologyMetrics] = useState(null);
  const [strategyPerformance, setStrategyPerformance] = useState([]);

  const API_URL = `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}`;

  const fetchTrades = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const headers = { 'Authorization': `Bearer ${token}` };
      const params = new URLSearchParams(filters);
      const [tradesRes, psychRes, stratRes] = await Promise.all([
        fetch(`${API_URL}/api/journal?${params}`, { headers }),
        fetch(`${API_URL}/api/psychology/metrics`, { headers }),
        fetch(`${API_URL}/api/analytics/strategy-performance`, { headers }),
      ]);
      if (tradesRes.ok) setTrades(await tradesRes.json());
      if (psychRes.ok) setPsychologyMetrics(await psychRes.json());
      if (stratRes.ok) setStrategyPerformance((await stratRes.json()).strategies || []);
    } catch (err) {
      console.error('Fetch trades error:', err);
    } finally {
      setLoading(false);
    }
  }, [token, filters, API_URL]);

  useEffect(() => {
    fetchTrades();
  }, [fetchTrades]);

  const handleAddTrade = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const headers = { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' };
      const url = editingTrade
        ? `${API_URL}/api/journal/${editingTrade.id}`
        : `${API_URL}/api/journal`;
      const method = editingTrade ? 'PUT' : 'POST';
      const res = await fetch(url, { method, headers, body: JSON.stringify(newTrade) });
      if (res.ok) {
        fetchTrades();
        setShowAddModal(false);
        setEditingTrade(null);
        setNewTrade({ symbol: '', side: 'BUY', quantity: 1, entry_price: 0, exit_price: 0, entry_time: new Date().toISOString().slice(0, 16), exit_time: '', strategy: '', tags: [], notes: '', commission: 0, slippage: 0 });
      }
    } catch (err) {
      console.error('Add trade error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteTrade = async (tradeId) => {
    if (!confirm('Delete this trade?')) return;
    try {
      const headers = { 'Authorization': `Bearer ${token}` };
      await fetch(`${API_URL}/api/journal/${tradeId}`, { method: 'DELETE', headers });
      fetchTrades();
    } catch (err) {
      console.error('Delete trade error:', err);
    }
  };

  const handleEditTrade = (trade) => {
    setEditingTrade(trade);
    setNewTrade({
      symbol: trade.symbol,
      side: trade.side,
      quantity: trade.qty,
      entry_price: trade.entry_price,
      exit_price: trade.exit_price || 0,
      entry_time: trade.entry_time?.slice(0, 16) || '',
      exit_time: trade.exit_time?.slice(0, 16) || '',
      strategy: trade.strategy || '',
      tags: trade.tags || [],
      notes: trade.notes || '',
      commission: trade.commission || 0,
      slippage: trade.slippage || 0,
    });
    setShowAddModal(true);
  };

  // Calculate P&L for display
  const enrichedTrades = useMemo(() => trades.map(trade => {
    const pnl = trade.pnl || ((trade.exit_price - trade.entry_price) * trade.qty * (trade.side === 'BUY' ? 1 : -1));
    const pnlPct = trade.entry_price ? (pnl / (trade.entry_price * trade.qty)) * 100 : 0;
    return { ...trade, pnl, pnlPct };
  }), [trades]);

  // Journal Tab
  const journalColumns = [
    { key: 'entry_time', header: 'Entry Time', width: '140px' },
    { key: 'exit_time', header: 'Exit Time', width: '140px' },
    { key: 'symbol', header: 'Symbol', width: '100px' },
    { key: 'side', header: 'Side', width: '80px' },
    { key: 'quantity', header: 'Qty', align: 'right', width: '80px' },
    { key: 'entry_price', header: 'Entry', align: 'right', format: 'price', width: '100px' },
    { key: 'exit_price', header: 'Exit', align: 'right', format: 'price', width: '100px' },
    { key: 'pnl', header: 'P&L', align: 'right', format: 'price', width: '100px' },
    { key: 'pnlPct', header: 'P&L %', align: 'right', format: 'percent', width: '90px' },
    { key: 'strategy', header: 'Strategy', width: '120px' },
    { key: 'tags', header: 'Tags', width: '120px' },
  ];

  // Psychology Tab
  const renderPsychology = () => {
    if (!psychologyMetrics) return <div style={{ textAlign: 'center', padding: 'var(--space-8)', color: 'var(--color-text-tertiary)' }}>Loading psychology metrics...</div>;

    const metrics = [
      { label: 'Total Trades', value: formatters.quantity(psychologyMetrics.total_trades || 0) },
      { label: 'Win Rate', value: formatters.percent(psychologyMetrics.win_rate || 0), trend: psychologyMetrics.win_rate >= 50 ? 'up' : 'down' },
      { label: 'Avg Win', value: formatters.price(psychologyMetrics.avg_win || 0) },
      { label: 'Avg Loss', value: formatters.price(psychologyMetrics.avg_loss || 0) },
      { label: 'Profit Factor', value: (psychologyMetrics.profit_factor || 0).toFixed(2), trend: psychologyMetrics.profit_factor >= 1.5 ? 'up' : 'neutral' },
      { label: 'Expectancy', value: formatters.price(psychologyMetrics.expectancy || 0), trend: psychologyMetrics.expectancy > 0 ? 'up' : 'down' },
      { label: 'Max Consecutive Wins', value: formatters.quantity(psychologyMetrics.max_consecutive_wins || 0) },
      { label: 'Max Consecutive Losses', value: formatters.quantity(psychologyMetrics.max_consecutive_losses || 0) },
      { label: 'Avg Hold Time (winning)', value: `${psychologyMetrics.avg_hold_winning || 0} min` },
      { label: 'Avg Hold Time (losing)', value: `${psychologyMetrics.avg_hold_losing || 0} min` },
      { label: 'Largest Win', value: formatters.price(psychologyMetrics.largest_win || 0) },
      { label: 'Largest Loss', value: formatters.price(psychologyMetrics.largest_loss || 0) },
      { label: 'Recovery Factor', value: (psychologyMetrics.recovery_factor || 0).toFixed(2) },
      { label: 'Sharpe Ratio', value: (psychologyMetrics.sharpe_ratio || 0).toFixed(2) },
    ];

    return (
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 'var(--space-4)' }}>
        {metrics.map((m, i) => (
          <StatCard key={i} label={m.label} value={m.value} trend={m.trend} />
        ))}
      </div>
    );
  };

  // Strategy Performance Tab
  const renderStrategyPerformance = () => {
    if (!strategyPerformance.length) return <div style={{ textAlign: 'center', padding: 'var(--space-8)', color: 'var(--color-text-tertiary)' }}>No strategy performance data</div>;

    return (
      <Card variant="default" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
        <CardHeader title="Strategy Performance" />
        <CardContent style={{ flex: 1, overflow: 'auto' }}>
          <Table
            columns={[
              { key: 'strategy', header: 'Strategy', width: '180px' },
              { key: 'trades', header: 'Trades', align: 'center', width: '80px' },
              { key: 'win_rate', header: 'Win Rate', align: 'right', format: 'percent', width: '100px' },
              { key: 'total_pnl', header: 'Total P&L', align: 'right', format: 'price', width: '120px' },
              { key: 'avg_pnl', header: 'Avg P&L', align: 'right', format: 'price', width: '120px' },
              { key: 'profit_factor', header: 'Profit Factor', align: 'right', format: (v) => v.toFixed(2), width: '120px' },
              { key: 'expectancy', header: 'Expectancy', align: 'right', format: 'price', width: '120px' },
              { key: 'sharpe', header: 'Sharpe', align: 'right', format: (v) => v.toFixed(2), width: '100px' },
            ]}
            data={strategyPerformance}
            keyField="strategy"
            sortable
            striped
            hoverable
          />
        </CardContent>
      </Card>
    );
  };

  // Analytics Tab
  const renderAnalytics = () => {
    if (!enrichedTrades.length) return <div style={{ textAlign: 'center', padding: 'var(--space-8)', color: 'var(--color-text-tertiary)' }}>No trades to analyze</div>;

    // Monthly P&L
    const monthlyPnl = useMemo(() => {
      const months = {};
      enrichedTrades.forEach(t => {
        if (!t.exit_time) return;
        const month = t.exit_time.slice(0, 7);
        months[month] = (months[month] || 0) + (t.pnl || 0);
      });
      return Object.entries(months).sort().map(([month, pnl]) => ({ month, pnl }));
    }, [enrichedTrades]);

    // Symbol performance
    const symbolPerf = useMemo(() => {
      const symbols = {};
      enrichedTrades.forEach(t => {
        symbols[t.symbol] = symbols[t.symbol] || { trades: 0, wins: 0, pnl: 0 };
        symbols[t.symbol].trades++;
        if (t.pnl > 0) symbols[t.symbol].wins++;
        symbols[t.symbol].pnl += t.pnl || 0;
      });
      return Object.entries(symbols).map(([symbol, data]) => ({ symbol, ...data, winRate: data.trades ? (data.wins / data.trades) * 100 : 0 }));
    }, [enrichedTrades]);

    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
        <Card variant="default">
          <CardHeader title="Monthly P&L" />
          <CardContent>
            <Table
              columns={[
                { key: 'month', header: 'Month', width: '120px' },
                { key: 'pnl', header: 'P&L', align: 'right', format: 'price', width: '120px' },
              ]}
              data={monthlyPnl}
              keyField="month"
              sortable
            />
          </CardContent>
        </Card>

        <Card variant="default">
          <CardHeader title="Symbol Performance" />
          <CardContent>
            <Table
              columns={[
                { key: 'symbol', header: 'Symbol', width: '120px' },
                { key: 'trades', header: 'Trades', align: 'center', width: '80px' },
                { key: 'wins', header: 'Wins', align: 'center', width: '80px' },
                { key: 'winRate', header: 'Win Rate', align: 'right', format: 'percent', width: '100px' },
                { key: 'pnl', header: 'Total P&L', align: 'right', format: 'price', width: '120px' },
              ]}
              data={symbolPerf}
              keyField="symbol"
              sortable
              striped
              hoverable
            />
          </CardContent>
        </Card>
      </div>
    );
  };

  return (
    <div className={clsx('elco-trade-journal', className)} style={{ ...style, height: '100%', display: 'flex', flexDirection: 'column', ...props }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: 'var(--space-4)', background: 'var(--color-surface-panel)', borderBottom: '1px solid var(--color-surface-border)' }}>
        <h2 style={{ fontSize: 'var(--font-size-xl)', fontWeight: 'var(--font-weight-semibold)', margin: 0 }}>Trade Journal</h2>
        <Button variant="primary" size="sm" onClick={() => { setEditingTrade(null); setNewTrade({ symbol: '', side: 'BUY', quantity: 1, entry_price: 0, exit_price: 0, entry_time: new Date().toISOString().slice(0, 16), exit_time: '', strategy: '', tags: [], notes: '', commission: 0, slippage: 0 }); setShowAddModal(true); }} leftIcon={<PlusIcon />}>
          Add Trade
        </Button>
      </div>

      {/* Filters */}
      <div style={{ display: 'flex', gap: 'var(--space-3)', padding: 'var(--space-3) var(--space-4)', background: 'var(--color-surface-base)', borderBottom: '1px solid var(--color-surface-border)', flexWrap: 'wrap' }}>
        <Input placeholder="Symbol" value={filters.symbol} onChange={(e) => setFilters(prev => ({ ...prev, symbol: e.target.value }))} size="sm" style={{ width: '140px' }} />
        <Select value={filters.side} onChange={(e) => setFilters(prev => ({ ...prev, side: e.target.value }))} options={[{ value: '', label: 'All Sides' }, { value: 'BUY', label: 'BUY' }, { value: 'SELL', label: 'SELL' }]} size="sm" style={{ width: '120px' }} />
        <Input placeholder="Strategy" value={filters.strategy} onChange={(e) => setFilters(prev => ({ ...prev, strategy: e.target.value }))} size="sm" style={{ width: '160px' }} />
        <Input type="date" value={filters.dateFrom} onChange={(e) => setFilters(prev => ({ ...prev, dateFrom: e.target.value }))} size="sm" style={{ width: '160px' }} />
        <Input type="date" value={filters.dateTo} onChange={(e) => setFilters(prev => ({ ...prev, dateTo: e.target.value }))} size="sm" style={{ width: '160px' }} />
        <Select value={filters.outcome} onChange={(e) => setFilters(prev => ({ ...prev, outcome: e.target.value }))} options={[{ value: '', label: 'All Outcomes' }, { value: 'win', label: 'Wins' }, { value: 'loss', label: 'Losses' }]} size="sm" style={{ width: '140px' }} />
        <div style={{ flex: 1 }} />
        <Button variant="ghost" size="sm" onClick={fetchTrades} loading={loading} leftIcon={<RefreshIcon />}>Refresh</Button>
      </div>

      {/* Tabs */}
      <Tabs activeTab={activeTab} onChange={setActiveTab} style={{ borderBottom: '1px solid var(--color-surface-border)' }}>
        <Tab id="journal" label="Trade Log" />
        <Tab id="psychology" label="Psychology" />
        <Tab id="strategies" label="Strategies" />
        <Tab id="analytics" label="Analytics" />
      </Tabs>

      <div style={{ flex: 1, overflow: 'auto', padding: 'var(--space-4)' }}>
        {activeTab === 'journal' && (
          <Card variant="default" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            <CardHeader title="Trade History" action={<span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-tertiary)' }}>{enrichedTrades.length} trades</span>} />
            <CardContent style={{ flex: 1, overflow: 'auto' }}>
              <Table
                columns={journalColumns}
                data={enrichedTrades}
                keyField="id"
                sortable
                striped
                hoverable
                emptyMessage="No trades found"
                renderCell={(value, row, column) => {
                  if (column.key === 'side') return <Badge variant={value === 'BUY' ? 'success' : 'danger'} size="sm">{value}</Badge>;
                  if (column.key === 'pnl' || column.key === 'pnlPct') {
                    const color = value >= 0 ? 'var(--color-market-buy)' : 'var(--color-market-sell)';
                    return <span style={{ color, fontWeight: 'var(--font-weight-medium)', fontFamily: 'var(--font-family-mono)' }}>{value >= 0 ? '+' : ''}{column.format ? column.format(value) : value}</span>;
                  }
                  if (column.key === 'tags' && Array.isArray(value)) {
                    return <div style={{ display: 'flex', gap: 'var(--space-1)', flexWrap: 'wrap' }}>{value.map((tag, i) => <Badge key={i} variant="ghost" size="sm">{tag}</Badge>)}</div>;
                  }
                  return column.format ? column.format(value) : value;
                }}
                onRowClick={(row) => handleEditTrade(row)}
              />
            </CardContent>
          </Card>
        )}
        {activeTab === 'psychology' && <div style={{ padding: 'var(--space-4)' }}>{renderPsychology()}</div>}
        {activeTab === 'strategies' && <div style={{ height: '100%' }}>{renderStrategyPerformance()}</div>}
        {activeTab === 'analytics' && <div style={{ height: '100%' }}>{renderAnalytics()}</div>}
      </div>

      {/* Add/Edit Trade Modal */}
      <Modal
        isOpen={showAddModal}
        onClose={() => { setShowAddModal(false); setEditingTrade(null); }}
        title={editingTrade ? 'Edit Trade' : 'Add Trade'}
        size="lg"
        footer={
          <>
            <Button variant="ghost" onClick={() => { setShowAddModal(false); setEditingTrade(null); }}>Cancel</Button>
            <Button variant="primary" onClick={handleAddTrade} loading={loading}>{editingTrade ? 'Update' : 'Add'}</Button>
          </>
        }
      >
        <form onSubmit={handleAddTrade} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 'var(--space-4)' }}>
            <Input label="Symbol" value={newTrade.symbol} onChange={(e) => setNewTrade(prev => ({ ...prev, symbol: e.target.value.toUpperCase() }))} size="sm" required />
            <Select label="Side" value={newTrade.side} onChange={(e) => setNewTrade(prev => ({ ...prev, side: e.target.value }))} options={[{ value: 'BUY', label: 'BUY' }, { value: 'SELL', label: 'SELL' }]} size="sm" />
            <Input label="Quantity" type="number" min="1" value={newTrade.quantity} onChange={(e) => setNewTrade(prev => ({ ...prev, quantity: parseInt(e.target.value) || 1 }))} size="sm" />
            <Input label="Strategy" value={newTrade.strategy} onChange={(e) => setNewTrade(prev => ({ ...prev, strategy: e.target.value }))} size="sm" placeholder="e.g., SMA Crossover" />
            <Input label="Entry Price" type="number" step="0.01" min="0" value={newTrade.entry_price} onChange={(e) => setNewTrade(prev => ({ ...prev, entry_price: parseFloat(e.target.value) || 0 }))} size="sm" required />
            <Input label="Exit Price" type="number" step="0.01" min="0" value={newTrade.exit_price} onChange={(e) => setNewTrade(prev => ({ ...prev, exit_price: parseFloat(e.target.value) || 0 }))} size="sm" />
            <Input label="Entry Time" type="datetime-local" value={newTrade.entry_time} onChange={(e) => setNewTrade(prev => ({ ...prev, entry_time: e.target.value }))} size="sm" required />
            <Input label="Exit Time" type="datetime-local" value={newTrade.exit_time} onChange={(e) => setNewTrade(prev => ({ ...prev, exit_time: e.target.value }))} size="sm" />
            <Input label="Commission" type="number" step="0.01" min="0" value={newTrade.commission} onChange={(e) => setNewTrade(prev => ({ ...prev, commission: parseFloat(e.target.value) || 0 }))} size="sm" />
            <Input label="Slippage" type="number" step="0.01" min="0" value={newTrade.slippage} onChange={(e) => setNewTrade(prev => ({ ...prev, slippage: parseFloat(e.target.value) || 0 }))} size="sm" />
          </div>
          <Textarea label="Tags (comma separated)" value={newTrade.tags.join(', ')} onChange={(e) => setNewTrade(prev => ({ ...prev, tags: e.target.value.split(',').map(t => t.trim()).filter(Boolean) }))} rows={2} size="sm" placeholder="e.g., breakout, earnings, high-volume" />
          <Textarea label="Notes" value={newTrade.notes} onChange={(e) => setNewTrade(prev => ({ ...prev, notes: e.target.value }))} rows={4} size="sm" placeholder="Trade rationale, emotions, lessons learned..." />
        </form>
      </Modal>
    </div>
  );
}

function RefreshIcon() { return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M23 4v6h-6" /><path d="M1 20v-6h6" /><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" /></svg>; }
function PlusIcon() { return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></svg>; }
function StatCard({ label, value, trend }) { return (<div style={{ padding: 'var(--space-4)', background: 'var(--color-surface-panel)', border: '1px solid var(--color-surface-border)', borderRadius: 'var(--radius-md)' }}><div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: 'var(--letter-spacing-wider)', marginBottom: 'var(--space-2)' }}>{label}</div><div style={{ fontSize: 'var(--font-size-xl)', fontWeight: 'var(--font-weight-bold)', color: trend === 'up' ? 'var(--color-market-buy)' : trend === 'down' ? 'var(--color-market-sell)' : 'var(--color-text-primary)', fontFamily: 'var(--font-family-mono)' }}>{value}</div></div>); }

export default TradeJournalAdvanced;