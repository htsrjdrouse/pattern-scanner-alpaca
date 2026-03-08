# Pattern Scanner with Alpaca Trading Integration

A Flask-based stock pattern scanner with **live trading capabilities** powered by Alpaca Markets API. Detects bullish patterns, analyzes options strategies, and executes trades in paper or live mode.

## 🚀 Key Features

### Trading & Execution
- **Real-Time Trading**: Market and limit orders via Alpaca API
- **Paper & Live Modes**: Safe testing before going live
- **Fractional Shares**: Buy partial shares (e.g., 0.5 AAPL)
- **WebSocket Streaming**: Live price updates
- **Portfolio Management**: Track positions, orders, and P&L

### Pattern Detection
- Cup & Handle
- Double Bottom
- Ascending Triangle  
- Bull Flag

### Analysis Tools
- **Options Strategies**: Long Call, PMCC, Cash-Secured Put, Iron Condor
- **Technical Indicators**: RSI, MACD, ADX, Volume, CTO Larsson Lines
- **DCF Valuation**: Intrinsic value with margin of safety
- **IV Analysis**: Implied volatility rank and expected moves
- **Trade Journal**: Track performance with detailed analytics

### Alpha Research Platform
- Signal backtesting with IC/Sharpe metrics
- Decay analysis across multiple horizons
- Signal correlation and combination
- Market regime detection

## 📊 Hybrid Data Approach

**Best of both worlds:**
- **Alpaca**: Real-time prices, order execution, streaming data
- **yfinance**: Options chains, IV data, company fundamentals

## 🛠️ Quick Start

### Prerequisites
- Python 3.12+
- Alpaca Markets account (free at https://alpaca.markets)

### Installation

```bash
# Clone repository
git clone <your-repo-url>
cd pattern_scanner_alpaca

# Create environment file
cp .env.example .env
# Edit .env with your Alpaca API keys

# Install dependencies
pip install -r requirements.txt

# Start application
python pattern_scanner.py
```

Access at: **http://localhost:5004**

### Docker Setup

```bash
# Create .env file with your credentials
cp .env.example .env

# Build and start
docker compose up -d --build

# View logs
docker compose logs -f
```

## 🔑 Configuration

Create `.env` file:
```
ALPACA_API_KEY=your_api_key_here
ALPACA_SECRET_KEY=your_secret_key_here
ALPACA_MODE=paper
```

**⚠️ IMPORTANT**: 
- Start with `ALPACA_MODE=paper` for testing
- Never commit your `.env` file
- Mode badge always shows PAPER/LIVE in UI

## 📡 API Endpoints

### Trading
```bash
# Get account info
GET /api/account

# Place market order (fractional shares supported)
POST /api/order/market
{"symbol": "AAPL", "qty": 0.5, "side": "buy"}

# Place limit order
POST /api/order/limit
{"symbol": "AAPL", "qty": 1, "side": "buy", "limit_price": 175.00}

# View positions
GET /api/positions

# View orders
GET /api/orders

# Cancel order
DELETE /api/order/<order_id>
```

### Real-Time Data
```bash
# Subscribe to symbols
POST /api/stream/subscribe
{"symbols": ["AAPL", "MSFT"]}

# Get latest price
GET /api/stream/latest/AAPL
```

## 🎯 Usage Examples

### Scan for Patterns
1. Select market (S&P 500, NASDAQ, All US)
2. Click "Scan"
3. View detected patterns with scores

### Analyze Stock
1. Click "View" on any result
2. Review chart with pattern overlays
3. Check technical indicators
4. Review options strategies
5. See DCF valuation

### Place Trade
1. On chart page, expand "Trade" panel
2. Select Market or Limit order
3. Enter quantity (fractional OK)
4. Confirm order
5. Check mode badge (PAPER/LIVE)

### Research Dashboard
Access at: **http://localhost:5004/research**
- Backtest signals
- Analyze signal decay
- Build composite signals
- Regime-conditional analysis

## 🔒 Security

- ✅ Environment-based configuration
- ✅ No hardcoded credentials
- ✅ Mode always visible in UI
- ✅ Comprehensive trade logging
- ✅ `.env` in `.gitignore`

## 📦 Tech Stack

- **Backend**: Flask, Python 3.12
- **Trading**: Alpaca-py SDK
- **Data**: Alpaca (prices), yfinance (options/fundamentals)
- **Analysis**: pandas, pandas-ta, scipy
- **Visualization**: matplotlib
- **Deployment**: Docker, docker-compose

## 🚨 Limitations

- **Options Trading**: Analysis only (Alpaca doesn't support options execution)
- **Market Hours**: Real-time data during market hours only
- **Rate Limits**: Alpaca API rate limits apply

## 📝 Port Configuration

- **5002**: pattern_scanner_extended (original)
- **5003**: Portfolio Analyzer
- **5004**: pattern_scanner_alpaca (this app)

## 🤝 Contributing

This is a fork of `pattern_scanner_expanded` with Alpaca integration. The original repo remains unchanged and uses yfinance exclusively.

## ⚠️ Disclaimer

**For educational purposes only. Not financial advice.**

- Patterns are probabilistic, not guarantees
- Always do your own research
- Paper trade extensively before going live
- Trading involves risk of loss

## 📄 License

MIT License

## 🔗 Resources

- [Alpaca Markets](https://alpaca.markets)
- [Alpaca API Docs](https://alpaca.markets/docs)
- [Alpaca Community](https://forum.alpaca.markets)

---

**Ready to trade?** Start with paper mode, test thoroughly, then switch to live when confident. Happy trading! 📈
