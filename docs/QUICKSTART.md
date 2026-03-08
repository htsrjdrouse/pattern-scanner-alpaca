# Alpha Research Platform - Quick Start

## Installation

No additional dependencies required beyond existing pattern_scanner requirements.

## 5-Minute Quick Start

### 1. Start the Server

```bash
python pattern_scanner.py
```

Access research dashboard at: **http://localhost:5002/research**

### 2. Run Your First Backtest (Python)

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

# Compute signal
signal = get_signal('rsi_14')
df_signals = signal.compute(df_prices)

# Backtest
results = run_signal_backtest(df_signals, df_prices, horizon_days=20)

print(f"IC: {results['ic_pearson_mean']:.2%}")
print(f"Hit Rate: {results['hit_rate']:.1%}")
print(f"Sharpe: {results['long_short_sharpe']:.2f}")
```

### 3. Run Your First Backtest (API)

```bash
curl -X POST http://localhost:5002/signals/backtest \
  -H "Content-Type: application/json" \
  -d '{
    "signal_name": "rsi_14",
    "symbols": ["AAPL", "MSFT", "GOOGL"],
    "horizon_days": 20,
    "start_date": "2024-01-01",
    "end_date": "2025-12-31"
  }'
```

## Available Signals

| Signal | Type | Description |
|--------|------|-------------|
| `rsi_14` | Technical | RSI oversold/overbought |
| `macd` | Technical | MACD momentum |
| `momentum_20` | Technical | 20-day price momentum |
| `volume_surge_20` | Technical | Volume vs average |
| `ma_cross_50_200` | Technical | Golden/Death cross |
| `cto_larsson` | Technical | CTO Larsson lines |
| `adx_14` | Technical | Trend strength |
| `cup_handle` | Pattern | Cup & Handle |
| `asc_triangle` | Pattern | Ascending Triangle |
| `bull_flag` | Pattern | Bull Flag |
| `double_bottom` | Pattern | Double Bottom |

## Key Metrics Explained

### Information Coefficient (IC)
- Correlation between signal and future returns
- **Good**: >2%, **Strong**: >5%
- Higher is better

### Hit Rate
- % of correct directional predictions
- **Random**: 50%, **Good**: >55%
- Higher is better

### Sharpe Ratio
- Return per unit of risk
- **Good**: >1.0, **Strong**: >2.0
- Higher is better

## Common Tasks

### Analyze Signal Decay

```python
from backtest import run_decay_analysis

decay_df = run_decay_analysis(
    df_signals, 
    df_prices, 
    horizons=[1, 5, 10, 20, 60]
)
print(decay_df)
```

### Check Signal Correlation

```python
from analytics import signal_correlation_matrix

# Compute multiple signals
all_signals = []
for name in ['rsi_14', 'macd', 'momentum_20']:
    signal = get_signal(name)
    all_signals.append(signal.compute(df_prices))

df_all = pd.concat(all_signals)
corr = signal_correlation_matrix(df_all)
print(corr)
```

### Build Composite Signal

```python
from analytics import build_composite_signal

weights = {
    'rsi_14': 0.4,
    'macd': 0.3,
    'momentum_20': 0.3
}

df_composite = build_composite_signal(df_all, signal_weights=weights)
```

### Analyze by Market Regime

```python
from analytics import detect_market_regime, compute_regime_conditional_ic

df_regimes = detect_market_regime(df_prices, index_symbol='SPY')
regime_ic = compute_regime_conditional_ic(df_all, df_prices, df_regimes)
print(regime_ic)
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/signals/list` | GET | List all signals |
| `/signals/backtest` | POST | Run backtest |
| `/signals/decay` | POST | Decay analysis |
| `/signals/correlation` | POST | Correlation matrix |
| `/signals/composite` | POST | Build composite |
| `/signals/regime` | POST | Regime analysis |
| `/signals/turnover` | POST | Turnover analysis |

## Examples

Run complete workflow examples:

```bash
cd examples
python research_workflow.py
```

## Documentation

Full documentation: `docs/RESEARCH_PLATFORM.md`

## Adding Your Own Signal

```python
# In signals.py
from signals import Signal, SIGNAL_REGISTRY

class MySignal(Signal):
    def __init__(self):
        super().__init__('my_signal', 'My custom signal', 60, 10)
    
    def compute(self, df_prices, df_fundamentals=None, df_alt=None):
        results = []
        for symbol in df_prices['symbol'].unique():
            df = df_prices[df_prices['symbol'] == symbol]
            # Your logic here
            signal_value = ...
            results.append({
                'symbol': symbol,
                'date': df['date'].iloc[-1],
                'signal_name': self.name,
                'signal_value': signal_value
            })
        return pd.DataFrame(results)

# Register
SIGNAL_REGISTRY['my_signal'] = MySignal()
```

## Troubleshooting

### "No module named 'signals'"
Make sure you're in the project directory: `/home/rista/pattern_scanner_expanded`

### "Insufficient data for backtest"
- Ensure date range has enough data (>30 days)
- Check symbols are valid and have data

### Low IC (<1%)
- Signal may be weak
- Try different horizons
- Check data quality

## Next Steps

1. **Explore signals**: Try different signals and horizons
2. **Analyze decay**: Understand signal timing
3. **Check correlations**: Find diversifying signals
4. **Build composite**: Combine best signals
5. **Monitor live**: Track performance vs backtest

## Support

- Full docs: `docs/RESEARCH_PLATFORM.md`
- Examples: `examples/research_workflow.py`
- Web UI: http://localhost:5002/research
