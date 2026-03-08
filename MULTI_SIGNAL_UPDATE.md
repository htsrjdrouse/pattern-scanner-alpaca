# Multi-Signal Backtest Update

## Changes Made

Updated the Alpha Research Platform dashboard to support running multiple signals simultaneously for comparison.

### Modified Files

**research_dashboard.py**
- Changed signal selector from single dropdown to multi-select list (Ctrl+Click to select multiple)
- Updated JavaScript to run backtests in parallel using `Promise.all()`
- Modified results display to show comparison table instead of detailed single-signal view

### New Features

1. **Multi-Signal Selection**: Select one or more signals using Ctrl+Click (Cmd+Click on Mac)
2. **Parallel Execution**: All selected signals are backtested simultaneously for faster results
3. **Comparison Table**: Results displayed in a compact table showing key metrics side-by-side:
   - IC (Information Coefficient)
   - Hit Rate
   - Long Return
   - Long/Short Return
   - Long/Short Sharpe
   - Observations

### Usage

1. Navigate to http://localhost:5004/research
2. In the "Quick Backtest" section, hold Ctrl (or Cmd on Mac) and click multiple signals
3. Configure symbols, timeframe, and horizon as before
4. Click "Run Backtest"
5. View comparison table with all selected signals

### Example Use Cases

- Compare technical indicators (RSI vs MACD vs Momentum)
- Evaluate pattern signals (Cup & Handle vs Bull Flag vs Ascending Triangle)
- Test signal combinations to find the best performers
- Identify redundant signals with similar performance

### Technical Details

- Backtests run in parallel via JavaScript `Promise.all()`
- Each signal makes an independent API call to `/signals/backtest`
- Results are aggregated and displayed in a sortable comparison table
- Color-coded metrics (green=positive, red=negative) for quick visual analysis

### Backward Compatibility

The underlying API endpoints remain unchanged. This is purely a UI enhancement that leverages existing backend functionality.
