# ELCO Trader - Algorithmic Trading Platform

> **Professional-grade algorithmic trading platform for Indian markets**  
> Built with modern architecture, real-time data, and institutional-grade risk management

[![CI/CD](https://github.com/yourusername/elco-trader/workflows/CI/CD%20Pipeline/badge.svg)](https://github.com/yourusername/elco-trader/actions)
[![Docker](https://img.shields.io/badge/docker-ready-blue)](https://hub.docker.com/r/elco/trader)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

## 🚀 Features

### 📊 Market Analysis
- **Real-time Market Scanner** - Gap ups, breakouts, high volume, momentum signals
- **Advanced Charting** - Multi-timeframe charts with 20+ technical indicators
- **Options Chain Analyzer** - Greeks, IV surface, PCR, Max Pain, flow visualization
- **Universal Screener** - Multi-asset screening with custom filters
- **Market Regime Detection** - Trending, ranging, volatile regime identification

### 🧠 Strategy Development
- **Visual Strategy Builder** - Drag-and-drop node-based strategy creation
- **Backtest Engine** - Event-driven backtesting with walk-forward analysis
- **Strategy Generator** - Automated strategy discovery with out-of-sample validation
- **Monte Carlo Simulation** - Robustness testing with confidence intervals
- **Parameter Optimization** - Genetic algorithm and grid search optimization

### 🛡️ Risk Management
- **Real-time Risk Dashboard** - VaR, CVaR, stress testing, correlation analysis
- **Position Sizing** - Kelly criterion, volatility-adjusted, risk-parity
- **Circuit Breakers** - Daily loss limits, drawdown controls, exposure limits
- **Portfolio Analytics** - Attribution, factor exposure, scenario analysis

### 🤖 AI & Intelligence
- **AI Assistant** - Natural language queries for analysis, strategy review, risk assessment
- **Pattern Recognition** - Candlestick, chart, and harmonic pattern detection
- **News Sentiment** - Real-time NLP sentiment analysis with impact scoring
- **Institutional Flow** - FII/DII activity, block deals, delivery analysis

### 📈 Trade Management
- **Multi-Broker Integration** - Zerodha, Dhan, Upstox, Angel One, Fyers, and more
- **Order Management** - Smart routing, execution algorithms, TCA
- **Trade Journal** - Psychology analytics, behavioral patterns, performance attribution
- **Execution Replay** - Historical trade reconstruction with market context

### 🏗️ Architecture
- **Microservices** - Modular, scalable, independently deployable
- **Event-Driven** - Real-time data pipeline with WebSocket streaming
- **Multi-Broker** - Unified abstraction layer with automatic failover
- **Cloud-Native** - Kubernetes-ready with Helm charts

## 📋 Quick Start

### Prerequisites
- Docker 24+ and Docker Compose 2+
- 4GB+ RAM, 2+ CPU cores
- (Optional) Broker API credentials for live trading

### Development Setup

```bash
# Clone repository
git clone https://github.com/yourusername/elco-trader.git
cd elco-trader

# Configure environment
cp .env.example .env.development
# Edit .env.development with your settings

# Start development environment
./deploy.sh development up

# Access the application
# Frontend: http://localhost:5173
# API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Production Deployment

```bash
# Configure production environment
cp .env.example .env.production
# Fill in all required values (SECRET_KEY, passwords, API keys)

# Deploy to production
./deploy.sh production up

# Monitor deployment
./deploy.sh production status
./deploy.sh production logs
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `ELCO_SECRET_KEY` | JWT signing key (min 32 chars) | Yes |
| `POSTGRES_PASSWORD` | Database password | Yes |
| `ELCO_CORS_ORIGINS` | Allowed origins (comma-separated) | Yes |
| `LIVE_TRADING` | Enable live trading (`true`/`false`) | No |
| Broker API keys | See `.env.example` for all options | No |

### Broker Setup

1. **Zerodha**: Create Kite Connect app at [developers.kite.trade](https://developers.kite.trade)
2. **Dhan**: Get API credentials from [DhanHQ](https://dhan.co/)
3. **Upstox**: Register at [Upstox Developer](https://developer.upstox.com/)
4. **Angel One**: Apply for SmartAPI at [Angel One](https://smartapi.angelone.in/)

Add credentials to your environment file:
```bash
ZERODHA_API_KEY=your_key
ZERODHA_API_SECRET=your_secret
# ... etc
```

## 📚 API Documentation

### REST API
- **Base URL**: `http://localhost:8000`
- **Interactive Docs**: `http://localhost:8000/docs` (Swagger UI)
- **ReDoc**: `http://localhost:8000/redoc`

### Key Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /login` | Authentication |
| `GET /analyze/{symbol}` | Symbol analysis |
| `GET /api/history/{symbol}` | Historical data |
| `GET /portfolio` | Portfolio summary |
| `POST /api/orders` | Place order |
| `GET /journal` | Trade history |
| `GET /api/backtest/{symbol}` | Run backtest |
| `WS /ws/live` | Real-time data |

### WebSocket

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/live?token=YOUR_TOKEN&symbols=NIFTY,RELIANCE');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'ticks') {
    console.log('Live ticks:', data.ticks);
  }
};
```

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Unit tests only
pytest tests/test_api.py -m "not integration" -v

# Integration tests
pytest tests/test_api.py -m "integration" -v

# With coverage
pytest tests/ --cov=app --cov-report=html
```

## 📊 Monitoring

### Grafana Dashboards
- **Overview**: `http://localhost:3000/d/elco-trader-overview`
- **Risk**: `http://localhost:3000/d/elco-trader-risk`
- **Trading**: `http://localhost:3000/d/elco-trader-trading`

### Prometheus Metrics
- `http://localhost:9090` - Prometheus UI
- `http://localhost:8000/metrics` - Application metrics

### Key Metrics
- `elco_daily_pnl` - Daily P&L
- `elco_max_drawdown_pct` - Max drawdown
- `elco_portfolio_exposure_pct` - Portfolio exposure
- `elco_auto_trade_state` - Trading state (0=off, 1=active, 2=halted)
- `http_request_duration_seconds` - API latency

## 🔐 Security

### Production Checklist
- [ ] Change all default passwords
- [ ] Generate strong `ELCO_SECRET_KEY` (64+ chars)
- [ ] Enable HTTPS with valid SSL certificates
- [ ] Configure firewall rules
- [ ] Set up automated backups
- [ ] Enable audit logging
- [ ] Configure alerting (Slack, Email, PagerDuty)

### API Security
- All endpoints require Bearer token authentication
- Rate limiting: 100 req/s per IP
- CORS restricted to configured origins
- Input validation on all endpoints

## 🚢 Deployment

### Docker Compose (Single Server)
```bash
# Development
./deploy.sh development up

# Staging
./deploy.sh staging up

# Production
./deploy.sh production up
```

### Kubernetes (Production)
```bash
# Apply manifests
kubectl apply -f k8s/

# Check status
kubectl get pods -n elco-trader
```

### Database Migrations
```bash
# Run migrations
./deploy.sh production migrate

# Create new migration
docker-compose exec elco-trader alembic revision --autogenerate -m "description"
```

## 🛠️ Development

### Project Structure
```
elco-trader/
├── app/                    # Backend (FastAPI)
│   ├── main.py            # Application entry point
│   ├── engine.py          # Signal fusion engine
│   ├── risk_manager.py    # Risk management
│   ├── execution.py       # Order execution
│   ├── modules/           # Analysis modules
│   ├── brokers/           # Broker integrations
│   └── data/              # Data providers
├── frontend/              # Frontend (React + Vite)
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── charts/        # Charting components
│   │   ├── scanner/       # Scanner components
│   │   ├── strategy/      # Strategy builder
│   │   └── design-system/ # Design tokens & UI
│   └── package.json
├── tests/                 # Test suite
├── docs/                  # Documentation
├── prometheus/            # Prometheus config
├── grafana/               # Grafana dashboards
├── deploy.sh              # Deployment script
└── docker-compose.yml     # Docker orchestration
```

### Adding a New Analysis Module

```python
# app/modules/my_module.py
from app.modules.base import BaseModule, ModuleSignal

class MyModule(BaseModule):
    name = "my_module"
    
    async def analyze(self, symbol: str) -> ModuleSignal:
        # Your analysis logic
        return ModuleSignal(score=0.5, confidence=0.8, reasons=["Signal"])

# Register in app/main.py
engine.register_module(MyModule(provider))
```

### Adding a New Broker

```python
# app/brokers/my_broker.py
from app.brokers.base import BaseBroker

class MyBroker(BaseBroker):
    async def connect(self): ...
    async def place_order(self, order): ...
    async def get_positions(self): ...
    # ... implement all abstract methods

# Register in app/brokers/factory.py
BROKER_REGISTRY["mybroker"] = MyBroker
```

## 📖 Documentation

- [Architecture Overview](docs/architecture.md)
- [API Reference](docs/api.md)
- [Strategy Development](docs/strategies.md)
- [Risk Management](docs/risk.md)
- [Broker Integration](docs/brokers.md)
- [Deployment Guide](docs/deployment.md)

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

### Code Style
- Python: Ruff + MyPy
- JavaScript/TypeScript: ESLint + Prettier
- Commits: Conventional Commits

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## ⚠️ Disclaimer

**This software is for educational and research purposes only.**  
Trading financial instruments carries significant risk.  
Past performance does not guarantee future results.  
The authors are not responsible for any financial losses.

---

**Built with ❤️ for the algorithmic trading community**

[Website](https://elco-trader.com) • [Documentation](https://docs.elco-trader.com) • [Discord](https://discord.gg/elco-trader)