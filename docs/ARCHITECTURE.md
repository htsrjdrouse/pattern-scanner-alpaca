# Alpha Research Platform Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    ALPHA RESEARCH PLATFORM                       │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                         DATA LAYER                               │
├─────────────────────────────────────────────────────────────────┤
│  • yfinance (price data)                                         │
│  • DataFrame format: [symbol, date, OHLCV]                       │
│  • Standardized signal output: [symbol, date, signal_name, value]│
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                       SIGNAL LAYER                               │
├─────────────────────────────────────────────────────────────────┤
│  signals.py                                                      │
│  ├── Signal (base class)                                         │
│  ├── Pattern Signals (4)                                         │
│  │   ├── Cup & Handle                                            │
│  │   ├── Ascending Triangle                                      │
│  │   ├── Bull Flag                                               │
│  │   └── Double Bottom                                           │
│  ├── Technical Signals (7)                                       │
│  │   ├── RSI, MACD, ADX                                          │
│  │   ├── Volume Surge                                            │
│  │   ├── CTO Larsson                                             │
│  │   ├── MA Cross                                                │
│  │   └── Momentum                                                │
│  └── SIGNAL_REGISTRY                                             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      BACKTEST LAYER                              │
├─────────────────────────────────────────────────────────────────┤
│  backtest.py                                                     │
│  ├── Forward Returns                                             │
│  ├── Information Coefficient (IC)                                │
│  │   ├── Pearson (linear)                                        │
│  │   └── Spearman (rank)                                         │
│  ├── Hit Rate                                                    │
│  ├── Portfolio Metrics                                           │
│  │   ├── Long-Only                                               │
│  │   └── Long-Short                                              │
│  ├── Sharpe Ratio                                                │
│  ├── Quantile Analysis                                           │
│  └── Decay Analysis                                              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                     ANALYTICS LAYER                              │
├─────────────────────────────────────────────────────────────────┤
│  analytics.py                                                    │
│  ├── Signal Correlation                                          │
│  │   ├── Cross-sectional                                         │
│  │   └── IC time-series                                          │
│  ├── Signal Combination                                          │
│  │   ├── IC-weighted                                             │
│  │   └── Correlation penalty                                     │
│  ├── Regime Detection                                            │
│  │   ├── Trending                                                │
│  │   ├── Mean-Reverting                                          │
│  │   └── Volatile                                                │
│  └── Turnover Analysis                                           │
│      ├── Portfolio churn                                         │
│      └── Transaction costs                                       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                            │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────┐ │
│  │   REST API       │  │   Web Dashboard  │  │  Python API   │ │
│  │  research_api.py │  │ research_dash.py │  │  Direct Import│ │
│  ├──────────────────┤  ├──────────────────┤  ├───────────────┤ │
│  │ /signals/list    │  │ Signal Library   │  │ get_signal()  │ │
│  │ /signals/backtest│  │ Backtest UI      │  │ run_backtest()│ │
│  │ /signals/decay   │  │ Correlation UI   │  │ analytics.*() │ │
│  │ /signals/corr    │  │ Results Display  │  │               │ │
│  │ /signals/composite│ │                  │  │               │ │
│  │ /signals/regime  │  │                  │  │               │ │
│  │ /signals/turnover│  │                  │  │               │ │
│  └──────────────────┘  └──────────────────┘  └───────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. Signal Computation
```
Price Data → Signal.compute() → Signal Values
[OHLCV]                         [symbol, date, signal_name, value]
```

### 2. Backtesting
```
Signal Values + Price Data → run_signal_backtest() → Metrics
                                                      [IC, Hit Rate, Sharpe]
```

### 3. Signal Combination
```
Multiple Signals → Correlation Analysis → IC Weights → Composite Signal
                                                        [weighted combination]
```

### 4. Regime Analysis
```
Price Data → Regime Detection → Regime Labels → Conditional IC
[SPY]        [trend/mean/vol]                   [IC by regime]
```

## Module Dependencies

```
pattern_scanner.py (main Flask app)
    ├── research_api.py (API endpoints)
    │   ├── signals.py
    │   ├── backtest.py
    │   └── analytics.py
    └── research_dashboard.py (Web UI)
        └── signals.py

signals.py (standalone)
    └── pandas, numpy, pandas_ta, scipy

backtest.py
    ├── pandas, numpy
    └── scipy.stats

analytics.py
    ├── pandas, numpy
    ├── scipy.stats
    └── backtest.py (for regime IC)
```

## Key Design Principles

### 1. Standardization
- All signals produce same output format
- Consistent DataFrame schemas
- Unified metric definitions

### 2. Modularity
- Each module is independent
- Clear separation of concerns
- Easy to extend

### 3. Composability
- Signals can be combined
- Metrics can be computed independently
- Flexible analysis pipelines

### 4. Performance
- Vectorized operations (pandas/numpy)
- Cross-sectional computations
- Efficient data structures

## Workflow Examples

### Research Workflow
```
1. Define Signal → 2. Compute on Data → 3. Backtest
                                            ↓
                                        4. Analyze Decay
                                            ↓
                                        5. Check Correlation
                                            ↓
                                        6. Combine Signals
                                            ↓
                                        7. Regime Analysis
                                            ↓
                                        8. Production
```

### API Workflow
```
Client → POST /signals/backtest → research_api.py
                                        ↓
                                   fetch_data()
                                        ↓
                                   get_signal()
                                        ↓
                                   signal.compute()
                                        ↓
                                   run_signal_backtest()
                                        ↓
                                   JSON Response
```

### Dashboard Workflow
```
Browser → /research → research_dashboard.py
                            ↓
                      Render HTML/JS
                            ↓
                      User Interaction
                            ↓
                      AJAX → /signals/* API
                            ↓
                      Display Results
```

## Integration Points

### With Existing Pattern Scanner
- No modifications to existing endpoints
- Shared Flask app instance
- Optional research features
- Backward compatible

### With External Systems
- REST API for programmatic access
- Standard DataFrame formats
- JSON responses
- Easy to integrate with other tools

## Scalability Considerations

### Current Implementation
- In-memory computation
- Single-threaded
- Suitable for 100s of symbols, years of data

### Future Enhancements
- Parallel signal computation
- Database backend for results
- Caching layer
- Distributed backtesting

## Security & Best Practices

- No sensitive data storage
- Read-only data access
- Input validation on API endpoints
- Error handling throughout
- Graceful degradation

## Monitoring & Observability

### Metrics to Track
- Signal IC over time
- Hit rate trends
- Correlation drift
- Regime shifts
- Turnover changes

### Logging
- API request/response
- Backtest execution time
- Data fetch errors
- Signal computation warnings
