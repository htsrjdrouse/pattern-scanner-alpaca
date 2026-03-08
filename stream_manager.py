"""
Real-time WebSocket streaming manager for Alpaca market data.
"""
import logging
import threading
from typing import Optional
from alpaca_client import data_stream

logger = logging.getLogger(__name__)

latest_bars = {}
_stream_thread = None
_subscribed_symbols = set()

async def _bar_handler(bar):
    """Handle incoming bar updates"""
    symbol = bar.symbol
    latest_bars[symbol] = {
        'symbol': symbol,
        'timestamp': bar.timestamp.isoformat(),
        'open': float(bar.open),
        'high': float(bar.high),
        'low': float(bar.low),
        'close': float(bar.close),
        'volume': int(bar.volume)
    }
    logger.debug(f"Updated bar for {symbol}: {bar.close}")

async def _trade_handler(trade):
    """Handle incoming trade updates"""
    symbol = trade.symbol
    if symbol not in latest_bars:
        latest_bars[symbol] = {}
    latest_bars[symbol]['last_trade_price'] = float(trade.price)
    latest_bars[symbol]['last_trade_time'] = trade.timestamp.isoformat()

def subscribe(symbols: list[str]):
    """Subscribe to real-time bar and trade updates for given symbols"""
    global _stream_thread, _subscribed_symbols
    
    new_symbols = [s for s in symbols if s not in _subscribed_symbols]
    if not new_symbols:
        logger.info("All symbols already subscribed")
        return
    
    data_stream.subscribe_bars(_bar_handler, *new_symbols)
    data_stream.subscribe_trades(_trade_handler, *new_symbols)
    _subscribed_symbols.update(new_symbols)
    
    logger.info(f"Subscribed to {len(new_symbols)} symbols: {new_symbols}")
    
    if _stream_thread is None or not _stream_thread.is_alive():
        _stream_thread = threading.Thread(target=data_stream.run, daemon=True)
        _stream_thread.start()
        logger.info("Started WebSocket stream thread")

def get_latest(symbol: str) -> Optional[dict]:
    """Get latest bar data for a symbol"""
    return latest_bars.get(symbol)

def get_all_latest() -> dict:
    """Get all latest bars"""
    return latest_bars.copy()

def stop():
    """Stop the stream (for cleanup)"""
    global _stream_thread
    if _stream_thread and _stream_thread.is_alive():
        data_stream.stop()
        _stream_thread = None
        logger.info("Stopped WebSocket stream")
