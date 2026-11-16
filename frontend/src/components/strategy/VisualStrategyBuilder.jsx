import { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { clsx } from '../../design-system';
import { Button, Select, Input, Card, CardHeader, CardContent, Modal, Badge, Table } from '../ui';

// Node types for strategy building
const NODE_TYPES = {
  // Data sources
  price: { category: 'Data', label: 'Price', icon: '📈', color: '#6366f1', inputs: 0, outputs: 1, params: ['symbol', 'timeframe'] },
  volume: { category: 'Data', label: 'Volume', icon: '📊', color: '#0ea5e9', inputs: 0, outputs: 1, params: [] },
  indicator: { category: 'Indicators', label: 'Technical Indicator', icon: '📐', color: '#a855f7', inputs: 1, outputs: 1, params: ['type', 'period'] },

  // Indicators
  sma: { category: 'Indicators', label: 'SMA', icon: '📈', color: '#6366f1', inputs: 1, outputs: 1, params: ['period'] },
  ema: { category: 'Indicators', label: 'EMA', icon: '📈', color: '#0ea5e9', inputs: 1, outputs: 1, params: ['period'] },
  rsi: { category: 'Indicators', label: 'RSI', icon: '📊', color: '#a855f7', inputs: 1, outputs: 1, params: ['period', 'overbought', 'oversold'] },
  macd: { category: 'Indicators', label: 'MACD', icon: '📊', color: '#f59e0b', inputs: 1, outputs: 3, params: ['fast', 'slow', 'signal'] }, // macd, signal, histogram
  bollinger: { category: 'Indicators', label: 'Bollinger Bands', icon: '📊', color: '#ef4444', inputs: 1, outputs: 3, params: ['period', 'stdDev'] }, // upper, middle, lower
  vwap: { category: 'Indicators', label: 'VWAP', icon: '📊', color: '#10b981', inputs: 1, outputs: 1, params: [] },
  atr: { category: 'Indicators', label: 'ATR', icon: '📊', color: '#fb923c', inputs: 1, outputs: 1, params: ['period'] },

  // Logic
  compare: { category: 'Logic', label: 'Compare', icon: '⚖️', color: '#8b5cf6', inputs: 2, outputs: 1, params: ['operator'] },
  crossover: { category: 'Logic', label: 'Crossover', icon: '⤴', color: '#7c3aed', inputs: 2, outputs: 1, params: ['direction'] },
  and: { category: 'Logic', label: 'AND', icon: '∧', color: '#6d28d9', inputs: 2, outputs: 1, params: [] },
  or: { category: 'Logic', label: 'OR', icon: '∨', color: '#5b21b6', inputs: 2, outputs: 1, params: [] },
  not: { category: 'Logic', label: 'NOT', icon: '¬', color: '#4c1d95', inputs: 1, outputs: 1, params: [] },

  // Math
  add: { category: 'Math', label: 'Add', icon: '+', color: '#10b981', inputs: 2, outputs: 1, params: [] },
  subtract: { category: 'Math', label: 'Subtract', icon: '−', color: '#ef4444', inputs: 2, outputs: 1, params: [] },
  multiply: { category: 'Math', label: 'Multiply', icon: '×', color: '#f59e0b', inputs: 2, outputs: 1, params: [] },
  divide: { category: 'Math', label: 'Divide', icon: '÷', color: '#0ea5e9', inputs: 2, outputs: 1, params: [] },

  // Actions
  buy: { category: 'Actions', label: 'Buy', icon: '🟢', color: '#10b981', inputs: 1, outputs: 0, params: ['quantity', 'type', 'stopLoss', 'takeProfit'] },
  sell: { category: 'Actions', label: 'Sell', icon: '🔴', color: '#ef4444', inputs: 1, outputs: 0, params: ['quantity', 'type', 'stopLoss', 'takeProfit'] },
  close: { category: 'Actions', label: 'Close Position', icon: '⚪', color: '#6b7280', inputs: 1, outputs: 0, params: [] },
  alert: { category: 'Actions', label: 'Alert', icon: '🔔', color: '#8b5cf6', inputs: 1, outputs: 0, params: ['message', 'severity'] },

  // Risk
  positionSize: { category: 'Risk', label: 'Position Size', icon: '📏', color: '#0ea5e9', inputs: 1, outputs: 1, params: ['riskPercent', 'method'] },
  riskReward: { category: 'Risk', label: 'Risk/Reward', icon: '⚖️', color: '#6366f1', inputs: 1, outputs: 1, params: ['ratio'] },
  trailingStop: { category: 'Risk', label: 'Trailing Stop', icon: '🔻', color: '#ef4444', inputs: 1, outputs: 0, params: ['activation', 'trailPercent'] },
};

// Categorized nodes for palette
const NODE_CATEGORIES = useMemo(() => {
  const cats = {};
  Object.entries(NODE_TYPES).forEach(([key, node]) => {
    if (!cats[node.category]) cats[node.category] = [];
    cats[node.category].push({ ...node, type: key });
  });
  return cats;
}, []);

export function VisualStrategyBuilder({
  token,
  initialStrategy,
  onSave,
  onBacktest,
  className = '',
  style = {},
  ...props
}) {
  const [nodes, setNodes] = useState(initialStrategy?.nodes || []);
  const [edges, setEdges] = useState(initialStrategy?.edges || []);
  const [selectedNodeId, setSelectedNodeId] = useState(null);
  const [viewport, setViewport] = useState({ x: 0, y: 0, zoom: 1 });
  const [showGrid, setShowGrid] = useState(true);
  const [snapToGrid, setSnapToGrid] = useState(true);
  const [history, setHistory] = useState([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const [isExecuting, setIsExecuting] = useState(false);
  const [validationErrors, setValidationErrors] = useState([]);

  const canvasRef = useRef(null);
  const nodeRefs = useRef({});
  const dragRef = useRef({ nodeId: null, offsetX: 0, offsetY: 0 });
  const connectionRef = useRef({ sourceNode: null, sourceOutput: null, targetNode: null, targetInput: null });

  const GRID_SIZE = 20;
  const NODE_WIDTH = 200;
  const NODE_HEIGHT = 120;

  // Save to history for undo/redo
  const saveToHistory = useCallback((newNodes, newEdges) => {
    setHistory(prev => {
      const newHistory = prev.slice(0, historyIndex + 1);
      newHistory.push({ nodes: newNodes, edges: newEdges });
      if (newHistory.length > 50) newHistory.shift();
      return newHistory;
    });
    setHistoryIndex(prev => Math.min(prev + 1, 49));
  }, [historyIndex]);

  // Update nodes
  const updateNodes = useCallback((updater) => {
    setNodes(prev => {
      const newNodes = typeof updater === 'function' ? updater(prev) : updater;
      saveToHistory(newNodes, edges);
      return newNodes;
    });
  }, [edges, saveToHistory]);

  // Update edges
  const updateEdges = useCallback((updater) => {
    setEdges(prev => {
      const newEdges = typeof updater === 'function' ? updater(prev) : updater;
      saveToHistory(nodes, newEdges);
      return newEdges;
    });
  }, [nodes, saveToHistory]);

  // Add node
  const addNode = useCallback((type, position) => {
    const nodeType = NODE_TYPES[type];
    if (!nodeType) return;

    const newNode = {
      id: `node_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      type,
      position: { x: position.x, y: position.y },
      params: { ...nodeType.params.reduce((acc, p) => ({ ...acc, [p]: '' }), {}) },
      data: {},
    };

    updateNodes(prev => [...prev, newNode]);
    return newNode.id;
  }, [updateNodes]);

  // Delete node
  const deleteNode = useCallback((nodeId) => {
    updateNodes(prev => prev.filter(n => n.id !== nodeId));
    updateEdges(prev => prev.filter(e => e.source !== nodeId && e.target !== nodeId));
  }, [updateNodes, updateEdges]);

  // Update node params
  const updateNodeParams = useCallback((nodeId, params) => {
    updateNodes(prev => prev.map(n => n.id === nodeId ? { ...n, params: { ...n.params, ...params } } : n));
  }, [updateNodes]);

  // Update node position
  const updateNodePosition = useCallback((nodeId, position) => {
    if (snapToGrid) {
      position = {
        x: Math.round(position.x / GRID_SIZE) * GRID_SIZE,
        y: Math.round(position.y / GRID_SIZE) * GRID_SIZE,
      };
    }
    updateNodes(prev => prev.map(n => n.id === nodeId ? { ...n, position } : n));
  }, [updateNodes, snapToGrid]);

  // Handle edge creation
  const handleOutputClick = useCallback((nodeId, outputIndex, event) => {
    event.stopPropagation();
    connectionRef.current = { sourceNode: nodeId, sourceOutput: outputIndex, targetNode: null, targetInput: null };
  }, []);

  const handleInputClick = useCallback((nodeId, inputIndex, event) => {
    event.stopPropagation();
    const { sourceNode, sourceOutput } = connectionRef.current;
    if (sourceNode && sourceNode !== nodeId) {
      // Check if connection already exists
      const exists = edges.some(e =>
        e.source === sourceNode && e.target === nodeId &&
        e.sourceOutput === sourceOutput && e.targetInput === inputIndex
      );
      if (!exists) {
        updateEdges(prev => [...prev, {
          id: `edge_${Date.now()}`,
          source: sourceNode,
          target: nodeId,
          sourceOutput,
          targetInput: inputIndex,
        }]);
      }
    }
    connectionRef.current = { sourceNode: null, sourceOutput: null, targetNode: null, targetInput: null };
  }, [edges, updateEdges]);

  // Delete edge
  const deleteEdge = useCallback((edgeId) => {
    updateEdges(prev => prev.filter(e => e.id !== edgeId));
  }, [updateEdges]);

  // Canvas mouse handlers
  const handleCanvasMouseDown = useCallback((e) => {
    if (e.target === canvasRef.current) {
      setSelectedNodeId(null);
    }
  }, []);

  const handleCanvasDoubleClick = useCallback((e) => {
    if (e.target === canvasRef.current) {
      const rect = canvasRef.current.getBoundingClientRect();
      const x = (e.clientX - rect.left - viewport.x) / viewport.zoom;
      const y = (e.clientY - rect.top - viewport.y) / viewport.zoom;
      // Show quick add menu at position
    }
  }, [viewport]);

  // Pan and zoom
  const handleWheel = useCallback((e) => {
    e.preventDefault();
    const rect = canvasRef.current.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1;
    const newZoom = Math.max(0.1, Math.min(3, viewport.zoom * zoomFactor));

    setViewport(prev => ({
      x: mouseX - (mouseX - prev.x) * (newZoom / prev.zoom),
      y: mouseY - (mouseY - prev.y) * (newZoom / prev.zoom),
      zoom: newZoom,
    }));
  }, [viewport]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

      if ((e.ctrlKey || e.metaKey) && e.key === 'z') {
        e.preventDefault();
        if (e.shiftKey) {
          // Redo
          if (historyIndex < history.length - 1) {
            const next = history[historyIndex + 1];
            setNodes(next.nodes);
            setEdges(next.edges);
            setHistoryIndex(i => i + 1);
          }
        } else {
          // Undo
          if (historyIndex > 0) {
            const prev = history[historyIndex - 1];
            setNodes(prev.nodes);
            setEdges(prev.edges);
            setHistoryIndex(i => i - 1);
          }
        }
      }

      if (e.key === 'Delete' || e.key === 'Backspace') {
        if (selectedNodeId) {
          deleteNode(selectedNodeId);
          setSelectedNodeId(null);
        }
      }

      if (e.key === 'Escape') {
        setSelectedNodeId(null);
        connectionRef.current = { sourceNode: null, sourceOutput: null, targetNode: null, targetInput: null };
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [history, historyIndex, selectedNodeId, deleteNode]);

  // Validate strategy
  const validateStrategy = useCallback(() => {
    const errors = [];

    // Check for buy/sell nodes
    const actionNodes = nodes.filter(n => ['buy', 'sell', 'close', 'alert'].includes(n.type));
    if (actionNodes.length === 0) {
      errors.push('Strategy must have at least one action node (Buy/Sell/Close/Alert)');
    }

    // Check for disconnected nodes (except data sources)
    nodes.forEach(node => {
      const nodeType = NODE_TYPES[node.type];
      if (nodeType.inputs > 0) {
        const hasInput = edges.some(e => e.target === node.id);
        if (!hasInput) {
          errors.push(`${nodeType.label} node "${node.id.slice(0,8)}" has no input connection`);
        }
      }
    });

    setValidationErrors(errors);
    return errors.length === 0;
  }, [nodes, edges]);

  // Generate strategy code
  const generateCode = useCallback(() => {
    // Topological sort to determine execution order
    const visited = new Set();
    const order = [];

    const visit = (nodeId) => {
      if (visited.has(nodeId)) return;
      visited.add(nodeId);

      // Visit dependencies first
      edges.filter(e => e.target === nodeId).forEach(e => visit(e.source));
      order.push(nodeId);
    };

    nodes.forEach(n => visit(n.id));

    // Generate Python code
    let code = `# Generated Strategy\nfrom elco.strategy import StrategyBase\n\nclass GeneratedStrategy(StrategyBase):\n    def __init__(self):\n        super().__init__()\n`;

    order.forEach(nodeId => {
      const node = nodes.find(n => n.id === nodeId);
      if (!node) return;

      const nodeType = NODE_TYPES[node.type];
      code += `    # ${nodeType.label} (${node.id.slice(0,8)})\n`;

      switch (node.type) {
        case 'price':
          code += `    self.price = self.data.price('${node.params.symbol || 'SYMBOL'}', '${node.params.timeframe || '15m'}')\n`;
          break;
        case 'sma':
          code += `    self.sma_${node.params.period || 20} = self.indicator.sma(${node.params.period || 20})\n`;
          break;
        case 'rsi':
          code += `    self.rsi = self.indicator.rsi(${node.params.period || 14}, ${node.params.overbought || 70}, ${node.params.oversold || 30})\n`;
          break;
        case 'compare':
          code += `    self.condition_${node.id.slice(0,8)} = self.logic.compare('${node.params.operator || '>'}')\n`;
          break;
        case 'crossover':
          code += `    self.crossover_${node.id.slice(0,8)} = self.logic.crossover('${node.params.direction || 'up'}')\n`;
          break;
        case 'buy':
          code += `    if self.condition: self.buy(qty=${node.params.quantity || 1}, type='${node.params.type || 'MARKET'}', sl=${node.params.stopLoss || 'None'}, tp=${node.params.takeProfit || 'None'})\n`;
          break;
        case 'sell':
          code += `    if self.condition: self.sell(qty=${node.params.quantity || 1}, type='${node.params.type || 'MARKET'}', sl=${node.params.stopLoss || 'None'}, tp=${node.params.takeProfit || 'None'})\n`;
          break;
      }
    });

    return code;
  }, [nodes, edges]);

  // Handle backtest
  const handleBacktest = useCallback(async () => {
    if (!validateStrategy()) return;

    setIsExecuting(true);
    try {
      const code = generateCode();
      const res = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/strategy/backtest`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ code, symbol: 'NIFTY', timeframe: '15m' }),
      });
      const result = await res.json();
      // Show results modal
      console.log('Backtest result:', result);
    } catch (err) {
      console.error('Backtest error:', err);
    } finally {
      setIsExecuting(false);
    }
  }, [token, validateStrategy, generateCode]);

  // Handle save
  const handleSave = useCallback(() => {
    const strategy = { nodes, edges, viewport };
    onSave?.(strategy);
  }, [nodes, edges, viewport, onSave]);

  // Get node at position for connection preview
  const getConnectionPath = useCallback((source, target) => {
    if (!source || !target) return '';

    const sourceNode = nodeRefs.current[source.nodeId];
    const targetNode = nodeRefs.current[target.nodeId];
    if (!sourceNode || !targetNode) return '';

    const sourceRect = sourceNode.getBoundingClientRect();
    const targetRect = targetNode.getBoundingClientRect();
    const canvasRect = canvasRef.current.getBoundingClientRect();

    const startX = sourceRect.right - canvasRect.left;
    const startY = sourceRect.top + sourceRect.height / 2 - canvasRect.top;
    const endX = targetRect.left - canvasRect.left;
    const endY = targetRect.top + targetRect.height / 2 - canvasRect.top;

    const midX = (startX + endX) / 2;

    return `M ${startX} ${startY} C ${midX} ${startY} ${midX} ${endY} ${endX} ${endY}`;
  }, []);

  // Connection preview path
  const previewPath = connectionRef.current.sourceNode ? getConnectionPath(
    { nodeId: connectionRef.current.sourceNode, output: connectionRef.current.sourceOutput },
    { nodeId: connectionRef.current.targetNode || connectionRef.current.sourceNode, input: connectionRef.current.targetInput }
  ) : '';

  return (
    <div className={clsx('elco-strategy-builder', className)} style={{ ...style, height: '100%', display: 'flex', flexDirection: 'column', ...props }}>
      {/* Toolbar */}
      <div className="elco-builder-toolbar" style={{
        display: 'flex',
        alignItems: 'center',
        gap: 'var(--space-3)',
        padding: 'var(--space-3) var(--space-4)',
        background: 'var(--color-surface-panel)',
        borderBottom: '1px solid var(--color-surface-border)',
        flexWrap: 'wrap',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
          <Button variant="ghost" size="sm" onClick={() => { if (historyIndex > 0) { const prev = history[historyIndex - 1]; setNodes(prev.nodes); setEdges(prev.edges); setHistoryIndex(i => i - 1); }} } disabled={historyIndex <= 0} leftIcon={<UndoIcon />} />
          <Button variant="ghost" size="sm" onClick={() => { if (historyIndex < history.length - 1) { const next = history[historyIndex + 1]; setNodes(next.nodes); setEdges(next.edges); setHistoryIndex(i => i + 1); }} } disabled={historyIndex >= history.length - 1} leftIcon={<RedoIcon />} />
        </div>

        <div style={{ width: '1px', height: '24px', background: 'var(--color-surface-border)', margin: '0 var(--space-2)' }} />

        <Button variant={validationErrors.length ? 'danger' : 'ghost'} size="sm" onClick={validateStrategy} leftIcon={<CheckIcon />}>
          Validate
          {validationErrors.length && <Badge variant="danger" size="sm">{validationErrors.length}</Badge>}
        </Button>

        <Button variant="ghost" size="sm" onClick={handleSave} leftIcon={<SaveIcon />}>Save</Button>

        <Button variant="outline" size="sm" onClick={handleBacktest} loading={isExecuting} leftIcon={<PlayIcon />}>Backtest</Button>

        <Button variant="primary" size="sm" onClick={() => { const code = generateCode(); navigator.clipboard.writeText(code); }} leftIcon={<CodeIcon />}>Export Code</Button>

        <div style={{ flex: 1 }} />

        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', fontSize: 'var(--font-size-xs)', color: 'var(--color-text-tertiary)' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-1)' }}>
            <input type="checkbox" checked={showGrid} onChange={e => setShowGrid(e.target.checked)} />
            Grid
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-1)' }}>
            <input type="checkbox" checked={snapToGrid} onChange={e => setSnapToGrid(e.target.checked)} />
            Snap
          </label>
          <span>{Math.round(viewport.zoom * 100)}%</span>
          <Button variant="ghost" size="iconSm" onClick={() => setViewport({ x: 0, y: 0, zoom: 1 })} aria-label="Reset view"><ZoomResetIcon /></Button>
        </div>
      </div>

      {/* Main Area */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {/* Node Palette */}
        <div className="elco-node-palette" style={{
          width: '280px',
          background: 'var(--color-surface-panel)',
          borderRight: '1px solid var(--color-surface-border)',
          overflow: 'auto',
          padding: 'var(--space-3)',
        }}>
          <div style={{ fontSize: 'var(--font-size-xs)', fontWeight: 'var(--font-weight-semibold)', color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: 'var(--letter-spacing-wider)', marginBottom: 'var(--space-3)' }}>
            Node Library
          </div>
          <Input placeholder="Search nodes..." size="sm" style={{ marginBottom: 'var(--space-3)' }} leftIcon={<SearchIcon />} />

          {Object.entries(NODE_CATEGORIES).map(([category, nodeTypes]) => (
            <div key={category} style={{ marginBottom: 'var(--space-4)' }}>
              <div style={{ fontSize: 'var(--font-size-xs)', fontWeight: 'var(--font-weight-medium)', color: 'var(--color-text-tertiary)', textTransform: 'uppercase', marginBottom: 'var(--space-2)', padding: '0 var(--space-2)' }}>
                {category}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-1)' }}>
                {nodeTypes.map(nodeType => (
                  <button
                    key={nodeType.type}
                    onClick={() => {
                      const centerX = (canvasRef.current?.clientWidth || 800) / 2 / viewport.zoom - viewport.x / viewport.zoom;
                      const centerY = (canvasRef.current?.clientHeight || 600) / 2 / viewport.zoom - viewport.y / viewport.zoom;
                      addNode(nodeType.type, { x: centerX - 100, y: centerY - 60 });
                    }}
                    draggable
                    onDragStart={(e) => {
                      e.dataTransfer.setData('node-type', nodeType.type);
                      e.dataTransfer.effectAllowed = 'copy';
                    }}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 'var(--space-2)',
                      padding: 'var(--space-2) var(--space-3)',
                      background: 'var(--color-surface-interactive)',
                      border: '1px solid var(--color-surface-border)',
                      borderRadius: 'var(--radius-md)',
                      color: 'var(--color-text-primary)',
                      fontSize: 'var(--font-size-sm)',
                      cursor: 'grab',
                      textAlign: 'left',
                      transition: 'all var(--transition-fast)',
                    }}
                    onMouseEnter={(e) => { e.target.style.borderColor = nodeType.color; e.target.style.background = 'var(--color-surface-panel-hover)'; }}
                    onMouseLeave={(e) => { e.target.style.borderColor = 'var(--color-surface-border)'; e.target.style.background = 'var(--color-surface-interactive)'; }}
                  >
                    <span style={{ fontSize: '18px' }}>{nodeType.icon}</span>
                    <span style={{ flex: 1 }}>{nodeType.label}</span>
                    <Badge variant="ghost" size="sm" style={{ background: nodeType.color, color: nodeType.color }}>
                      {nodeType.inputs}▶{nodeType.outputs}
                    </Badge>
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Canvas */}
        <div className="elco-canvas-wrapper" style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
          <div
            ref={canvasRef}
            className="elco-canvas"
            style={{
              width: '100%',
              height: '100%',
              transform: `translate(${viewport.x}px, ${viewport.y}px) scale(${viewport.zoom})`,
              transformOrigin: '0 0',
              background: showGrid
                ? `linear-gradient(var(--color-surface-border) 1px, transparent 1px) 0 0, linear-gradient(90deg, var(--color-surface-border) 1px, transparent 1px) 0 0`
                : 'var(--color-surface-base)',
              backgroundSize: `${GRID_SIZE * viewport.zoom}px ${GRID_SIZE * viewport.zoom}px`,
              backgroundColor: 'var(--color-surface-base)',
              transition: 'transform var(--transition-fast)',
            }}
            onMouseDown={handleCanvasMouseDown}
            onDoubleClick={handleCanvasDoubleClick}
            onWheel={handleWheel}
            onDragOver={(e) => { e.preventDefault(); e.dataTransfer.dropEffect = 'copy'; }}
            onDrop={(e) => {
              e.preventDefault();
              const type = e.dataTransfer.getData('node-type');
              if (type && NODE_TYPES[type]) {
                const rect = canvasRef.current.getBoundingClientRect();
                const x = (e.clientX - rect.left - viewport.x) / viewport.zoom;
                const y = (e.clientY - rect.top - viewport.y) / viewport.zoom;
                addNode(type, { x, y });
              }
            }}
          >
            {/* Connection Preview */}
            {previewPath && (
              <svg style={{ position: 'absolute', inset: 0, pointerEvents: 'none', zIndex: 10 }}>
                <path d={previewPath} stroke="var(--color-brand-500)" strokeWidth="2" fill="none" strokeDasharray="8,4" style={{ filter: 'drop-shadow(0 0 4px var(--color-brand-500))' }} />
                <defs>
                  <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
                    <polygon points="0 0, 10 3.5, 0 7" fill="var(--color-brand-500)" />
                  </marker>
                </defs>
              </svg>
            )}

            {/* Edges */}
            <svg style={{ position: 'absolute', inset: 0, pointerEvents: 'none', zIndex: 5 }}>
              {edges.map(edge => {
                const sourceNode = nodeRefs.current[edge.source];
                const targetNode = nodeRefs.current[edge.target];
                if (!sourceNode || !targetNode) return null;

                const sourceRect = sourceNode.getBoundingClientRect();
                const targetRect = targetNode.getBoundingClientRect();
                const canvasRect = canvasRef.current.getBoundingClientRect();

                const startX = sourceRect.right - canvasRect.left;
                const startY = sourceRect.top + sourceRect.height / 2 - canvasRect.top;
                const endX = targetRect.left - canvasRect.left;
                const endY = targetRect.top + targetRect.height / 2 - canvasRect.top;

                const midX = (startX + endX) / 2;
                const path = `M ${startX} ${startY} C ${midX} ${startY} ${midX} ${endY} ${endX} ${endY}`;

                return (
                  <g key={edge.id}>
                    <path d={path} stroke="var(--color-surface-border-strong)" strokeWidth="2" fill="none" markerEnd="url(#arrowhead)" />
                    <defs>
                      <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
                        <polygon points="0 0, 10 3.5, 0 7" fill="var(--color-surface-border-strong)" />
                      </marker>
                    </defs>
                  </g>
                );
              })}
            </svg>

            {/* Nodes */}
            {nodes.map(node => {
              const nodeType = NODE_TYPES[node.type];
              const isSelected = selectedNodeId === node.id;

              return (
                <div
                  key={node.id}
                  ref={(el) => { nodeRefs.current[node.id] = el; }}
                  className="elco-node"
                  style={{
                    position: 'absolute',
                    left: node.position.x,
                    top: node.position.y,
                    width: NODE_WIDTH,
                    minHeight: NODE_HEIGHT,
                    background: 'var(--color-surface-panel)',
                    border: isSelected ? '2px solid var(--color-brand-500)' : `1px solid ${nodeType.color}`,
                    borderRadius: 'var(--radius-lg)',
                    boxShadow: isSelected ? 'var(--shadow-glow-brand)' : 'var(--shadow-md)',
                    zIndex: isSelected ? 10 : 5,
                    transition: 'all var(--transition-fast)',
                    userSelect: 'none',
                  }}
                  onClick={(e) => { e.stopPropagation(); setSelectedNodeId(node.id); }}
                  onMouseDown={(e) => {
                    if (e.target.classList.contains('elco-node-handle')) return;
                    dragRef.current = {
                      nodeId: node.id,
                      offsetX: e.clientX - node.position.x * viewport.zoom - viewport.x,
                      offsetY: e.clientY - node.position.y * viewport.zoom - viewport.y,
                    };
                    setSelectedNodeId(node.id);
                  }}
                >
                  {/* Node Header */}
                  <div className="elco-node-header" style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 'var(--space-2)',
                    padding: 'var(--space-2) var(--space-3)',
                    background: nodeType.color,
                    borderRadius: 'var(--radius-lg) var(--radius-lg) 0 0',
                    color: 'white',
                  }}>
                    <span style={{ fontSize: '16px' }}>{nodeType.icon}</span>
                    <span style={{ fontWeight: 'var(--font-weight-semibold)', flex: 1 }}>{nodeType.label}</span>
                    <button
                      className="elco-node-handle"
                      onClick={(e) => { e.stopPropagation(); deleteNode(node.id); }}
                      style={{
                        width: '20px', height: '20px', display: 'flex', alignItems: 'center', justifyContent: 'center',
                        background: 'rgba(255,255,255,0.2)', border: 'none', borderRadius: 'var(--radius-sm)',
                        color: 'white', cursor: 'pointer', padding: 0,
                      }}
                      aria-label="Delete node"
                    >
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
                    </button>
                  </div>

                  {/* Input Handles */}
                  {nodeType.inputs > 0 && (
                    <div className="elco-node-inputs" style={{ position: 'absolute', left: -8, top: '40px', display: 'flex', flexDirection: 'column', gap: 'var(--space-3)', paddingLeft: '8px' }}>
                      {Array.from({ length: nodeType.inputs }, (_, i) => (
                        <div
                          key={i}
                          className="elco-node-handle input"
                          onClick={(e) => handleInputClick(node.id, i, e)}
                          style={{
                            width: '16px', height: '16px', borderRadius: '50%',
                            background: 'var(--color-surface-panel)', border: '2px solid var(--color-brand-500)',
                            cursor: 'pointer', transition: 'all var(--transition-fast)',
                            boxShadow: '0 0 0 2px var(--color-surface-base)',
                          }}
                          onMouseEnter={(e) => { e.target.style.background = 'var(--color-brand-500)'; e.target.style.transform = 'scale(1.2)'; }}
                          onMouseLeave={(e) => { e.target.style.background = 'var(--color-surface-panel)'; e.target.style.transform = 'scale(1)'; }}
                        />
                      ))}
                    </div>
                  )}

                  {/* Output Handles */}
                  {nodeType.outputs > 0 && (
                    <div className="elco-node-outputs" style={{ position: 'absolute', right: -8, top: '40px', display: 'flex', flexDirection: 'column', gap: 'var(--space-3)', paddingRight: '8px' }}>
                      {Array.from({ length: nodeType.outputs }, (_, i) => (
                        <div
                          key={i}
                          className="elco-node-handle output"
                          onClick={(e) => handleOutputClick(node.id, i, e)}
                          style={{
                            width: '16px', height: '16px', borderRadius: '50%',
                            background: 'var(--color-brand-500)', border: '2px solid var(--color-surface-base)',
                            cursor: 'pointer', transition: 'all var(--transition-fast)',
                          }}
                          onMouseEnter={(e) => { e.target.style.transform = 'scale(1.2)'; e.target.style.boxShadow = '0 0 8px var(--color-brand-500)'; }}
                          onMouseLeave={(e) => { e.target.style.transform = 'scale(1)'; e.target.style.boxShadow = 'none'; }}
                        />
                      ))}
                    </div>
                  )}

                  {/* Node Content */}
                  <div className="elco-node-content" style={{ padding: 'var(--space-3)' }}>
                    {nodeType.params.length > 0 && (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
                        {nodeType.params.map(param => (
                          <Input
                            key={param}
                            label={param.charAt(0).toUpperCase() + param.slice(1)}
                            value={node.params[param] || ''}
                            onChange={(e) => updateNodeParams(node.id, { [param]: e.target.value })}
                            size="sm"
                            placeholder={param}
                          />
                        ))}
                      </div>
                    )}
                    {nodeType.params.length === 0 && (
                      <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-tertiary)', textAlign: 'center', padding: 'var(--space-2)' }}>
                        No parameters
                      </p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Properties Panel */}
        {selectedNodeId && (
          <div className="elco-properties-panel" style={{
            width: '300px',
            background: 'var(--color-surface-panel)',
            borderLeft: '1px solid var(--color-surface-border)',
            overflow: 'auto',
            padding: 'var(--space-4)',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-4)' }}>
              <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 'var(--font-weight-semibold)' }}>Properties</h3>
              <button onClick={() => setSelectedNodeId(null)} style={{ background: 'none', border: 'none', color: 'var(--color-text-tertiary)', cursor: 'pointer' }}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
              </button>
            </div>

            {(() => {
              const node = nodes.find(n => n.id === selectedNodeId);
              if (!node) return null;
              const nodeType = NODE_TYPES[node.type];

              return (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
                  <div style={{ padding: 'var(--space-3)', background: 'var(--color-surface-interactive)', borderRadius: 'var(--radius-md)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginBottom: 'var(--space-2)' }}>
                      <span style={{ fontSize: '24px' }}>{nodeType.icon}</span>
                      <span style={{ fontWeight: 'var(--font-weight-semibold)', fontSize: 'var(--font-size-lg)' }}>{nodeType.label}</span>
                    </div>
                    <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)' }}>
                      Category: {nodeType.category}
                    </div>
                    <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)', marginTop: 'var(--space-1)' }}>
                      ID: {node.id}
                    </div>
                  </div>

                  {nodeType.params.length > 0 && (
                    <div>
                      <h4 style={{ fontSize: 'var(--font-size-sm)', fontWeight: 'var(--font-weight-semibold)', color: 'var(--color-text-secondary)', textTransform: 'uppercase', marginBottom: 'var(--space-2)' }}>Parameters</h4>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
                        {nodeType.params.map(param => (
                          <Input
                            key={param}
                            label={param.charAt(0).toUpperCase() + param.slice(1)}
                            value={node.params[param] || ''}
                            onChange={(e) => updateNodeParams(node.id, { [param]: e.target.value })}
                            size="sm"
                          />
                        ))}
                      </div>
                    </div>
                  )}

                  <div style={{ borderTop: '1px solid var(--color-surface-border)', paddingTop: 'var(--space-3)' }}>
                    <h4 style={{ fontSize: 'var(--font-size-sm)', fontWeight: 'var(--font-weight-semibold)', color: 'var(--color-text-secondary)', textTransform: 'uppercase', marginBottom: 'var(--space-2)' }}>Connections</h4>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)', fontSize: 'var(--font-size-xs)' }}>
                      <div style={{ color: 'var(--color-text-tertiary)' }}>
                        Inputs: {edges.filter(e => e.target === node.id).length} / {nodeType.inputs}
                      </div>
                      <div style={{ color: 'var(--color-text-tertiary)' }}>
                        Outputs: {edges.filter(e => e.source === node.id).length} / {nodeType.outputs}
                      </div>
                    </div>
                  </div>

                  <div style={{ marginTop: 'auto', paddingTop: 'var(--space-3)', borderTop: '1px solid var(--color-surface-border)' }}>
                    <Button variant="danger" size="sm" fullWidth onClick={() => deleteNode(node.id)}>Delete Node</Button>
                  </div>
                </div>
              );
            })()}
          </div>
        )}

        {/* Validation Errors Panel */}
        {validationErrors.length > 0 && !selectedNodeId && (
          <div className="elco-validation-panel" style={{
            width: '300px',
            background: 'var(--color-market-sell-bg)',
            borderLeft: '1px solid var(--color-market-sell-border)',
            overflow: 'auto',
            padding: 'var(--space-4)',
          }}>
            <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 'var(--font-weight-semibold)', color: 'var(--color-market-sell)', marginBottom: 'var(--space-3)', display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" /></svg>
              Validation Errors
            </h3>
            <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
              {validationErrors.map((error, i) => (
                <li key={i} style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-market-sell)', padding: 'var(--space-2)', background: 'var(--color-surface-panel)', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-market-sell-border)' }}>
                  {error}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}

// Icons
function UndoIcon() { return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 7v6h6" /><path d="M21 17a9 9 0 0 0-9-9 9 9 0 0 0-6 2.3L3 13" /></svg>; }
function RedoIcon() { return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 7v6h-6" /><path d="M3 17a9 9 0 0 1 9-9 9 9 0 0 1 6 2.3l3 2.7" /></svg>; }
function CheckIcon() { return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="20 6 9 17 4 12" /></svg>; }
function SaveIcon() { return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z" /><polyline points="17 21 17 13 7 13 7 21" /><polyline points="7 3 7 8 15 8" /></svg>; }
function PlayIcon() { return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="5 3 19 12 5 21 5 3" /></svg>; }
function CodeIcon() { return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="16 18 22 12 16 6" /><polyline points="8 6 2 12 8 18" /></svg>; }
function SearchIcon() { return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" /></svg>; }
function ZoomResetIcon() { return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" /></svg>; }

import { useMemo } from 'react';

export default VisualStrategyBuilder;