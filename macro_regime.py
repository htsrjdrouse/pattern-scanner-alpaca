# -*- coding: utf-8 -*-
"""
Macro Regime Module - Geopolitical/Macro Overlay for Pattern Scanner Suite

Provides daily macro context for scanner pipeline with sector-regime alignment
and geopolitical risk scoring.
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import os
import pandas as pd
import yfinance as yf
import feedparser

# Regime->Sector Mapping Table
REGIME_SECTOR_MAP = {
    "STAGFLATION": {  # high inflation, slowing growth
        "favored": ["energy", "minerals_mining", "agriculture", "gold_miners"],
        "suppressed": ["semiconductors", "saas", "consumer_discretionary", "real_estate"]
    },
    "REFLATION": {  # rising inflation, expanding growth
        "favored": ["energy", "minerals_mining", "industrials", "financials", "agriculture"],
        "suppressed": ["utilities", "bonds_proxy"]
    },
    "GOLDILOCKS": {  # low inflation, expanding growth
        "favored": ["semiconductors", "saas", "consumer_discretionary", "industrials", "financials"],
        "suppressed": ["energy", "gold_miners", "utilities"]
    },
    "DEFLATION": {  # falling inflation, contracting growth
        "favored": ["utilities", "consumer_staples", "healthcare", "bonds_proxy"],
        "suppressed": ["energy", "minerals_mining", "financials", "industrials"]
    }
}

# Commodity->Sector Mapping
COMMODITY_SECTOR_MAP = {
    "oil": ["energy", "transportation", "chemicals"],
    "lng": ["energy", "utilities", "chemicals"],
    "ammonia": ["agriculture", "chemicals", "fertilizers"],
    "urea": ["agriculture", "fertilizers"],
    "sulfur": ["agriculture", "chemicals", "fertilizers"],
    "phosphate": ["agriculture", "fertilizers"]
}

# Geopolitical keywords for news sentiment
GEO_KEYWORDS = [
    "hormuz", "strait", "sanctions", "war", "supply shock", 
    "shortage", "embargo", "pipeline", "disruption", "conflict",
    "blockade", "crisis", "attack"
]

CACHE_FILE = 'data/macro_regime_cache.json'
CACHE_TTL_HOURS = 4


@dataclass
class MacroRegime:
    """Macro regime context object"""
    growth_regime: str  # EXPANDING | SLOWING | CONTRACTING | RECOVERING
    inflation_regime: str  # LOW | RISING | HIGH | FALLING
    quadrant: str  # GOLDILOCKS | STAGFLATION | REFLATION | DEFLATION
    geopolitical_risk: str  # LOW | ELEVATED | HIGH | UNKNOWN
    commodity_disruption: Dict[str, str]  # {commodity: severity}
    favored_sectors: List[str]
    suppressed_sectors: List[str]
    regime_confidence: float  # 0-1
    last_updated: str
    sources: List[str]


def build_macro_context() -> MacroRegime:
    """
    Build macro context from market data and news sentiment.
    
    Returns:
        MacroRegime object with current regime classification
    """
    # Check cache first
    cached = _load_cache()
    if cached:
        return cached
    
    sources = []
    regime_confidence = 1.0
    
    try:
        # Fetch market data
        growth_regime, growth_conf = _classify_growth()
        inflation_regime, inflation_conf = _classify_inflation()
        
        # Check if we got valid data
        if growth_regime == "UNKNOWN" or inflation_regime == "UNKNOWN":
            print(f"Insufficient data: growth={growth_regime}, inflation={inflation_regime}")
            return MacroRegime(
                growth_regime=growth_regime,
                inflation_regime=inflation_regime,
                quadrant="UNKNOWN",
                geopolitical_risk="UNKNOWN",
                commodity_disruption={},
                favored_sectors=[],
                suppressed_sectors=[],
                regime_confidence=0.0,
                last_updated=datetime.now().isoformat(),
                sources=["INSUFFICIENT_DATA"]
            )
        
        regime_confidence = min(growth_conf, inflation_conf)
        sources.extend(['yfinance:SPY', 'yfinance:TLT', 'yfinance:DBC'])
        
        # Derive quadrant
        quadrant = _derive_quadrant(growth_regime, inflation_regime)
        
        # Geopolitical risk scoring
        geo_risk, geo_sources = _score_geopolitical_risk()
        sources.extend(geo_sources)
        
        # Commodity disruption detection
        commodity_disruption = _detect_commodity_disruption()
        
        # Map to sectors
        regime_map = REGIME_SECTOR_MAP.get(quadrant, REGIME_SECTOR_MAP["GOLDILOCKS"])
        favored_sectors = regime_map["favored"]
        suppressed_sectors = regime_map["suppressed"]
        
    except Exception as e:
        print(f"Error building macro context: {e}")
        # Graceful degradation
        return MacroRegime(
            growth_regime="UNKNOWN",
            inflation_regime="UNKNOWN",
            quadrant="UNKNOWN",
            geopolitical_risk="UNKNOWN",
            commodity_disruption={},
            favored_sectors=[],
            suppressed_sectors=[],
            regime_confidence=0.0,
            last_updated=datetime.now().isoformat(),
            sources=["ERROR"]
        )
    
    regime = MacroRegime(
        growth_regime=growth_regime,
        inflation_regime=inflation_regime,
        quadrant=quadrant,
        geopolitical_risk=geo_risk,
        commodity_disruption=commodity_disruption,
        favored_sectors=favored_sectors,
        suppressed_sectors=suppressed_sectors,
        regime_confidence=regime_confidence,
        last_updated=datetime.now().isoformat(),
        sources=sources
    )
    
    _save_cache(regime)
    return regime


def get_sector_macro_alignment(sector_id: str, macro_context: MacroRegime) -> str:
    """
    Check if sector aligns with current macro regime.
    
    Args:
        sector_id: Sector identifier from sectors.json
        macro_context: Current MacroRegime object
        
    Returns:
        "TAILWIND" | "NEUTRAL" | "HEADWIND"
    """
    if sector_id in macro_context.favored_sectors:
        return "TAILWIND"
    elif sector_id in macro_context.suppressed_sectors:
        return "HEADWIND"
    return "NEUTRAL"


def _classify_growth() -> tuple:
    """Classify growth regime from SPY momentum and trend"""
    try:
        spy = yf.Ticker("SPY")
        hist = spy.history(period="1y")  # Get more history
        
        if hist is None or len(hist) < 50:
            print("Growth: Insufficient SPY data")
            return "UNKNOWN", 0.0
        
        # Ensure we have Close column
        if 'Close' not in hist.columns:
            print("Growth: No Close column in SPY data")
            return "UNKNOWN", 0.0
        
        close_prices = hist['Close'].dropna()
        if len(close_prices) < 50:
            print("Growth: Insufficient non-NaN prices")
            return "UNKNOWN", 0.0
        
        # 20-day momentum
        if len(close_prices) >= 20:
            momentum_20 = (close_prices.iloc[-1] / close_prices.iloc[-20] - 1) * 100
        else:
            momentum_20 = 0
        
        # 50/200 SMA
        if len(close_prices) >= 50:
            sma_50 = close_prices.iloc[-50:].mean()
        else:
            sma_50 = close_prices.mean()
            
        if len(close_prices) >= 200:
            sma_200 = close_prices.iloc[-200:].mean()
        else:
            sma_200 = sma_50
        
        # Check for NaN
        if pd.isna(momentum_20) or pd.isna(sma_50) or pd.isna(sma_200):
            print(f"Growth: NaN values - momentum={momentum_20}, sma_50={sma_50}, sma_200={sma_200}")
            return "UNKNOWN", 0.0
        
        if momentum_20 > 5 and sma_50 > sma_200:
            return "EXPANDING", 0.9
        elif momentum_20 < -5 and sma_50 < sma_200:
            return "CONTRACTING", 0.9
        elif momentum_20 < 0 and sma_50 > sma_200:
            return "SLOWING", 0.7
        elif momentum_20 > 0 and sma_50 < sma_200:
            return "RECOVERING", 0.7
        else:
            return "SLOWING", 0.5
            
    except Exception as e:
        print(f"Growth classification error: {e}")
        import traceback
        traceback.print_exc()
        return "UNKNOWN", 0.0


def _classify_inflation() -> tuple:
    """Classify inflation regime from commodities and bonds"""
    try:
        # DBC (commodities) and TLT (bonds) as inflation proxies
        dbc = yf.Ticker("DBC")
        tlt = yf.Ticker("TLT")
        
        dbc_hist = dbc.history(period="3mo")
        tlt_hist = tlt.history(period="3mo")
        
        if dbc_hist is None or tlt_hist is None:
            print("Inflation: No data returned")
            return "UNKNOWN", 0.0
        
        if len(dbc_hist) < 20 or len(tlt_hist) < 20:
            print(f"Inflation: Insufficient data - DBC={len(dbc_hist)}, TLT={len(tlt_hist)}")
            return "UNKNOWN", 0.0
        
        # Ensure Close column exists
        if 'Close' not in dbc_hist.columns or 'Close' not in tlt_hist.columns:
            print("Inflation: No Close column")
            return "UNKNOWN", 0.0
        
        dbc_close = dbc_hist['Close'].dropna()
        tlt_close = tlt_hist['Close'].dropna()
        
        if len(dbc_close) < 20 or len(tlt_close) < 20:
            print("Inflation: Insufficient non-NaN prices")
            return "UNKNOWN", 0.0
        
        # Commodity momentum (inflation proxy)
        dbc_momentum = (dbc_close.iloc[-1] / dbc_close.iloc[-20] - 1) * 100
        
        # Bond price momentum (inverse inflation)
        tlt_momentum = (tlt_close.iloc[-1] / tlt_close.iloc[-20] - 1) * 100
        
        # Check for NaN
        if pd.isna(dbc_momentum) or pd.isna(tlt_momentum):
            print(f"Inflation: NaN values - dbc={dbc_momentum}, tlt={tlt_momentum}")
            return "UNKNOWN", 0.0
        
        if dbc_momentum > 5 and tlt_momentum < -2:
            return "RISING", 0.8
        elif dbc_momentum > 10:
            return "HIGH", 0.9
        elif dbc_momentum < -5 and tlt_momentum > 2:
            return "FALLING", 0.8
        elif dbc_momentum < -5:
            return "LOW", 0.7
        else:
            return "LOW", 0.6
            
    except Exception as e:
        print(f"Inflation classification error: {e}")
        import traceback
        traceback.print_exc()
        return "UNKNOWN", 0.0


def _derive_quadrant(growth: str, inflation: str) -> str:
    """Map growth + inflation to macro quadrant"""
    # Return UNKNOWN if either input is UNKNOWN
    if growth == "UNKNOWN" or inflation == "UNKNOWN":
        return "UNKNOWN"
    
    if growth in ["EXPANDING", "RECOVERING"] and inflation in ["LOW", "FALLING"]:
        return "GOLDILOCKS"
    elif growth in ["EXPANDING", "RECOVERING"] and inflation in ["RISING", "HIGH"]:
        return "REFLATION"
    elif growth in ["SLOWING", "CONTRACTING"] and inflation in ["RISING", "HIGH"]:
        return "STAGFLATION"
    elif growth in ["SLOWING", "CONTRACTING"] and inflation in ["LOW", "FALLING"]:
        return "DEFLATION"
    else:
        return "GOLDILOCKS"  # default


def _score_geopolitical_risk() -> tuple:
    """Score geopolitical risk from VIX term structure and news sentiment"""
    sources = []
    
    try:
        # VIX term structure
        vix = yf.Ticker("^VIX")
        vix_hist = vix.history(period="5d")
        
        if len(vix_hist) > 0:
            vix_level = vix_hist['Close'][-1]
            sources.append('yfinance:VIX')
            
            # VIX thresholds
            if vix_level > 30:
                vix_risk = "HIGH"
            elif vix_level > 20:
                vix_risk = "ELEVATED"
            else:
                vix_risk = "LOW"
        else:
            vix_risk = "UNKNOWN"
        
        # News sentiment
        news_risk = _check_news_sentiment()
        sources.append('yahoo_finance_rss')
        
        # Combine
        if vix_risk == "HIGH" or news_risk == "HIGH":
            return "HIGH", sources
        elif vix_risk == "ELEVATED" or news_risk == "ELEVATED":
            return "ELEVATED", sources
        elif vix_risk == "LOW" and news_risk == "LOW":
            return "LOW", sources
        else:
            return "ELEVATED", sources
            
    except Exception as e:
        print(f"Geopolitical risk scoring error: {e}")
        return "UNKNOWN", ["ERROR"]


def _check_news_sentiment() -> str:
    """Check news headlines for geopolitical keywords"""
    try:
        feed_url = "https://feeds.finance.yahoo.com/rss/2.0/headline?s=USO,UNG,MOO,LXU,NTR,CF,UAN&region=US&lang=en-US"
        feed = feedparser.parse(feed_url)
        
        if not feed.entries:
            return "LOW"
        
        total_headlines = len(feed.entries[:20])  # Check last 20
        keyword_hits = 0
        
        for entry in feed.entries[:20]:
            title = entry.get('title', '').lower()
            summary = entry.get('summary', '').lower()
            text = title + ' ' + summary
            
            if any(keyword in text for keyword in GEO_KEYWORDS):
                keyword_hits += 1
        
        hit_rate = keyword_hits / total_headlines if total_headlines > 0 else 0
        
        if hit_rate > 0.3:
            return "HIGH"
        elif hit_rate > 0.15:
            return "ELEVATED"
        else:
            return "LOW"
            
    except Exception as e:
        print(f"News sentiment check error: {e}")
        return "LOW"


def _detect_commodity_disruption() -> Dict[str, str]:
    """Detect commodity supply disruptions from price spikes"""
    disruptions = {}
    
    try:
        # Check key commodity ETFs
        commodities = {
            "oil": "USO",
            "lng": "UNG"
        }
        
        for commodity, ticker in commodities.items():
            try:
                etf = yf.Ticker(ticker)
                hist = etf.history(period="1mo")
                
                if hist is not None and len(hist) >= 20 and 'Close' in hist.columns:
                    close_prices = hist['Close'].dropna()
                    if len(close_prices) >= 20:
                        # 20-day momentum
                        momentum = (close_prices.iloc[-1] / close_prices.iloc[-20] - 1) * 100
                        
                        if not pd.isna(momentum):
                            if momentum > 15:
                                disruptions[commodity] = "HIGH"
                            elif momentum > 8:
                                disruptions[commodity] = "ELEVATED"
            except Exception as e:
                print(f"Commodity {commodity} error: {e}")
                pass
                
    except Exception as e:
        print(f"Commodity disruption detection error: {e}")
    
    return disruptions


def _load_cache() -> Optional[MacroRegime]:
    """Load cached macro regime if still valid"""
    try:
        if not os.path.exists(CACHE_FILE):
            return None
        
        with open(CACHE_FILE, 'r') as f:
            data = json.load(f)
        
        last_updated = datetime.fromisoformat(data['last_updated'])
        age = datetime.now() - last_updated
        
        if age < timedelta(hours=CACHE_TTL_HOURS):
            return MacroRegime(**data)
        
        return None
        
    except Exception as e:
        print(f"Cache load error: {e}")
        return None


def _save_cache(regime: MacroRegime):
    """Save macro regime to cache"""
    try:
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        
        with open(CACHE_FILE, 'w') as f:
            json.dump(asdict(regime), f, indent=2)
            
    except Exception as e:
        print(f"Cache save error: {e}")


if __name__ == "__main__":
    # Test
    regime = build_macro_context()
    print(json.dumps(asdict(regime), indent=2))
