import React, { useState, useEffect } from 'react';
import { 
  BookOpen, Calendar, Filter, Search, Plus, 
  TrendingUp, TrendingDown, Tag, ChevronDown, Check, X 
} from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || '';

const TradeJournal = ({ token }) => {
  const [entries, setEntries] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    const fetchJournal = async () => {
      try {
        const res = await fetch(`${API_URL}/journal`, {
          headers: token ? { 'Authorization': `Bearer ${token}` } : {}
        });
        if (res.ok) {
          const data = await res.json();
          // Transform backend data to match frontend requirements
          const formatted = data.map(t => ({
            id: t.trade_id,
            date: new Date(t.timestamp).toLocaleDateString(),
            time: new Date(t.timestamp).toLocaleTimeString(),
            symbol: t.symbol,
            type: 'Equity', // Default or parse from symbol
            action: t.action,
            entryPrice: t.entry_price,
            exitPrice: t.exit_price || t.entry_price,
            qty: t.qty,
            pnl: t.pnl || 0,
            setup: t.reasons && t.reasons.length > 0 ? t.reasons[0].substring(0, 30) + '...' : 'System Trade',
            emotion: 'Neutral',
            notes: t.reasons ? t.reasons.join('. ') : 'Automated AI Execution.',
            tags: ['Auto-Execution', t.status]
          }));
          setEntries(formatted.reverse());
        }
      } catch (err) {
        console.error("Failed to fetch journal:", err);
      } finally {
        setLoading(false);
      }
    };
    
    fetchJournal();
    const interval = setInterval(fetchJournal, 60000);
    return () => clearInterval(interval);
  }, [token]);

  const filteredEntries = entries.filter(entry => 
    entry.symbol.toLowerCase().includes(searchTerm.toLowerCase()) ||
    entry.notes.toLowerCase().includes(searchTerm.toLowerCase()) ||
    entry.setup.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const totalTrades = entries.length;
  const profitableTrades = entries.filter(e => e.pnl > 0).length;
  const winRate = ((profitableTrades / totalTrades) * 100).toFixed(1);
  const totalPnL = entries.reduce((acc, curr) => acc + curr.pnl, 0);

  return (
    <div style={{ fontFamily: 'system-ui, -apple-system, sans-serif', padding: '24px', backgroundColor: '#0f172a', minHeight: '100vh', color: '#f8fafc' }}>
      {/* Header Section */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h1 style={{ fontSize: '24px', fontWeight: 'bold', margin: '0 0 8px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <BookOpen size={28} color="#3b82f6" />
            Execution Trade Journal
          </h1>
          <p style={{ margin: 0, color: '#94a3b8' }}>Log, analyze, and improve your trading psychology and setups.</p>
        </div>
        <button style={{ 
          backgroundColor: '#3b82f6', color: 'white', border: 'none', 
          padding: '10px 20px', borderRadius: '8px', fontWeight: '600',
          display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer',
          boxShadow: '0 4px 6px -1px rgba(59, 130, 246, 0.3)'
        }}>
          <Plus size={18} /> New Entry
        </button>
      </div>

      {/* Stats Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', marginBottom: '24px' }}>
        <div style={{ backgroundColor: '#1e293b', padding: '20px', borderRadius: '12px', border: '1px solid #334155' }}>
          <div style={{ color: '#94a3b8', fontSize: '14px', marginBottom: '8px' }}>Total Trades Logged</div>
          <div style={{ fontSize: '28px', fontWeight: 'bold' }}>{totalTrades}</div>
        </div>
        <div style={{ backgroundColor: '#1e293b', padding: '20px', borderRadius: '12px', border: '1px solid #334155' }}>
          <div style={{ color: '#94a3b8', fontSize: '14px', marginBottom: '8px' }}>Win Rate</div>
          <div style={{ fontSize: '28px', fontWeight: 'bold', color: '#10b981' }}>{winRate}%</div>
        </div>
        <div style={{ backgroundColor: '#1e293b', padding: '20px', borderRadius: '12px', border: '1px solid #334155' }}>
          <div style={{ color: '#94a3b8', fontSize: '14px', marginBottom: '8px' }}>Net P&L (Logged)</div>
          <div style={{ fontSize: '28px', fontWeight: 'bold', color: totalPnL >= 0 ? '#10b981' : '#ef4444' }}>
            ₹ {totalPnL.toLocaleString()}
          </div>
        </div>
      </div>

      {/* Filters and Search */}
      <div style={{ display: 'flex', gap: '16px', marginBottom: '24px' }}>
        <div style={{ flex: 1, position: 'relative' }}>
          <Search size={18} color="#94a3b8" style={{ position: 'absolute', left: '12px', top: '10px' }} />
          <input 
            type="text" 
            placeholder="Search symbols, notes, setups..." 
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{ 
              width: '100%', padding: '10px 10px 10px 40px', 
              backgroundColor: '#1e293b', border: '1px solid #334155', 
              borderRadius: '8px', color: '#f8fafc', outline: 'none' 
            }}
          />
        </div>
        <button style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '10px 16px', backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px', color: '#cbd5e1', cursor: 'pointer' }}>
          <Filter size={18} /> Filter <ChevronDown size={14} />
        </button>
      </div>

      {/* Journal Entries List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {filteredEntries.map(entry => (
          <div key={entry.id} style={{ 
            backgroundColor: '#1e293b', borderRadius: '12px', border: '1px solid #334155', 
            padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px',
            transition: 'transform 0.2s, box-shadow 0.2s', cursor: 'pointer'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
                <div style={{ 
                  backgroundColor: entry.pnl >= 0 ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                  padding: '12px', borderRadius: '50%',
                  color: entry.pnl >= 0 ? '#10b981' : '#ef4444'
                }}>
                  {entry.pnl >= 0 ? <TrendingUp size={24} /> : <TrendingDown size={24} />}
                </div>
                <div>
                  <h3 style={{ margin: '0 0 4px 0', fontSize: '18px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    {entry.symbol} 
                    <span style={{ fontSize: '12px', padding: '2px 8px', backgroundColor: '#334155', borderRadius: '12px', fontWeight: 'normal' }}>{entry.type}</span>
                    <span style={{ fontSize: '12px', padding: '2px 8px', backgroundColor: entry.action === 'BUY' ? 'rgba(59, 130, 246, 0.2)' : 'rgba(245, 158, 11, 0.2)', color: entry.action === 'BUY' ? '#60a5fa' : '#fbbf24', borderRadius: '12px', fontWeight: 'normal' }}>{entry.action}</span>
                  </h3>
                  <div style={{ color: '#94a3b8', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '16px' }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}><Calendar size={14} /> {entry.date} at {entry.time}</span>
                    <span>Qty: {entry.qty}</span>
                    <span>Entry: ₹{entry.entryPrice} &rarr; Exit: ₹{entry.exitPrice}</span>
                  </div>
                </div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '20px', fontWeight: 'bold', color: entry.pnl >= 0 ? '#10b981' : '#ef4444' }}>
                  {entry.pnl >= 0 ? '+' : ''}₹{entry.pnl.toLocaleString()}
                </div>
                <div style={{ color: '#94a3b8', fontSize: '13px', marginTop: '4px' }}>Setup: <span style={{ color: '#f8fafc' }}>{entry.setup}</span></div>
              </div>
            </div>
            
            <div style={{ padding: '16px', backgroundColor: '#0f172a', borderRadius: '8px', borderLeft: `3px solid ${entry.pnl >= 0 ? '#10b981' : '#ef4444'}` }}>
              <p style={{ margin: '0 0 12px 0', lineHeight: '1.5', color: '#cbd5e1' }}>"{entry.notes}"</p>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', gap: '8px' }}>
                  {entry.tags.map((tag, idx) => (
                    <span key={idx} style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '12px', color: '#94a3b8', backgroundColor: '#1e293b', padding: '4px 8px', borderRadius: '4px' }}>
                      <Tag size={12} /> {tag}
                    </span>
                  ))}
                </div>
                <div style={{ fontSize: '12px', color: '#94a3b8' }}>
                  Emotion: <span style={{ color: '#f8fafc' }}>{entry.emotion}</span>
                </div>
              </div>
            </div>
          </div>
        ))}
        {filteredEntries.length === 0 && (
          <div style={{ textAlign: 'center', padding: '40px', color: '#94a3b8', backgroundColor: '#1e293b', borderRadius: '12px' }}>
            No journal entries found matching your search.
          </div>
        )}
      </div>
    </div>
  );
};

export default TradeJournal;
