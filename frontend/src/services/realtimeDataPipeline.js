/**
 * Real-time Data Pipeline
 * Handles WebSocket connections, caching, fallback providers, and data validation
 */

import { EventEmitter } from 'events';

class DataPipeline extends EventEmitter {
  constructor() {
    super();
    this.ws = null;
    this.cache = new Map();
    this.cacheTimeout = 5000; // 5 seconds default cache
    this.subscriptions = new Set();
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 10;
    this.reconnectDelay = 1000;
    this.isConnected = false;
    this.token = null;
    this.wsUrl = null;
    this.fallbackPolling = null;
    this.pollingInterval = 30000; // 30 seconds fallback
    this.dataValidators = new Map();
    this.metrics = {
      messagesReceived: 0,
      messagesProcessed: 0,
      errors: 0,
      reconnections: 0,
      cacheHits: 0,
      cacheMisses: 0,
    };
  }

  // Initialize the pipeline
  initialize(config = {}) {
    this.token = config.token || localStorage.getItem('elco_token');
    this.wsUrl = config.wsUrl || `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.hostname}:8000`;
    this.cacheTimeout = config.cacheTimeout || 5000;
    this.pollingInterval = config.pollingInterval || 30000;

    // Register default validators
    this.registerValidator('tick', this.validateTick.bind(this));
    this.registerValidator('quote', this.validateQuote.bind(this));
    this.registerValidator('depth', this.validateDepth.bind(this));
    this.registerValidator('trade', this.validateTrade.bind(this));

    // Setup fallback polling
    this.setupFallbackPolling();

    // Connect if token available
    if (this.token) {
      this.connect();
    }

    return this;
  }

  // Register data validator
  registerValidator(type, validator) {
    this.dataValidators.set(type, validator);
  }

  // Validate incoming tick data
  validateTick(data) {
    return data &&
      typeof data.symbol === 'string' &&
      typeof data.ltp === 'number' &&
      data.ltp > 0 &&
      typeof data.timestamp === 'number';
  }

  // Validate quote data
  validateQuote(data) {
    return data &&
      typeof data.symbol === 'string' &&
      typeof data.price === 'number' &&
      data.price > 0;
  }

  // Validate market depth
  validateDepth(data) {
    return data &&
      typeof data.symbol === 'string' &&
      Array.isArray(data.bids) &&
      Array.isArray(data.asks);
  }

  // Validate trade data
  validateTrade(data) {
    return data &&
      typeof data.symbol === 'string' &&
      typeof data.price === 'number' &&
      typeof data.quantity === 'number' &&
      data.price > 0 &&
      data.quantity > 0;
  }

  // Generic validation
  validateData(type, data) {
    const validator = this.dataValidators.get(type);
    if (!validator) return true; // No validator = pass
    return validator(data);
  }

  // Connect to WebSocket
  connect() {
    if (this.ws?.readyState === WebSocket.OPEN) return;

    const url = `${this.wsUrl}/ws/live?token=${this.token}`;
    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      this.isConnected = true;
      this.reconnectAttempts = 0;
      this.reconnectDelay = 1000;
      this.emit('connected');
      this.resubscribe();
      this.stopFallbackPolling();
    };

    this.ws.onmessage = (event) => {
      this.metrics.messagesReceived++;
      try {
        const data = JSON.parse(event.data);
        this.handleMessage(data);
      } catch (err) {
        this.metrics.errors++;
        this.emit('error', new Error(`Failed to parse message: ${err.message}`));
      }
    };

    this.ws.onclose = (event) => {
      this.isConnected = false;
      this.emit('disconnected', event.code, event.reason);
      this.scheduleReconnect();
      this.startFallbackPolling();
    };

    this.ws.onerror = (error) => {
      this.metrics.errors++;
      this.emit('error', error);
    };
  }

  // Handle incoming message
  handleMessage(data) {
    // Handle different message types
    switch (data.type) {
      case 'status':
        this.emit('status', data);
        break;
      case 'ticks':
        this.processTicks(data.ticks);
        break;
      case 'quote':
        this.processQuote(data);
        break;
      case 'depth':
        this.processDepth(data);
        break;
      case 'trade':
        this.processTrade(data);
        break;
      case 'error':
        this.emit('error', new Error(data.message));
        break;
      default:
        this.emit('message', data);
    }
  }

  // Process tick data
  processTicks(ticks) {
    const timestamp = Date.now();
    Object.entries(ticks).forEach(([symbol, tick]) => {
      if (this.validateData('tick', tick)) {
        // Add metadata
        tick._receivedAt = timestamp;
        tick._source = 'websocket';

        // Update cache
        this.updateCache(`tick:${symbol}`, tick);

        // Emit for subscribers
        this.emit(`tick:${symbol}`, tick);
        this.emit('tick', { symbol, ...tick });
        this.metrics.messagesProcessed++;
      } else {
        this.metrics.errors++;
        console.warn('Invalid tick data:', tick);
      }
    });
  }

  // Process quote data
  processQuote(data) {
    if (this.validateData('quote', data)) {
      this.updateCache(`quote:${data.symbol}`, data);
      this.emit(`quote:${data.symbol}`, data);
      this.metrics.messagesProcessed++;
    }
  }

  // Process market depth
  processDepth(data) {
    if (this.validateData('depth', data)) {
      this.updateCache(`depth:${data.symbol}`, data);
      this.emit(`depth:${data.symbol}`, data);
      this.metrics.messagesProcessed++;
    }
  }

  // Process trade data
  processTrade(data) {
    if (this.validateData('trade', data)) {
      this.updateCache(`trade:${data.symbol}`, data);
      this.emit(`trade:${data.symbol}`, data);
      this.metrics.messagesProcessed++;
    }
  }

  // Update cache with timestamp
  updateCache(key, data) {
    this.cache.set(key, {
      data,
      timestamp: Date.now(),
      expiresAt: Date.now() + this.cacheTimeout,
    });
  }

  // Get data from cache
  getFromCache(key) {
    const entry = this.cache.get(key);
    if (!entry) {
      this.metrics.cacheMisses++;
      return null;
    }

    if (Date.now() > entry.expiresAt) {
      this.cache.delete(key);
      this.metrics.cacheMisses++;
      return null;
    }

    this.metrics.cacheHits++;
    return entry.data;
  }

  // Get latest tick for symbol
  getLatestTick(symbol) {
    return this.getFromCache(`tick:${symbol}`);
  }

  // Get latest quote for symbol
  getLatestQuote(symbol) {
    return this.getFromCache(`quote:${symbol}`);
  }

  // Subscribe to symbols
  subscribe(symbols) {
    const symbolList = Array.isArray(symbols) ? symbols : [symbols];
    symbolList.forEach(s => this.subscriptions.add(s.toUpperCase()));

    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        type: 'subscribe',
        symbols: symbolList.map(s => s.toUpperCase()),
      }));
    }
  }

  // Unsubscribe from symbols
  unsubscribe(symbols) {
    const symbolList = Array.isArray(symbols) ? symbols : [symbols];
    symbolList.forEach(s => this.subscriptions.delete(s.toUpperCase()));

    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        type: 'unsubscribe',
        symbols: symbolList.map(s => s.toUpperCase()),
      }));
    }
  }

  // Resubscribe after reconnect
  resubscribe() {
    if (this.subscriptions.size > 0) {
      this.subscribe(Array.from(this.subscriptions));
    }
  }

  // Schedule reconnection with exponential backoff
  scheduleReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      this.emit('maxReconnectAttemptsReached');
      return;
    }

    this.reconnectAttempts++;
    this.metrics.reconnections++;

    const delay = Math.min(
      this.reconnectDelay * Math.pow(1.5, this.reconnectAttempts - 1),
      30000 // Max 30 seconds
    );

    setTimeout(() => {
      if (!this.isConnected) {
        this.connect();
      }
    }, delay);
  }

  // Setup fallback HTTP polling
  setupFallbackPolling() {
    // Will be started when WS disconnects
  }

  // Start fallback polling
  startFallbackPolling() {
    if (this.fallbackPolling) return;

    this.fallbackPolling = setInterval(async () => {
      if (this.isConnected) {
        this.stopFallbackPolling();
        return;
      }

      if (this.subscriptions.size === 0) return;

      try {
        const symbols = Array.from(this.subscriptions).join(',');
        const response = await fetch(
          `${this.wsUrl.replace('ws:', 'http:').replace('wss:', 'https:')}/api/live/quotes?symbols=${symbols}`,
          {
            headers: { 'Authorization': `Bearer ${this.token}` },
          }
        );

        if (response.ok) {
          const data = await response.json();
          if (data.ticks) {
            this.processTicks(data.ticks);
          }
        }
      } catch (err) {
        console.error('Fallback polling error:', err);
      }
    }, this.pollingInterval);
  }

  // Stop fallback polling
  stopFallbackPolling() {
    if (this.fallbackPolling) {
      clearInterval(this.fallbackPolling);
      this.fallbackPolling = null;
    }
  }

  // Get pipeline metrics
  getMetrics() {
    return {
      ...this.metrics,
      isConnected: this.isConnected,
      cacheSize: this.cache.size,
      subscriptions: this.subscriptions.size,
      reconnectAttempts: this.reconnectAttempts,
      cacheHitRate: this.metrics.cacheHits / (this.metrics.cacheHits + this.metrics.cacheMisses) || 0,
    };
  }

  // Clear cache
  clearCache() {
    this.cache.clear();
  }

  // Disconnect
  disconnect() {
    this.stopFallbackPolling();
    if (this.ws) {
      this.ws.close(1000, 'Client disconnect');
      this.ws = null;
    }
    this.isConnected = false;
    this.subscriptions.clear();
    this.clearCache();
  }

  // Update token
  setToken(token) {
    this.token = token;
    if (token) {
      localStorage.setItem('elco_token', token);
      if (!this.isConnected) {
        this.connect();
      }
    } else {
      localStorage.removeItem('elco_token');
      this.disconnect();
    }
  }
}

// Create singleton instance
const dataPipeline = new DataPipeline();

// React hook for using the data pipeline
export function useDataPipeline(config) {
  const [pipeline] = useState(() => dataPipeline.initialize(config));
  const [metrics, setMetrics] = useState(pipeline.getMetrics());
  const [connected, setConnected] = useState(pipeline.isConnected);

  useEffect(() => {
    const updateMetrics = () => setMetrics(pipeline.getMetrics());
    const handleConnect = () => setConnected(true);
    const handleDisconnect = () => setConnected(false);

    pipeline.on('metricsUpdate', updateMetrics);
    pipeline.on('connected', handleConnect);
    pipeline.on('disconnected', handleDisconnect);

    // Update metrics periodically
    const interval = setInterval(updateMetrics, 5000);

    return () => {
      pipeline.off('metricsUpdate', updateMetrics);
      pipeline.off('connected', handleConnect);
      pipeline.off('disconnected', handleDisconnect);
      clearInterval(interval);
    };
  }, [pipeline]);

  return { pipeline, metrics, connected };
}

// Export for non-React usage
export { dataPipeline, DataPipeline };

// Import React for hook
import { useState, useEffect } from 'react';

export default dataPipeline;