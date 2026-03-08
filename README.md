# Pattern Scanner & Alpha Research Platform

A Flask-based stock pattern scanner that detects bullish patterns (Cup & Handle, Double Bottoms, Ascending Triangles, Bull Flags) with advanced charting, technical analysis, DCF valuation, and options strategies.

**NEW**: Modular alpha research platform for systematic signal backtesting, IC analysis, signal combination, and regime detection.

## Features

### Pattern Detection
- **Cup & Handle**: Classic U-shaped pattern with handle pullback
- **Double Bottoms**: W-shaped reversal with neckline breakout
- **Ascending Triangles**: Rising support with flat resistance
- **Bull Flags**: Strong pole followed by consolidation

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
  - Long Call (low IV environments)
  - Cash-Secured Put (elevated IV)
  - Poor Man's Covered Call (moderate IV)
  - Iron Condor (range-bound markets)
  - Regime detection using ADX and CTO Larsson lines
  - Bearish trend warnings to prevent counter-trend trades
- **Expected Move Analysis**: IV-based expected moves (1-week, 1-month, 45-day) with delta-to-probability translation and pattern target comparison
- **External Links**: Quick access to Yahoo Finance, Seeking Alpha, and SEC EDGAR filings

### UI
- Dark theme with interactive controls
- Stock search and detailed analysis pages
- Chart toggles for SMAs and CTO lines
- **Trade Journal**: Track both stock and options trades with P&L analysis
  - Stock trades: Entry/exit tracking with position sizing
  - Options trades: Strategy, strikes, expiration, IV, delta tracking
  - Auto-fetch historical indicators (ADX, RSI, volume)
  - Performance analytics and win rate metrics

### Alpha Research Platform 🆕
- **Signal Framework**: Standardized signal abstraction with 11+ built-in signals
- **Backtesting Engine**: IC, hit rate, Sharpe ratio, quantile analysis
- **Decay Analysis**: Signal predictive power across multiple horizons
- **Correlation Analysis**: Identify redundant and diversifying signals
- **Signal Combination**: IC-weighted composite signals with correlation penalty
- **Regime Detection**: Market regime classification (trending/mean-reverting/volatile)
- **Turnover Analysis**: Portfolio turnover and transaction cost modeling
- **REST API**: Complete API for programmatic access
- **Research Dashboard**: Interactive web UI for signal analysis

## Installation

### Prerequisites
- Docker and Docker Compose
- Python 3.12 (for local development)

Access at http://localhost:5002

### Quick Start with Docker
git clone <your-repo-url>
cd pattern_scanner_extended
docker compose up -d --build

### Local Development
```bash
pip install -r requirements.txt
python pattern_scanner.py
```
Access at http://127.0.0.1:5002

## Usage

### Pattern Scanner

1. **Scan Markets**: Use the dropdown to scan S&P 500, NASDAQ, or All US stocks
2. **View Details**: Click "View" on any detected pattern for full analysis
3. **Customize Charts**:
   - Toggle SMAs: 50 & 200, All, Short-term, None
   - Enable CTO Larsson Lines
4. **Analyze Patterns**: Review technical indicators, DCF, and options plays

### Alpha Research Platform

Access research dashboard at: **http://localhost:5002/research**

#### Sector Management 🆕

Organize stocks into market sectors for quick benchmarking:

- **Sector Dropdown**: Select from 19 pre-configured sectors (Semiconductors, Energy, AI, etc.)
- **Auto-populate**: Symbols field automatically fills with sector tickers
- **CRUD Operations**: Create, edit, and delete custom sectors via UI or API
- **Sector Manager**: Click "Manage" button to add/edit sectors in modal interface
- **API Endpoints**: Full REST API for programmatic sector management

**Pre-loaded Sectors**: Minerals & Mining, Energy, Solar, Nuclear, Semiconductors, Communications, SaaS, Biotech, Healthcare, Cybersecurity, AI, Data Centers, Crypto, Construction, Agriculture, Materials, Chemicals, Financial Services, REITs

#### Quick Start

```python
from signals import get_signal
from backtest import run_signal_backtest
import yfinance as yf
import pandas as pd

# Fetch data
symbols = ['AAPL', 'MSFT', 'GOOGL']
data = []
for symbol in symbols:
    df = yf.Ticker(symbol).history(start='2024-01-01', end='2025-12-31')
    df['symbol'] = symbol
    df = df.reset_index()
    df.columns = [c.lower() for c in df.columns]
    data.append(df[['symbol', 'date', 'open', 'high', 'low', 'close', 'volume']])

df_prices = pd.concat(data)

# Compute and backtest signal
signal = get_signal('rsi_14')
df_signals = signal.compute(df_prices)
results = run_signal_backtest(df_signals, df_prices, horizon_days=20)

print(f"IC: {results['ic_pearson_mean']:.2%}")
print(f"Hit Rate: {results['hit_rate']:.1%}")
print(f"Sharpe: {results['long_short_sharpe']:.2f}")
```

#### Available Signals

- **Technical**: `rsi_14`, `macd`, `momentum_20`, `volume_surge_20`, `ma_cross_50_200`, `cto_larsson`, `adx_14`
- **Patterns**: `cup_handle`, `asc_triangle`, `bull_flag`, `double_bottom`

#### Key Features

1. **Backtest Signals**: Compute IC, hit rate, and risk-adjusted returns
2. **Decay Analysis**: Analyze signal strength across multiple horizons
3. **Correlation Matrix**: Identify redundant and diversifying signals
4. **Composite Signals**: Combine multiple signals with IC-based weights
5. **Regime Analysis**: Evaluate signal performance by market regime
6. **Turnover Analysis**: Model transaction costs and portfolio turnover

See `docs/QUICKSTART.md` for detailed guide.

## API Endpoints

### Pattern Scanner

### Pattern Scanner

- `GET /`: Main scanner page
- `GET /chart/<symbol>`: Detailed chart with toggles
- `POST /scan`: Bulk market scan (JSON response)
- `GET /api/scan?market=sp500`: API scan endpoint

### Alpha Research Platform

- `GET /signals/list`: List all available signals
- `POST /signals/backtest`: Run signal backtest
- `POST /signals/decay`: Decay analysis across horizons
- `POST /signals/correlation`: Signal correlation matrix
- `POST /signals/composite`: Build composite signal
- `POST /signals/regime`: Regime-conditional analysis
- `POST /signals/turnover`: Portfolio turnover analysis
- `GET /research`: Research dashboard UI
- `GET /signals/sectors`: Get all sectors
- `GET /signals/sectors/<id>`: Get specific sector
- `POST /signals/sectors`: Create new sector
- `PUT /signals/sectors/<id>`: Update sector
- `DELETE /signals/sectors/<id>`: Delete sector

## Configuration

- **SMA Options**: ?sma=50,200 or ?sma=all
- **CTO Lines**: ?cto=1
- **EDGAR Financials**: ?edgar=1
- **Budget for Options**: ?budget=500

## Technical Details

- Built with Flask, yfinance, pandas-ta, matplotlib
- Docker containerized for easy deployment
- Responsive dark UI with HTML/CSS/JS
- Real-time data from Yahoo Finance

## Disclaimer

For educational purposes only. Not financial advice. Patterns are probabilistic—always do your own research.

## License

MIT License
