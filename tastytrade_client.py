"""
Tastytrade API client for pattern_scanner_alpaca.
Provides live options Greeks, IV rank, and SPX chain data.
Mirrors the structure of alpaca_client.py.

Credentials come from .env:
  TASTYTRADE_CLIENT_SECRET — from OAuth app creation (shown once)
  TASTYTRADE_REFRESH_TOKEN — from OAuth Applications > Manage > Create Grant
  TASTYTRADE_ENV           — 'production' or 'sandbox'

Usage:
    from tastytrade_client import get_session, is_connected, TASTYTRADE_ENV
    session = get_session()  # returns cached session, refreshes if needed
"""

import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

TASTYTRADE_CLIENT_SECRET = os.getenv('TASTYTRADE_CLIENT_SECRET')
TASTYTRADE_REFRESH_TOKEN = os.getenv('TASTYTRADE_REFRESH_TOKEN')
TASTYTRADE_ENV = os.getenv('TASTYTRADE_ENV', 'production').lower()

# Validate env — but don't crash the whole app if Tastytrade isn't configured.
# Alpaca and yfinance will continue working. Tastytrade features will be
# unavailable and callers will receive None from get_session().
_credentials_present = bool(TASTYTRADE_CLIENT_SECRET and TASTYTRADE_REFRESH_TOKEN)

if not _credentials_present:
    logger.warning(
        "TASTYTRADE_CLIENT_SECRET or TASTYTRADE_REFRESH_TOKEN not set in .env. "
        "Live options Greeks and IV data will be unavailable. "
        "Alpaca and yfinance data sources are unaffected."
    )

if TASTYTRADE_ENV not in ('production', 'sandbox'):
    logger.warning("TASTYTRADE_ENV must be 'production' or 'sandbox'. Defaulting to 'production'.")
    TASTYTRADE_ENV = 'production'

_is_test = TASTYTRADE_ENV == 'sandbox'

# Module-level cached session — reused across requests, auto-refreshes token
_session = None


def get_session():
    """
    Return a cached, authenticated Tastytrade Session object.
    Creates the session on first call. Returns None if credentials are missing
    or if authentication fails — callers must handle None gracefully.
    
    The tastytrade SDK (>=12.0.0) automatically refreshes the 15-minute access
    token behind the scenes on every API call. No manual refresh needed.
    """
    global _session

    if not _credentials_present:
        return None

    if _session is not None:
        return _session

    try:
        from tastytrade import Session
        _session = Session(
            TASTYTRADE_CLIENT_SECRET,
            TASTYTRADE_REFRESH_TOKEN,
            is_test=_is_test
        )
        logger.info(f"Tastytrade session established ({TASTYTRADE_ENV})")
        return _session
    except Exception as e:
        logger.error(f"Tastytrade authentication failed: {e}")
        _session = None
        return None


def reset_session():
    """Force a new session on next get_session() call. Use if session becomes stale."""
    global _session
    _session = None


def is_connected() -> bool:
    """Return True if Tastytrade session is active and credentials are present."""
    return get_session() is not None


def get_env() -> str:
    """Return current Tastytrade environment ('production' or 'sandbox')."""
    return TASTYTRADE_ENV
