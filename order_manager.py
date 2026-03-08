"""
Order execution and portfolio management via Alpaca Trading API.
"""
import logging
from typing import Optional
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca_client import trading_client, get_mode

logger = logging.getLogger(__name__)

def place_market_order(symbol: str, qty: int, side: str) -> dict:
    """
    Place a market order.
    side: 'buy' or 'sell'
    Returns order details dict
    """
    try:
        order_side = OrderSide.BUY if side.lower() == 'buy' else OrderSide.SELL
        request = MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=order_side,
            time_in_force=TimeInForce.DAY
        )
        order = trading_client.submit_order(request)
        logger.info(f"[{get_mode().upper()}] Market {side} order placed: {symbol} x{qty}, order_id={order.id}")
        
        return {
            'order_id': str(order.id),
            'symbol': order.symbol,
            'qty': int(order.qty),
            'side': order.side.value,
            'type': order.type.value,
            'status': order.status.value,
            'mode': get_mode()
        }
    except Exception as e:
        logger.error(f"Error placing market order: {e}")
        raise

def place_limit_order(symbol: str, qty: int, side: str, limit_price: float) -> dict:
    """
    Place a limit order.
    side: 'buy' or 'sell'
    Returns order details dict
    """
    try:
        order_side = OrderSide.BUY if side.lower() == 'buy' else OrderSide.SELL
        request = LimitOrderRequest(
            symbol=symbol,
            qty=qty,
            side=order_side,
            time_in_force=TimeInForce.DAY,
            limit_price=limit_price
        )
        order = trading_client.submit_order(request)
        logger.info(f"[{get_mode().upper()}] Limit {side} order placed: {symbol} x{qty} @ ${limit_price}, order_id={order.id}")
        
        return {
            'order_id': str(order.id),
            'symbol': order.symbol,
            'qty': int(order.qty),
            'side': order.side.value,
            'type': order.type.value,
            'limit_price': float(order.limit_price),
            'status': order.status.value,
            'mode': get_mode()
        }
    except Exception as e:
        logger.error(f"Error placing limit order: {e}")
        raise

def get_open_orders() -> list[dict]:
    """Get all open orders"""
    try:
        orders = trading_client.get_orders()
        return [{
            'order_id': str(o.id),
            'symbol': o.symbol,
            'qty': int(o.qty),
            'side': o.side.value,
            'type': o.type.value,
            'status': o.status.value,
            'limit_price': float(o.limit_price) if o.limit_price else None,
            'filled_qty': int(o.filled_qty) if o.filled_qty else 0,
            'created_at': o.created_at.isoformat()
        } for o in orders]
    except Exception as e:
        logger.error(f"Error fetching orders: {e}")
        raise

def cancel_order(order_id: str) -> dict:
    """Cancel a specific order"""
    try:
        trading_client.cancel_order_by_id(order_id)
        logger.info(f"[{get_mode().upper()}] Cancelled order {order_id}")
        return {'order_id': order_id, 'status': 'cancelled', 'mode': get_mode()}
    except Exception as e:
        logger.error(f"Error cancelling order {order_id}: {e}")
        raise

def get_positions() -> list[dict]:
    """Get current portfolio positions"""
    try:
        positions = trading_client.get_all_positions()
        return [{
            'symbol': p.symbol,
            'qty': int(p.qty),
            'avg_entry_price': float(p.avg_entry_price),
            'current_price': float(p.current_price),
            'market_value': float(p.market_value),
            'unrealized_pl': float(p.unrealized_pl),
            'unrealized_plpc': float(p.unrealized_plpc),
            'side': 'long' if float(p.qty) > 0 else 'short'
        } for p in positions]
    except Exception as e:
        logger.error(f"Error fetching positions: {e}")
        raise

def get_account_info() -> dict:
    """Get account summary"""
    try:
        account = trading_client.get_account()
        return {
            'equity': float(account.equity),
            'cash': float(account.cash),
            'buying_power': float(account.buying_power),
            'portfolio_value': float(account.portfolio_value),
            'mode': get_mode()
        }
    except Exception as e:
        logger.error(f"Error fetching account info: {e}")
        raise
