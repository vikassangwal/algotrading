import { useState, useEffect, useRef, useCallback } from 'react';
import { clsx, formatters } from '../../design-system';
import { Button, Input, Card, CardHeader, CardContent, Badge, Tabs, Tab, Select } from '../ui';

const MESSAGE_TYPES = {
  USER: 'user',
  ASSISTANT: 'assistant',
  SYSTEM: 'system',
  TOOL: 'tool',
};

const AI_CAPABILITIES = [
  { id: 'market_analysis', name: 'Market Analysis', description: 'Analyze current market conditions, trends, and key levels', icon: '📊' },
  { id: 'strategy_review', name: 'Strategy Review', description: 'Review and critique your trading strategies', icon: '🔍' },
  { id: 'risk_assessment', name: 'Risk Assessment', description: 'Evaluate portfolio risk and position sizing', icon: '🛡️' },
  { id: 'trade_analysis', name: 'Trade Analysis', description: 'Analyze specific trades or trade patterns', icon: '📈' },
  { id: 'regime_detection', name: 'Regime Detection', description: 'Identify current market regime (trending, ranging, volatile)', icon: '🌊' },
  { id: 'options_flow', name: 'Options Flow', description: 'Analyze options activity, Greeks, and flow data', icon: '🎯' },
  { id: 'news_impact', name: 'News Impact', description: 'Assess impact of news events on positions', icon: '📰' },
  { id: 'backtest_interpret', name: 'Backtest Interpretation', description: 'Interpret backtest results and suggest improvements', icon: '📉' },
];

export function AIAssistant({
  token,
  className = '',
  style = {},
  ...props
}) {
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      type: MESSAGE_TYPES.ASSISTANT,
      content: `Welcome to ELCO AI Assistant! I can help you with market analysis, strategy review, risk assessment, and more.

**Capabilities:**
${AI_CAPABILITIES.map(c => `• ${c.icon} **${c.name}**: ${c.description}`).join('\n')}

How can I assist you today?`,
      timestamp: new Date().toISOString(),
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [selectedCapability, setSelectedCapability] = useState(null);
  const [context, setContext] = useState({ symbols: [], timeframe: '15m' });
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const API_URL = `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}`;

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const sendMessage = useCallback(async () => {
    if (!input.trim() || loading || !token) return;

    const userMessage = {
      id: `msg_${Date.now()}`,
      type: MESSAGE_TYPES.USER,
      content: input,
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMessage]);
    const currentInput = input;
    setInput('');
    setLoading(true);

    try {
      const headers = { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' };
      const res = await fetch(`${API_URL}/api/ai/chat`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          message: currentInput,
          context: { ...context, selectedCapability },
          history: messages.slice(-10).map(m => ({ role: m.type === MESSAGE_TYPES.USER ? 'user' : 'assistant', content: m.content })),
        }),
      });

      if (!res.ok) throw new Error('AI request failed');

      const data = await res.json();

      const assistantMessage = {
        id: `msg_${Date.now()}_assistant`,
        type: MESSAGE_TYPES.ASSISTANT,
        content: data.response,
        timestamp: new Date().toISOString(),
        tools: data.tools_used,
        confidence: data.confidence,
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (err) {
      const errorMessage = {
        id: `msg_${Date.now()}_error`,
        type: MESSAGE_TYPES.SYSTEM,
        content: `Error: ${err.message}. Please try again.`,
        timestamp: new Date().toISOString(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  }, [input, loading, token, context, selectedCapability, messages, API_URL]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const useCapability = (capability) => {
    setSelectedCapability(capability.id);
    const prompts = {
      market_analysis: "Analyze the current market conditions for NIFTY and BANKNIFTY. What are the key levels, trends, and your outlook for the next session?",
      strategy_review: "Review my current strategy configuration. What are the strengths and weaknesses? Suggest improvements.",
      risk_assessment: "Assess my current portfolio risk. Are position sizes appropriate? Any concentration risks?",
      trade_analysis: "Analyze my recent trades. What patterns do you see in my winning vs losing trades?",
      regime_detection: "What is the current market regime? Trending, ranging, or volatile? How should I adjust my strategy?",
      options_flow: "Analyze current options flow for NIFTY. Any unusual activity or key levels from options data?",
      news_impact: "Summarize recent market-moving news and assess impact on my positions.",
      backtest_interpret: "Interpret my latest backtest results. Is the strategy robust? What are the red flags?",
    };
    setInput(prompts[capability.id] || '');
    inputRef.current?.focus();
  };

  const clearChat = () => {
    setMessages([messages[0]]);
    setSelectedCapability(null);
  };

  return (
    <div className={clsx('elco-ai-assistant', className)} style={{ ...style, height: '100%', display: 'flex', flexDirection: 'column', ...props }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: 'var(--space-4)', background: 'var(--color-surface-panel)', borderBottom: '1px solid var(--color-surface-border)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
          <div style={{ width: '40px', height: '40px', borderRadius: 'var(--radius-lg)', background: 'var(--color-brand-500)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '20px' }}>🤖</div>
          <div>
            <h2 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 'var(--font-weight-semibold)', margin: 0 }}>ELCO AI Assistant</h2>
            <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-tertiary)' }}>
              {selectedCapability ? `Mode: ${AI_CAPABILITIES.find(c => c.id === selectedCapability)?.name}` : 'General Assistant'}
            </div>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
          <Badge variant={selectedCapability ? 'success' : 'default'} size="sm" dot>
            {selectedCapability ? 'Active' : 'Ready'}
          </Badge>
          <Button variant="ghost" size="sm" onClick={clearChat} leftIcon={<ClearIcon />} disabled={messages.length <= 1}>
            Clear
          </Button>
        </div>
      </div>

      {/* Capability Selector */}
      <div style={{ padding: 'var(--space-3) var(--space-4)', background: 'var(--color-surface-base)', borderBottom: '1px solid var(--color-surface-border)' }}>
        <div style={{ display: 'flex', gap: 'var(--space-2)', overflowX: 'auto', paddingBottom: 'var(--space-2)' }}>
          {AI_CAPABILITIES.map(cap => (
            <Button
              key={cap.id}
              variant={selectedCapability === cap.id ? 'primary' : 'outline'}
              size="sm"
              onClick={() => useCapability(cap)}
              style={{ whiteSpace: 'nowrap' }}
            >
              <span>{cap.icon}</span>
              <span>{cap.name}</span>
            </Button>
          ))}
        </div>
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflow: 'auto', padding: 'var(--space-4)', display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
        {messages.map((message, index) => (
          <MessageBubble key={message.id} message={message} isLast={index === messages.length - 1} />
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Typing Indicator */}
      {loading && (
        <div style={{ padding: 'var(--space-3) var(--space-4)', display: 'flex', alignItems: 'center', gap: 'var(--space-3)', background: 'var(--color-surface-panel)', borderTop: '1px solid var(--color-surface-border)' }}>
          <div style={{ display: 'flex', gap: '4px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--color-brand-500)', animation: 'bounce 1.4s infinite ease-in-out' }} />
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--color-brand-500)', animation: 'bounce 1.4s infinite ease-in-out 0.16s' }} />
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--color-brand-500)', animation: 'bounce 1.4s infinite ease-in-out 0.32s' }} />
          </div>
          <style jsx>{`@keyframes bounce { 0%, 80%, 100% { transform: scale(0); } 40% { transform: scale(1); } }`}</style>
          <span style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)' }}>AI is thinking...</span>
        </div>
      )}

      {/* Input */}
      <div style={{ padding: 'var(--space-4)', background: 'var(--color-surface-panel)', borderTop: '1px solid var(--color-surface-border)' }}>
        <div style={{ display: 'flex', alignItems: 'flex-end', gap: 'var(--space-3)' }}>
          <div style={{ flex: 1, position: 'relative' }}>
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={selectedCapability ? `Ask about ${AI_CAPABILITIES.find(c => c.id === selectedCapability)?.name.toLowerCase()}...` : 'Ask me anything about markets, strategies, risk...'}
              style={{
                width: '100%',
                minHeight: '48px',
                maxHeight: '150px',
                padding: 'var(--space-3) var(--space-4)',
                paddingRight: '48px',
                background: 'var(--color-surface-interactive)',
                border: '1px solid var(--color-surface-border)',
                borderRadius: 'var(--radius-lg)',
                color: 'var(--color-text-primary)',
                fontSize: 'var(--font-size-sm)',
                fontFamily: 'var(--font-family-sans)',
                resize: 'vertical',
                outline: 'none',
                lineHeight: 'var(--line-height-normal)',
              }}
              onFocus={(e) => e.target.style.borderColor = 'var(--color-brand-500)'}
              onBlur={(e) => e.target.style.borderColor = 'var(--color-surface-border)'}
            />
            {input && (
              <button
                onClick={() => setInput('')}
                style={{
                  position: 'absolute',
                  right: '12px',
                  top: '50%',
                  transform: 'translateY(-50%)',
                  background: 'none',
                  border: 'none',
                  color: 'var(--color-text-tertiary)',
                  cursor: 'pointer',
                  padding: '4px',
                }}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
              </button>
            )}
          </div>
          <Button
            variant="primary"
            size="lg"
            onClick={sendMessage}
            disabled={!input.trim() || loading}
            loading={loading}
            style={{ height: '48px' }}
          >
            <SendIcon />
          </Button>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', marginTop: 'var(--space-2)', fontSize: 'var(--font-size-xs)', color: 'var(--color-text-tertiary)' }}>
          <kbd style={{ background: 'var(--color-surface-interactive)', padding: '2px 6px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--color-surface-border)' }}>Enter</kbd>
          <span>Send</span>
          <span>•</span>
          <kbd style={{ background: 'var(--color-surface-interactive)', padding: '2px 6px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--color-surface-border)' }}>Shift+Enter</kbd>
          <span>New line</span>
          <span>•</span>
          <span>Powered by ELCO AI Engine</span>
        </div>
      </div>
    </div>
  );
}

function MessageBubble({ message, isLast }) {
  const isUser = message.type === MESSAGE_TYPES.USER;
  const isSystem = message.type === MESSAGE_TYPES.SYSTEM;
  const isTool = message.type === MESSAGE_TYPES.TOOL;

  if (isSystem) {
    return (
      <div style={{ textAlign: 'center', padding: 'var(--space-2)', color: 'var(--color-text-tertiary)', fontSize: 'var(--font-size-xs)' }}>
        {message.content}
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', gap: 'var(--space-3)', justifyContent: isUser ? 'flex-end' : 'flex-start' }}>
      {!isUser && (
        <div style={{ width: '32px', height: '32px', borderRadius: '50%', background: 'var(--color-brand-500)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, fontSize: '14px' }}>🤖</div>
      )}
      <div style={{ maxWidth: '80%', display: 'flex', flexDirection: 'column', gap: 'var(--space-1)' }}>
        <div
          style={{
            padding: 'var(--space-3) var(--space-4)',
            background: isUser ? 'var(--color-brand-500)' : 'var(--color-surface-panel)',
            border: isUser ? 'none' : '1px solid var(--color-surface-border)',
            borderRadius: isUser ? 'var(--radius-xl) var(--radius-xl) 4px var(--radius-xl)' : 'var(--radius-xl) var(--radius-xl) var(--radius-xl) 4px',
            color: isUser ? 'white' : 'var(--color-text-primary)',
            fontSize: 'var(--font-size-sm)',
            lineHeight: 'var(--line-height-relaxed)',
            whiteSpace: 'pre-wrap',
          }}
        >
          {message.content}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', fontSize: 'var(--font-size-xs)', color: 'var(--color-text-tertiary)' }}>
          <span>{formatters.timeOnly(message.timestamp)}</span>
          {message.confidence && (
            <Badge variant="ghost" size="sm">Confidence: {Math.round(message.confidence * 100)}%</Badge>
          )}
          {message.tools && message.tools.length > 0 && (
            <Badge variant="outline" size="sm">Tools: {message.tools.join(', ')}</Badge>
          )}
        </div>
      </div>
      {isUser && (
        <div style={{ width: '32px', height: '32px', borderRadius: '50%', background: 'var(--color-surface-interactive)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" /></svg>
        </div>
      )}
    </div>
  );
}

function ClearIcon() { return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" /></svg>; }
function SendIcon() { return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" /></svg>; }

export default AIAssistant;