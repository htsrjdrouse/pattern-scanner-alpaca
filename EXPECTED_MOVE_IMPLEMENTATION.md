# Expected Move Analysis Panel - Implementation Summary

## Changes Made

### 1. New Function: `calculate_expected_move()` (Line ~858)

Calculates expected move analysis using IV from options chain:

**Inputs:**
- `symbol`: Stock ticker
- `current_price`: Current stock price
- `pattern_target`: Optional pattern target price for comparison

**Returns:**
- `status`: 'success' or 'no_data'
- `iv`: Implied volatility percentage
- `move_1w`: 1-week expected move (± dollars)
- `move_1m`: 1-month expected move (± dollars)
- `move_45d`: 45-day expected move (± dollars)
- `delta_strikes`: List of strikes at 0.30, 0.20, 0.15, 0.10 delta with probabilities
- `target_assessment`: Pattern target vs expected move comparison (if pattern_target provided)
- `expiration`: Expiration date used for calculations
- `dte`: Days to expiration

**Calculations:**
- Expected moves use: `current_price * IV * sqrt(days/252)`
- Delta strikes: Finds actual strikes from options chain closest to target deltas
- Probability OTM: `(1 - delta) * 100`

### 2. Updated Chart Route (Line ~3250)

Added expected move calculation after options strategy:
```python
pattern_target = None
if cup_pattern and 'target' in cup_pattern:
    pattern_target = cup_pattern['target']
expected_move = calculate_expected_move(
    symbol,
    company_info['current_price'] or df['Close'].iloc[-1],
    pattern_target
)
```

Passed `expected_move` to template in `render_template_string()`.

### 3. New HTML Panel (Lines 3860-3940)

Added "Expected Move Analysis" panel between Options Strategy and Company Info sections.

**Panel Structure:**

#### Section 1: Expected Moves
- 1-Week: ± $X.XX
- 1-Month: ± $X.XX  
- 45-Day: ± $X.XX
- Shows IV percentage and expiration used

#### Section 2: Pattern Target Comparison (if pattern detected)
- Pattern Target: $X (Y% above current)
- 45-Day Upper Bound: $Z (W% above current)
- Assessment: "Target WITHIN/EXCEEDS expected move"
- Warning note if target exceeds expected move

#### Section 3: Delta-to-Probability Table
Table with columns:
- Delta (0.30, 0.20, 0.15, 0.10)
- Strike (actual from options chain)
- Prob OTM (70%, 80%, 85%, 90%)
- Distance from Current (percentage)

**Styling:**
- Matches existing dark theme
- Uses same `.card` class and table styles
- Color coding: green for positive moves, orange for warnings
- Responsive 2-column grid layout

**Error Handling:**
- If `status == 'no_data'`: Shows placeholder message
- Gracefully hides panel if options chain unavailable
- No crashes on missing data

## Data Flow

```
Chart Route
  ↓
Get pattern target (if cup & handle detected)
  ↓
calculate_expected_move(symbol, price, target)
  ↓
Fetch options chain (nearest exp >= 30 days)
  ↓
Extract ATM IV
  ↓
Calculate expected moves (1w, 1m, 45d)
  ↓
Find delta-based strikes (0.30, 0.20, 0.15, 0.10)
  ↓
Compare pattern target to 45d expected move
  ↓
Return data dict
  ↓
Pass to template
  ↓
Render panel
```

## Example Output

For AAPL with 30% IV and $180 current price:

**Expected Moves:**
- 1-Week: ± $2.54
- 1-Month: ± $5.20
- 45-Day: ± $7.62

**Delta Table:**
| Delta | Strike | Prob OTM | Distance |
|-------|--------|----------|----------|
| 0.30  | $190   | 70%      | +5.6%    |
| 0.20  | $195   | 80%      | +8.3%    |
| 0.15  | $198   | 85%      | +10.0%   |
| 0.10  | $202   | 90%      | +12.2%   |

**Pattern Assessment:**
If cup & handle target is $195:
- "Pattern target: $195 (8.3% above current)"
- "45-day expected move upper bound: $187.62 (4.2% above current)"
- "Assessment: Target EXCEEDS expected move"
- Warning: "Consider longer dated options (60-90 DTE)"

## Files Modified

- `pattern_scanner.py`:
  - Lines 858-940: New `calculate_expected_move()` function
  - Lines 3250-3258: Call function in chart route
  - Line 3922: Add to template variables
  - Lines 3860-3940: HTML panel template

## No Changes To

- Existing options strategy logic
- Pattern detection
- DCF valuation
- Chart generation
- Any other panels or sections
