# Alpha Research Platform Documentation

## Overview

The Alpha Research Platform transforms the pattern scanner into a systematic signal research and backtesting framework. It enables quantitative analysis of trading signals with institutional-grade metrics.

## Architecture

### Core Modules

1. **signals.py** - Signal abstraction and registry
2. **backtest.py** - Backtesting engine with IC, hit rate, and portfolio metrics
3. **analytics.py** - Signal correlation, combination, regime detection, and turnover analysis
4. **research_api.py** - Flask API endpoints
5. **research_dashboard.py** - Web UI for signal analysis

## Signal Framework

### Signal Base Class

All signals inherit from the `Signal` base class and implement:

```python
class Signal(ABC):
    def __init__(self, name, description, lookback_window, holding_period):
        pass
    
    def compute(self, df_prices, df_fundamentals=None, df_alt=None):
        """Returns DataFrame: [symbol, date, signal_name, signal_value]"""
        pass
```

### Available Signals

#### Pattern Signals
- **cup_handle** - Cup & Handle pattern strength (0-100 score)
- **asc_triangle** - Ascending triangle pattern strength
- **bull_flag** - Bull flag pattern strength
- **double_bottom** - Double bottom pattern strength

#### Technical Indicators
- **rsi_14** - RSI oversold/overbought (positive = oversold)
- **macd** - MACD histogram momentum
- **adx_14** - ADX trend strength (>25 = trending)
- **volume_surge_20** - Volume vs 20-day average (%)
- **cto_larsson** - CTO Larsson line momentum (EMA15 vs EMA29)
- **ma_cross_50_200** - Golden/Death cross (SMA 50 vs 200)
- **momentum_20** - 20-day price momentum (%)

### Adding New Signals

```python
class MySignal(Signal):
    def __init__(self):
        super().__init__('my_signal', 'Description', lookback_window=60, holding_period=10)
    
    def compute(self, df_prices, df_fundamentals=None, df_alt=None):
        results = []
        for symbol in df_prices['symbol'].unique():
            df = df_prices[df_prices['symbol'] == symbol]
            # Compute signal logic
            signal_value = ...  # Your calculation
            results.append({
                'symbol': symbol,
                'date': df['date'].iloc[-1],
                'signal_name': self.name,
                'signal_value': signal_value
            })
        return pd.DataFrame(results)

# Register in SIGNAL_REGISTRY
SIGNAL_REGISTRY['my_signal'] = MySignal()
```

## Backtesting

### Key Metrics

#### Information Coefficient (IC)
- **Pearson IC**: Linear correlation between signal and forward returns
- **Spearman IC**: Rank correlation (robust to outliers)
- Computed cross-sectionally per date, then averaged
- **Good IC**: >2% (0.02), **Strong IC**: >5% (0.05)

#### Hit Rate
- Percentage of times signal correctly predicts return sign
- **Random**: 50%, **Good**: >55%, **Strong**: >60%

#### Risk-Adjusted Returns
- **Long-Only**: Top quantile (80th percentile) portfolio
- **Long-Short**: Top vs bottom quantile
- **Sharpe Ratio**: Mean return / volatility

### Running Backtests

#### Python API

```python
from signals import get_signal
from backtest import run_signal_backtest
import pandas as pd

# Prepare price data
df_prices = pd.DataFrame({
    'symbol': ['AAPL', 'AAPL', ...],
    'date': [pd.Timestamp('2024-01-01'), ...],
    'open': [...], 'high': [...], 'low': [...],
    'close': [...], 'volume': [...]
})

# Compute signal
signal = get_signal('rsi_14')
df_signals = signal.compute(df_prices)

# Run backtest
results = run_signal_backtest(
    df_signals, 
    df_prices, 
    horizon_days=20,
    start_date='2024-01-01',
    end_date='2025-12-31'
)

print(f"IC: {results['ic_pearson_mean']:.3f}")
print(f"Hit Rate: {results['hit_rate']:.1%}")
print(f"Sharpe: {results['long_short_sharpe']:.2f}")
```

#### REST API

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

## Signal Decay Analysis

Analyze how signal predictive power decays over different horizons.

```python
from backtest import run_decay_analysis

decay_df = run_decay_analysis(
    df_signals,
    df_prices,
    horizons=[1, 2, 5, 10, 20, 60]
)

# decay_df columns: horizon, ic_pearson, ic_spearman, hit_rate, long_only_sharpe, long_short_sharpe
```

**Interpretation**:
- **Fast decay** (peak at 1-5 days): High-frequency signal, requires frequent rebalancing
- **Slow decay** (peak at 20-60 days): Position signal, lower turnover
- **No decay**: Signal may be spurious or data-mined

## Signal Correlation & Redundancy

### Correlation Matrix

```python
from analytics import signal_correlation_matrix

# Compute all signals
all_signals = []
for signal_name in ['rsi_14', 'macd', 'momentum_20']:
    signal = get_signal(signal_name)
    all_signals.append(signal.compute(df_prices))

df_all_signals = pd.concat(all_signals)
corr_matrix = signal_correlation_matrix(df_all_signals)
```

**Interpretation**:
- **|corr| > 0.7**: Highly redundant, consider dropping one
- **|corr| < 0.3**: Diversifying, good for combination
- **corr < 0**: Potentially complementary (e.g., trend vs mean-reversion)

## Signal Combination

### IC-Weighted Composite

```python
from analytics import build_composite_signal, compute_ic_weights

# Compute IC for each signal
ic_dict = {
    'rsi_14': 0.03,
    'macd': 0.025,
    'momentum_20': 0.04
}

# Compute weights with correlation penalty
weights = compute_ic_weights(ic_dict, corr_matrix, correlation_penalty=0.5)

# Build composite
df_composite = build_composite_signal(
    df_all_signals,
    signal_weights=weights
)

# Backtest composite
composite_results = run_signal_backtest(df_composite, df_prices, horizon_days=20)
```

**Expected Improvement**:
- Composite IC typically 1.2-1.5x best individual signal
- Lower volatility due to diversification
- More stable performance across regimes

## Regime Detection

### Market Regimes

```python
from analytics import detect_market_regime, compute_regime_conditional_ic

# Detect regimes using SPY
df_regimes = detect_market_regime(df_prices, index_symbol='SPY', lookback=60)

# Regimes: 'trending', 'mean_reverting', 'volatile'

# Compute IC by regime
regime_ic = compute_regime_conditional_ic(
    df_all_signals,
    df_prices,
    df_regimes,
    horizon_days=20
)
```

**Interpretation**:
- **Momentum signals**: Strong in trending regimes, weak in mean-reverting
- **Mean-reversion signals**: Strong in mean-reverting, weak in trending
- **Pattern signals**: Often regime-agnostic or prefer low volatility

## Turnover & Transaction Costs

```python
from analytics import analyze_turnover, apply_transaction_costs

# Analyze turnover
turnover_metrics = analyze_turnover(
    df_signals,
    rebalance_freq=20,  # days
    top_pct=0.2  # top 20% of stocks
)

print(f"Mean Turnover: {turnover_metrics['mean_turnover']:.1%}")

# Apply costs (10 bps per trade)
net_returns = apply_transaction_costs(
    portfolio_returns,
    turnover=turnover_metrics['mean_turnover'],
    cost_bps=10
)
```

**Typical Turnover**:
- **Low**: <20% per rebalance (position signals)
- **Medium**: 20-50% (swing signals)
- **High**: >50% (high-frequency signals)

**Cost Impact**:
- 10 bps cost + 50% turnover = -5 bps per rebalance
- For 20-day rebalance: -5 bps * 12 = -60 bps/year

## API Endpoints

### GET /signals/list
List all available signals with metadata.

### POST /signals/backtest
Run backtest for a signal.

**Request**:
```json
{
  "signal_name": "rsi_14",
  "symbols": ["AAPL", "MSFT"],
  "horizon_days": 20,
  "start_date": "2024-01-01",
  "end_date": "2025-12-31"
}
```

**Response**:
```json
{
  "signal_name": "rsi_14",
  "ic_pearson_mean": 0.032,
  "ic_spearman_mean": 0.028,
  "hit_rate": 0.56,
  "long_only_sharpe": 1.2,
  "long_short_sharpe": 1.8,
  "n_observations": 1250
}
```

### POST /signals/decay
Run decay analysis across multiple horizons.

### POST /signals/correlation
Compute signal correlation matrix.

### POST /signals/composite
Build and backtest composite signal.

### POST /signals/regime
Analyze signal performance by market regime.

### POST /signals/turnover
Analyze portfolio turnover.

## Web Dashboard

Access at: **http://localhost:5002/research**

Features:
- Signal library browser
- Quick backtest interface
- Correlation analysis
- Interactive results display

## Best Practices

### Signal Development
1. **Start simple**: Single indicator or pattern
2. **Economic intuition**: Why should this predict returns?
3. **Avoid overfitting**: Test on out-of-sample data
4. **Check decay**: Ensure predictive power at intended horizon
5. **Correlation check**: Verify not redundant with existing signals

### Backtesting
1. **Sufficient data**: >500 observations for reliable IC
2. **Cross-sectional**: Compute IC per date, not pooled
3. **Multiple horizons**: Check decay curve
4. **Regime analysis**: Understand when signal works
5. **Transaction costs**: Always include realistic costs

### Signal Combination
1. **IC-weighted**: Weight by historical IC
2. **Diversify**: Combine low-correlation signals
3. **Regime-aware**: Consider regime-conditional weights
4. **Rebalance**: Update weights periodically (e.g., quarterly)

### Production Monitoring
1. **Track live IC**: Compare to backtest expectations
2. **Decay monitoring**: Check if decay curve shifts
3. **Correlation drift**: Monitor signal correlations over time
4. **Regime shifts**: Detect regime changes early

## Example Workflow

### 1. Develop New Signal

```python
# signals.py
class NewPatternSignal(Signal):
    def __init__(self):
        super().__init__('new_pattern', 'My new pattern', 60, 15)
    
    def compute(self, df_prices, df_fundamentals=None, df_alt=None):
        # Implementation
        pass

SIGNAL_REGISTRY['new_pattern'] = NewPatternSignal()
```

### 2. Backtest

```python
signal = get_signal('new_pattern')
df_signals = signal.compute(df_prices)
results = run_signal_backtest(df_signals, df_prices, horizon_days=15)
```

### 3. Analyze Decay

```python
decay_df = run_decay_analysis(df_signals, df_prices, horizons=[1, 5, 10, 15, 20, 30])
# Plot decay curve
```

### 4. Check Correlation

```python
# Compare with existing signals
corr_matrix = signal_correlation_matrix(df_all_signals)
# If |corr| < 0.5 with all existing signals, it's diversifying
```

### 5. Combine Signals

```python
# Add to composite with IC-based weights
weights = compute_ic_weights(ic_dict, corr_matrix)
df_composite = build_composite_signal(df_all_signals, weights)
```

### 6. Monitor Live

```python
# Daily: compute signal on latest data
# Weekly: compare realized IC vs backtest
# Monthly: update weights if needed
```

## Performance Benchmarks

### Good Signal Characteristics
- **IC**: >2% (Pearson or Spearman)
- **Hit Rate**: >53%
- **Sharpe**: >1.0 (long-short)
- **Decay**: Predictive power at intended horizon
- **Stability**: IC std < 2x IC mean

### Composite Signal Targets
- **IC**: 4-6% (from combining 3-5 signals)
- **Hit Rate**: 55-58%
- **Sharpe**: 1.5-2.5 (long-short)
- **Turnover**: <40% per rebalance

## Troubleshooting

### Low IC (<1%)
- Signal may be weak or spurious
- Check data quality
- Try different horizons
- Consider regime-conditional analysis

### High Correlation (>0.8)
- Signals are redundant
- Drop one or reduce weight
- Look for diversifying signals

### High Turnover (>70%)
- Signal is too noisy
- Smooth signal (e.g., moving average)
- Increase rebalancing frequency
- Apply turnover penalty in optimization

### Regime Instability
- Signal works in some regimes, not others
- Use regime-conditional weights
- Combine with regime-agnostic signals
- Consider regime-switching model

## References

- **Information Coefficient**: Grinold & Kahn, "Active Portfolio Management"
- **Signal Combination**: Kakushadze, "101 Formulaic Alphas"
- **Transaction Costs**: Frazzini et al., "Betting Against Beta"
- **Regime Detection**: Kritzman et al., "Regime Shifts: Implications for Dynamic Strategies"
