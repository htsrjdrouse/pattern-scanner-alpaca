#!/usr/bin/env python3
"""
Test regime detection logic for options strategy selector.
"""

def classify_regime(adx_value, cto_bullish):
    """Classify market regime using ADX and CTO Larsson."""
    if adx_value is None:
        return 'UNKNOWN', 'Insufficient data'
    
    if adx_value > 25:
        if cto_bullish:
            return 'TRENDING_BULLISH', f'Strong bullish trend (ADX {adx_value:.1f})'
        else:
            return 'TRENDING_BEARISH', f'Strong bearish trend (ADX {adx_value:.1f})'
    elif adx_value < 20:
        return 'RANGE_BOUND', f'Range-bound market (ADX {adx_value:.1f})'
    else:
        return 'TRANSITIONING', f'Transitioning regime (ADX {adx_value:.1f})'


# Test cases: (adx, cto_bullish, expected_regime)
test_cases = [
    (30, True, 'TRENDING_BULLISH'),
    (28, False, 'TRENDING_BEARISH'),
    (15, True, 'RANGE_BOUND'),
    (18, False, 'RANGE_BOUND'),
    (22, True, 'TRANSITIONING'),
    (23, False, 'TRANSITIONING'),
    (None, True, 'UNKNOWN'),
]

print("Regime Detection Test\n")
print("=" * 70)

for adx, cto_bullish, expected in test_cases:
    regime, desc = classify_regime(adx, cto_bullish)
    status = "✓" if regime == expected else "✗"
    cto_str = "Bullish" if cto_bullish else "Bearish"
    adx_str = f"{adx:5.1f}" if adx is not None else " None"
    print(f"{status} ADX: {adx_str} | CTO: {cto_str:8} | Regime: {regime:18} | {desc}")

print("=" * 70)
print("\nRegime Override Rules:")
print("  TRENDING_BEARISH → Suppress options, show warning")
print("  RANGE_BOUND + Low IV → Iron Condor instead of Long Call")
print("  TRENDING_BULLISH/TRANSITIONING → Use IV-based selection")
