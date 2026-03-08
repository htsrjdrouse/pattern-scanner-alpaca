# IV-Aware Options Strategy Selector - Implementation Summary

## Changes Made

### 1. Core Logic Replacement (Lines 230-600+)

Replaced the static Bull Call Spread recommendation with an IV-aware strategy selector that dynamically chooses between three strategies based on market conditions.

### 2. New Functions Added

#### `calculate_iv_rank(symbol)` (Line ~258)
- Calculates IV rank (0-100) using 52-week IV range
- Samples first 12 expirations to build IV history
- Returns 50 (neutral) if insufficient data
- Formula: `(current_iv - iv_low) / (iv_high - iv_low) * 100`

#### `get_vix()` (Line ~285)
- Fetches current VIX level from Yahoo Finance
- Returns 20 as default if fetch fails

#### `suggest_bull_call_spread()` - Refactored (Line ~304)
- Now acts as strategy selector/router
- Determines regime based on IV rank and VIX
- Calls appropriate strategy builder function

#### `_build_long_call()` (Line ~330)
- **Trigger**: IV rank < 35 AND VIX < 20
- **Regime**: Low IV
- **Rationale**: "Low IV environment — buy premium, don't sell it. Spread caps upside on a breakout setup."
- **Structure**: Single long call at 1 SD above current price
- **Expiration**: 45 DTE (finds nearest >= 40 days)
- **Strike Selection**: `SD = current_price * IV * sqrt(45/365)`
- **Returns**: Strike, premium, max loss (premium paid), max gain (unlimited)

#### `_build_cash_secured_put()` (Line ~390)
- **Trigger**: IV rank >= 65
- **Regime**: Elevated IV
- **Rationale**: "Elevated IV — sell rich premium. Get paid to wait for pullback to your entry price."
- **Structure**: Sell ATM put
- **Expiration**: 30-45 DTE
- **Strike Selection**: ATM or first OTM put near support
- **Returns**: Premium collected, effective entry price, breakeven

#### `_build_pmcc()` (Line ~450)
- **Trigger**: IV rank >= 35 AND < 65
- **Regime**: Moderate IV
- **Rationale**: "Moderate IV — diagonal gives long delta exposure with reduced capital vs. shares, and short leg offsets cost."
- **Structure**: Poor Man's Covered Call (diagonal spread)
- **Long Leg**: Deep ITM call (0.80+ delta), 90+ DTE
- **Short Leg**: OTM call (0.30 delta), 30-45 DTE
- **Returns**: Both legs with strikes, expirations, net debit, max profit, max loss

### 3. HTML Template Updates (Lines 3250-3460)

#### Options Conditions Summary Box
Added new section displaying:
- IV Rank: [value]%
- VIX: [value]
- Regime: [Low IV / Moderate IV / Elevated IV]
- Strategy Selected: [strategy name]
- Rationale text

#### Strategy-Specific Display Sections

**Long Call Display**:
- 2-column layout
- Trade Setup: Strike, premium, delta, volume, OI, IV
- Risk & Reward: Max loss, max gain (unlimited), budget

**Cash-Secured Put Display**:
- 2-column layout
- Trade Setup: Put strike, premium collected, effective entry, breakeven
- Risk & Reward: Max gain (premium), max loss, collateral requirement note

**Poor Man's Covered Call Display**:
- 3-column layout
- Long Leg (LEAP): Deep ITM call details with 90+ DTE
- Short Leg: OTM call details with 30-45 DTE
- Position: Net debit, contracts, total cost, max gain/loss

### 4. Error Handling

- Returns `{'status': 'no_options', 'message': 'Options data unavailable for [TICKER] — consider equity position sizing instead.'}` when options chain is unavailable
- No crashes on missing data
- Graceful fallbacks for IV rank (50) and VIX (20)

## Decision Tree

```
IF IV rank < 35 AND VIX < 20:
  → Long Call (buy premium in low IV)

ELSE IF IV rank >= 65:
  → Cash-Secured Put (sell premium in high IV)

ELSE (IV rank 35-64):
  → Poor Man's Covered Call (diagonal spread)
```

## Testing Recommendations

1. Test with high IV stock (e.g., meme stocks, biotech): Should recommend Cash-Secured Put
2. Test with low IV stock (e.g., utilities, stable blue chips): Should recommend Long Call
3. Test with moderate IV stock (e.g., SPY, QQQ): Should recommend PMCC
4. Test with stock that has no options: Should display "Options data unavailable" message
5. Test budget adjustments with each strategy type

## Files Modified

- `pattern_scanner.py`: Lines 230-600 (functions), Lines 3250-3460 (HTML template)

## Unchanged Components

- Pattern detection logic
- DCF valuation
- Technical indicators
- Charting functionality
- All other Flask routes and endpoints
- Budget adjustment controls
