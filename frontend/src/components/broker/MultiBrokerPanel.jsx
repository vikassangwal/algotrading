import { useState, useEffect, useCallback } from 'react';
import { clsx, formatters } from '../../design-system';
import { Button, Input, Select, Card, CardHeader, CardContent, Badge, Table, Modal, Switch, Tabs, Tab } from '../ui';

const SUPPORTED_BROKERS = [
  { id: 'zerodha', name: 'Zerodha (Kite Connect)', logo: '🟢', status: 'production', features: ['Equity', 'F&O', 'Commodity', 'Currency', 'MF'], websocket: true },
  { id: 'dhan', name: 'Dhan (DhanHQ)', logo: '🟡', status: 'production', features: ['Equity', 'F&O', 'Commodity', 'Currency'], websocket: true },
  { id: 'upstox', name: 'Upstox API', logo: '🔵', status: 'production', features: ['Equity', 'F&O', 'Commodity', 'Currency', 'MF'], websocket: true },
  { id: 'angelone', name: 'Angel One SmartAPI', logo: '🟠', status: 'production', features: ['Equity', 'F&O', 'Commodity', 'Currency'], websocket: true },
  { id: 'fyers', name: 'Fyers API v3', logo: '🟣', status: 'production', features: ['Equity', 'F&O', 'Commodity', 'Currency'], websocket: true },
  { id: 'kotakneo', name: 'Kotak Neo Trade API', logo: '🔴', status: 'beta', features: ['Equity', 'F&O'], websocket: true },
  { id: 'shoonya', name: 'Shoonya (Finvasia)', logo: '⚫', status: 'beta', features: ['Equity', 'F&O', 'Currency'], websocket: true },
  { id: 'aliceblue', name: 'Alice Blue (Ant Web)', logo: '🔵', status: 'beta', features: ['Equity', 'F&O', 'Commodity'], websocket: false },
  { id: '5paisa', name: '5Paisa Developer API', logo: '🟢', status: 'beta', features: ['Equity', 'F&O', 'Currency'], websocket: false },
  { id: 'flattrade', name: 'Flattrade API', logo: '🟠', status: 'beta', features: ['Equity', 'F&O'], websocket: false },
  { id: 'mock', name: 'Mock Broker (Paper Trading)', logo: '⚪', status: 'built-in', features: ['All'], websocket: false },
];

export function MultiBrokerPanel({
  token,
  className = '',
  style = {},
  ...props
}) {
  const [activeTab, setActiveTab] = useState('brokers');
  const [brokers, setBrokers] = useState([]);
  const [activeBroker, setActiveBroker] = useState(null);
  const [accounts, setAccounts] = useState([]);
  const [positions, setPositions] = useState([]);
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(false);
  const [connecting, setConnecting] = useState(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [newBrokerConfig, setNewBrokerConfig] = useState({ brokerId: '', apiKey: '', apiSecret: '', clientId: '', totpSecret: '' });

  const API_URL = `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}`;

  const fetchBrokers = useCallback(async () => {
    if (!token) return;
    try {
      const headers = { 'Authorization': `Bearer ${token}` };
      const res = await fetch(`${API_URL}/api/brokers`, { headers });
      if (res.ok) setBrokers(await res.json());
    } catch (err) {
      console.error('Fetch brokers error:', err);
    }
  }, [token, API_URL]);

  const fetchAccountData = useCallback(async (brokerId) => {
    try {
      const headers = { 'Authorization': `Bearer ${token}` };
      const [accRes, posRes, ordRes] = await Promise.all([
        fetch(`${API_URL}/api/brokers/${brokerId}/accounts`, { headers }),
        fetch(`${API_URL}/api/brokers/${brokerId}/positions`, { headers }),
        fetch(`${API_URL}/api/brokers/${brokerId}/orders`, { headers }),
      ]);
      if (accRes.ok) setAccounts(await accRes.json());
      if (posRes.ok) setPositions(await posRes.json());
      if (ordRes.ok) setOrders(await ordRes.json());
    } catch (err) {
      console.error('Fetch account data error:', err);
    }
  }, [token, API_URL]);

  useEffect(() => {
    fetchBrokers();
  }, [fetchBrokers]);

  useEffect(() => {
    if (activeBroker) {
      fetchAccountData(activeBroker.id);
      const interval = setInterval(() => fetchAccountData(activeBroker.id), 30000);
      return () => clearInterval(interval);
    }
  }, [activeBroker, fetchAccountData]);

  const connectBroker = async (broker) => {
    setConnecting(broker.id);
    try {
      const headers = { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' };
      const res = await fetch(`${API_URL}/api/brokers/connect`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ broker_id: broker.id }),
      });
      if (res.ok) {
        fetchBrokers();
        setActiveBroker(broker);
      }
    } catch (err) {
      console.error('Connect broker error:', err);
    } finally {
      setConnecting(null);
    }
  };

  const disconnectBroker = async (brokerId) => {
    try {
      const headers = { 'Authorization': `Bearer ${token}` };
      await fetch(`${API_URL}/api/brokers/${brokerId}/disconnect`, { method: 'POST', headers });
      fetchBrokers();
      if (activeBroker?.id === brokerId) setActiveBroker(null);
    } catch (err) {
      console.error('Disconnect broker error:', err);
    }
  };

  const testConnection = async (brokerId) => {
    try {
      const headers = { 'Authorization': `Bearer ${token}` };
      const res = await fetch(`${API_URL}/api/brokers/${brokerId}/test`, { method: 'POST', headers });
      return res.ok;
    } catch {
      return false;
    }
  };

  const handleAddBroker = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const headers = { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' };
      const res = await fetch(`${API_URL}/api/brokers/add`, {
        method: 'POST',
        headers,
        body: JSON.stringify(newBrokerConfig),
      });
      if (res.ok) {
        fetchBrokers();
        setShowAddModal(false);
        setNewBrokerConfig({ brokerId: '', apiKey: '', apiSecret: '', clientId: '', totpSecret: '' });
      }
    } catch (err) {
      console.error('Add broker error:', err);
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'connected': return <Badge variant="success" dot size="sm">Connected</Badge>;
      case 'connecting': return <Badge variant="warning" dot size="sm">Connecting...</Badge>;
      case 'error': return <Badge variant="danger" dot size="sm">Error</Badge>;
      default: return <Badge variant="default" dot size="sm">Disconnected</Badge>;
    }
  };

  return (
    <div className={clsx('elco-multi-broker', className)} style={{ ...style, height: '100%', display: 'flex', flexDirection: 'column', ...props }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: 'var(--space-4)', background: 'var(--color-surface-panel)', borderBottom: '1px solid var(--color-surface-border)' }}>
        <h2 style={{ fontSize: 'var(--font-size-xl)', fontWeight: 'var(--font-weight-semibold)', margin: 0 }}>Multi-Broker Integration</h2>
        <Button variant="primary" size="sm" onClick={() => setShowAddModal(true)} leftIcon={<PlusIcon />}>
          Add Broker
        </Button>
      </div>

      {/* Tabs */}
      <Tabs activeTab={activeTab} onChange={setActiveTab} style={{ borderBottom: '1px solid var(--color-surface-border)' }}>
        <Tab id="brokers" label="Brokers" />
        <Tab id="accounts" label="Accounts" disabled={!activeBroker} />
        <Tab id="positions" label="Positions" disabled={!activeBroker} />
        <Tab id="orders" label="Orders" disabled={!activeBroker} />
        <Tab id="analytics" label="Analytics" disabled={!activeBroker} />
      </Tabs>

      <div style={{ flex: 1, overflow: 'auto', padding: 'var(--space-4)' }}>
        {activeTab === 'brokers' && <BrokersTab brokers={brokers} supportedBrokers={SUPPORTED_BROKERS} activeBroker={activeBroker} connecting={connecting} onConnect={connectBroker} onDisconnect={disconnectBroker} onTest={testConnection} onSelect={setActiveBroker} token={token} />}
        {activeTab === 'accounts' && <AccountsTab accounts={accounts} activeBroker={activeBroker} />}
        {activeTab === 'positions' && <PositionsTab positions={positions} activeBroker={activeBroker} />}
        {activeTab === 'orders' && <OrdersTab orders={orders} activeBroker={activeBroker} />}
        {activeTab === 'analytics' && <AnalyticsTab activeBroker={activeBroker} />}
      </div>

      {/* Add Broker Modal */}
      <Modal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        title="Add Broker Connection"
        size="lg"
        footer={
          <>
            <Button variant="ghost" onClick={() => setShowAddModal(false)}>Cancel</Button>
            <Button variant="primary" onClick={handleAddBroker} loading={loading} disabled={!newBrokerConfig.brokerId || !newBrokerConfig.apiKey}>
              Add Connection
            </Button>
          </>
        }
      >
        <form onSubmit={handleAddBroker} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
          <Select
            label="Broker"
            value={newBrokerConfig.brokerId}
            onChange={(e) => setNewBrokerConfig(prev => ({ ...prev, brokerId: e.target.value }))}
            options={SUPPORTED_BROKERS.map(b => ({ value: b.id, label: b.name }))}
            placeholder="Select broker"
            size="sm"
          />
          <Input
            label="API Key / Client ID"
            value={newBrokerConfig.apiKey}
            onChange={(e) => setNewBrokerConfig(prev => ({ ...prev, apiKey: e.target.value }))}
            size="sm"
            placeholder="Enter API key"
          />
          <Input
            label="API Secret"
            type="password"
            value={newBrokerConfig.apiSecret}
            onChange={(e) => setNewBrokerConfig(prev => ({ ...prev, apiSecret: e.target.value }))}
            size="sm"
            placeholder="Enter API secret"
          />
          <Input
            label="Client ID / User ID"
            value={newBrokerConfig.clientId}
            onChange={(e) => setNewBrokerConfig(prev => ({ ...prev, clientId: e.target.value }))}
            size="sm"
            placeholder="Enter client ID (if required)"
          />
          <Input
            label="TOTP Secret (for 2FA)"
            value={newBrokerConfig.totpSecret}
            onChange={(e) => setNewBrokerConfig(prev => ({ ...prev, totpSecret: e.target.value }))}
            size="sm"
            placeholder="Enter TOTP secret (if required)"
          />
        </form>
      </Modal>
    </div>
  );
}

function BrokersTab({ brokers, supportedBrokers, activeBroker, connecting, onConnect, onDisconnect, onTest, onSelect, token }) {
  const brokerMap = {};
  supportedBrokers.forEach(b => { brokerMap[b.id] = b; });

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 'var(--space-4)' }}>
      {supportedBrokers.map(broker => {
        const connected = brokers.find(b => b.broker_id === broker.id);
        const isActive = activeBroker?.id === broker.id;
        const isConnecting = connecting === broker.id;
        const status = connected?.status || 'disconnected';

        return (
          <Card
            key={broker.id}
            variant={isActive ? 'elevated' : 'default'}
            style={{ border: isActive ? '2px solid var(--color-brand-500)' : undefined }}
          >
            <CardHeader
              title={broker.name}
              action={
                <Badge variant={broker.status === 'production' ? 'success' : broker.status === 'beta' ? 'warning' : 'info'} size="sm">
                  {broker.status.toUpperCase()}
                </Badge>
              }
            />
            <CardContent>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)' }}>Status</span>
                  {getStatusBadge(status)}
                </div>

                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-1)' }}>
                  {broker.features.map(f => (
                    <Badge key={f} variant="ghost" size="sm">{f}</Badge>
                  ))}
                  {broker.websocket && <Badge variant="info" size="sm">WebSocket</Badge>}
                </div>

                {connected && (
                  <div style={{ padding: 'var(--space-2)', background: 'var(--color-surface-interactive)', borderRadius: 'var(--radius-md)', fontSize: 'var(--font-size-xs)' }}>
                    <div><strong>Account:</strong> {connected.account_id || 'N/A'}</div>
                    <div><strong>Last Sync:</strong> {connected.last_sync ? formatters.timeOnly(connected.last_sync) : 'Never'}</div>
                    <div><strong>Margin:</strong> {connected.margin_available ? formatters.price(connected.margin_available) : 'N/A'}</div>
                  </div>
                )}

                <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
                  {connected ? (
                    <>
                      <Button variant={isActive ? 'primary' : 'outline'} size="sm" onClick={() => onSelect(connected)} fullWidth>
                        {isActive ? 'Active' : 'Select'}
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => onTest(broker.id)} loading={isConnecting} fullWidth leftIcon={<RefreshIcon />}>
                        Test
                      </Button>
                      <Button variant="danger" size="sm" onClick={() => onDisconnect(broker.id)} fullWidth>
                        Disconnect
                      </Button>
                    </>
                  ) : (
                    <Button variant="primary" size="sm" onClick={() => onConnect(broker)} loading={isConnecting} fullWidth leftIcon={<LinkIcon />}>
                      Connect
                    </Button>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}

function AccountsTab({ accounts, activeBroker }) {
  return (
    <Card variant="default" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <CardHeader title={`Accounts - ${activeBroker?.name}`} />
      <CardContent style={{ flex: 1, overflow: 'auto' }}>
        {accounts.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 'var(--space-8)', color: 'var(--color-text-tertiary)' }}>No accounts found</div>
        ) : (
          <Table
            columns={[
              { key: 'account_id', header: 'Account ID', width: '140px' },
              { key: 'account_type', header: 'Type', width: '100px' },
              { key: 'balance', header: 'Balance', align: 'right', format: 'price', width: '120px' },
              { key: 'margin_available', header: 'Margin Avail.', align: 'right', format: 'price', width: '120px' },
              { key: 'margin_used', header: 'Margin Used', align: 'right', format: 'price', width: '120px' },
              { key: 'pnl', header: 'Day P&L', align: 'right', format: 'price', width: '120px' },
              { key: 'currency', header: 'Currency', align: 'center', width: '80px' },
            ]}
            data={accounts}
            keyField="account_id"
            sortable
            striped
            hoverable
          />
        )}
      </CardContent>
    </Card>
  );
}

function PositionsTab({ positions, activeBroker }) {
  return (
    <Card variant="default" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <CardHeader title={`Positions - ${activeBroker?.name}`} action={<span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-tertiary)' }}>{positions.length} positions</span>} />
      <CardContent style={{ flex: 1, overflow: 'auto' }}>
        {positions.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 'var(--space-8)', color: 'var(--color-text-tertiary)' }}>No open positions</div>
        ) : (
          <Table
            columns={[
              { key: 'symbol', header: 'Symbol', width: '100px' },
              { key: 'side', header: 'Side', width: '80px' },
              { key: 'quantity', header: 'Qty', align: 'right', width: '80px' },
              { key: 'avg_price', header: 'Avg Price', align: 'right', format: 'price', width: '100px' },
              { key: 'ltp', header: 'LTP', align: 'right', format: 'price', width: '100px' },
              { key: 'unrealized_pnl', header: 'Unrealized P&L', align: 'right', format: 'price', width: '130px' },
              { key: 'unrealized_pnl_pct', header: 'P&L %', align: 'right', format: 'percent', width: '100px' },
              { key: 'value', header: 'Position Value', align: 'right', format: 'price', width: '120px' },
            ]}
            data={positions}
            keyField="symbol"
            sortable
            striped
            hoverable
          />
        )}
      </CardContent>
    </Card>
  );
}

function OrdersTab({ orders, activeBroker }) {
  return (
    <Card variant="default" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <CardHeader title={`Orders - ${activeBroker?.name}`} action={<span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-tertiary)' }}>{orders.length} orders</span>} />
      <CardContent style={{ flex: 1, overflow: 'auto' }}>
        {orders.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 'var(--space-8)', color: 'var(--color-text-tertiary)' }}>No orders</div>
        ) : (
          <Table
            columns={[
              { key: 'order_id', header: 'Order ID', width: '140px' },
              { key: 'symbol', header: 'Symbol', width: '100px' },
              { key: 'side', header: 'Side', width: '80px' },
              { key: 'quantity', header: 'Qty', align: 'right', width: '80px' },
              { key: 'order_type', header: 'Type', width: '100px' },
              { key: 'price', header: 'Price', align: 'right', format: 'price', width: '100px' },
              { key: 'status', header: 'Status', width: '100px' },
              { key: 'timestamp', header: 'Time', width: '160px' },
            ]}
            data={orders}
            keyField="order_id"
            sortable
            striped
            hoverable
          />
        )}
      </CardContent>
    </Card>
  );
}

function AnalyticsTab({ activeBroker }) {
  return (
    <Card variant="default" style={{ height: '100%' }}>
      <CardHeader title={`Analytics - ${activeBroker?.name}`} />
      <CardContent style={{ height: 'calc(100% - 60px)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--color-text-tertiary)' }}>
        Broker analytics - P&L attribution, execution quality, commission analysis
      </CardContent>
    </Card>
  );
}

function getStatusBadge(status) {
  switch (status) {
    case 'connected': return <Badge variant="success" dot size="sm">Connected</Badge>;
    case 'connecting': return <Badge variant="warning" dot size="sm">Connecting...</Badge>;
    case 'error': return <Badge variant="danger" dot size="sm">Error</Badge>;
    default: return <Badge variant="default" dot size="sm">Disconnected</Badge>;
  }
}

function PlusIcon() { return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></svg>; }
function LinkIcon() { return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" /><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" /></svg>; }
function RefreshIcon() { return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M23 4v6h-6" /><path d="M1 20v-6h6" /><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" /></svg>; }

export default MultiBrokerPanel;