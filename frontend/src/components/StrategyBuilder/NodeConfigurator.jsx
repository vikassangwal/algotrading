import React from 'react';
import { X, Sliders } from 'lucide-react';

const NodeConfigurator = ({ node, onUpdateProps, onClose }) => {
  
  const handlePropChange = (key, value) => {
    onUpdateProps({ ...node.props, [key]: value });
  };

  return (
    <div style={{ width: '320px', backgroundColor: '#1e293b', borderLeft: '1px solid #334155', display: 'flex', flexDirection: 'column' }}>
      
      {/* Header */}
      <div style={{ padding: '16px 20px', borderBottom: '1px solid #334155', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Sliders size={18} color="#3b82f6" />
          <h2 style={{ fontSize: '15px', fontWeight: 'bold', margin: 0, color: '#e2e8f0' }}>Node Properties</h2>
        </div>
        <button onClick={onClose} style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer' }}>
          <X size={18} />
        </button>
      </div>

      {/* Body */}
      <div style={{ padding: '20px', flex: 1, overflowY: 'auto' }}>
        
        <div style={{ marginBottom: '24px' }}>
          <h3 style={{ fontSize: '18px', color: '#f8fafc', margin: '0 0 4px 0' }}>{node.name}</h3>
          <span style={{ fontSize: '12px', color: '#3b82f6', backgroundColor: 'rgba(59, 130, 246, 0.1)', padding: '2px 8px', borderRadius: '4px' }}>
            {node.category} ({node.type})
          </span>
        </div>

        {Object.keys(node.props).length === 0 ? (
          <p style={{ color: '#64748b', fontSize: '14px', fontStyle: 'italic' }}>This node requires no configuration.</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {Object.entries(node.props).map(([key, value]) => {
              
              // Handle Booleans
              if (typeof value === 'boolean') {
                return (
                  <div key={key} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <label style={{ fontSize: '13px', color: '#cbd5e1', textTransform: 'capitalize' }}>{key}</label>
                    <input 
                      type="checkbox" 
                      checked={value}
                      onChange={(e) => handlePropChange(key, e.target.checked)}
                      style={{ width: '16px', height: '16px', cursor: 'pointer' }}
                    />
                  </div>
                );
              }

              // Handle Numbers
              if (typeof value === 'number') {
                return (
                  <div key={key} style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <label style={{ fontSize: '13px', color: '#cbd5e1', textTransform: 'capitalize' }}>{key}</label>
                    <input 
                      type="number" 
                      value={value}
                      onChange={(e) => handlePropChange(key, parseFloat(e.target.value))}
                      style={{ padding: '8px 12px', backgroundColor: '#0f172a', border: '1px solid #334155', borderRadius: '6px', color: '#f8fafc', outline: 'none' }}
                    />
                  </div>
                );
              }

              // Handle Strings (and Operators)
              return (
                <div key={key} style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <label style={{ fontSize: '13px', color: '#cbd5e1', textTransform: 'capitalize' }}>{key}</label>
                  {key === 'op' || key === 'operator' ? (
                    <select 
                      value={value}
                      onChange={(e) => handlePropChange(key, e.target.value)}
                      style={{ padding: '8px 12px', backgroundColor: '#0f172a', border: '1px solid #334155', borderRadius: '6px', color: '#f8fafc', outline: 'none' }}
                    >
                      <option value=">">Greater Than (&gt;)</option>
                      <option value="<">Less Than (&lt;)</option>
                      <option value="==">Equals (==)</option>
                      <option value=">=">Greater or Equal (&gt;=)</option>
                      <option value="<=">Less or Equal (&lt;=)</option>
                    </select>
                  ) : (
                    <input 
                      type="text" 
                      value={value}
                      onChange={(e) => handlePropChange(key, e.target.value)}
                      style={{ padding: '8px 12px', backgroundColor: '#0f172a', border: '1px solid #334155', borderRadius: '6px', color: '#f8fafc', outline: 'none' }}
                    />
                  )}
                </div>
              );
            })}
          </div>
        )}

      </div>
    </div>
  );
};

export default NodeConfigurator;
