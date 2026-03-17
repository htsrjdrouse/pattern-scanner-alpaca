"""
Tastytrade data fetching functions for pattern_scanner_alpaca.
Provides live options Greeks, IV rank, VIX term structure, and SPX chain data.

All functions return None or empty structures if Tastytrade is not configured
or if a fetch fails. The app continues working on Alpaca + yfinance in that case.

Imported by hybrid_data.py as the options Greeks data source.
"""

import logging
import asyncio
from datetime import date, datetime
from functools import wraps
from tastytrade_client import get_session

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run an async coroutine from synchronous Flask context."""
    try:
        # Try nest_asyncio first to handle nested event loops
        try:
            import nest_asyncio
            nest_asyncio.apply()
        except ImportError:
            pass
        
        return asyncio.run(coro)
    except RuntimeError as e:
        # If asyncio.run fails, try creating a new event loop
        if "Event loop is closed" in str(e) or "no running event loop" in str(e):
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(coro)
                finally:
                    loop.close()
            except Exception:
                pass
    except Exception as e:
        logger.error(f"Async execution error: {e}")
    return None


def _require_session(func):
    """Decorator: return None immediately if no Tastytrade session available."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        session = get_session()
        if session is None:
            logger.debug(f"Tastytrade not connected — {func.__name__} returning None")
            return None
        return func(*args, session=session, **kwargs)
    return wrapper


# ── Options Chain ────────────────────────────────────────────────────────────

@_require_session
def get_live_option_chain(symbol: str, expiration: date = None, session=None) -> dict | None:
    """
    Fetch live options chain with Greeks for a given symbol and expiration.
    
    Returns dict with structure:
    {
        'symbol': str,
        'expiration': date,
        'calls': [{'strike': float, 'delta': float, 'gamma': float, 
                   'theta': float, 'vega': float, 'iv': float,
                   'bid': float, 'ask': float, 'mid': float}, ...],
        'puts':  [same structure as calls],
        'fetched_at': datetime
    }
    Returns None on failure.
    """
    async def _fetch():
        try:
            from tastytrade.instruments import get_option_chain
            from tastytrade import DXLinkStreamer
            from tastytrade.dxfeed import Greeks, Quote

            chain = await get_option_chain(session, symbol)
            
            # Use provided expiration or nearest available
            available_expirations = sorted(chain.keys())
            if not available_expirations:
                return None
            
            target_exp = expiration or available_expirations[0]
            if target_exp not in chain:
                # Find nearest expiration
                target_exp = min(available_expirations, 
                                 key=lambda e: abs((e - (expiration or date.today())).days))
            
            options = chain[target_exp]
            streamer_symbols = [o.streamer_symbol for o in options]
            
            calls_data = []
            puts_data = []
            
            async with DXLinkStreamer(session) as streamer:
                await streamer.subscribe(Quote, streamer_symbols)
                await streamer.subscribe(Greeks, streamer_symbols)
                
                quotes = {}
                greeks = {}
                
                # Collect data for all options (with timeout)
                import asyncio as aio
                async def collect():
                    collected = 0
                    target = len(streamer_symbols) * 2  # quotes + greeks
                    while collected < target:
                        try:
                            event = await aio.wait_for(streamer.get_event(Quote), timeout=5)
                            quotes[event.event_symbol] = event
                            collected += 1
                        except aio.TimeoutError:
                            break
                        try:
                            event = await aio.wait_for(streamer.get_event(Greeks), timeout=5)
                            greeks[event.event_symbol] = event
                            collected += 1
                        except aio.TimeoutError:
                            break
                
                await collect()
            
            for opt in options:
                sym = opt.streamer_symbol
                q = quotes.get(sym)
                g = greeks.get(sym)
                
                entry = {
                    'strike': float(opt.strike_price),
                    'expiration': opt.expiration_date,
                    'dte': opt.days_to_expiration,
                    'delta': float(g.delta) if g else None,
                    'gamma': float(g.gamma) if g else None,
                    'theta': float(g.theta) if g else None,
                    'vega': float(g.vega) if g else None,
                    'iv': float(g.volatility) if g else None,
                    'bid': float(q.bid_price) if q else None,
                    'ask': float(q.ask_price) if q else None,
                    'mid': round((float(q.bid_price) + float(q.ask_price)) / 2, 2) if q else None,
                    'streamer_symbol': sym
                }
                
                if opt.option_type.value == 'C':
                    calls_data.append(entry)
                else:
                    puts_data.append(entry)
            
            return {
                'symbol': symbol,
                'expiration': target_exp,
                'calls': sorted(calls_data, key=lambda x: x['strike']),
                'puts': sorted(puts_data, key=lambda x: x['strike']),
                'fetched_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"get_live_option_chain({symbol}) failed: {e}")
            return None
    
    return _run_async(_fetch())


# ── Delta-Targeted Strike Selection ─────────────────────────────────────────

@_require_session
def get_strike_by_delta(symbol: str, expiration: date, target_delta: float, 
                        option_type: str = 'put', session=None) -> dict | None:
    """
    Find the option strike closest to a target delta.
    Essential for 0DTE scanner: find 0.10-0.15 delta strikes for credit spreads.
    
    Args:
        symbol: underlying symbol (e.g. 'SPX')
        expiration: target expiration date
        target_delta: e.g. 0.12 for 0.10-0.15 delta range
        option_type: 'call' or 'put'
    
    Returns dict with best matching strike details, or None on failure.
    """
    chain = get_live_option_chain(symbol, expiration)
    if chain is None:
        return None
    
    options = chain['calls'] if option_type == 'call' else chain['puts']
    options_with_delta = [o for o in options if o['delta'] is not None]
    
    if not options_with_delta:
        return None
    
    # For puts, delta is negative — compare absolute values
    best = min(options_with_delta, 
               key=lambda o: abs(abs(o['delta']) - target_delta))
    
    return {
        'symbol': symbol,
        'option_type': option_type,
        'strike': best['strike'],
        'delta': best['delta'],
        'iv': best['iv'],
        'bid': best['bid'],
        'ask': best['ask'],
        'mid': best['mid'],
        'dte': best['dte'],
        'target_delta': target_delta,
        'delta_diff': abs(abs(best['delta']) - target_delta)
    }


# ── IV Rank ──────────────────────────────────────────────────────────────────

def _validate_iv_rank(symbol: str, iv_rank_value: float) -> tuple[float | None, str]:
    """Cross-validate IV rank against ATM IV from yfinance."""
    import yfinance as yf
    
    if iv_rank_value is None:
        return None, 'unvalidated'
    
    if iv_rank_value > 5:
        return iv_rank_value, 'valid'
    
    # IV rank 0-5% — cross-validate
    try:
        ticker = yf.Ticker(symbol)
        expirations = ticker.options
        if not expirations:
            return iv_rank_value, 'unvalidated'
        
        chain = ticker.option_chain(expirations[0])
        calls = chain.calls
        
        if calls.empty:
            return iv_rank_value, 'unvalidated'
        
        hist = ticker.history(period='2d')
        if hist.empty:
            return iv_rank_value, 'unvalidated'
        current_price = hist['Close'].iloc[-1]
        
        atm_idx = (calls['strike'] - current_price).abs().idxmin()
        atm_iv = calls.loc[atm_idx, 'impliedVolatility']
        
        if atm_iv > 0.20 and iv_rank_value < 5:
            return None, 'suspect_low'
        
        return iv_rank_value, 'valid'
    
    except Exception:
        return iv_rank_value, 'unvalidated'


def get_iv_rank_with_retry(symbol: str, max_retries: int = 2) -> dict:
    """Fetch IV rank with retry logic and validation."""
    import time
    from tastytrade_client import get_session
    
    last_result = None
    session = get_session()
    
    for attempt in range(max_retries):
        try:
            result = get_iv_rank(symbol, session=session)
            iv_val = None
            
            if isinstance(result, dict):
                iv_val = result.get('iv_rank') or result.get('iv_percentile')
            elif isinstance(result, (int, float)):
                iv_val = float(result)
            
            validated_val, status = _validate_iv_rank(symbol, iv_val)
            
            if status == 'suspect_low' and attempt < max_retries - 1:
                time.sleep(1.5)
                last_result = result
                continue
            
            if validated_val is None and status == 'suspect_low':
                return _iv_rank_yfinance_fallback(symbol)
            
            if isinstance(result, dict):
                result['iv_rank_validation'] = status
            return result
        
        except Exception as e:
            last_result = {'error': str(e)}
            if attempt < max_retries - 1:
                time.sleep(1.0)
    
    return last_result or _iv_rank_yfinance_fallback(symbol)


def _iv_rank_yfinance_fallback(symbol: str) -> dict:
    """Approximate IV rank using yfinance when Tastytrade is unreliable."""
    import yfinance as yf
    import numpy as np
    
    try:
        ticker = yf.Ticker(symbol)
        expirations = ticker.options
        if not expirations:
            return {'iv_rank': None, 'source': 'unavailable'}
        
        chain = ticker.option_chain(expirations[0])
        calls = chain.calls
        hist = ticker.history(period='2d')
        
        if calls.empty or hist.empty:
            return {'iv_rank': None, 'source': 'unavailable'}
        
        current_price = hist['Close'].iloc[-1]
        atm_idx = (calls['strike'] - current_price).abs().idxmin()
        current_iv = float(calls.loc[atm_idx, 'impliedVolatility'])
        
        hist_1y = ticker.history(period='1y')
        if len(hist_1y) < 50:
            return {'iv_rank': None, 'source': 'unavailable'}
        
        returns = hist_1y['Close'].pct_change().dropna()
        realized_vol = float(returns.std() * np.sqrt(252))
        
        iv_low_est = realized_vol * 0.8
        iv_high_est = realized_vol * 2.5
        
        if iv_high_est <= iv_low_est:
            return {'iv_rank': None, 'source': 'unavailable'}
        
        iv_rank_approx = round(
            ((current_iv - iv_low_est) / (iv_high_est - iv_low_est)) * 100, 1
        )
        iv_rank_approx = max(0.0, min(100.0, iv_rank_approx))
        
        return {
            'iv_rank': iv_rank_approx,
            'iv_percentile': iv_rank_approx,
            'current_iv': round(current_iv, 4),
            'realized_vol': round(realized_vol, 4),
            'source': 'yfinance_approximation',
            'iv_rank_validation': 'approximated'
        }
    
    except Exception as e:
        return {'iv_rank': None, 'source': 'unavailable', 'error': str(e)}


def get_iv_rank(symbol: str, session=None) -> dict | None:
    """
    Get current IV rank and IV percentile for a symbol.
    IV rank = where current IV sits relative to its 52-week range.
    
    Returns:
    {
        'symbol': str,
        'current_iv': float,
        'iv_rank': float,       # 0-100, where current IV sits in 52-week range
        'iv_percentile': float, # % of days in past year where IV was lower
        'iv_high_52w': float,
        'iv_low_52w': float
    }
    Falls back to yfinance calculation if Tastytrade data unavailable.
    """
    if session is None:
        return _get_iv_rank_yfinance_fallback(symbol)
    
    async def _fetch():
        try:
            from tastytrade.metrics import get_market_metrics
            
            metrics_list = await get_market_metrics(session, [symbol])
            
            if metrics_list and len(metrics_list) > 0:
                metrics = metrics_list[0]
                
                # Parse IV rank - it's returned as a string like "0.45" (45%)
                iv_rank_str = metrics.implied_volatility_index_rank
                iv_percentile_str = metrics.implied_volatility_percentile
                
                iv_rank = float(iv_rank_str) * 100 if iv_rank_str else None
                iv_percentile = float(iv_percentile_str) * 100 if iv_percentile_str else None
                
                if iv_rank is not None or iv_percentile is not None:
                    return {
                        'symbol': symbol,
                        'current_iv': float(metrics.implied_volatility_index or 0),
                        'iv_rank': iv_rank or iv_percentile or 0,
                        'iv_percentile': iv_percentile or iv_rank or 0,
                        'source': 'tastytrade'
                    }
        except Exception as e:
            logger.warning(f"Tastytrade IV rank fetch failed for {symbol}: {e}")
        
        return None
    
    result = _run_async(_fetch())
    
    # Fallback to yfinance IV calculation if Tastytrade unavailable
    if result is None:
        return _get_iv_rank_yfinance_fallback(symbol)
    
    return result


def _get_iv_rank_yfinance_fallback(symbol: str) -> dict | None:
    """Calculate approximate IV rank from yfinance options chain data."""
    try:
        import yfinance as yf
        import numpy as np
        
        ticker = yf.Ticker(symbol)
        expirations = ticker.options
        
        if not expirations:
            return None
        
        # Get IV from nearest expiration ATM options
        chain = ticker.option_chain(expirations[0])
        current_price = ticker.fast_info.last_price
        
        # Find ATM options
        calls = chain.calls
        atm_call = calls.iloc[(calls['strike'] - current_price).abs().argsort()[:1]]
        current_iv = float(atm_call['impliedVolatility'].values[0]) if len(atm_call) else None
        
        if current_iv is None:
            return None
        
        # Approximate 52-week range using VIX as proxy for market IV
        import yfinance as yf2
        vix = yf2.Ticker('^VIX')
        vix_hist = vix.history(period='1y')
        iv_high = float(vix_hist['Close'].max()) / 100
        iv_low = float(vix_hist['Close'].min()) / 100
        
        iv_rank = ((current_iv - iv_low) / (iv_high - iv_low)) * 100 if iv_high != iv_low else 50
        
        return {
            'symbol': symbol,
            'current_iv': current_iv,
            'iv_rank': round(iv_rank, 1),
            'iv_percentile': None,  # Not calculable from yfinance
            'iv_high_52w': iv_high,
            'iv_low_52w': iv_low,
            'source': 'yfinance_approximate'
        }
    except Exception as e:
        logger.error(f"yfinance IV rank fallback failed for {symbol}: {e}")
        return None


# ── VIX Term Structure ───────────────────────────────────────────────────────

@_require_session
def get_vix_term_structure(session=None) -> dict | None:
    """
    Get VIX spot and VIX futures prices to determine contango vs backwardation.
    Used by regime_classifier.py as a real-time data source.
    
    Returns:
    {
        'vix_spot': float,
        'vix_1m': float,    # front month futures
        'vix_2m': float,    # second month futures  
        'vix_3m': float,    # third month futures
        'term_spread': float,  # vix_3m - vix_spot
        'structure': 'CONTANGO' | 'FLAT' | 'BACKWARDATION',
        'source': 'tastytrade'
    }
    """
    async def _fetch():
        try:
            from tastytrade import DXLinkStreamer
            from tastytrade.dxfeed import Quote
            
            # VIX spot and VIX futures symbols on dxfeed
            vix_symbols = ['^VIX', '/VX1', '/VX2', '/VX3']
            
            prices = {}
            async with DXLinkStreamer(session) as streamer:
                await streamer.subscribe(Quote, vix_symbols)
                import asyncio as aio
                for _ in range(len(vix_symbols) * 2):
                    try:
                        event = await aio.wait_for(streamer.get_event(Quote), timeout=5)
                        prices[event.event_symbol] = (event.bid_price + event.ask_price) / 2
                    except aio.TimeoutError:
                        break
            
            vix_spot = prices.get('^VIX')
            vix_1m = prices.get('/VX1')
            vix_2m = prices.get('/VX2')
            vix_3m = prices.get('/VX3')
            
            if vix_spot is None:
                return None
            
            # Use 3m vs spot for term structure, fall back to 2m or 1m
            far_month = vix_3m or vix_2m or vix_1m
            term_spread = (far_month - vix_spot) if far_month else None
            
            structure = 'UNKNOWN'
            if term_spread is not None:
                if term_spread > 1.0:
                    structure = 'CONTANGO'
                elif term_spread > -1.0:
                    structure = 'FLAT'
                else:
                    structure = 'BACKWARDATION'
            
            return {
                'vix_spot': float(vix_spot),
                'vix_1m': float(vix_1m) if vix_1m else None,
                'vix_2m': float(vix_2m) if vix_2m else None,
                'vix_3m': float(vix_3m) if vix_3m else None,
                'term_spread': float(term_spread) if term_spread else None,
                'structure': structure,
                'source': 'tastytrade'
            }
        except Exception as e:
            logger.error(f"get_vix_term_structure failed: {e}")
            return None
    
    return _run_async(_fetch())


# ── Account Positions (for risk_manager.py upgrade path) ────────────────────

@_require_session
def get_tastytrade_positions(session=None) -> list | None:
    """
    Fetch open positions from Tastytrade account.
    Returns list of position dicts in the same schema used by risk_manager.py.
    
    This is the Tastytrade upgrade path documented in risk_manager.py.
    When called, it returns options positions WITH live Greeks — the key 
    advantage over Alpaca which has no Greeks on positions.
    """
    async def _fetch():
        try:
            from tastytrade import Account
            accounts = await Account.get(session)
            if not accounts:
                return []
            
            account = accounts[0]  # Primary account
            positions = await account.get_positions(session)
            
            result = []
            for pos in positions:
                entry = {
                    'symbol': pos.underlying_symbol,
                    'instrument_type': pos.instrument_type.value,
                    'quantity': float(pos.quantity),
                    'quantity_direction': pos.quantity_direction.value,
                    'close_price': float(pos.close_price) if pos.close_price else None,
                    'average_open_price': float(pos.average_open_price) if pos.average_open_price else None,
                    'account': 'tastytrade_live'
                }
                result.append(entry)
            
            return result
        except Exception as e:
            logger.error(f"get_tastytrade_positions failed: {e}")
            return None
    
    return _run_async(_fetch())


# ── Connection Test ──────────────────────────────────────────────────────────

def test_connection() -> dict:
    """
    Test Tastytrade connection and return status dict.
    Called by Flask health check endpoint and startup verification.
    """
    from tastytrade_client import is_connected, get_env
    
    if not is_connected():
        return {
            'connected': False,
            'env': get_env(),
            'error': 'Session not established — check TASTYTRADE_CLIENT_SECRET and TASTYTRADE_REFRESH_TOKEN in .env'
        }
    
    try:
        # Simple connection test - if we got here, session is valid
        return {
            'connected': True,
            'env': get_env(),
            'message': 'Tastytrade session active'
        }
    except Exception as e:
        return {
            'connected': False,
            'env': get_env(),
            'error': str(e)
        }

