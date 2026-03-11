"""
Market Regime Classifier for Options Premium Selling
Analyzes 7 dimensions to classify market into GREEN/YELLOW/RED regimes
"""
import json
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import pandas_ta as ta
import io

CACHE_FILE = Path('data/regime_cache.json')
HISTORY_FILE = Path('data/regime_history.json')
CACHE_DURATION_MINUTES = 60

# Top 20 SPX components for correlation analysis
SPX_COMPONENTS = ['AAPL', 'MSFT', 'NVDA', 'AMZN', 'META', 'GOOGL', 'TSLA', 'BRK-B', 
                  'UNH', 'JPM', 'V', 'XOM', 'JNJ', 'LLY', 'AVGO', 'MA', 'HD', 'PG', 'MRK', 'COST']

def _load_cache():
    """Load cached regime analysis if fresh"""
    if not CACHE_FILE.exists():
        return None
    try:
        with open(CACHE_FILE, 'r') as f:
            cache = json.load(f)
        cache_time = datetime.fromisoformat(cache['timestamp'])
        age_minutes = (datetime.now() - cache_time).total_seconds() / 60
        if age_minutes < CACHE_DURATION_MINUTES:
            cache['cache_age_minutes'] = age_minutes
            return cache
    except:
        pass
    return None

def _save_cache(data):
    """Save regime analysis to cache"""
    CACHE_FILE.parent.mkdir(exist_ok=True)
    with open(CACHE_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def _append_history(data):
    """Append regime verdict to history, keep last 30"""
    HISTORY_FILE.parent.mkdir(exist_ok=True)
    history = []
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, 'r') as f:
                history = json.load(f)
        except:
            history = []
    
    history.append({
        'timestamp': data['timestamp'],
        'spx_price': data['spx_price'],
        'vix_level': data['vix_level'],
        'composite_score': data['composite_score'],
        'verdict': data['verdict']
    })
    
    # Keep last 30
    history = history[-30:]
    
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)

def run_regime_analysis(force_refresh=False):
    """
    Run complete regime analysis
    Returns dict with all dimensions, scores, and verdict
    """
    # Check cache first
    if not force_refresh:
        cached = _load_cache()
        if cached:
            return cached
    
    result = {
        'timestamp': datetime.now().isoformat(),
        'cache_age_minutes': 0,
        'spx_price': None,
        'vix_level': None,
        'vix_3m': None,
        'term_structure_source': 'unknown',
        'pcr_source': 'unavailable',
        'dimensions': {},
        'composite_score': 0.0,
        'hard_override_triggered': False,
        'override_reason': None,
        'verdict': 'YELLOW',
        'recommended_strategy': '',
        'position_sizing': '',
        'entry_timing': '',
        'errors': []
    }
    
    # Fetch SPX data
    try:
        spx = yf.Ticker('^GSPC')
        spx_hist = spx.history(period='60d')
        if not spx_hist.empty:
            result['spx_price'] = round(spx_hist['Close'].iloc[-1], 2)
            spx_closes = spx_hist['Close']
        else:
            result['errors'].append('SPX data unavailable')
            spx_closes = pd.Series()
    except Exception as e:
        result['errors'].append(f'SPX fetch failed: {str(e)}')
        spx_closes = pd.Series()
    
    # Fetch VIX data
    try:
        vix = yf.Ticker('^VIX')
        vix_hist = vix.history(period='5d')
        if not vix_hist.empty:
            result['vix_level'] = round(vix_hist['Close'].iloc[-1], 2)
        else:
            result['errors'].append('VIX data unavailable')
    except Exception as e:
        result['errors'].append(f'VIX fetch failed: {str(e)}')
    
    # Fetch VIX3M — try Tastytrade live futures first, fall back to yfinance
    try:
        from hybrid_data import get_vix_term_structure
        tt_term = get_vix_term_structure()
        if tt_term and tt_term.get('vix_3m'):
            result['vix_3m'] = round(tt_term['vix_3m'], 2)
            result['term_structure_source'] = tt_term.get('source', 'tastytrade')
        else:
            raise ValueError("Tastytrade term structure unavailable")
    except Exception:
        # Fallback: yfinance ^VIX3M proxy
        try:
            vix3m = yf.Ticker('^VIX3M')
            vix3m_hist = vix3m.history(period='5d')
            if not vix3m_hist.empty:
                result['vix_3m'] = round(vix3m_hist['Close'].iloc[-1], 2)
                result['term_structure_source'] = 'yfinance_fallback'
            else:
                result['vix_3m'] = None
                result['term_structure_source'] = 'unavailable'
        except:
            result['vix_3m'] = None
            result['term_structure_source'] = 'unavailable'
    
    # 1. VIX Regime
    vix_score = 0.0
    vix_regime = 'UNKNOWN'
    vix_desc = ''
    if result['vix_level']:
        vix = result['vix_level']
        if vix < 15:
            vix_regime = 'LOW'
            vix_score = 0.3
            vix_desc = 'Premium thin, be selective'
        elif vix < 20:
            vix_regime = 'NORMAL'
            vix_score = 1.0
            vix_desc = 'Ideal for selling premium'
        elif vix < 30:
            vix_regime = 'ELEVATED'
            vix_score = 0.6
            vix_desc = 'Good premium but wider strikes required'
        else:
            vix_regime = 'CRISIS'
            vix_score = -1.0
            vix_desc = 'Stop selling, undefined risk'
    
    result['dimensions']['vix_regime'] = {
        'value': vix_regime,
        'score': vix_score,
        'description': vix_desc
    }
    
    # 2. Term Structure
    term_score = 0.0
    term_structure = 'UNKNOWN'
    term_spread = 0.0
    term_desc = ''
    if result['vix_level'] and result['vix_3m']:
        term_spread = result['vix_3m'] - result['vix_level']
        if term_spread > 0:
            term_structure = 'CONTANGO'
            term_score = 1.0
            term_desc = 'Normal, favorable for sellers'
        elif term_spread > -1:
            term_structure = 'FLAT'
            term_score = 0.0
            term_desc = 'Neutral, caution'
        else:
            term_structure = 'BACKWARDATION'
            term_score = -1.0
            term_desc = 'Danger, stop selling premium'
    
    result['dimensions']['term_structure'] = {
        'value': term_structure,
        'spread': round(term_spread, 2),
        'score': term_score,
        'description': term_desc
    }
    
    # 3. Trend Assessment (ADX)
    trend_score = 0.0
    trend_value = 'UNKNOWN'
    adx_value = 0.0
    trend_desc = ''
    if len(spx_closes) > 20:
        try:
            adx_series = ta.adx(spx_hist['High'], spx_hist['Low'], spx_hist['Close'], length=14)
            if adx_series is not None and 'ADX_14' in adx_series.columns:
                adx_value = adx_series['ADX_14'].iloc[-1]
                if adx_value > 28:
                    trend_value = 'TRENDING'
                    trend_score = -0.5
                    trend_desc = 'Bad for iron condors, use directional spreads'
                elif adx_value > 20:
                    trend_value = 'MIXED'
                    trend_score = 0.3
                    trend_desc = 'Use wider strikes'
                else:
                    trend_value = 'RANGE_BOUND'
                    trend_score = 1.0
                    trend_desc = 'Ideal for premium selling'
        except:
            result['errors'].append('ADX calculation failed')
    
    result['dimensions']['trend_assessment'] = {
        'value': trend_value,
        'adx': round(adx_value, 1),
        'score': trend_score,
        'description': trend_desc
    }
    
    # 4. Realized vs Implied Vol Spread
    vol_score = 0.0
    vol_edge = 'UNKNOWN'
    realized_vol = 0.0
    implied_vol = 0.0
    vol_spread = 0.0
    vol_desc = ''
    if len(spx_closes) > 20 and result['vix_level']:
        try:
            log_returns = np.log(spx_closes / spx_closes.shift(1)).dropna()
            realized_vol = log_returns.tail(20).std() * np.sqrt(252)
            implied_vol = result['vix_level'] / 100
            vol_spread = implied_vol - realized_vol
            
            if vol_spread > 0.03:
                vol_edge = 'STRONG'
                vol_score = 1.0
                vol_desc = 'IV significantly overpricing, clear seller edge'
            elif vol_spread > 0:
                vol_edge = 'MILD'
                vol_score = 0.5
                vol_desc = 'Slight edge, proceed conservatively'
            else:
                vol_edge = 'NONE'
                vol_score = -0.5
                vol_desc = 'IV underpricing realized moves, no edge'
        except:
            result['errors'].append('Vol spread calculation failed')
    
    result['dimensions']['vol_spread'] = {
        'value': vol_edge,
        'realized_vol': round(realized_vol, 4),
        'implied_vol': round(implied_vol, 4),
        'spread': round(vol_spread, 4),
        'score': vol_score,
        'description': vol_desc
    }
    
    # 5. Market Breadth
    breadth_score = 0.0
    breadth_value = 'UNKNOWN'
    ad_ratio = 0.5
    nh_nl_ratio = 0.5
    breadth_desc = ''
    try:
        adv = yf.Ticker('^ADV').history(period='5d')
        decl = yf.Ticker('^DECL').history(period='5d')
        nhgh = yf.Ticker('^NYHGH').history(period='5d')
        nlow = yf.Ticker('^NYLOW').history(period='5d')
        
        if not adv.empty and not decl.empty:
            adv_val = adv['Close'].iloc[-1]
            decl_val = decl['Close'].iloc[-1]
            ad_ratio = adv_val / (adv_val + decl_val) if (adv_val + decl_val) > 0 else 0.5
        
        if not nhgh.empty and not nlow.empty:
            nh_val = nhgh['Close'].iloc[-1]
            nl_val = nlow['Close'].iloc[-1]
            nh_nl_ratio = nh_val / (nh_val + nl_val) if (nh_val + nl_val) > 0 else 0.5
        
        if ad_ratio > 0.55 and nh_nl_ratio > 0.6:
            breadth_value = 'BULLISH'
            breadth_score = 0.8
            breadth_desc = 'Strong breadth supports premium selling'
        elif ad_ratio < 0.45 or nh_nl_ratio < 0.35:
            breadth_value = 'BEARISH'
            breadth_score = -0.8
            breadth_desc = 'Weak breadth, caution on premium selling'
        else:
            breadth_value = 'NEUTRAL'
            breadth_score = 0.2
            breadth_desc = 'Mixed breadth, proceed with caution'
    except Exception as e:
        result['errors'].append(f'Breadth fetch failed: {str(e)}')
    
    result['dimensions']['breadth'] = {
        'value': breadth_value,
        'ad_ratio': round(ad_ratio, 3),
        'nh_nl_ratio': round(nh_nl_ratio, 3),
        'score': breadth_score,
        'description': breadth_desc
    }
    
    # 6. Put/Call Ratio
    pcr_score = 0.0
    pcr_sentiment = 'UNKNOWN'
    pcr_value = None
    pcr_source = 'unavailable'
    pcr_desc = ''
    
    # PCR fetch — CBOE direct CSV first, yfinance tickers as last resort
    
    def _fetch_cboe_pcr() -> tuple:
        """
        Fetch put/call ratio directly from CBOE's public daily statistics page.
        Returns (pcr_value, source_label) or (None, 'unavailable') on failure.

        CBOE publishes two relevant CSVs:
          - Equity P/C:  https://www.cboe.com/data/volatility-indexes/  (not CSV)
          - Daily stats: https://www.cboe.com/us/options/market_statistics/daily/
            direct CSV:  https://www.cboe.com/publish/scheduledtask/mktstat/daily_volume.csv

        The daily_volume.csv contains total put volume and call volume for all CBOE
        products. We compute total P/C = total_put_volume / total_call_volume.

        If that fails, try the equity-only P/C from:
          https://www.cboe.com/publish/scheduledtask/mktstat/equity_pc.csv
        """
        import requests
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; market-regime-classifier/1.0)'
        }

        # Attempt 1: equity-only P/C ratio CSV (most relevant for sentiment)
        try:
            url = 'https://www.cboe.com/publish/scheduledtask/mktstat/equity_pc.csv'
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            # File format: DATE,PC_RATIO  (header on row 0, data starts row 1)
            df = pd.read_csv(io.StringIO(resp.text))
            df.columns = [c.strip().upper() for c in df.columns]
            # Find the ratio column — may be named PC_RATIO, P/C, RATIO, etc.
            ratio_col = next(
                (c for c in df.columns if 'RATIO' in c or 'PC' in c or 'P/C' in c),
                None
            )
            if ratio_col:
                val = pd.to_numeric(df[ratio_col].iloc[-1], errors='coerce')
                if pd.notna(val) and val > 0:
                    return round(float(val), 3), 'cboe_equity_pc'
        except Exception:
            pass

        # Attempt 2: total P/C from daily volume CSV
        try:
            url = 'https://www.cboe.com/publish/scheduledtask/mktstat/daily_volume.csv'
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            df = pd.read_csv(io.StringIO(resp.text))
            df.columns = [c.strip().upper() for c in df.columns]
            put_col = next((c for c in df.columns if 'PUT' in c), None)
            call_col = next((c for c in df.columns if 'CALL' in c), None)
            if put_col and call_col:
                puts = pd.to_numeric(df[put_col].iloc[-1], errors='coerce')
                calls = pd.to_numeric(df[call_col].iloc[-1], errors='coerce')
                if pd.notna(puts) and pd.notna(calls) and calls > 0:
                    return round(float(puts / calls), 3), 'cboe_total_pc'
        except Exception:
            pass

        return None, 'unavailable'

    # Try CBOE direct first
    pcr_value, pcr_source = _fetch_cboe_pcr()

    # Last resort: yfinance tickers (kept as fallback, known to be unreliable)
    if pcr_value is None:
        for pcr_ticker in ['^CPCE', '^CPC', '^PCALL']:
            try:
                pcr_data = yf.Ticker(pcr_ticker).history(period='5d')
                if not pcr_data.empty:
                    val = pcr_data['Close'].iloc[-1]
                    if val > 0:
                        pcr_value = round(val, 3)
                        pcr_source = pcr_ticker
                        break
            except Exception:
                continue
    
    if pcr_value is not None:
        if pcr_value > 1.2:
            pcr_sentiment = 'EXTREME_FEAR'
            pcr_score = 0.8
            pcr_desc = 'Elevated put buying, contrarian bullish'
        elif pcr_value > 0.9:
            pcr_sentiment = 'FEAR'
            pcr_score = 0.5
            pcr_desc = 'Slight put bias, mild bullish lean'
        elif pcr_value > 0.6:
            pcr_sentiment = 'NEUTRAL'
            pcr_score = 0.2
            pcr_desc = 'Balanced sentiment'
        elif pcr_value > 0.4:
            pcr_sentiment = 'COMPLACENCY'
            pcr_score = -0.3
            pcr_desc = 'Caution on call side'
        else:
            pcr_sentiment = 'EXTREME_COMPLACENCY'
            pcr_score = -0.8
            pcr_desc = 'Significant caution, risk of reversal'
    else:
        result['errors'].append('PCR data unavailable from all sources')
    
    result['pcr_source'] = pcr_source
    result['dimensions']['pcr_sentiment'] = {
        'value': pcr_sentiment,
        'pcr': pcr_value if pcr_value is not None else 0.0,
        'score': pcr_score,
        'description': pcr_desc
    }
    
    # 7. Correlation Regime
    corr_score = 0.0
    corr_regime = 'UNKNOWN'
    avg_corr = 0.0
    corr_desc = ''
    try:
        returns_data = {}
        for symbol in SPX_COMPONENTS[:10]:  # Use top 10 for speed
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period='30d')
                if len(hist) > 20:
                    returns_data[symbol] = hist['Close'].pct_change().dropna().tail(20)
            except:
                continue
        
        if len(returns_data) >= 5:
            df_returns = pd.DataFrame(returns_data)
            corr_matrix = df_returns.corr()
            # Average of upper triangle (exclude diagonal)
            mask = np.triu(np.ones_like(corr_matrix), k=1).astype(bool)
            avg_corr = corr_matrix.where(mask).stack().mean()
            
            if avg_corr > 0.65:
                corr_regime = 'HIGH'
                corr_score = 0.0
                corr_desc = 'Macro-driven, use index-level strategies'
            elif avg_corr > 0.40:
                corr_regime = 'NORMAL'
                corr_score = 0.5
                corr_desc = 'Balanced correlation environment'
            else:
                corr_regime = 'LOW'
                corr_score = 0.8
                corr_desc = 'Stock-picking environment, individual names work'
    except Exception as e:
        result['errors'].append(f'Correlation calculation failed: {str(e)}')
    
    result['dimensions']['correlation_regime'] = {
        'value': corr_regime,
        'avg_correlation': round(avg_corr, 3),
        'score': corr_score,
        'description': corr_desc
    }
    
    # Calculate composite score
    weights = {
        'vix_regime': 0.20,
        'term_structure': 0.20,
        'trend_assessment': 0.15,
        'vol_spread': 0.20,
        'breadth': 0.10,
        'pcr_sentiment': 0.10,
        'correlation_regime': 0.05
    }
    
    composite = 0.0
    for dim, weight in weights.items():
        composite += result['dimensions'][dim]['score'] * weight
    
    result['composite_score'] = round(composite, 3)
    
    # Determine verdict
    if composite >= 0.50:
        verdict = 'GREEN'
    elif composite >= 0.15:
        verdict = 'YELLOW'
    else:
        verdict = 'RED'
    
    # Hard overrides
    if term_structure == 'BACKWARDATION':
        verdict = 'RED'
        result['hard_override_triggered'] = True
        result['override_reason'] = 'VIX term structure in backwardation'
    elif vix_regime == 'CRISIS':
        verdict = 'RED'
        result['hard_override_triggered'] = True
        result['override_reason'] = 'VIX in crisis mode (>30)'
    elif vol_edge == 'NONE' and trend_value == 'TRENDING':
        verdict = 'RED'
        result['hard_override_triggered'] = True
        result['override_reason'] = 'No vol edge + strong trend = no premium selling edge'
    
    result['verdict'] = verdict
    
    # Strategy recommendations
    if verdict == 'GREEN':
        result['recommended_strategy'] = 'Iron Condor — sell 0.10-0.15 delta on both sides, standard 5-wide spreads'
        result['position_sizing'] = 'Full size — up to $500 per spread'
        result['entry_timing'] = '9:45-10:30 AM after opening volatility settles'
    elif verdict == 'YELLOW':
        result['recommended_strategy'] = 'Single-side credit spread — put spread only if bullish breadth, call spread only if bearish; avoid iron condor'
        result['position_sizing'] = 'Half size — max $250 per spread'
        result['entry_timing'] = 'Wait for 10:30 AM — confirm direction before entering'
    else:
        result['recommended_strategy'] = 'No premium selling — sit in cash or use defined-risk debit spreads only if high conviction directional view'
        result['position_sizing'] = 'Zero options premium selling'
        result['entry_timing'] = 'N/A'
    
    # Save cache and history
    _save_cache(result)
    _append_history(result)
    
    return result

def get_regime_history():
    """Get last 30 regime verdicts"""
    if not HISTORY_FILE.exists():
        return []
    try:
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    except:
        return []
