import React from 'react';
import { ArrowDown, Plus, Trash2, Settings } from 'lucide-react';

const VisualStrategyTree = ({ nodes, onDropNode, selectedNodeId, onSelectNode, onDeleteNode }) => {
  
  const handleDragOver = (e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
  };

  const handleDrop = (e) => {
    e.preventDefault();
    try {
      const data = e.dataTransfer.getData('application/json');
      if (data) {
        const nodeData = JSON.parse(data);
        onDropNode(nodeData);
      }
    } catch (err) {
      console.error("Drop failed", err);
    }
  };

  return (
    <div 
      style={{ minHeight: '100%', padding: '40px', display: 'flex', flexDirection: 'column', alignItems: 'center' }}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      <div style={{ textAlign: 'center', marginBottom: '30px' }}>
        <h2 style={{ fontSize: '20px', color: '#e2e8f0', margin: '0 0 8px 0' }}>Visual Strategy Flow</h2>
        <p style={{ color: '#64748b', fontSize: '14px', margin: 0 }}>Drag blocks from the toolbox to build your logic</p>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        {nodes.map((node, index) => {
          const isSelected = selectedNodeId === node.id;
          const isRoot = node.id === 'start';
          
          return (
            <React.Fragment key={node.id}>
              {/* Connecting Arrow */}
              {index > 0 && (
                <div style={{ height: '40px', width: '2px', backgroundColor: '#334155', position: 'relative' }}>
                  <ArrowDown size={14} color="#334155" style={{ position: 'absolute', bottom: '-4px', left: '-6px' }} />
                </div>
              )}

              {/* Node Card */}
              <div 
                onClick={() => onSelectNode(node.id)}
                style={{
                  width: '300px',
                  backgroundColor: isSelected ? 'rgba(59, 130, 246, 0.1)' : '#1e293b',
                  border: `1px solid ${isSelected ? '#3b82f6' : '#334155'}`,
                  borderRadius: '8px',
                  padding: '16px',
                  cursor: 'pointer',
                  position: 'relative',
                  boxShadow: isSelected ? '0 0 0 2px rgba(59, 130, 246, 0.2)' : '0 4px 6px rgba(0,0,0,0.1)',
                  transition: 'all 0.2s',
                  marginTop: index > 0 ? '12px' : '0'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <span style={{ fontSize: '10px', textTransform: 'uppercase', color: '#3b82f6', fontWeight: 'bold', letterSpacing: '0.5px' }}>
                      {node.category}
                    </span>
                    <h3 style={{ margin: '4px 0 0 0', fontSize: '15px', color: '#f8fafc' }}>{node.name}</h3>
                  </div>
                  
                  {/* Actions */}
                  <div style={{ display: 'flex', gap: '6px' }}>
                    <button style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', padding: '2px' }}>
                      <Settings size={14} />
                    </button>
                    {!isRoot && (
                      <button 
                        onClick={(e) => { e.stopPropagation(); onDeleteNode(node.id); }}
                        style={{ background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer', padding: '2px' }}
                      >
                        <Trash2 size={14} />
                      </button>
                    )}
                  </div>
                </div>

                {/* Props summary preview */}
                {Object.keys(node.props).length > 0 && (
                  <div style={{ marginTop: '12px', padding: '8px', backgroundColor: '#0f172a', borderRadius: '4px', fontSize: '12px', color: '#cbd5e1' }}>
                    {Object.entries(node.props).map(([k, v]) => (
                      <span key={k} style={{ marginRight: '10px' }}>
                        <span style={{ color: '#64748b' }}>{k}:</span> {v.toString()}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </React.Fragment>
          );
        })}

        {/* Drop Zone Placeholder at the bottom */}
        <div style={{ height: '40px', width: '2px', backgroundColor: '#334155', position: 'relative' }}>
          <ArrowDown size={14} color="#334155" style={{ position: 'absolute', bottom: '-4px', left: '-6px' }} />
        </div>
        
        <div style={{
          marginTop: '12px',
          width: '300px',
          border: '2px dashed #334155',
          borderRadius: '8px',
          padding: '20px',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#64748b',
          backgroundColor: 'rgba(30, 41, 59, 0.5)'
        }}>
          <Plus size={20} style={{ marginBottom: '8px' }} />
          <span style={{ fontSize: '13px' }}>Drag here to add next step</span>
        </div>

      </div>
    </div>
  );
};

export default VisualStrategyTree;
