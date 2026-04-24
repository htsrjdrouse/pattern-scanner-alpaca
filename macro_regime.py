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

def _fetch_fred_series(series_id: str, limit: int = 12) -> list[float] | None:
    """
    Fetch a FRED economic data series using the public API.
    No API key required for basic access.

    Args:
        series_id: FRED series identifier (e.g. 'CPIAUCSL', 'UNRATE')
        limit: number of most recent observations to return

    Returns:
        List of float values (most recent last), or None on failure.

    FRED series used in this module:
        CPIAUCSL — Consumer Price Index, All Urban Consumers (monthly)
        UNRATE   — Unemployment Rate (monthly)
        T10YIE   — 10-Year Breakeven Inflation Rate (daily, market-implied)
        ICSA     — Initial Jobless Claims (weekly, leading indicator)
    """
    import requests

    try:
        url = (
            f'https://api.stlouisfed.org/fred/series/observations'
            f'?series_id={series_id}'
            f'&sort_order=desc'
            f'&limit={limit}'
            f'&file_type=json'
            f'&api_key=NONE'  # Public read access for common series
        )

        # FRED public endpoint — no API key needed for standard series
        # Falls back gracefully if rate limited
        resp = requests.get(url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (compatible; macro-regime/1.0)'
        })

        if resp.status_code != 200:
            # Try alternative public endpoint
            url_alt = (
                f'https://fred.stlouisfed.org/graph/fredgraph.csv'
                f'?id={series_id}'
            )
            resp = requests.get(url_alt, timeout=10)
            if resp.status_code != 200:
                return None

            # Parse CSV format
            import io
            import csv
            reader = csv.reader(io.StringIO(resp.text))
            next(reader)  # skip header
            values = []
            for row in reader:
                try:
                    if row[1] != '.' and row[1] != '':
                        values.append(float(row[1]))
                except (IndexError, ValueError):
                    continue
            return values[-limit:] if values else None

        data = resp.json()
        observations = data.get('observations', [])

        values = []
        for obs in reversed(observations):  # newest first from API, reverse to oldest-first
            try:
                if obs['value'] != '.':
                    values.append(float(obs['value']))
            except (KeyError, ValueError):
                continue

        return values if values else None

    except Exception as e:
        print(f'FRED fetch failed for {series_id}: {e}')
        return None


# Regime->Sector Mapping Table
REGIME_SECTOR_MAP = {
    "STAGFLATION": {  # high inflation, slowing growth
        "favored": ["energy", "minerals_mining", "agriculture", "gold_miners"],
        "suppressed": ["semiconductors", "saas", "consumer_discretionary", "real_estate"]
    },
    "REFLATION": {  # rising inflation, expanding growth (current likely regime)
        "favored": ["energy", "minerals_mining", "industrials", "financials", "agriculture", "defense"],
        "suppressed": ["utilities", "bonds_proxy", "saas", "consumer_discretionary"]
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
        sources.extend([
            'fred:CPIAUCSL', 'fred:UNRATE', 'fred:T10YIE', 'fred:ICSA',
            'yfinance:SPY', 'yfinance:CL=F', 'yfinance:GLD'
        ])
        
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
    """
    Classify growth regime using real economic indicators.

    Primary signals (FRED):
        - Unemployment rate trend (rising = slowing, falling = expanding)
        - Initial jobless claims trend (leading indicator)

    Secondary signal (yfinance):
        - SPY SMA 50/200 crossover (market's forward-looking growth view)
        - Used as tiebreaker only, not primary signal

    Returns: (regime_string, confidence_float)
    """
    scores = []  # positive = expanding, negative = slowing
    confidence_factors = []

    # ── Signal 1: Unemployment Rate (FRED UNRATE) ──────────────────────────
    # Most reliable growth indicator. Rising unemployment = slowing economy.
    try:
        unrate = _fetch_fred_series('UNRATE', limit=6)
        if unrate and len(unrate) >= 3:
            # Compare latest to 3 months ago
            recent = unrate[-1]
            prior = unrate[-3]
            unrate_change = recent - prior

            if unrate_change > 0.3:
                scores.append(-2)  # Clearly slowing — unemployment rising fast
                confidence_factors.append(0.9)
            elif unrate_change > 0.1:
                scores.append(-1)  # Softening
                confidence_factors.append(0.8)
            elif unrate_change < -0.2:
                scores.append(2)  # Clearly expanding — unemployment falling
                confidence_factors.append(0.9)
            elif unrate_change < 0:
                scores.append(1)  # Modest improvement
                confidence_factors.append(0.7)
            else:
                scores.append(0)  # Stable
                confidence_factors.append(0.6)

            print(f'Growth UNRATE: {recent:.1f}% (change: {unrate_change:+.2f}pp)')
        else:
            print('Growth: UNRATE data unavailable')
    except Exception as e:
        print(f'Growth UNRATE error: {e}')

    # ── Signal 2: Initial Jobless Claims (FRED ICSA) ───────────────────────
    # Weekly leading indicator. Spike in claims = labor market deteriorating.
    try:
        claims = _fetch_fred_series('ICSA', limit=8)
        if claims and len(claims) >= 4:
            # 4-week moving average vs prior 4-week average
            recent_avg = sum(claims[-4:]) / 4
            prior_avg = sum(claims[-8:-4]) / 4
            claims_change_pct = (recent_avg - prior_avg) / prior_avg * 100

            if claims_change_pct > 10:
                scores.append(-2)  # Claims spiking — bad sign
                confidence_factors.append(0.85)
            elif claims_change_pct > 5:
                scores.append(-1)
                confidence_factors.append(0.7)
            elif claims_change_pct < -5:
                scores.append(1)  # Claims falling — healthy
                confidence_factors.append(0.75)
            else:
                scores.append(0)
                confidence_factors.append(0.6)

            print(f'Growth ICSA: {recent_avg:.0f}k avg (change: {claims_change_pct:+.1f}%)')
        else:
            print('Growth: ICSA data unavailable')
    except Exception as e:
        print(f'Growth ICSA error: {e}')

    # ── Signal 3: SPY SMA crossover (secondary confirmation only) ─────────
    # Market is forward-looking. Use as tiebreaker with lower weight.
    try:
        spy = yf.Ticker('SPY')
        hist = spy.history(period='1y')
        if hist is not None and len(hist) >= 50 and 'Close' in hist.columns:
            close = hist['Close'].dropna()
            if len(close) >= 200:
                sma_50 = close.iloc[-50:].mean()
                sma_200 = close.iloc[-200:].mean()
                if sma_50 > sma_200 * 1.02:
                    scores.append(1)  # Bull trend — modest positive signal
                    confidence_factors.append(0.5)  # Low weight
                elif sma_50 < sma_200 * 0.98:
                    scores.append(-1)
                    confidence_factors.append(0.5)
                else:
                    scores.append(0)
                    confidence_factors.append(0.4)
                print(f'Growth SPY SMA50/200: {sma_50:.1f}/{sma_200:.1f}')
    except Exception as e:
        print(f'Growth SPY error: {e}')

    # ── Derive regime from composite score ─────────────────────────────────
    if not scores:
        return 'UNKNOWN', 0.0

    composite = sum(scores) / len(scores)
    confidence = sum(confidence_factors) / len(confidence_factors) if confidence_factors else 0.5

    if composite >= 1.5:
        return 'EXPANDING', min(confidence, 0.9)
    elif composite >= 0.5:
        return 'RECOVERING', confidence
    elif composite >= -0.5:
        return 'SLOWING', confidence
    else:
        return 'CONTRACTING', min(confidence, 0.9)


def _classify_inflation() -> tuple:
    """
    Classify inflation regime using real CPI data.

    Primary signals (FRED):
        - CPI YoY rate (actual inflation, not a proxy)
        - 10-year breakeven inflation rate (market's inflation expectation)

    Secondary signals (yfinance):
        - Oil price (CL=F): geopolitical energy inflation
        - Gold (GLD): inflation hedge demand

    Returns: (regime_string, confidence_float)
    """
    scores = []  # positive = higher inflation, negative = lower/falling
    confidence_factors = []
    cpi_yoy = None

    # ── Signal 1: CPI YoY Rate (FRED CPIAUCSL) ────────────────────────────
    # The definitive inflation measure. Not a proxy — the real number.
    try:
        cpi = _fetch_fred_series('CPIAUCSL', limit=14)
        if cpi and len(cpi) >= 13:
            # Calculate YoY rate: (current / 12-months-ago - 1) * 100
            cpi_yoy = (cpi[-1] / cpi[-13] - 1) * 100
            # Calculate MoM trend (last 3 months annualized)
            cpi_3m_trend = (cpi[-1] / cpi[-4] - 1) * 400  # annualized

            print(f'Inflation CPI YoY: {cpi_yoy:.2f}%, 3M trend: {cpi_3m_trend:.2f}%')

            # Fed target is 2.0%. Score based on distance from target.
            if cpi_yoy > 4.0:
                scores.append(3)  # Significantly above target
                confidence_factors.append(0.95)
            elif cpi_yoy > 3.0:
                scores.append(2)  # Above target, rising
                confidence_factors.append(0.9)
            elif cpi_yoy > 2.5:
                scores.append(1)  # Mildly elevated
                confidence_factors.append(0.85)
            elif cpi_yoy > 2.0:
                scores.append(0.5)  # At/near target
                confidence_factors.append(0.8)
            elif cpi_yoy > 1.5:
                scores.append(-1)  # Below target, mild deflation risk
                confidence_factors.append(0.8)
            else:
                scores.append(-2)  # Well below target
                confidence_factors.append(0.85)
        else:
            print('Inflation: CPI data unavailable from FRED')
    except Exception as e:
        print(f'Inflation CPI error: {e}')

    # ── Signal 2: 10-Year Breakeven Inflation (FRED T10YIE) ───────────────
    # Market's forward-looking inflation expectation. Highly reliable.
    try:
        breakeven = _fetch_fred_series('T10YIE', limit=20)
        if breakeven and len(breakeven) >= 5:
            current_be = breakeven[-1]
            prior_be = breakeven[-5]  # ~1 week ago
            be_trend = current_be - prior_be

            print(f'Inflation 10Y Breakeven: {current_be:.2f}% (trend: {be_trend:+.2f})')

            if current_be > 3.0:
                scores.append(2)
                confidence_factors.append(0.85)
            elif current_be > 2.5:
                scores.append(1)
                confidence_factors.append(0.8)
            elif current_be > 2.0:
                scores.append(0)
                confidence_factors.append(0.75)
            else:
                scores.append(-1)
                confidence_factors.append(0.75)

            # Trend matters too — rising expectations are a warning
            if be_trend > 0.1:
                scores.append(0.5)  # Expectations rising
                confidence_factors.append(0.7)
            elif be_trend < -0.1:
                scores.append(-0.5)  # Expectations falling
                confidence_factors.append(0.7)
        else:
            print('Inflation: Breakeven data unavailable')
    except Exception as e:
        print(f'Inflation breakeven error: {e}')

    # ── Signal 3: Oil Price (yfinance CL=F) ───────────────────────────────
    # Energy inflation directly impacts CPI. Oil above $80 = inflationary.
    # Especially relevant given current Strait of Hormuz disruption.
    try:
        oil = yf.Ticker('CL=F')
        oil_hist = oil.history(period='3mo')
        if oil_hist is not None and len(oil_hist) >= 20 and 'Close' in oil_hist.columns:
            oil_close = oil_hist['Close'].dropna()
            current_oil = oil_close.iloc[-1]
            oil_3m_change = (oil_close.iloc[-1] / oil_close.iloc[-20] - 1) * 100

            print(f'Inflation Oil: ${current_oil:.2f} (3M change: {oil_3m_change:+.1f}%)')

            # Oil above $80 is inflationary, above $90 significantly so
            if current_oil > 90:
                scores.append(1.5)
                confidence_factors.append(0.8)
            elif current_oil > 80:
                scores.append(0.5)
                confidence_factors.append(0.7)
            elif current_oil < 60:
                scores.append(-1)
                confidence_factors.append(0.7)
            else:
                scores.append(0)
                confidence_factors.append(0.6)
        else:
            print('Inflation: Oil price unavailable')
    except Exception as e:
        print(f'Inflation oil error: {e}')

    # ── Signal 4: Gold (yfinance GLD) ─────────────────────────────────────
    # Gold rising = inflation hedge demand / fear. Secondary signal.
    try:
        gld = yf.Ticker('GLD')
        gld_hist = gld.history(period='3mo')
        if gld_hist is not None and len(gld_hist) >= 20 and 'Close' in gld_hist.columns:
            gld_close = gld_hist['Close'].dropna()
            gld_momentum = (gld_close.iloc[-1] / gld_close.iloc[-20] - 1) * 100

            print(f'Inflation GLD momentum: {gld_momentum:+.1f}%')

            if gld_momentum > 10:
                scores.append(1)  # Strong gold demand = inflation fear
                confidence_factors.append(0.6)
            elif gld_momentum > 5:
                scores.append(0.5)
                confidence_factors.append(0.55)
            elif gld_momentum < -5:
                scores.append(-0.5)
                confidence_factors.append(0.55)
            else:
                scores.append(0)
                confidence_factors.append(0.5)
        else:
            print('Inflation: GLD data unavailable')
    except Exception as e:
        print(f'Inflation GLD error: {e}')

    # ── Derive regime from composite score ─────────────────────────────────
    if not scores:
        # Last resort fallback: use DBC/TLT if all else fails
        try:
            dbc = yf.Ticker('DBC')
            tlt = yf.Ticker('TLT')
            dbc_hist = dbc.history(period='3mo')
            tlt_hist = tlt.history(period='3mo')
            if (dbc_hist is not None and tlt_hist is not None and
                    len(dbc_hist) >= 20 and len(tlt_hist) >= 20):
                dbc_mom = (dbc_hist['Close'].iloc[-1] /
                           dbc_hist['Close'].iloc[-20] - 1) * 100
                tlt_mom = (tlt_hist['Close'].iloc[-1] /
                           tlt_hist['Close'].iloc[-20] - 1) * 100
                if dbc_mom > 5 and tlt_mom < -2:
                    return 'RISING', 0.4  # Low confidence fallback
                elif dbc_mom < -5:
                    return 'FALLING', 0.4
                else:
                    return 'LOW', 0.3
        except Exception:
            pass
        return 'UNKNOWN', 0.0

    composite = sum(scores) / len(scores)
    confidence = sum(confidence_factors) / len(confidence_factors)

    # Map composite score to regime
    # Score > 1.5 = clearly elevated inflation
    # Score 0.5-1.5 = mildly elevated / rising
    # Score -0.5 to 0.5 = near target
    # Score < -0.5 = below target / falling
    if composite >= 1.5:
        return 'HIGH', min(confidence, 0.9)
    elif composite >= 0.5:
        return 'RISING', confidence
    elif composite >= -0.5:
        return 'LOW', confidence
    else:
        return 'FALLING', confidence


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
        
        if vix_hist is not None and len(vix_hist) > 0 and 'Close' in vix_hist.columns:
            vix_close = vix_hist['Close'].dropna()
            if len(vix_close) > 0:
                vix_level = vix_close.iloc[-1]
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
