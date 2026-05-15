"""
Options Parser — Parse TOS (ThinkOrSwim) order strings into structured leg data.
Handles STRANGLE, single legs, PUT/CALL and CALL/PUT formats.
"""

from typing import List, Dict
from datetime import datetime


MONTH_MAP = {
    'JAN': '01', 'FEB': '02', 'MAR': '03', 'APR': '04',
    'MAY': '05', 'JUN': '06', 'JUL': '07', 'AUG': '08',
    'SEP': '09', 'OCT': '10', 'NOV': '11', 'DEC': '12'
}


def parse_tos_string(raw: str) -> List[Dict]:
    """Parse a single TOS order string into leg dicts.

    Supported formats:
        SELL -1 STRANGLE AMAT 100 20 JUN 26 360/490 PUT/CALL @12.50 LMT
        SELL -1 STRANGLE GOOG 100 18 JUN 26 350/420 CALL/PUT @78.89 LMT
        BUY +1 GOOG 100 21 AUG 26 400 CALL @22.35 LMT
        SELL -1 STRANGLE AMAT 100 20 JUN 26 360/490 PUT/CALL @LMT
    """
    # Fix D — Input sanitization
    raw = raw.strip()
    if not raw:
        return []

    raw_normalized = ' '.join(raw.upper().split())
    raw_normalized = raw_normalized.replace('@', ' @ ')
    tokens = raw_normalized.split()
    if not tokens:
        return []

    idx = 0

    # Action: BUY / SELL
    action = tokens[idx]; idx += 1
    if action not in ('BUY', 'SELL'):
        return []

    direction = 'credit' if action == 'SELL' else 'debit'

    # Quantity: +1, -1, +2, etc.
    qty_token = tokens[idx]; idx += 1
    quantity = abs(int(qty_token.replace('+', '').replace('-', '')))

    # Strategy or symbol next
    strategy = None
    if tokens[idx] in ('STRANGLE', 'STRADDLE', 'VERTICAL', 'IRON', 'CONDOR', 'BUTTERFLY', 'CALENDAR'):
        strategy = tokens[idx]; idx += 1

    # Symbol
    symbol = tokens[idx]; idx += 1

    # Shares multiplier (100)
    if idx < len(tokens) and tokens[idx].isdigit() and int(tokens[idx]) >= 100:
        idx += 1  # skip the 100 multiplier

    # Expiration: DD MON YY
    if idx + 2 >= len(tokens):
        return []
    day = tokens[idx]; idx += 1
    month_str = tokens[idx]; idx += 1
    year_str = tokens[idx]; idx += 1

    if month_str not in MONTH_MAP:
        return []

    year = int(year_str)
    if year < 100:
        year += 2000
    expiration = f"{year}-{MONTH_MAP[month_str]}-{day.zfill(2)}"

    # Strikes: single (400) or dual (360/490)
    if idx >= len(tokens):
        return []
    strike_token = tokens[idx]; idx += 1

    if '/' in strike_token:
        parts = strike_token.split('/')
        s1 = float(parts[0])
        s2 = float(parts[1])
        strike_low = min(s1, s2)
        strike_high = max(s1, s2)
    else:
        strike_low = float(strike_token)
        strike_high = None

    # Fix A — Option types parsing
    if idx >= len(tokens):
        return []
    types_raw = tokens[idx]; idx += 1

    if '/' in types_raw:
        type_parts = types_raw.split('/')
        has_call = 'CALL' in type_parts
        has_put = 'PUT' in type_parts
        is_two_legged = has_call and has_put
        type_low = type_parts[0]
        type_high = type_parts[1]
    else:
        is_two_legged = False
        type_low = types_raw
        type_high = None
        has_call = type_low == 'CALL'
        has_put = type_low == 'PUT'

    # Fix C — Entry price parsing
    entry_price = 0.0
    for t in tokens[idx:]:
        if t == '@':
            continue
        if t in ('LMT', 'MKT', 'LIMIT', 'MARKET'):
            continue
        # Try to parse as number
        cleaned = t.replace(',', '')
        if cleaned.replace('.', '').replace('-', '').isdigit():
            entry_price = float(cleaned)
            break

    # Build legs
    legs = []

    if strategy == 'STRANGLE':
        # Fix B — Lower strike = PUT, higher strike = CALL, always
        if strike_high is None:
            print(f"STRANGLE parse error: need two strikes, got one. raw: {raw}")
            return []

        half_price = round(entry_price / 2, 4) if entry_price > 0 else 0.0

        legs.append({
            "symbol": symbol,
            "action": action,
            "quantity": quantity,
            "strike": strike_low,
            "option_type": "PUT",
            "expiration": expiration,
            "entry_premium": half_price,
            "direction": direction,
            "strategy": strategy,
            "raw": raw
        })
        legs.append({
            "symbol": symbol,
            "action": action,
            "quantity": quantity,
            "strike": strike_high,
            "option_type": "CALL",
            "expiration": expiration,
            "entry_premium": half_price,
            "direction": direction,
            "strategy": strategy,
            "raw": raw
        })
    else:
        # Single leg
        option_type = type_low if type_low in ('CALL', 'PUT') else 'CALL'
        legs.append({
            "symbol": symbol,
            "action": action,
            "quantity": quantity,
            "strike": strike_low,
            "option_type": option_type,
            "expiration": expiration,
            "entry_premium": entry_price,
            "direction": direction,
            "strategy": strategy or "SINGLE",
            "raw": raw
        })

    return legs


def parse_multiple_tos_strings(raw_block: str) -> List[Dict]:
    """Parse a multi-line block of TOS strings into a flat list of legs."""
    all_legs = []
    for line in raw_block.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        legs = parse_tos_string(line)
        all_legs.extend(legs)
    return all_legs
