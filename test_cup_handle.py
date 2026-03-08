#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick test to verify cup & handle signal works with the Alpha Research Platform
"""
import sys
sys.path.insert(0, '/Users/richard/Documents/stocks/pattern_scanner_extended/pattern_scanner_expanded')

from signals import get_signal
from backtest import run_signal_backtest
import yfinance as yf
import pandas as pd

print("Testing Cup & Handle Signal...")
print("=" * 60)

# Fetch data for a few stocks
symbols = ['AAPL', 'MSFT', 'GOOGL']
data = []

print("\n1. Fetching price data...")
for symbol in symbols:
    try:
        df = yf.Ticker(symbol).history(start='2024-01-01', end='2025-12-31')
        if df.empty:
            continue
        df['symbol'] = symbol
        df = df.reset_index()
        df.columns = [c.lower() for c in df.columns]
        # Remove timezone
        if 'date' in df.columns and hasattr(df['date'].dtype, 'tz') and df['date'].dt.tz is not None:
            df['date'] = df['date'].dt.tz_localize(None)
        data.append(df[['symbol', 'date', 'open', 'high', 'low', 'close', 'volume']])
        print(f"   ✓ {symbol}: {len(df)} days")
    except Exception as e:
        print(f"   ✗ {symbol}: {e}")

if not data:
    print("\n❌ No data fetched. Exiting.")
    sys.exit(1)

df_prices = pd.concat(data)
print(f"\n   Total rows: {len(df_prices)}")

# Get cup & handle signal
print("\n2. Computing cup & handle signal...")
signal = get_signal('cup_handle')
if not signal:
    print("   ❌ Signal 'cup_handle' not found in registry!")
    sys.exit(1)

print(f"   ✓ Signal loaded: {signal.name}")

df_signals = signal.compute(df_prices)
print(f"   ✓ Signal computed: {len(df_signals)} signal values")

if df_signals.empty:
    print("   ❌ No signal values generated!")
    sys.exit(1)

# Show sample signal values
print("\n3. Sample signal values:")
print(df_signals.head(10).to_string(index=False))

# Run backtest
print("\n4. Running backtest (horizon=20 days)...")
try:
    results = run_signal_backtest(df_signals, df_prices, horizon_days=20)
    
    if 'error' in results:
        print(f"   ❌ Backtest error: {results['error']}")
        sys.exit(1)
    
    print("\n5. Backtest Results:")
    print("=" * 60)
    print(f"   IC (Pearson):        {results['ic_pearson_mean']:.2%}")
    print(f"   IC (Spearman):       {results['ic_spearman_mean']:.2%}")
    print(f"   Hit Rate:            {results['hit_rate']:.1%}")
    print(f"   Long-Only Return:    {results['long_only_return']:.2%}")
    print(f"   Long-Short Return:   {results['long_short_return']:.2%}")
    print(f"   Long-Short Sharpe:   {results['long_short_sharpe']:.2f}")
    print(f"   Observations:        {results['n_observations']}")
    print("=" * 60)
    
    if results['ic_pearson_mean'] > 0:
        print("\n✅ Cup & Handle signal is working! Positive IC detected.")
    else:
        print("\n⚠️  Cup & Handle signal computed but shows negative IC.")
        print("    This may be due to limited data or market conditions.")
    
except Exception as e:
    print(f"   ❌ Backtest failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n✅ Test completed successfully!")
