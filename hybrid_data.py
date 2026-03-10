"""
Hybrid data source: Alpaca for price data, yfinance for options/fundamentals.
Best of both worlds - real-time trading with Alpaca, options analysis with yfinance.
"""
import yfinance as yf
from alpaca_data import fetch_stock_data

def get_options_chain(symbol, expiration=None):
    """Get options chain from yfinance (Alpaca doesn't provide this)."""
    try:
        ticker = yf.Ticker(symbol)
        if expiration:
            return ticker.option_chain(expiration)
        else:
            return ticker.options  # Return available expirations
    except Exception as e:
        return None

def get_company_info(symbol):
    """Get company fundamentals from yfinance."""
    try:
        ticker = yf.Ticker(symbol)
        return ticker.info
    except:
        return {}

def get_financials(symbol):
    """Get financial statements from yfinance."""
    try:
        ticker = yf.Ticker(symbol)
        return {
            'cashflow': ticker.cashflow,
            'income_stmt': ticker.income_stmt,
            'balance_sheet': ticker.balance_sheet
        }
    except:
        return {}

# Price data always comes from Alpaca (for consistency with trading)
get_price_data = fetch_stock_data


# ── Tastytrade: Live Options Greeks & IV Data ────────────────────────────────
# Tastytrade is used when live Greeks or real-time IV rank are needed.
# Falls back to yfinance automatically if Tastytrade is not configured.
# Import is inside functions to prevent startup crash if tastytrade not installed.

def get_live_greeks(symbol: str, expiration=None) -> dict | None:
    """
    Get live options chain with Greeks from Tastytrade.
    Returns None if Tastytrade not configured — callers should fall back to yfinance.
    """
    try:
        from tastytrade_data import get_live_option_chain
        return get_live_option_chain(symbol, expiration)
    except ImportError:
        return None


def get_iv_rank(symbol: str) -> dict | None:
    """
    Get IV rank for a symbol.
    Uses Tastytrade if connected, falls back to yfinance approximation.
    """
    try:
        from tastytrade_data import get_iv_rank as tt_iv_rank
        return tt_iv_rank(symbol)
    except ImportError:
        return None


def get_strike_by_delta(symbol: str, expiration, target_delta: float,
                        option_type: str = 'put') -> dict | None:
    """
    Find option strike nearest to target delta.
    Requires Tastytrade — returns None if not connected.
    Used by 0DTE scanner for credit spread strike selection.
    """
    try:
        from tastytrade_data import get_strike_by_delta as tt_strike
        return tt_strike(symbol, expiration, target_delta, option_type)
    except ImportError:
        return None


def get_vix_term_structure() -> dict | None:
    """
    Get VIX spot + futures term structure (contango vs backwardation).
    Uses Tastytrade if connected, falls back to yfinance VIX/VIX3M proxy.
    Used by regime_classifier.py.
    """
    try:
        from tastytrade_data import get_vix_term_structure as tt_vts
        result = tt_vts()
        if result:
            return result
    except ImportError:
        pass
    
    # Fallback: yfinance VIX3M proxy (already used in regime_classifier)
    try:
        import yfinance as yf
        vix = yf.Ticker('^VIX').fast_info.last_price
        vix3m = yf.Ticker('^VIX3M').fast_info.last_price
        spread = vix3m - vix
        return {
            'vix_spot': vix,
            'vix_3m': vix3m,
            'term_spread': spread,
            'structure': 'CONTANGO' if spread > 1 else ('BACKWARDATION' if spread < -1 else 'FLAT'),
            'source': 'yfinance_fallback'
        }
    except Exception:
        return None


def get_tastytrade_status() -> dict:
    """Return Tastytrade connection status. Used by dashboard health panel."""
    try:
        from tastytrade_data import test_connection
        return test_connection()
    except ImportError:
        return {'connected': False, 'error': 'tastytrade package not installed'}
