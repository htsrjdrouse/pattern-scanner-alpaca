#!/usr/bin/env python3
"""
Quick test script for IV-aware options strategy selector.
Tests the decision tree logic without running the full Flask app.
"""

# Test the decision tree logic
test_cases = [
    # (iv_rank, vix, expected_strategy)
    (25, 15, "Long Call"),           # Low IV, Low VIX
    (30, 18, "Long Call"),           # Low IV, Low VIX
    (70, 25, "Cash-Secured Put"),    # High IV
    (80, 30, "Cash-Secured Put"),    # High IV
    (45, 22, "Poor Man's Covered Call"),  # Moderate IV
    (50, 18, "Poor Man's Covered Call"),  # Moderate IV
    (35, 25, "Poor Man's Covered Call"),  # Moderate IV (VIX too high for Long Call)
]

print("IV-Aware Strategy Selector - Decision Tree Test\n")
print("=" * 60)

for iv_rank, vix, expected in test_cases:
    # Apply decision tree
    if iv_rank < 35 and vix < 20:
        strategy = "Long Call"
        regime = "Low IV"
    elif iv_rank >= 65:
        strategy = "Cash-Secured Put"
        regime = "Elevated IV"
    else:
        strategy = "Poor Man's Covered Call"
        regime = "Moderate IV"
    
    status = "✓" if strategy == expected else "✗"
    print(f"{status} IV Rank: {iv_rank:3}% | VIX: {vix:5.1f} | Regime: {regime:12} | Strategy: {strategy}")
    
    if strategy != expected:
        print(f"  ERROR: Expected {expected}, got {strategy}")

print("=" * 60)
print("\nDecision Tree:")
print("  IF IV rank < 35 AND VIX < 20:")
print("    → Long Call (Low IV regime)")
print("  ELSE IF IV rank >= 65:")
print("    → Cash-Secured Put (Elevated IV regime)")
print("  ELSE:")
print("    → Poor Man's Covered Call (Moderate IV regime)")
