# Pattern Scanner & Alpha Research Platform (Alpaca-Powered)

A Flask-based stock pattern scanner powered by **Alpaca Markets API** that detects bullish patterns (Cup & Handle, Double Bottoms, Ascending Triangles, Bull Flags) with advanced charting, technical analysis, DCF valuation, options strategies, and **live trading capabilities**.

**This is the Alpaca-powered fork of pattern_scanner_expanded** - featuring real-time market data, order execution, and paper/live trading modes.

## Features

### Pattern Detection
- **Cup & Handle**: Classic U-shaped pattern with handle pullback
- **Double Bottoms**: W-shaped reversal with neckline breakout
- **Ascending Triangles**: Rising support with flat resistance
- **Bull Flags**: Strong pole followed by consolidation

### Alpaca Integration 🆕
- **Real-Time Data**: WebSocket streaming for live price updates
- **Order Execution**: Market and limit orders via Alpaca Trading API
- **Paper & Live Trading**: Switch between paper and live modes via environment variable
- **Portfolio Management**: View positions, orders, and account info
- **Mode Indicator**: UI badge shows current trading mode (PAPER/LIVE)

### Charting
- **CTO Larsson Lines**: Two EMAs of (High+Low)/2 at 15 & 29 periods with color-coded fill (yellow bullish, blue bearish)
- **Moving Averages**: 13, 26, 40, 50, 200 SMAs with customizable display
- **Pattern Overlays**: Visual indicators for detected patterns (resistance lines, pole lines, necklines, markers)
- **Golden/Death Cross Markers**: Gold/red markers when 50 SMA crosses 200 SMA

### Analysis
- **Technical Indicators**: RSI, MACD, ADX, Volume analysis
- **DCF Valuation**: Intrinsic value estimates with margin of safety
- **Breakout Criteria**: 8-point checklist for entry signals
- **IV-Aware Options Strategies**: Dynamic strategy selection based on IV rank, VIX, and market regime
- **Expected Move Analysis**: IV-based expected moves with pattern target comparison
- **External Links**: Quick access to Yahoo Finance, Seeking Alpha, and SEC EDGAR filings

### UI
- Dark theme with interactive controls
- Stock search and detailed analysis pages
- Chart toggles for SMAs and CTO lines
- **Trade Panel**: Place market/limit orders directly from chart page
- **Mode Badge**: Always visible PAPER/LIVE indicator
- **Trade Journal**: Track both stock and options trades with P&L analysis

### Alpha Research Platform
- **Signal Framework**: Standardized signal abstraction with 11+ built-in signals
- **Backtesting Engine**: IC, hit rate, Sharpe ratio, quantile analysis
- **Decay Analysis**: Signal predictive power across multiple horizons
- **Correlation Analysis**: Identify redundant and diversifying signals
- **Signal Combination**: IC-weighted composite signals with correlation penalty
- **Regime Detection**: Market regime classification
- **REST API**: Complete API for programmatic access
- **Research Dashboard**: Interactive web UI for signal analysis

## Installation

### Prerequisites
- Docker and Docker Compose
- Python 3.12 (for local development)
- **Alpaca Markets Account** (free paper trading account available at https://alpaca.markets)

### Quick Start with Docker

1. **Clone the repository**
```bash
git clone <your-repo-url>
cd pattern_scanner_alpaca
```

2. **Create .env file with your Alpaca credentials**
```bash
cp .env.example .env
# Edit .env and add your Alpaca API keys
```

Your `.env` file should contain:
```
ALPACA_API_KEY=your_api_key_here
ALPACA_SECRET_KEY=your_secret_key_here
ALPACA_MODE=paper
```

3. **Start the application**
```bash
docker compose up -d --build
```

Access at http://localhost:5004

### Local Development
```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your Alpaca credentials
python pattern_scanner.py
```
Access at http://127.0.0.1:5003

## Alpaca API Setup

1. **Sign up for Alpaca**: Visit https://alpaca.markets and create a free account
2. **Get API Keys**: 
   - Navigate to your dashboard
   - Generate API keys for paper trading (or live trading if approved)
3. **Configure Environment**:
   - Copy `.env.example` to `.env`
   - Add your `ALPACA_API_KEY` and `ALPACA_SECRET_KEY`
   - Set `ALPACA_MODE=paper` for paper trading or `ALPACA_MODE=live` for live trading

⚠️ **IMPORTANT**: Never commit your `.env` file or expose your API keys. The `.env` file is already in `.gitignore`.

## Usage

### Pattern Scanner

1. **Scan Markets**: Use the dropdown to scan S&P 500, NASDAQ, or All US stocks
2. **View Details**: Click "View" on any detected pattern for full analysis
3. **Customize Charts**:
   - Toggle SMAs: 50 & 200, All, Short-term, None
   - Enable CTO Larsson Lines
4. **Analyze Patterns**: Review technical indicators, DCF, and options plays

### Trading Features 🆕

#### Place Orders
- Navigate to any stock's chart page
- Click "Trade" panel to expand order form
- Select Market or Limit order
- Enter quantity and (for limit orders) price
- Confirm order - mode badge shows if PAPER or LIVE

#### View Positions & Orders
- **GET /api/positions** - Current portfolio positions
- **GET /api/orders** - Open orders
- **GET /api/account** - Account balance and buying power

#### Real-Time Streaming
- **POST /api/stream/subscribe** - Subscribe to real-time data
- **GET /api/stream/latest/<symbol>** - Get latest streaming price

### Alpha Research Platform

Access research dashboard at: **http://localhost:5004/research**

#### Quick Start

```python
from signals import get_signal
from backtest import run_signal_backtest
from alpaca_data import fetch_multiple_stocks

# Fetch data from Alpaca
symbols = ['AAPL', 'MSFT', 'GOOGL']
df_prices = fetch_multiple_stocks(symbols, '2024-01-01', '2025-12-31')

# Compute and backtest signal
signal = get_signal('rsi_14')
df_signals = signal.compute(df_prices)
results = run_signal_backtest(df_signals, df_prices, horizon_days=20)

print(f"IC: {results['ic_pearson_mean']:.2%}")
print(f"Hit Rate: {results['hit_rate']:.1%}")
```

## API Endpoints

### Pattern Scanner
- `GET /`: Main scanner page
- `GET /chart/<symbol>`: Detailed chart with toggles
- `POST /scan`: Bulk market scan (JSON response)
- `GET /api/scan?market=sp500`: API scan endpoint

### Alpaca Trading 🆕
- `GET /api/account`: Account info (equity, cash, buying power, mode)
- `GET /api/positions`: Current positions
- `GET /api/orders`: Open orders
- `POST /api/order/market`: Place market order
- `POST /api/order/limit`: Place limit order
- `DELETE /api/order/<order_id>`: Cancel order
- `GET /api/stream/latest/<symbol>`: Latest streaming price
- `POST /api/stream/subscribe`: Subscribe to real-time data

### Alpha Research Platform
- `GET /signals/list`: List all available signals
- `POST /signals/backtest`: Run signal backtest
- `POST /signals/decay`: Decay analysis across horizons
- `POST /signals/correlation`: Signal correlation matrix
- `POST /signals/composite`: Build composite signal
- `POST /signals/regime`: Regime-conditional analysis
- `GET /research`: Research dashboard UI

## Configuration

- **Trading Mode**: Set `ALPACA_MODE=paper` or `ALPACA_MODE=live` in `.env`
- **SMA Options**: ?sma=50,200 or ?sma=all
- **CTO Lines**: ?cto=1
- **EDGAR Financials**: ?edgar=1

## Technical Details

- Built with Flask, Alpaca-py, pandas, pandas-ta, matplotlib
- Docker containerized for easy deployment
- Responsive dark UI with HTML/CSS/JS
- Real-time data from Alpaca Markets
- Paper and live trading support

## Differences from pattern_scanner_expanded

This fork uses a **hybrid data approach**:
- ✅ **Alpaca**: Real-time price data, WebSocket streaming, order execution, paper/live trading
- ✅ **yfinance**: Options chains, IV data, company fundamentals, DCF valuation
- ✅ Best of both worlds: Trade with Alpaca, analyze options with yfinance
- ✅ Full options strategy analysis (Long Call, Cash-Secured Put, PMCC, Iron Condor)
- ✅ Complete fundamental analysis and DCF valuation

## Disclaimer

For educational purposes only. Not financial advice. Patterns are probabilistic—always do your own research. 

**Trading involves risk. Paper trade first before using live mode.**

## License

MIT License
