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
  - Clickable trade rows → full detail view (entry, plan, indicators, options, exit, notes)
  - Planned R:R auto-calculated from entry/stop/target with manual override
  - Live P&L and days open for open positions (via yfinance)
  - Stock and options trade support (contracts × 100 multiplier)

### 0DTE Morning Observation Log
- SPX-focused pre-market observation logging
- Live market snapshot: SPX price, VIX, ATM straddle, vol edge
- **Delta-based iron condor suggestions**: Strikes selected by ~0.10-0.12 delta (Tastytrade with yfinance fallback)
- Graceful single-leg fallback when one side lacks liquidity
- Observation history sorted by date and time (most recent first)
- Would-trade / strategy / notes tracking for building a decision baseline

### Alpha Research Platform
- Signal backtesting with IC/Sharpe metrics
- Decay analysis across multiple horizons
- Signal correlation and combination
- **Market Regime Classifier**: Pre-market intelligence for options premium selling
  - 7-dimension market analysis (VIX, term structure, trend, volatility spread, breadth, put/call ratio, correlation)
  - GREEN/YELLOW/RED regime classification with automatic strategy recommendations
  - Hard override rules for dangerous market conditions (backwardation, VIX crisis, no vol edge)
  - 30-day regime history with visualization
  - 60-minute caching to prevent API rate limiting

### Wolverine Risk Management System
- **Multi-Account Portfolio Tracking**: Aggregate view across Alpaca, Robinhood, Schwab, ThinkorSwim, SoFi
- **Bulk Position Import**: 
  - Paste Robinhood portfolio text directly
  - Upload ThinkorSwim CSV position statements
  - Paste Schwab equity positions
- **Real-Time Risk Monitoring**:
  - Daily/Weekly/Monthly P&L tracking
  - Position concentration alerts (>15% threshold)
  - Buying power usage monitoring
  - VIX spike detection
  - PDT (Pattern Day Trader) tracking
- **Recovery Mode**: Automatic position size reduction after daily loss limit breach
- **Circuit Breakers**: Hard stops at daily/monthly loss limits
- **30-Day P&L History**: Visual performance tracking

## 📊 Hybrid Data Approach

**Best of three worlds:**
- **Alpaca**: Real-time prices, order execution, streaming data
- **Tastytrade**: IV rank, IV percentile, market metrics (with fallback to yfinance approximation)
- **yfinance**: Options chains, historical data, company fundamentals

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
# Alpaca Trading (required)
ALPACA_API_KEY=your_api_key_here
ALPACA_SECRET_KEY=your_secret_key_here
ALPACA_MODE=paper

# Tastytrade Market Data (optional - falls back to yfinance if not configured)
TASTYTRADE_CLIENT_SECRET=your_client_secret_here
TASTYTRADE_REFRESH_TOKEN=your_refresh_token_here
```

**⚠️ IMPORTANT**: 
- Start with `ALPACA_MODE=paper` for testing
- Never commit your `.env` file
- Mode badge always shows PAPER/LIVE in UI
- Tastytrade credentials are optional - system uses yfinance approximation as fallback

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

#### Market Regime Classifier
The regime classifier analyzes 7 market dimensions to determine optimal conditions for options premium selling:

**Dimensions Analyzed:**
1. **VIX Regime** - Current volatility level (LOW/NORMAL/ELEVATED/CRISIS)
2. **Term Structure** - VIX futures curve shape (CONTANGO/FLAT/BACKWARDATION)
3. **Trend Assessment** - Market directionality via ADX (RANGE_BOUND/MIXED/TRENDING)
4. **Vol Spread** - Implied vs realized volatility edge (STRONG/MILD/NONE)
5. **Market Breadth** - Advance/decline and new highs/lows (BULLISH/NEUTRAL/BEARISH)
6. **Put/Call Sentiment** - Options positioning (EXTREME_FEAR to EXTREME_COMPLACENCY)
7. **Correlation Regime** - Stock correlation levels (HIGH/NORMAL/LOW)

**Verdict System:**
- **GREEN**: Sell premium aggressively (iron condors, 0.10-0.15 delta, full size)
- **YELLOW**: Sell premium conservatively (single-side spreads, half size, wider strikes)
- **RED**: No premium selling (sit in cash or use debit spreads only)

**Hard Overrides:**
- Backwardation detected → RED (regardless of other factors)
- VIX > 30 → RED (crisis mode)
- No vol edge + strong trend → RED (no edge for sellers)

Access the regime classifier in the research dashboard's "Regime Classifier" tab.

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
