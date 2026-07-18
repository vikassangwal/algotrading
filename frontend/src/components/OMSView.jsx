import React, { useState, useEffect } from 'react';

const API_URL = import.meta.env.VITE_API_URL || '';

const OMSView = () => {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const token = localStorage.getItem('elco_token');

  useEffect(() => {
    fetchOrders();
    const interval = setInterval(fetchOrders, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchOrders = async () => {
    try {
      const res = await fetch(`${API_URL}/api/orders`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setOrders(data.reverse());
        setLoading(false);
      }
    } catch (err) {
      console.error("Failed to fetch orders:", err);
    }
  };

  const [formData, setFormData] = useState({
    symbol: '',
    side: 'BUY',
    qty: '',
    type: 'MARKET',
    price: '',
    stopPrice: '',
    duration: '',
    interval: '',
    displayQty: ''
  });

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch(`${API_URL}/api/orders`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          symbol: formData.symbol.toUpperCase(),
          action: formData.side,
          qty: parseInt(formData.qty),
          type: formData.type,
          price: formData.price ? parseFloat(formData.price) : null
        })
      });
      
      if (res.ok) {
        fetchOrders(); // Refresh instantly
        setFormData(prev => ({ ...prev, symbol: '', qty: '', price: '', stopPrice: '', duration: '', interval: '', displayQty: '' }));
      } else {
        alert("Failed to execute order. Check console or risk rules.");
      }
    } catch (err) {
      console.error("Order submission failed:", err);
    }
  };

  const styles = {
    container: {
      padding: '24px',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
      backgroundColor: '#121212',
      color: '#ffffff',
      minHeight: '100vh',
      boxSizing: 'border-box'
    },
    header: {
      fontSize: '28px',
      fontWeight: '600',
      marginBottom: '24px',
      color: '#fff',
      borderBottom: '1px solid #333',
      paddingBottom: '12px'
    },
    grid: {
      display: 'grid',
      gridTemplateColumns: '1fr 2fr',
      gap: '24px',
      alignItems: 'start'
    },
    card: {
      backgroundColor: '#1e1e1e',
      borderRadius: '8px',
      padding: '20px',
      boxShadow: '0 4px 6px rgba(0,0,0,0.3)',
      border: '1px solid #333'
    },
    cardTitle: {
      fontSize: '20px',
      fontWeight: '500',
      marginBottom: '16px',
      color: '#e0e0e0'
    },
    formGroup: {
      marginBottom: '16px'
    },
    label: {
      display: 'block',
      marginBottom: '8px',
      fontSize: '14px',
      color: '#aaa'
    },
    input: {
      width: '100%',
      padding: '10px 12px',
      backgroundColor: '#2a2a2a',
      border: '1px solid #444',
      borderRadius: '4px',
      color: '#fff',
      fontSize: '14px',
      boxSizing: 'border-box',
      outline: 'none',
      transition: 'border-color 0.2s'
    },
    select: {
      width: '100%',
      padding: '10px 12px',
      backgroundColor: '#2a2a2a',
      border: '1px solid #444',
      borderRadius: '4px',
      color: '#fff',
      fontSize: '14px',
      boxSizing: 'border-box',
      outline: 'none',
      cursor: 'pointer'
    },
    row: {
      display: 'flex',
      gap: '16px'
    },
    col: {
      flex: 1
    },
    buttonContainer: {
      marginTop: '24px',
      display: 'flex',
      gap: '12px'
    },
    buyBtn: {
      flex: 1,
      padding: '12px',
      backgroundColor: '#00c853',
      color: '#000',
      border: 'none',
      borderRadius: '4px',
      fontWeight: '600',
      cursor: 'pointer',
      fontSize: '16px',
      transition: 'opacity 0.2s'
    },
    sellBtn: {
      flex: 1,
      padding: '12px',
      backgroundColor: '#ff3d00',
      color: '#fff',
      border: 'none',
      borderRadius: '4px',
      fontWeight: '600',
      cursor: 'pointer',
      fontSize: '16px',
      transition: 'opacity 0.2s'
    },
    table: {
      width: '100%',
      borderCollapse: 'collapse',
      fontSize: '14px'
    },
    th: {
      textAlign: 'left',
      padding: '12px',
      borderBottom: '2px solid #333',
      color: '#aaa',
      fontWeight: '500'
    },
    td: {
      padding: '12px',
      borderBottom: '1px solid #333',
      color: '#e0e0e0'
    },
    statusBadge: (status) => {
      const colors = {
        PENDING: { bg: '#ffb30033', text: '#ffb300' },
        WORKING: { bg: '#29b6f633', text: '#29b6f6' },
        FILLED: { bg: '#00e67633', text: '#00e676' },
        CANCELLED: { bg: '#ff525233', text: '#ff5252' },
      };
      const theme = colors[status] || colors.PENDING;
      return {
        display: 'inline-block',
        padding: '4px 8px',
        borderRadius: '12px',
        fontSize: '12px',
        fontWeight: '600',
        backgroundColor: theme.bg,
        color: theme.text
      };
    },
    sideBadge: (side) => ({
      color: side === 'BUY' ? '#00e676' : '#ff5252',
      fontWeight: '600'
    })
  };

  return (
    <div style={styles.container}>
      <h1 style={styles.header}>Order Management System (OMS)</h1>
      
      <div style={styles.grid}>
        {/* Order Entry Form */}
        <div style={styles.card}>
          <h2 style={styles.cardTitle}>Order Entry</h2>
          <form onSubmit={handleSubmit}>
            <div style={styles.row}>
              <div style={styles.col}>
                <div style={styles.formGroup}>
                  <label style={styles.label}>Symbol</label>
                  <input 
                    type="text" 
                    name="symbol" 
                    value={formData.symbol} 
                    onChange={handleInputChange} 
                    style={styles.input} 
                    placeholder="e.g. AAPL" 
                    required 
                  />
                </div>
              </div>
              <div style={styles.col}>
                <div style={styles.formGroup}>
                  <label style={styles.label}>Side</label>
                  <select name="side" value={formData.side} onChange={handleInputChange} style={styles.select}>
                    <option value="BUY">BUY</option>
                    <option value="SELL">SELL</option>
                  </select>
                </div>
              </div>
            </div>

            <div style={styles.row}>
              <div style={styles.col}>
                <div style={styles.formGroup}>
                  <label style={styles.label}>Quantity</label>
                  <input 
                    type="number" 
                    name="qty" 
                    value={formData.qty} 
                    onChange={handleInputChange} 
                    style={styles.input} 
                    min="1" 
                    required 
                  />
                </div>
              </div>
              <div style={styles.col}>
                <div style={styles.formGroup}>
                  <label style={styles.label}>Order Type</label>
                  <select name="type" value={formData.type} onChange={handleInputChange} style={styles.select}>
                    <option value="MARKET">Market</option>
                    <option value="LIMIT">Limit</option>
                    <option value="STOP">Stop</option>
                    <option value="TWAP">TWAP</option>
                    <option value="ICEBERG">Iceberg</option>
                  </select>
                </div>
              </div>
            </div>

            {formData.type === 'LIMIT' && (
              <div style={styles.formGroup}>
                <label style={styles.label}>Limit Price</label>
                <input type="number" name="price" value={formData.price} onChange={handleInputChange} style={styles.input} step="0.01" required />
              </div>
            )}

            {formData.type === 'STOP' && (
              <div style={styles.formGroup}>
                <label style={styles.label}>Stop Price</label>
                <input type="number" name="stopPrice" value={formData.stopPrice} onChange={handleInputChange} style={styles.input} step="0.01" required />
              </div>
            )}

            {formData.type === 'TWAP' && (
              <div style={styles.row}>
                <div style={styles.col}>
                  <div style={styles.formGroup}>
                    <label style={styles.label}>Duration (mins)</label>
                    <input type="number" name="duration" value={formData.duration} onChange={handleInputChange} style={styles.input} required />
                  </div>
                </div>
                <div style={styles.col}>
                  <div style={styles.formGroup}>
                    <label style={styles.label}>Interval (secs)</label>
                    <input type="number" name="interval" value={formData.interval} onChange={handleInputChange} style={styles.input} required />
                  </div>
                </div>
              </div>
            )}

            {formData.type === 'ICEBERG' && (
              <div style={styles.row}>
                <div style={styles.col}>
                  <div style={styles.formGroup}>
                    <label style={styles.label}>Limit Price</label>
                    <input type="number" name="price" value={formData.price} onChange={handleInputChange} style={styles.input} step="0.01" required />
                  </div>
                </div>
                <div style={styles.col}>
                  <div style={styles.formGroup}>
                    <label style={styles.label}>Display Qty</label>
                    <input type="number" name="displayQty" value={formData.displayQty} onChange={handleInputChange} style={styles.input} required />
                  </div>
                </div>
              </div>
            )}

            <div style={styles.buttonContainer}>
              {formData.side === 'BUY' ? (
                <button type="submit" style={styles.buyBtn}>SUBMIT BUY ORDER</button>
              ) : (
                <button type="submit" style={styles.sellBtn}>SUBMIT SELL ORDER</button>
              )}
            </div>
          </form>
        </div>

        {/* Live Orders Table */}
        <div style={styles.card}>
          <h2 style={styles.cardTitle}>Live Orders</h2>
          <div style={{ overflowX: 'auto' }}>
            <table style={styles.table}>
              <thead>
                <tr>
                  <th style={styles.th}>Order ID</th>
                  <th style={styles.th}>Symbol</th>
                  <th style={styles.th}>Side</th>
                  <th style={styles.th}>Type</th>
                  <th style={styles.th}>Qty</th>
                  <th style={styles.th}>Price</th>
                  <th style={styles.th}>Status</th>
                  <th style={styles.th}>Time</th>
                </tr>
              </thead>
              <tbody>
                {orders.map((order) => (
                  <tr key={order.order_id || order.trade_id || order.id}>
                    <td style={styles.td}>{order.order_id || order.trade_id || order.id}</td>
                    <td style={styles.td}><strong>{order.symbol}</strong></td>
                    <td style={styles.td}>
                      <span style={styles.sideBadge(order.action || order.side)}>{order.action || order.side}</span>
                    </td>
                    <td style={styles.td}>{order.type || order.order_type || 'MARKET'}</td>
                    <td style={styles.td}>{order.qty || order.quantity}</td>
                    <td style={styles.td}>{order.entry_price || order.average_price || order.price || '-'}</td>
                    <td style={styles.td}>
                      <span style={styles.statusBadge(order.status)}>{order.status}</span>
                    </td>
                    <td style={styles.td}>{order.timestamp ? new Date(order.timestamp).toLocaleTimeString() : '-'}</td>
                  </tr>
                ))}
                {orders.length === 0 && (
                  <tr>
                    <td colSpan="8" style={{...styles.td, textAlign: 'center', color: '#666', padding: '24px'}}>
                      No active orders found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default OMSView;
