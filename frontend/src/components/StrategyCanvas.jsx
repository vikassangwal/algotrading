import React, { useState } from 'react';

const availableIndicators = [
  { id: 'rsi', name: 'RSI', defaultOp: '>', defaultVal: 70 },
  { id: 'macd', name: 'MACD', defaultOp: '>', defaultVal: 0 },
  { id: 'sma', name: 'SMA (50)', defaultOp: '>', defaultVal: 100 }
];

const StrategyCanvas = () => {
  const [entryRules, setEntryRules] = useState([]);
  const [exitRules, setExitRules] = useState([]);
  const [draggedItem, setDraggedItem] = useState(null);

  const handleDragStart = (e, indicator) => {
    setDraggedItem(indicator);
  };

  const handleDrop = (e, type) => {
    e.preventDefault();
    if (!draggedItem) return;

    const newRule = {
      id: Date.now(),
      indicator: draggedItem.name,
      operator: draggedItem.defaultOp,
      value: draggedItem.defaultVal
    };

    if (type === 'entry') {
      setEntryRules([...entryRules, newRule]);
    } else {
      setExitRules([...exitRules, newRule]);
    }
    setDraggedItem(null);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
  };

  const removeRule = (id, type) => {
    if (type === 'entry') {
      setEntryRules(entryRules.filter(r => r.id !== id));
    } else {
      setExitRules(exitRules.filter(r => r.id !== id));
    }
  };

  const renderRule = (rule, type) => (
    <div key={rule.id} style={styles.ruleCard}>
      <span>{rule.indicator}</span>
      <select defaultValue={rule.operator} style={styles.input}>
        <option value=">">&gt;</option>
        <option value="<">&lt;</option>
        <option value="==">==</option>
      </select>
      <input type="number" defaultValue={rule.value} style={styles.input} />
      <button onClick={() => removeRule(rule.id, type)} style={styles.deleteBtn}>X</button>
    </div>
  );

  return (
    <div style={styles.container}>
      <div style={styles.sidebar}>
        <h3>Indicators</h3>
        {availableIndicators.map(ind => (
          <div
            key={ind.id}
            draggable
            onDragStart={(e) => handleDragStart(e, ind)}
            style={styles.draggableItem}
          >
            {ind.name}
          </div>
        ))}
      </div>

      <div style={styles.canvas}>
        <h2>Strategy Canvas</h2>
        
        <div style={styles.dropZoneContainer}>
          <div 
            style={styles.dropZone}
            onDrop={(e) => handleDrop(e, 'entry')}
            onDragOver={handleDragOver}
          >
            <h3>Entry Rules</h3>
            <p style={styles.placeholder}>Drag indicators here</p>
            {entryRules.map(rule => renderRule(rule, 'entry'))}
          </div>

          <div 
            style={styles.dropZone}
            onDrop={(e) => handleDrop(e, 'exit')}
            onDragOver={handleDragOver}
          >
            <h3>Exit Rules</h3>
            <p style={styles.placeholder}>Drag indicators here</p>
            {exitRules.map(rule => renderRule(rule, 'exit'))}
          </div>
        </div>
        
        <button style={styles.saveBtn} onClick={() => alert('Strategy Saved!')}>
          Save Strategy
        </button>
      </div>
    </div>
  );
};

const styles = {
  container: { display: 'flex', height: '100vh', fontFamily: 'Arial, sans-serif' },
  sidebar: { width: '200px', backgroundColor: '#f5f5f5', padding: '20px', borderRight: '1px solid #ddd' },
  draggableItem: { padding: '12px', margin: '10px 0', backgroundColor: '#fff', border: '1px solid #ccc', cursor: 'grab', borderRadius: '4px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' },
  canvas: { flex: 1, padding: '20px', display: 'flex', flexDirection: 'column', backgroundColor: '#fafafa' },
  dropZoneContainer: { display: 'flex', gap: '20px', flex: 1, marginTop: '20px' },
  dropZone: { flex: 1, backgroundColor: '#fff', border: '2px dashed #bbb', padding: '20px', borderRadius: '8px', minHeight: '400px', overflowY: 'auto' },
  placeholder: { color: '#888', fontStyle: 'italic', marginBottom: '20px' },
  ruleCard: { display: 'flex', alignItems: 'center', gap: '10px', padding: '15px', backgroundColor: '#f9f9f9', border: '1px solid #e0e0e0', marginBottom: '10px', borderRadius: '6px' },
  input: { padding: '8px', borderRadius: '4px', border: '1px solid #ccc' },
  deleteBtn: { backgroundColor: '#ff5252', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', padding: '8px 12px', marginLeft: 'auto' },
  saveBtn: { marginTop: '30px', padding: '12px 24px', backgroundColor: '#4CAF50', color: 'white', border: 'none', borderRadius: '6px', cursor: 'pointer', alignSelf: 'flex-start', fontSize: '16px', fontWeight: 'bold' }
};

export default StrategyCanvas;
