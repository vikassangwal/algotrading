import React, { useState } from 'react';
import { Layers, Settings, Save, Play, Download, Upload, Copy, Share2 } from 'lucide-react';
import ToolboxSidebar from './ToolboxSidebar';
import VisualStrategyTree from './VisualStrategyTree';
import NodeConfigurator from './NodeConfigurator';

const StrategyBuilderLayout = () => {
  // Modes: 'Beginner', 'Advanced', 'Pro', 'Institutional'
  const [builderMode, setBuilderMode] = useState('Beginner');
  const [strategyNodes, setStrategyNodes] = useState([
    { id: 'start', type: 'System', name: 'Market Open', category: 'Time', props: {} }
  ]);
  const [selectedNodeId, setSelectedNodeId] = useState(null);

  const handleDropNode = (nodeData) => {
    const newNode = {
      id: `node_${Date.now()}`,
      type: nodeData.type,
      name: nodeData.name,
      category: nodeData.category,
      props: nodeData.defaultProps || {}
    };
    setStrategyNodes([...strategyNodes, newNode]);
  };

  const handleUpdateNodeProps = (id, newProps) => {
    setStrategyNodes(nodes => nodes.map(n => 
      n.id === id ? { ...n, props: newProps } : n
    ));
  };

  const handleDeleteNode = (id) => {
    if (id === 'start') return; // Cannot delete the root node
    setStrategyNodes(nodes => nodes.filter(n => n.id !== id));
    if (selectedNodeId === id) setSelectedNodeId(null);
  };

  const selectedNode = strategyNodes.find(n => n.id === selectedNodeId);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', backgroundColor: '#0f172a', color: '#f8fafc', fontFamily: 'system-ui, -apple-system, sans-serif' }}>
      
      {/* Top Navigation Bar */}
      <div style={{ height: '60px', borderBottom: '1px solid #334155', display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 20px', backgroundColor: '#1e293b' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
          <Layers size={24} color="#3b82f6" />
          <h1 style={{ fontSize: '18px', margin: 0, fontWeight: 'bold' }}>Visual Strategy Builder</h1>
          <span style={{ backgroundColor: '#334155', padding: '4px 8px', borderRadius: '4px', fontSize: '12px', color: '#94a3b8' }}>Unsaved Strategy*</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
          {/* Mode Switcher */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', backgroundColor: '#0f172a', padding: '4px', borderRadius: '8px', border: '1px solid #334155' }}>
            {['Beginner', 'Advanced', 'Pro', 'Institutional'].map(mode => (
              <button
                key={mode}
                onClick={() => setBuilderMode(mode)}
                style={{
                  padding: '6px 12px',
                  borderRadius: '6px',
                  border: 'none',
                  fontSize: '13px',
                  fontWeight: builderMode === mode ? 'bold' : 'normal',
                  backgroundColor: builderMode === mode ? '#3b82f6' : 'transparent',
                  color: builderMode === mode ? '#fff' : '#94a3b8',
                  cursor: 'pointer',
                  transition: 'all 0.2s'
                }}
              >
                {mode}
              </button>
            ))}
          </div>

          <div style={{ display: 'flex', gap: '10px' }}>
            <button style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '8px 12px', backgroundColor: '#1e293b', border: '1px solid #334155', color: '#f8fafc', borderRadius: '6px', cursor: 'pointer' }}>
              <Save size={16} /> Save
            </button>
            <button style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '8px 12px', backgroundColor: '#10b981', border: 'none', color: '#fff', borderRadius: '6px', cursor: 'pointer', fontWeight: 'bold' }}>
              <Play size={16} /> Backtest
            </button>
          </div>
        </div>
      </div>

      {/* Main Workspace */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        
        {/* Left Sidebar: Toolbox */}
        <ToolboxSidebar mode={builderMode} />

        {/* Center Canvas: Visual Strategy Tree */}
        <div style={{ flex: 1, position: 'relative', overflow: 'auto', backgroundColor: '#0f172a' }}>
          <VisualStrategyTree 
            nodes={strategyNodes} 
            onDropNode={handleDropNode}
            selectedNodeId={selectedNodeId}
            onSelectNode={setSelectedNodeId}
            onDeleteNode={handleDeleteNode}
          />
        </div>

        {/* Right Sidebar: Node Configurator */}
        {selectedNode && (
          <NodeConfigurator 
            node={selectedNode} 
            onUpdateProps={(props) => handleUpdateNodeProps(selectedNode.id, props)}
            onClose={() => setSelectedNodeId(null)}
          />
        )}

      </div>
    </div>
  );
};

export default StrategyBuilderLayout;
