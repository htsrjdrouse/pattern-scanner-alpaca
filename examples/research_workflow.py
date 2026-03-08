"""
Example: Complete signal research workflow (Alpaca-powered)
"""
import pandas as pd
from datetime import datetime, timedelta
from signals import get_signal, SIGNAL_REGISTRY
from backtest import run_signal_backtest, run_decay_analysis
from analytics import (
    signal_correlation_matrix, 
    build_composite_signal,
    compute_ic_weights,
    detect_market_regime,
    compute_regime_conditional_ic
)
from alpaca_data import fetch_stock_data


def fetch_data(symbols, start_date, end_date):
    """Fetch price data for analysis using Alpaca."""
    data = []
    for symbol in symbols:
        try:
            df = fetch_stock_data(symbol, start_date, end_date)
            if df is None or df.empty:
                continue
            data.append(df[['symbol', 'date', 'open', 'high', 'low', 'close', 'volume']])
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
    
    return pd.concat(data, ignore_index=True) if data else pd.DataFrame()


def example_single_signal_backtest():
    """Example 1: Backtest a single signal."""
    print("=" * 60)
    print("Example 1: Single Signal Backtest")
    print("=" * 60)
    
    # Setup
    symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META']
    start_date = '2024-01-01'
    end_date = '2025-12-31'
    
    # Fetch data
    print(f"\nFetching data for {len(symbols)} symbols...")
    df_prices = fetch_data(symbols, start_date, end_date)
    print(f"Fetched {len(df_prices)} price records")
    
    # Compute signal
    signal = get_signal('rsi_14')
    print(f"\nComputing signal: {signal.name}")
    df_signals = signal.compute(df_prices)
    print(f"Computed {len(df_signals)} signal values")
    
    # Run backtest
    print("\nRunning backtest...")
    results = run_signal_backtest(df_signals, df_prices, horizon_days=20)
    
    # Display results
    print("\n" + "=" * 60)
    print("BACKTEST RESULTS")
    print("=" * 60)
    print(f"Signal: {results['signal_name']}")
    print(f"Observations: {results['n_observations']}")
    print(f"\nPredictive Power:")
    print(f"  IC (Pearson):  {results['ic_pearson_mean']:>7.2%} ± {results['ic_pearson_std']:.2%}")
    print(f"  IC (Spearman): {results['ic_spearman_mean']:>7.2%} ± {results['ic_spearman_std']:.2%}")
    print(f"  Hit Rate:      {results['hit_rate']:>7.1%}")
    print(f"\nPortfolio Performance:")
    print(f"  Long-Only Return:  {results['long_only_return']:>7.2%}")
    print(f"  Long-Only Sharpe:  {results['long_only_sharpe']:>7.2f}")
    print(f"  Long-Short Return: {results['long_short_return']:>7.2%}")
    print(f"  Long-Short Sharpe: {results['long_short_sharpe']:>7.2f}")
    print("=" * 60)


def example_decay_analysis():
    """Example 2: Analyze signal decay."""
    print("\n" + "=" * 60)
    print("Example 2: Signal Decay Analysis")
    print("=" * 60)
    
    symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA']
    df_prices = fetch_data(symbols, '2024-01-01', '2025-12-31')
    
    signal = get_signal('momentum_20')
    df_signals = signal.compute(df_prices)
    
    print(f"\nAnalyzing decay for: {signal.name}")
    decay_df = run_decay_analysis(df_signals, df_prices, horizons=[1, 5, 10, 20, 40, 60])
    
    print("\n" + "=" * 60)
    print("DECAY CURVE")
    print("=" * 60)
    print(f"{'Horizon':>8} {'IC':>8} {'Hit Rate':>10} {'L/S Sharpe':>12}")
    print("-" * 60)
    for _, row in decay_df.iterrows():
        print(f"{row['horizon']:>8}d {row['ic_pearson']:>7.2%} {row['hit_rate']:>9.1%} {row['long_short_sharpe']:>11.2f}")
    print("=" * 60)


def example_signal_correlation():
    """Example 3: Analyze signal correlations."""
    print("\n" + "=" * 60)
    print("Example 3: Signal Correlation Analysis")
    print("=" * 60)
    
    symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA']
    df_prices = fetch_data(symbols, '2024-01-01', '2025-12-31')
    
    # Compute multiple signals
    signal_names = ['rsi_14', 'macd', 'momentum_20', 'volume_surge_20']
    all_signals = []
    
    print(f"\nComputing {len(signal_names)} signals...")
    for name in signal_names:
        signal = get_signal(name)
        df_sig = signal.compute(df_prices)
        all_signals.append(df_sig)
    
    df_all_signals = pd.concat(all_signals, ignore_index=True)
    
    # Compute correlation
    corr_matrix = signal_correlation_matrix(df_all_signals)
    
    print("\n" + "=" * 60)
    print("CORRELATION MATRIX")
    print("=" * 60)
    print(corr_matrix.round(2))
    print("=" * 60)
    
    # Identify redundant signals
    print("\nRedundancy Analysis:")
    for i, sig1 in enumerate(signal_names):
        for sig2 in signal_names[i+1:]:
            if sig1 in corr_matrix.index and sig2 in corr_matrix.columns:
                corr = corr_matrix.loc[sig1, sig2]
                if abs(corr) > 0.7:
                    print(f"  ⚠️  {sig1} <-> {sig2}: {corr:.2f} (HIGH CORRELATION)")
                elif abs(corr) < 0.3:
                    print(f"  ✓  {sig1} <-> {sig2}: {corr:.2f} (diversifying)")


def example_composite_signal():
    """Example 4: Build composite signal."""
    print("\n" + "=" * 60)
    print("Example 4: Composite Signal")
    print("=" * 60)
    
    symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META']
    df_prices = fetch_data(symbols, '2024-01-01', '2025-12-31')
    
    # Compute signals
    signal_names = ['rsi_14', 'macd', 'momentum_20']
    all_signals = []
    ic_dict = {}
    
    print(f"\nComputing and backtesting {len(signal_names)} signals...")
    for name in signal_names:
        signal = get_signal(name)
        df_sig = signal.compute(df_prices)
        all_signals.append(df_sig)
        
        # Get IC for weighting
        results = run_signal_backtest(df_sig, df_prices, horizon_days=20)
        ic_dict[name] = results['ic_pearson_mean']
        print(f"  {name}: IC = {results['ic_pearson_mean']:.2%}")
    
    df_all_signals = pd.concat(all_signals, ignore_index=True)
    
    # Compute correlation
    corr_matrix = signal_correlation_matrix(df_all_signals)
    
    # Compute IC-weighted composite
    print("\nComputing IC-weighted composite...")
    weights = compute_ic_weights(ic_dict, corr_matrix, correlation_penalty=0.5)
    
    print("\nSignal Weights:")
    for name, weight in weights.items():
        print(f"  {name}: {weight:.1%}")
    
    # Build composite
    df_composite = build_composite_signal(df_all_signals, signal_weights=weights)
    
    # Backtest composite
    print("\nBacktesting composite...")
    composite_results = run_signal_backtest(df_composite, df_prices, horizon_days=20)
    
    print("\n" + "=" * 60)
    print("COMPOSITE vs INDIVIDUAL SIGNALS")
    print("=" * 60)
    print(f"{'Signal':<20} {'IC':>8} {'Hit Rate':>10} {'Sharpe':>8}")
    print("-" * 60)
    
    for name in signal_names:
        signal = get_signal(name)
        df_sig = signal.compute(df_prices)
        results = run_signal_backtest(df_sig, df_prices, horizon_days=20)
        print(f"{name:<20} {results['ic_pearson_mean']:>7.2%} {results['hit_rate']:>9.1%} {results['long_short_sharpe']:>7.2f}")
    
    print("-" * 60)
    print(f"{'COMPOSITE':<20} {composite_results['ic_pearson_mean']:>7.2%} {composite_results['hit_rate']:>9.1%} {composite_results['long_short_sharpe']:>7.2f}")
    print("=" * 60)


def example_regime_analysis():
    """Example 5: Regime-conditional analysis."""
    print("\n" + "=" * 60)
    print("Example 5: Regime-Conditional Analysis")
    print("=" * 60)
    
    symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'SPY']
    df_prices = fetch_data(symbols, '2024-01-01', '2025-12-31')
    
    # Detect regimes
    print("\nDetecting market regimes using SPY...")
    df_regimes = detect_market_regime(df_prices, index_symbol='SPY', lookback=60)
    
    regime_counts = df_regimes['regime'].value_counts()
    print("\nRegime Distribution:")
    for regime, count in regime_counts.items():
        print(f"  {regime}: {count} days ({count/len(df_regimes)*100:.1f}%)")
    
    # Compute signals
    signal_names = ['momentum_20', 'rsi_14']
    all_signals = []
    
    print(f"\nComputing {len(signal_names)} signals...")
    for name in signal_names:
        signal = get_signal(name)
        df_sig = signal.compute(df_prices)
        all_signals.append(df_sig)
    
    df_all_signals = pd.concat(all_signals, ignore_index=True)
    
    # Regime-conditional IC
    print("\nComputing regime-conditional IC...")
    regime_ic = compute_regime_conditional_ic(df_all_signals, df_prices, df_regimes, horizon_days=20)
    
    print("\n" + "=" * 60)
    print("REGIME-CONDITIONAL IC")
    print("=" * 60)
    print(f"{'Signal':<20} {'Regime':<15} {'IC':>8} {'N':>6}")
    print("-" * 60)
    for _, row in regime_ic.iterrows():
        print(f"{row['signal_name']:<20} {row['regime']:<15} {row['ic_mean']:>7.2%} {row['n_observations']:>6}")
    print("=" * 60)


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("ALPHA RESEARCH PLATFORM - EXAMPLES")
    print("=" * 60)
    
    # Run all examples
    example_single_signal_backtest()
    example_decay_analysis()
    example_signal_correlation()
    example_composite_signal()
    example_regime_analysis()
    
    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)
