import React, { useState, useEffect } from 'react';
import { ShieldCheck, UserPlus, Users, Key, CheckCircle, AlertCircle, RefreshCw, Lock } from 'lucide-react';

const API_URL = (import.meta.env.VITE_API_URL || 'https://elco-backend.onrender.com').replace(/\/$/, '');

const TenantDashboard = () => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [newEmail, setNewEmail] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newRole, setNewRole] = useState('trader');
  const [msg, setMsg] = useState('');
  const [err, setErr] = useState('');
  const [creating, setCreating] = useState(false);

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/admin/users`);
      if (res.ok) {
        const data = await res.json();
        setUsers(data);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const handleCreateUser = async (e) => {
    e.preventDefault();
    setMsg('');
    setErr('');
    if (!newEmail || !newPassword) {
      setErr('Please enter both Email and Password');
      return;
    }
    if (newPassword.length < 6) {
      setErr('Password must be at least 6 characters');
      return;
    }

    setCreating(true);
    try {
      const res = await fetch(`${API_URL}/api/admin/users`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: newEmail, password: newPassword, role: newRole })
      });
      const data = await res.json();
      if (res.ok) {
        setMsg(`✅ Account created for ${newEmail}`);
        setNewEmail('');
        setNewPassword('');
        fetchUsers();
      } else {
        setErr(data.detail || 'Failed to create user account');
      }
    } catch (e) {
      setErr('Connection error. Could not create account.');
    } finally {
      setCreating(false);
    }
  };

  return (
    <div style={{ backgroundColor: '#020617', minHeight: '100vh', color: '#f8fafc', padding: '24px', fontFamily: 'system-ui, sans-serif' }}>
      
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', backgroundColor: '#0f172a', padding: '20px 28px', borderRadius: '12px', marginBottom: '24px', border: '1px solid #1e293b' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '24px', fontWeight: 'bold', background: 'linear-gradient(90deg, #3b82f6, #10b981)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <ShieldCheck size={28} color="#10b981" /> Admin Control & User Account Manager
          </h1>
          <p style={{ margin: '4px 0 0 0', color: '#94a3b8', fontSize: '14px' }}>
            Master Admin: <strong style={{ color: '#38bdf8' }}>vsangwal54@gmail.com</strong> | Password: <strong style={{ color: '#10b981' }}>Vikas@0502</strong>
          </p>
        </div>

        <button onClick={fetchUsers} style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '10px 18px', backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px', color: '#fff', fontWeight: 'bold', cursor: 'pointer' }}>
          <RefreshCw size={16} className={loading ? "spin" : ""} /> Refresh Accounts
        </button>
      </div>

      {/* Main Grid: Create Account + Accounts List */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '24px' }}>
        
        {/* Card 1: Create New User Account */}
        <div style={{ backgroundColor: '#0f172a', padding: '24px', borderRadius: '12px', border: '1px solid #1e293b' }}>
          <h2 style={{ margin: '0 0 16px 0', fontSize: '18px', color: '#38bdf8', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <UserPlus size={20} /> Create New Account (नया अकाउंट बनाएं)
          </h2>

          {msg && <div style={{ backgroundColor: '#064e3b', color: '#34d399', padding: '10px 14px', borderRadius: '8px', marginBottom: '16px', fontSize: '14px' }}>{msg}</div>}
          {err && <div style={{ backgroundColor: '#7f1d1d', color: '#fca5a5', padding: '10px 14px', borderRadius: '8px', marginBottom: '16px', fontSize: '14px' }}>{err}</div>}

          <form onSubmit={handleCreateUser} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '13px', color: '#94a3b8', marginBottom: '6px', fontWeight: '600' }}>User Email Address (यूज़र ईमेल ID)</label>
              <input 
                type="email" 
                value={newEmail} 
                onChange={e => setNewEmail(e.target.value)} 
                placeholder="e.g. user@example.com"
                required
                style={{ width: '100%', padding: '12px', backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px', color: '#fff', fontSize: '14px', boxSizing: 'border-box' }} 
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '13px', color: '#94a3b8', marginBottom: '6px', fontWeight: '600' }}>Password (पासवर्ड)</label>
              <input 
                type="text" 
                value={newPassword} 
                onChange={e => setNewPassword(e.target.value)} 
                placeholder="Set user password"
                required
                style={{ width: '100%', padding: '12px', backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px', color: '#fff', fontSize: '14px', boxSizing: 'border-box' }} 
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '13px', color: '#94a3b8', marginBottom: '6px', fontWeight: '600' }}>Role (रोल / पद)</label>
              <select 
                value={newRole} 
                onChange={e => setNewRole(e.target.value)}
                style={{ width: '100%', padding: '12px', backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px', color: '#fff', fontSize: '14px', fontWeight: 'bold' }}
              >
                <option value="trader">📈 Trader (Trading & Analysis Access)</option>
                <option value="analyst">📊 Analyst (Research Access)</option>
                <option value="admin">⚡ Administrator (Full Admin Access)</option>
              </select>
            </div>

            <button 
              type="submit" 
              disabled={creating}
              style={{ marginTop: '8px', padding: '12px', background: 'linear-gradient(90deg, #3b82f6, #2563eb)', border: 'none', borderRadius: '8px', color: '#fff', fontWeight: 'bold', fontSize: '15px', cursor: 'pointer', opacity: creating ? 0.7 : 1 }}
            >
              {creating ? 'Creating Account...' : '➕ Create Account Now'}
            </button>
          </form>
        </div>

        {/* Card 2: Active Accounts List */}
        <div style={{ backgroundColor: '#0f172a', padding: '24px', borderRadius: '12px', border: '1px solid #1e293b' }}>
          <h2 style={{ margin: '0 0 16px 0', fontSize: '18px', color: '#10b981', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Users size={20} /> Active Registered Accounts ({users.length})
          </h2>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', maxHeight: '420px', overflowY: 'auto' }}>
            {users.map((u) => (
              <div key={u.email} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', backgroundColor: '#020617', padding: '14px 16px', borderRadius: '8px', border: '1px solid #1e293b' }}>
                <div>
                  <div style={{ fontWeight: 'bold', color: '#f8fafc', fontSize: '15px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    {u.email} {u.email === 'vsangwal54@gmail.com' && <span style={{ fontSize: '11px', backgroundColor: '#3b82f6', color: '#fff', padding: '2px 8px', borderRadius: '10px' }}>MASTER ADMIN</span>}
                  </div>
                  <div style={{ fontSize: '12px', color: '#64748b', marginTop: '2px' }}>Role: {u.role.toUpperCase()}</div>
                </div>
                <div>
                  <span style={{ fontSize: '12px', color: '#10b981', backgroundColor: '#064e3b', padding: '4px 10px', borderRadius: '6px', fontWeight: 'bold' }}>
                    Active
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

      </div>

    </div>
  );
};

export default TenantDashboard;
