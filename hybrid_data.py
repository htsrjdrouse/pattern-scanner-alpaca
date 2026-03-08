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
