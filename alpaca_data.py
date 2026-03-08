"""
Alpaca data fetching utilities with caching.
Replaces yfinance with Alpaca StockHistoricalDataClient.
"""
import time
import logging
from datetime import datetime, timedelta
from typing import Optional
import pandas as pd
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca_client import stock_client

logger = logging.getLogger(__name__)

# In-memory cache: {symbol: {'data': df, 'timestamp': float}}
_cache = {}
CACHE_TTL = 3600  # 1 hour

def _is_cache_valid(symbol: str) -> bool:
    """Check if cached data exists and is not expired"""
    if symbol not in _cache:
        return False
    age = time.time() - _cache[symbol]['timestamp']
    return age < CACHE_TTL

def fetch_stock_data(symbol: str, start: str, end: str) -> Optional[pd.DataFrame]:
    """
    Fetch daily OHLCV data from Alpaca.
    Returns DataFrame with columns: ['symbol', 'date', 'open', 'high', 'low', 'close', 'volume']
    """
    cache_key = f"{symbol}_{start}_{end}"
    
    if _is_cache_valid(cache_key):
        return _cache[cache_key]['data'].copy()
    
    try:
        request = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=TimeFrame.Day,
            start=datetime.fromisoformat(start.replace('Z', '+00:00')) if isinstance(start, str) else start,
            end=datetime.fromisoformat(end.replace('Z', '+00:00')) if isinstance(end, str) else end
        )
        bars = stock_client.get_stock_bars(request)
        
        if not bars:
            logger.warning(f"No data returned for {symbol}")
            return None
        
        df = bars.df
        if df.empty:
            logger.warning(f"Empty DataFrame for {symbol}")
            return None
        
        # Normalize to expected format - handle MultiIndex
        df = df.reset_index()
        df.columns = [c.lower() for c in df.columns]
        df = df.rename(columns={'timestamp': 'date'})
        
        # Ensure symbol column exists
        if 'symbol' not in df.columns:
            df['symbol'] = symbol
        
        df = df[['symbol', 'date', 'open', 'high', 'low', 'close', 'volume']]
        
        # Cache result
        _cache[cache_key] = {'data': df.copy(), 'timestamp': time.time()}
        
        return df
    
    except Exception as e:
        logger.error(f"Error fetching data for {symbol}: {e}")
        return None

def fetch_multiple_stocks(symbols: list[str], start: str, end: str, batch_size: int = 50, delay: float = 0.2) -> pd.DataFrame:
    """
    Fetch data for multiple symbols in batches.
    Returns concatenated DataFrame.
    """
    all_data = []
    
    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i + batch_size]
        logger.info(f"Fetching batch {i//batch_size + 1}: {len(batch)} symbols")
        
        for symbol in batch:
            df = fetch_stock_data(symbol, start, end)
            if df is not None:
                all_data.append(df)
        
        if i + batch_size < len(symbols):
            time.sleep(delay)
    
    if not all_data:
        return pd.DataFrame()
    
    return pd.concat(all_data, ignore_index=True)

def clear_cache():
    """Clear the in-memory cache"""
    global _cache
    _cache = {}
