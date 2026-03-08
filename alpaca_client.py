"""
Alpaca API client configuration for pattern_scanner_alpaca.
Reads credentials from environment and instantiates trading, data, and streaming clients.
"""
import os
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.live import StockDataStream

load_dotenv()

ALPACA_API_KEY = os.getenv('ALPACA_API_KEY')
ALPACA_SECRET_KEY = os.getenv('ALPACA_SECRET_KEY')
ALPACA_MODE = os.getenv('ALPACA_MODE', 'paper').lower()

if not ALPACA_API_KEY or not ALPACA_SECRET_KEY:
    raise ValueError("ALPACA_API_KEY and ALPACA_SECRET_KEY must be set in .env")

if ALPACA_MODE not in ('paper', 'live'):
    raise ValueError("ALPACA_MODE must be 'paper' or 'live'")

is_paper = ALPACA_MODE == 'paper'

trading_client = TradingClient(ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=is_paper)
stock_client = StockHistoricalDataClient(ALPACA_API_KEY, ALPACA_SECRET_KEY)
data_stream = StockDataStream(ALPACA_API_KEY, ALPACA_SECRET_KEY)

def get_mode() -> str:
    """Return current Alpaca mode ('paper' or 'live')"""
    return ALPACA_MODE
