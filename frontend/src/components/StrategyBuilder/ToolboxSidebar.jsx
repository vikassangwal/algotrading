import React, { useState } from 'react';
import { ChevronDown, ChevronRight, Activity, Zap, ShieldAlert, Clock, Code, TrendingUp, BarChart2 } from 'lucide-react';

const BUILDER_CATEGORIES = [
  {
    name: 'Strategy Types',
    icon: <TrendingUp size={16} />,
    minMode: 'Beginner',
    items: [
      { id: 'st_intraday', name: 'Intraday', type: 'Config', category: 'Strategy Types', defaultProps: { leverage: 5 } },
      { id: 'st_swing', name: 'Swing', type: 'Config', category: 'Strategy Types', defaultProps: { leverage: 1 } },
      { id: 'st_options_buy', name: 'Options Buying', type: 'Config', category: 'Strategy Types', defaultProps: { optionType: 'CE' } },
      { id: 'st_options_sell', name: 'Options Selling', type: 'Config', category: 'Strategy Types', defaultProps: { optionType: 'PE', hedge: true }, minMode: 'Advanced' }
    ]
  },
  {
    name: 'Entry Builder',
    icon: <Zap size={16} />,
    minMode: 'Beginner',
    items: [
      { id: 'en_indicator', name: 'Indicator Crossover', type: 'Entry', category: 'Entry Builder', defaultProps: { ind1: 'EMA', val1: 20, op: '>', ind2: 'EMA', val2: 50 } },
      { id: 'en_candlestick', name: 'Candlestick Pattern', type: 'Entry', category: 'Entry Builder', defaultProps: { pattern: 'Bullish Engulfing' } },
      { id: 'en_smart_money', name: 'Smart Money Flow', type: 'Entry', category: 'Entry Builder', defaultProps: { threshold: 80 }, minMode: 'Pro' },
      { id: 'en_order_flow', name: 'Order Flow Imbalance', type: 'Entry', category: 'Entry Builder', defaultProps: { imbalancePct: 15 }, minMode: 'Institutional' }
    ]
  },
  {
    name: 'Exit Builder',
    icon: <BarChart2 size={16} />,
    minMode: 'Beginner',
    items: [
      { id: 'ex_target', name: 'Fixed Target', type: 'Exit', category: 'Exit Builder', defaultProps: { type: 'Percentage', value: 2.0 } },
      { id: 'ex_dynamic', name: 'Dynamic Target (ATR)', type: 'Exit', category: 'Exit Builder', defaultProps: { atrMultiplier: 3.0 }, minMode: 'Advanced' },
      { id: 'ex_scale_out', name: 'Scale Out', type: 'Exit', category: 'Exit Builder', defaultProps: { target1: 1.0, qty1: 50, target2: 2.0, qty2: 50 }, minMode: 'Pro' }
    ]
  },
  {
    name: 'Stop Loss Builder',
    icon: <ShieldAlert size={16} />,
    minMode: 'Beginner',
    items: [
      { id: 'sl_fixed', name: 'Fixed % Stop Loss', type: 'StopLoss', category: 'Stop Loss Builder', defaultProps: { value: 1.0 } },
      { id: 'sl_trail', name: 'Trailing Stop Loss', type: 'StopLoss', category: 'Stop Loss Builder', defaultProps: { activation: 1.0, trailBy: 0.5 }, minMode: 'Advanced' },
      { id: 'sl_ai_dynamic', name: 'AI Dynamic Stop Loss', type: 'StopLoss', category: 'Stop Loss Builder', defaultProps: { regimeAdaptive: true }, minMode: 'Pro' }
    ]
  },
  {
    name: 'Risk Builder',
    icon: <Activity size={16} />,
    minMode: 'Beginner',
    items: [
      { id: 'rk_max_loss', name: 'Max Daily Loss', type: 'Risk', category: 'Risk Builder', defaultProps: { amount: 5000 } },
      { id: 'rk_pos_size', name: 'Position Size %', type: 'Risk', category: 'Risk Builder', defaultProps: { capitalPct: 2.0 } },
      { id: 'rk_portfolio', name: 'Portfolio Volatility Limit', type: 'Risk', category: 'Risk Builder', defaultProps: { maxBeta: 1.2 }, minMode: 'Institutional' }
    ]
  },
  {
    name: 'Time Builder',
    icon: <Clock size={16} />,
    minMode: 'Beginner',
    items: [
      { id: 'tm_hours', name: 'Trading Hours', type: 'Time', category: 'Time Builder', defaultProps: { start: '09:15', end: '15:15' } },
      { id: 'tm_expiry', name: 'Expiry Day Filter', type: 'Time', category: 'Time Builder', defaultProps: { tradeOnExpiry: false }, minMode: 'Advanced' }
    ]
  },
  {
    name: 'AI Builder',
    icon: <Code size={16} />,
    minMode: 'Pro',
    items: [
      { id: 'ai_confidence', name: 'AI Confidence Score', type: 'Condition', category: 'AI Builder', defaultProps: { minScore: 80 } },
      { id: 'ai_regime', name: 'Market Regime Filter', type: 'Condition', category: 'AI Builder', defaultProps: { allowedRegimes: ['TRENDING'] } }
    ]
  }
];

// Helper to determine if a category/item should be visible based on mode
const modeHierarchy = { 'Beginner': 1, 'Advanced': 2, 'Pro': 3, 'Institutional': 4 };
const isVisible = (minMode, currentMode) => {
  if (!minMode) return true;
  return modeHierarchy[currentMode] >= modeHierarchy[minMode];
};

const ToolboxSidebar = ({ mode }) => {
  const [expandedCats, setExpandedCats] = useState({
    'Entry Builder': true,
    'Exit Builder': true
  });

  const toggleCategory = (catName) => {
    setExpandedCats(prev => ({ ...prev, [catName]: !prev[catName] }));
  };

  const handleDragStart = (e, item) => {
    e.dataTransfer.setData('application/json', JSON.stringify(item));
    e.dataTransfer.effectAllowed = 'copy';
  };

  return (
    <div style={{ width: '280px', backgroundColor: '#1e293b', borderRight: '1px solid #334155', display: 'flex', flexDirection: 'column' }}>
      <div style={{ padding: '15px 20px', borderBottom: '1px solid #334155' }}>
        <h2 style={{ fontSize: '15px', fontWeight: 'bold', margin: 0, color: '#e2e8f0' }}>Builder Toolbox</h2>
        <p style={{ fontSize: '12px', color: '#94a3b8', margin: '4px 0 0 0' }}>Drag blocks onto the canvas</p>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '10px 0' }}>
        {BUILDER_CATEGORIES.filter(cat => isVisible(cat.minMode, mode)).map(category => (
          <div key={category.name} style={{ marginBottom: '4px' }}>
            
            {/* Category Header */}
            <div 
              onClick={() => toggleCategory(category.name)}
              style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 20px', cursor: 'pointer', backgroundColor: expandedCats[category.name] ? 'rgba(51, 65, 85, 0.5)' : 'transparent', transition: 'background 0.2s' }}
            >
              <span style={{ color: '#94a3b8', display: 'flex', alignItems: 'center' }}>
                {expandedCats[category.name] ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
              </span>
              <span style={{ color: '#3b82f6', display: 'flex', alignItems: 'center' }}>{category.icon}</span>
              <span style={{ fontSize: '13px', fontWeight: '600', color: '#cbd5e1' }}>{category.name}</span>
            </div>

            {/* Category Items */}
            {expandedCats[category.name] && (
              <div style={{ padding: '4px 20px 8px 44px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {category.items.filter(item => isVisible(item.minMode, mode)).map(item => (
                  <div
                    key={item.id}
                    draggable
                    onDragStart={(e) => handleDragStart(e, item)}
                    style={{
                      padding: '8px 12px',
                      backgroundColor: '#0f172a',
                      border: '1px solid #334155',
                      borderRadius: '6px',
                      fontSize: '12px',
                      color: '#94a3b8',
                      cursor: 'grab',
                      transition: 'all 0.2s',
                    }}
                    onMouseOver={(e) => {
                      e.currentTarget.style.borderColor = '#3b82f6';
                      e.currentTarget.style.color = '#f8fafc';
                    }}
                    onMouseOut={(e) => {
                      e.currentTarget.style.borderColor = '#334155';
                      e.currentTarget.style.color = '#94a3b8';
                    }}
                  >
                    {item.name}
                  </div>
                ))}
              </div>
            )}

          </div>
        ))}
      </div>
    </div>
  );
};

export default ToolboxSidebar;
