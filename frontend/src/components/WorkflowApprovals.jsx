import React, { useState, useEffect } from 'react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const WorkflowApprovals = ({ token }) => {
  const [workflows, setWorkflows] = useState([]);
  const [filter, setFilter] = useState('pending');

  const fetchWorkflows = async () => {
    try {
      const res = await fetch(`${API_URL}/workflows`, {
        headers: token ? { 'Authorization': `Bearer ${token}` } : {}
      });
      if (res.ok) {
        const data = await res.json();
        setWorkflows(data);
      }
    } catch (err) {
      console.error("Failed to fetch workflows", err);
    }
  };

  useEffect(() => {
    fetchWorkflows();
    const interval = setInterval(fetchWorkflows, 10000);
    return () => clearInterval(interval);
  }, [token]);

  const handleApprove = async (id) => {
    try {
      await fetch(`${API_URL}/workflows/${id}/approve`, {
        method: 'POST',
        headers: token ? { 'Authorization': `Bearer ${token}` } : {}
      });
      fetchWorkflows();
    } catch (err) {
      console.error(err);
    }
  };

  const handleReject = async (id) => {
    try {
      await fetch(`${API_URL}/workflows/${id}/reject`, {
        method: 'POST',
        headers: token ? { 'Authorization': `Bearer ${token}` } : {}
      });
      fetchWorkflows();
    } catch (err) {
      console.error(err);
    }
  };

  const filteredWorkflows = workflows.filter(w => w.status === filter);

  const getRiskColor = (risk) => {
    if (!risk) return '#6b7280';
    switch (risk.toLowerCase()) {
      case 'critical': return '#ef4444';
      case 'high': return '#f97316';
      case 'medium': return '#eab308';
      case 'low': return '#22c55e';
      default: return '#6b7280';
    }
  };

  return (
    <div className="wa-dashboard">
      <style>{`
        .wa-dashboard {
          font-family: 'Inter', system-ui, -apple-system, sans-serif;
          background-color: #0f172a;
          color: #e2e8f0;
          min-height: 100vh;
          padding: 2.5rem;
          box-sizing: border-box;
        }
        .wa-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 2rem;
          padding-bottom: 1rem;
          border-bottom: 1px solid #1e293b;
        }
        .wa-title {
          font-size: 1.8rem;
          font-weight: 600;
          margin: 0;
          background: linear-gradient(90deg, #38bdf8, #818cf8);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
        }
        .wa-subtitle {
          color: #94a3b8;
          font-size: 0.95rem;
          margin-top: 0.5rem;
        }
        .wa-tabs {
          display: flex;
          gap: 1rem;
          margin-bottom: 2rem;
        }
        .wa-tab {
          background: transparent;
          border: none;
          color: #94a3b8;
          font-size: 1rem;
          font-weight: 500;
          padding: 0.5rem 1rem;
          cursor: pointer;
          border-bottom: 2px solid transparent;
          transition: all 0.3s ease;
        }
        .wa-tab:hover {
          color: #e2e8f0;
        }
        .wa-tab.active {
          color: #38bdf8;
          border-bottom-color: #38bdf8;
        }
        .wa-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
          gap: 1.5rem;
        }
        .wa-card {
          background: #1e293b;
          border-radius: 12px;
          padding: 1.5rem;
          border: 1px solid #334155;
          box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
          transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        .wa-card:hover {
          transform: translateY(-2px);
          box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.2), 0 4px 6px -2px rgba(0, 0, 0, 0.1);
          border-color: #475569;
        }
        .wa-card-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 1rem;
        }
        .wa-card-id {
          font-size: 0.85rem;
          color: #94a3b8;
          font-family: monospace;
          background: #0f172a;
          padding: 0.2rem 0.5rem;
          border-radius: 4px;
        }
        .wa-risk-badge {
          font-size: 0.75rem;
          font-weight: 600;
          padding: 0.25rem 0.6rem;
          border-radius: 9999px;
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }
        .wa-card-title {
          font-size: 1.1rem;
          font-weight: 600;
          margin: 0 0 0.5rem 0;
          color: #f8fafc;
        }
        .wa-card-details {
          font-size: 0.9rem;
          color: #cbd5e1;
          margin-bottom: 1.5rem;
          line-height: 1.4;
        }
        .wa-card-meta {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
          font-size: 0.85rem;
          color: #94a3b8;
          margin-bottom: 1.5rem;
          padding-bottom: 1.5rem;
          border-bottom: 1px solid #334155;
        }
        .wa-meta-row {
          display: flex;
          justify-content: space-between;
        }
        .wa-meta-value {
          color: #e2e8f0;
          font-weight: 500;
        }
        .wa-card-actions {
          display: flex;
          gap: 1rem;
        }
        .wa-btn {
          flex: 1;
          padding: 0.6rem;
          border: none;
          border-radius: 6px;
          font-size: 0.9rem;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s ease;
          display: flex;
          justify-content: center;
          align-items: center;
          gap: 0.5rem;
        }
        .wa-btn-approve {
          background: rgba(34, 197, 94, 0.1);
          color: #4ade80;
          border: 1px solid rgba(34, 197, 94, 0.2);
        }
        .wa-btn-approve:hover {
          background: rgba(34, 197, 94, 0.2);
          border-color: rgba(34, 197, 94, 0.4);
        }
        .wa-btn-reject {
          background: rgba(239, 68, 68, 0.1);
          color: #f87171;
          border: 1px solid rgba(239, 68, 68, 0.2);
        }
        .wa-btn-reject:hover {
          background: rgba(239, 68, 68, 0.2);
          border-color: rgba(239, 68, 68, 0.4);
        }
        .wa-status-badge {
          display: block;
          width: 100%;
          text-align: center;
          padding: 0.6rem;
          border-radius: 6px;
          font-size: 0.9rem;
          font-weight: 600;
          text-transform: capitalize;
        }
        .wa-status-approved {
          background: rgba(34, 197, 94, 0.1);
          color: #4ade80;
        }
        .wa-status-rejected {
          background: rgba(239, 68, 68, 0.1);
          color: #f87171;
        }
        .wa-empty {
          grid-column: 1 / -1;
          text-align: center;
          padding: 4rem 2rem;
          background: #1e293b;
          border-radius: 12px;
          border: 1px dashed #475569;
          color: #94a3b8;
        }
      `}</style>

      <div className="wa-header">
        <div>
          <h1 className="wa-title">Operational Risk Control</h1>
          <div className="wa-subtitle">Four-Eyes Principle Approval Workflow</div>
        </div>
      </div>

      <div className="wa-tabs">
        <button 
          className={`wa-tab ${filter === 'pending' ? 'active' : ''}`}
          onClick={() => setFilter('pending')}
        >
          Pending My Approval ({workflows.filter(w => w.status === 'pending').length})
        </button>
        <button 
          className={`wa-tab ${filter === 'approved' ? 'active' : ''}`}
          onClick={() => setFilter('approved')}
        >
          Approved History
        </button>
        <button 
          className={`wa-tab ${filter === 'rejected' ? 'active' : ''}`}
          onClick={() => setFilter('rejected')}
        >
          Rejected History
        </button>
      </div>

      <div className="wa-grid">
        {filteredWorkflows.length === 0 ? (
          <div className="wa-empty">
            <h3>No workflows found in this category.</h3>
            <p>You're all caught up!</p>
          </div>
        ) : (
          filteredWorkflows.map(workflow => (
            <div className="wa-card" key={workflow.id}>
              <div className="wa-card-header">
                <span className="wa-card-id">{workflow.id}</span>
                <span 
                  className="wa-risk-badge" 
                  style={{ 
                    backgroundColor: `${getRiskColor(workflow.riskLevel)}20`,
                    color: getRiskColor(workflow.riskLevel),
                    border: `1px solid ${getRiskColor(workflow.riskLevel)}40`
                  }}
                >
                  {workflow.riskLevel} Risk
                </span>
              </div>
              
              <h3 className="wa-card-title">{workflow.type}</h3>
              <p className="wa-card-details">{workflow.details}</p>
              
              <div className="wa-card-meta">
                <div className="wa-meta-row">
                  <span>Initiated By</span>
                  <span className="wa-meta-value">{workflow.initiator}</span>
                </div>
                <div className="wa-meta-row">
                  <span>Timestamp</span>
                  <span className="wa-meta-value">{workflow.timestamp}</span>
                </div>
                <div className="wa-meta-row">
                  <span>Requirement</span>
                  <span className="wa-meta-value">2nd Approver Needed</span>
                </div>
              </div>

              {workflow.status === 'pending' ? (
                <div className="wa-card-actions">
                  <button 
                    className="wa-btn wa-btn-reject"
                    onClick={() => handleReject(workflow.id)}
                  >
                    <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12"></path></svg>
                    Reject
                  </button>
                  <button 
                    className="wa-btn wa-btn-approve"
                    onClick={() => handleApprove(workflow.id)}
                  >
                    <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7"></path></svg>
                    Approve
                  </button>
                </div>
              ) : (
                <div className={`wa-status-badge wa-status-${workflow.status}`}>
                  {workflow.status}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default WorkflowApprovals;
