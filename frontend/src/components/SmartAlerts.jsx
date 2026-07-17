import React, { useState } from 'react';

const SmartAlerts = () => {
  const [alerts, setAlerts] = useState([
    { id: 1, type: 'Price', asset: 'BTC/USD', condition: 'Crosses Above', value: '65000', status: 'Active' },
    { id: 2, type: 'Indicator', asset: 'ETH/USD', condition: 'RSI >', value: '70', status: 'Active' },
    { id: 3, type: 'Margin', asset: 'Account', condition: 'Drops Below', value: '15%', status: 'Triggered' },
  ]);

  const [newAlert, setNewAlert] = useState({
    type: 'Price',
    asset: '',
    condition: '',
    value: '',
  });

  const handleAddAlert = (e) => {
    e.preventDefault();
    if (!newAlert.asset || !newAlert.value) return;

    setAlerts([
      ...alerts,
      {
        id: Date.now(),
        ...newAlert,
        status: 'Active',
      },
    ]);
    setNewAlert({ type: 'Price', asset: '', condition: '', value: '' });
  };

  const deleteAlert = (id) => {
    setAlerts(alerts.filter(alert => alert.id !== id));
  };

  return (
    <div className="smart-alerts-container" style={{ padding: '20px', fontFamily: 'system-ui, sans-serif', maxWidth: '800px', margin: '0 auto', color: '#333' }}>
      <h2 style={{ borderBottom: '2px solid #eaeaea', paddingBottom: '10px' }}>Smart Alerts Configuration</h2>
      
      <div style={{ background: '#f9f9f9', padding: '20px', borderRadius: '8px', marginBottom: '30px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
        <h3 style={{ marginTop: 0 }}>Create New Alert</h3>
        <form onSubmit={handleAddAlert} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
          
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <label style={{ marginBottom: '5px', fontWeight: 'bold', fontSize: '14px' }}>Alert Type</label>
            <select 
              value={newAlert.type} 
              onChange={(e) => setNewAlert({...newAlert, type: e.target.value})}
              style={{ padding: '10px', borderRadius: '4px', border: '1px solid #ccc' }}
            >
              <option value="Price">Price Alert</option>
              <option value="Margin">Margin Alert</option>
              <option value="Indicator">Indicator Alert</option>
              <option value="Drawdown">Drawdown Alert</option>
            </select>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <label style={{ marginBottom: '5px', fontWeight: 'bold', fontSize: '14px' }}>Asset / Symbol</label>
            <input 
              type="text" 
              placeholder="e.g. BTC/USD or Account" 
              value={newAlert.asset} 
              onChange={(e) => setNewAlert({...newAlert, asset: e.target.value})}
              style={{ padding: '10px', borderRadius: '4px', border: '1px solid #ccc' }}
              required
            />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <label style={{ marginBottom: '5px', fontWeight: 'bold', fontSize: '14px' }}>Condition</label>
            <select 
              value={newAlert.condition} 
              onChange={(e) => setNewAlert({...newAlert, condition: e.target.value})}
              style={{ padding: '10px', borderRadius: '4px', border: '1px solid #ccc' }}
              required
            >
              <option value="">Select Condition</option>
              <option value="Crosses Above">Crosses Above</option>
              <option value="Crosses Below">Crosses Below</option>
              <option value="Greater Than">Greater Than (&gt;)</option>
              <option value="Less Than">Less Than (&lt;)</option>
              <option value="Drops Below">Drops Below</option>
            </select>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <label style={{ marginBottom: '5px', fontWeight: 'bold', fontSize: '14px' }}>Value</label>
            <input 
              type="text" 
              placeholder="e.g. 60000, 70, 15%" 
              value={newAlert.value} 
              onChange={(e) => setNewAlert({...newAlert, value: e.target.value})}
              style={{ padding: '10px', borderRadius: '4px', border: '1px solid #ccc' }}
              required
            />
          </div>

          <div style={{ gridColumn: '1 / -1', marginTop: '10px' }}>
            <button 
              type="submit" 
              style={{ 
                backgroundColor: '#0066cc', 
                color: 'white', 
                padding: '12px 20px', 
                border: 'none', 
                borderRadius: '4px', 
                cursor: 'pointer',
                fontWeight: 'bold',
                width: '100%'
              }}
            >
              Set Alert
            </button>
          </div>
        </form>
      </div>

      <div>
        <h3>Active Alerts</h3>
        {alerts.length === 0 ? (
          <p style={{ color: '#666' }}>No active alerts. Create one above.</p>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
              <thead>
                <tr style={{ backgroundColor: '#f1f1f1', borderBottom: '2px solid #ddd' }}>
                  <th style={{ padding: '12px 15px' }}>Type</th>
                  <th style={{ padding: '12px 15px' }}>Asset</th>
                  <th style={{ padding: '12px 15px' }}>Condition</th>
                  <th style={{ padding: '12px 15px' }}>Status</th>
                  <th style={{ padding: '12px 15px', textAlign: 'center' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {alerts.map((alert) => (
                  <tr key={alert.id} style={{ borderBottom: '1px solid #eee' }}>
                    <td style={{ padding: '12px 15px', fontWeight: 'bold' }}>{alert.type}</td>
                    <td style={{ padding: '12px 15px' }}>{alert.asset}</td>
                    <td style={{ padding: '12px 15px' }}>{alert.condition} {alert.value}</td>
                    <td style={{ padding: '12px 15px' }}>
                      <span style={{ 
                        padding: '4px 8px', 
                        borderRadius: '12px', 
                        fontSize: '12px',
                        backgroundColor: alert.status === 'Active' ? '#e6f4ea' : '#fce8e6',
                        color: alert.status === 'Active' ? '#137333' : '#c5221f'
                      }}>
                        {alert.status}
                      </span>
                    </td>
                    <td style={{ padding: '12px 15px', textAlign: 'center' }}>
                      <button 
                        onClick={() => deleteAlert(alert.id)}
                        style={{ 
                          backgroundColor: '#ff4d4f', 
                          color: 'white', 
                          border: 'none', 
                          padding: '6px 12px', 
                          borderRadius: '4px', 
                          cursor: 'pointer',
                          fontSize: '12px'
                        }}
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default SmartAlerts;
