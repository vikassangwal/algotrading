import React, { useState } from 'react';

const AIAssistant = ({ globalSymbol }) => {
  const [inputMessage, setInputMessage] = useState('');
  
  const handleSendMessage = (e) => {
    e.preventDefault();
    if (inputMessage.trim()) {
      // In a real application, you would handle sending the message here
      console.log('Sending message:', inputMessage);
      setInputMessage('');
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h2 style={styles.title}>AI Market Briefing & Strategy Advisor</h2>
        <p style={styles.subtitle}>Ask me about market trends, strategy optimization, and competitor analysis.</p>
      </div>

      <div style={styles.chatArea}>
        {/* Placeholder Messages */}
        <div style={{ ...styles.messageWrapper, justifyContent: 'flex-start' }}>
          <div style={{ ...styles.messageBubble, ...styles.aiMessage }}>
            Hello! I am your AI Market Advisor. Here is your daily briefing: The market is showing a strong upward trend in the tech sector, driven by recent AI developments. How can I help optimize your strategy today?
          </div>
        </div>

        <div style={{ ...styles.messageWrapper, justifyContent: 'flex-end' }}>
          <div style={{ ...styles.messageBubble, ...styles.userMessage }}>
            Can you analyze our current Q3 marketing strategy against top competitors?
          </div>
        </div>

        <div style={{ ...styles.messageWrapper, justifyContent: 'flex-start' }}>
          <div style={{ ...styles.messageBubble, ...styles.aiMessage }}>
            Certainly! Based on the latest data, your Q3 strategy has a strong focus on organic growth. However, Competitor X has increased their paid ad spend by 15%. I recommend re-evaluating your PPC allocation to maintain visibility. Let me know if you would like me to generate a detailed allocation plan.
          </div>
        </div>
      </div>

      <div style={styles.inputContainer}>
        <form onSubmit={handleSendMessage} style={styles.inputForm}>
          <input
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            placeholder="Type your message to the AI Advisor..."
            style={styles.inputField}
          />
          <button type="submit" style={styles.sendButton}>
            Send
          </button>
        </form>
      </div>
    </div>
  );
};

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: '600px',
    maxWidth: '800px',
    margin: '0 auto',
    border: '1px solid #e0e0e0',
    borderRadius: '12px',
    backgroundColor: '#ffffff',
    boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
    fontFamily: 'system-ui, -apple-system, sans-serif',
  },
  header: {
    padding: '20px',
    borderBottom: '1px solid #e0e0e0',
    backgroundColor: '#f8f9fa',
    borderTopLeftRadius: '12px',
    borderTopRightRadius: '12px',
  },
  title: {
    margin: 0,
    fontSize: '1.25rem',
    color: '#333333',
  },
  subtitle: {
    margin: '5px 0 0',
    fontSize: '0.875rem',
    color: '#666666',
  },
  chatArea: {
    flex: 1,
    padding: '20px',
    overflowY: 'auto',
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
    backgroundColor: '#fafafa',
  },
  messageWrapper: {
    display: 'flex',
    width: '100%',
  },
  messageBubble: {
    maxWidth: '75%',
    padding: '12px 16px',
    borderRadius: '16px',
    fontSize: '0.95rem',
    lineHeight: '1.5',
    boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
  },
  aiMessage: {
    backgroundColor: '#ffffff',
    color: '#333333',
    border: '1px solid #e5e5e5',
    borderBottomLeftRadius: '4px',
  },
  userMessage: {
    backgroundColor: '#2563eb',
    color: '#ffffff',
    borderBottomRightRadius: '4px',
  },
  inputContainer: {
    padding: '16px 20px',
    borderTop: '1px solid #e0e0e0',
    backgroundColor: '#ffffff',
    borderBottomLeftRadius: '12px',
    borderBottomRightRadius: '12px',
  },
  inputForm: {
    display: 'flex',
    gap: '12px',
  },
  inputField: {
    flex: 1,
    padding: '12px 16px',
    border: '1px solid #cccccc',
    borderRadius: '24px',
    fontSize: '0.95rem',
    outline: 'none',
  },
  sendButton: {
    padding: '10px 24px',
    backgroundColor: '#2563eb',
    color: 'white',
    border: 'none',
    borderRadius: '24px',
    fontSize: '0.95rem',
    fontWeight: '600',
    cursor: 'pointer',
  },
};

export default AIAssistant;
