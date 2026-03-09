# -*- coding: utf-8 -*-
# cup_handle_scanner_2.py
# Enhanced Cup & Handle Scanner with Advanced Pattern Detection
# Requirements: pip install flask yfinance pandas pandas_ta requests beautifulsoup4 scipy matplotlib

import re
import json
import os
import base64
from io import BytesIO
from pathlib import Path
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from flask import Flask, render_template_string, request, Response, flash, redirect
import yfinance as yf

# Alpaca integration
from alpaca_data import fetch_stock_data, fetch_multiple_stocks
from alpaca_client import get_mode
import stream_manager
import order_manager
import pandas as pd
import pandas_ta as ta
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from scipy.signal import argrelextrema
from scipy.stats import linregress
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend

import json
import os

app = Flask(__name__)
app.secret_key = 'your-unique-secret-key-here-change-in-production'  # Required for sessions/flash

TRACKED_FILE = 'data/tracked_stocks.json'

def load_tracked_stocks():
    if os.path.exists(TRACKED_FILE):
        with open(TRACKED_FILE, 'r') as f:
            return json.load(f)
    return []

def save_tracked_stocks(stocks):
    os.makedirs(os.path.dirname(TRACKED_FILE), exist_ok=True)
    with open(TRACKED_FILE, 'w') as f:
        json.dump(stocks, f, indent=2, default=str)

# ════════════════════════════════════════════════════════════════
# TICKER FETCHING FUNCTIONS
# ════════════════════════════════════════════════════════════════

# Hardcoded S&P 500 list (reliable fallback, updated Jan 2026)
SP500_TICKERS = [
    "AAPL", "ABBV", "ABT", "ACN", "ADBE", "ADI", "ADM", "ADP", "ADSK", "AEE", "AEP", "AES", "AFL", "AIG", "AIZ",
    "AJG", "AKAM", "ALB", "ALGN", "ALL", "ALLE", "AMAT", "AMCR", "AMD", "AME", "AMGN", "AMP", "AMT", "AMZN",
    "ANET", "ANSS", "AON", "AOS", "APA", "APD", "APH", "APTV", "ARE", "ATO", "AVB", "AVGO", "AVY", "AWK", "AXON",
    "AXP", "AZO", "BA", "BAC", "BALL", "BAX", "BBWI", "BBY", "BDX", "BEN", "BF.B", "BG", "BIIB", "BIO", "BK",
    "BKNG", "BKR", "BLDR", "BLK", "BMY", "BR", "BRK.B", "BRO", "BSX", "BWA", "BX", "BXP", "C", "CAG", "CAH",
    "CARR", "CAT", "CB", "CBOE", "CBRE", "CCI", "CCL", "CDNS", "CDW", "CE", "CEG", "CF", "CFG", "CHD", "CHRW",
    "CHTR", "CI", "CINF", "CL", "CLX", "CMA", "CMCSA", "CME", "CMG", "CMI", "CMS", "CNC", "CNP", "COF", "COO",
    "COP", "COR", "COST", "CPAY", "CPB", "CPRT", "CPT", "CRL", "CRM", "CSCO", "CSGP", "CSX", "CTAS", "CTLT",
    "CTRA", "CTSH", "CTVA", "CVS", "CVX", "CZR", "D", "DAL", "DD", "DE", "DECK", "DFS", "DG", "DGX", "DHI",
    "DHR", "DIS", "DLR", "DLTR", "DOC", "DOV", "DOW", "DPZ", "DRI", "DTE", "DUK", "DVA", "DVN", "DXCM", "EA",
    "EBAY", "ECL", "ED", "EFX", "EG", "EIX", "EL", "ELV", "EMN", "EMR", "ENPH", "EOG", "EPAM", "EQIX", "EQR",
    "EQT", "ES", "ESS", "ETN", "ETR", "ETSY", "EVRG", "EW", "EXC", "EXPD", "EXPE", "EXR", "F", "FANG", "FAST",
    "FCX", "FDS", "FDX", "FE", "FFIV", "FI", "FICO", "FIS", "FITB", "FLT", "FMC", "FOX", "FOXA", "FRT", "FSLR",
    "FTNT", "FTV", "GD", "GDDY", "GE", "GEHC", "GEN", "GEV", "GILD", "GIS", "GL", "GLW", "GM", "GNRC", "GOOG",
    "GOOGL", "GPC", "GPN", "GRMN", "GS", "GWW", "HAL", "HAS", "HBAN", "HCA", "HD", "HES", "HIG", "HII", "HLT",
    "HOLX", "HON", "HPE", "HPQ", "HRL", "HSIC", "HST", "HSY", "HUBB", "HUM", "HWM", "IBM", "ICE", "IDXX", "IEX",
    "IFF", "ILMN", "INCY", "INTC", "INTU", "INVH", "IP", "IPG", "IQV", "IR", "IRM", "ISRG", "IT", "ITW", "IVZ",
    "J", "JBHT", "JBL", "JCI", "JKHY", "JNJ", "JNPR", "JPM", "K", "KDP", "KEY", "KEYS", "KHC", "KIM", "KKR",
    "KLAC", "KMB", "KMI", "KMX", "KO", "KR", "KVUE", "L", "LDOS", "LEN", "LH", "LHX", "LIN", "LKQ", "LLY",
    "LMT", "LNT", "LOW", "LRCX", "LULU", "LUV", "LVS", "LW", "LYB", "LYV", "MA", "MAA", "MAR", "MAS", "MCD",
    "MCHP", "MCK", "MCO", "MDLZ", "MDT", "MET", "META", "MGM", "MHK", "MKC", "MKTX", "MLM", "MMC", "MMM", "MNST",
    "MO", "MOH", "MOS", "MPC", "MPWR", "MRK", "MRNA", "MRO", "MS", "MSCI", "MSFT", "MSI", "MTB", "MTCH", "MTD",
    "MU", "NCLH", "NDAQ", "NDSN", "NEE", "NEM", "NFLX", "NI", "NKE", "NOC", "NOW", "NRG", "NSC", "NTAP", "NTRS",
    "NUE", "NVDA", "NVR", "NWS", "NWSA", "NXPI", "O", "ODFL", "OKE", "OMC", "ON", "ORCL", "ORLY", "OTIS", "OXY",
    "PANW", "PARA", "PAYC", "PAYX", "PCAR", "PCG", "PEG", "PEP", "PFE", "PFG", "PG", "PGR", "PH", "PHM", "PKG",
    "PLD", "PLTR", "PM", "PNC", "PNR", "PNW", "PODD", "POOL", "PPG", "PPL", "PRU", "PSA", "PSX", "PTC", "PWR",
    "PYPL", "QCOM", "QRVO", "RCL", "REG", "REGN", "RF", "RJF", "RL", "RMD", "ROK", "ROL", "ROP", "ROST", "RSG",
    "RTX", "RVTY", "SBAC", "SBUX", "SCHW", "SHW", "SJM", "SLB", "SMCI", "SNA", "SNPS", "SO", "SOLV", "SPG",
    "SPGI", "SRE", "STE", "STLD", "STT", "STX", "STZ", "SWK", "SWKS", "SYF", "SYK", "SYY", "T", "TAP", "TDG",
    "TDY", "TECH", "TEL", "TER", "TFC", "TFX", "TGT", "TJX", "TMO", "TMUS", "TPR", "TRGP", "TRMB", "TROW",
    "TRV", "TSCO", "TSLA", "TSN", "TT", "TTWO", "TXN", "TXT", "TYL", "UAL", "UBER", "UDR", "UHS", "ULTA", "UNH",
    "UNP", "UPS", "URI", "USB", "V", "VICI", "VLO", "VLTO", "VMC", "VRSK", "VRSN", "VRTX", "VST", "VTR", "VTRS",
    "VZ", "WAB", "WAT", "WBA", "WBD", "WDC", "WEC", "WELL", "WFC", "WM", "WMB", "WMT", "WRB", "WST", "WTW", "WY",
    "WYNN", "XEL", "XOM", "XYL", "YUM", "ZBH", "ZBRA", "ZTS"
]


def get_sp500_tickers():
    """Get S&P 500 tickers - try GitHub CSV first, fallback to hardcoded list."""
    # Try datahub.io maintained list
    try:
        url = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            import io
            df = pd.read_csv(io.StringIO(response.text))
            tickers = df['Symbol'].tolist()
            return tickers
    except Exception as e:
        # Fallback to hardcoded list
        return SP500_TICKERS.copy()


def get_nasdaq_tickers(min_market_cap=1_000_000_000):
    try:
        url = "https://api.nasdaq.com/api/screener/stocks?tableonly=true&limit=5000&exchange=NASDAQ"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=30)
        data = response.json()

        tickers = []
        if 'data' in data and 'table' in data['data'] and 'rows' in data['data']['table']:
            for row in data['data']['table']['rows']:
                symbol = row.get('symbol', '')
                market_cap_str = row.get('marketCap', '0')
                try:
                    market_cap = int(market_cap_str.replace(
                        ',', '')) if market_cap_str else 0
                except:
                    market_cap = 0
                if (symbol and '^' not in symbol and '/' not in symbol
                        and len(symbol) <= 5 and market_cap >= min_market_cap):
                    tickers.append(symbol)

        return tickers if tickers else get_sp500_tickers()
    except Exception as e:
        return get_sp500_tickers()


def get_nyse_tickers(min_market_cap=1_000_000_000):
    try:
        url = "https://api.nasdaq.com/api/screener/stocks?tableonly=true&limit=5000&exchange=NYSE"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=30)
        data = response.json()

        tickers = []
        if 'data' in data and 'table' in data['data'] and 'rows' in data['data']['table']:
            for row in data['data']['table']['rows']:
                symbol = row.get('symbol', '')
                market_cap_str = row.get('marketCap', '0')
                try:
                    market_cap = int(market_cap_str.replace(
                        ',', '')) if market_cap_str else 0
                except:
                    market_cap = 0
                if (symbol and '^' not in symbol and '/' not in symbol
                        and len(symbol) <= 5 and market_cap >= min_market_cap):
                    tickers.append(symbol)

        return tickers
    except Exception as e:
        return []


def get_all_us_tickers(min_market_cap=1_000_000_000):
    nasdaq = get_nasdaq_tickers(min_market_cap)
    nyse = get_nyse_tickers(min_market_cap)
    all_tickers = list(set(nasdaq + nyse))
    return all_tickers


# ════════════════════════════════════════════════════════════════
# COMPANY INFO
# ════════════════════════════════════════════════════════════════

def get_company_info(symbol):
    """Get detailed company information."""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        # Handle case where info is None
        if info is None:
            info = {}

        return {
            'name': info.get('longName', info.get('shortName', symbol)),
            'sector': info.get('sector', 'N/A'),
            'industry': info.get('industry', 'N/A'),
            'exchange': info.get('exchange', 'N/A'),
            'market_cap': info.get('marketCap', 0),
            'market_cap_fmt': format_market_cap(info.get('marketCap', 0)),
            'description': info.get('longBusinessSummary', 'No description available.'),
            'website': info.get('website', ''),
            'employees': info.get('fullTimeEmployees', 'N/A'),
            'country': info.get('country', 'N/A'),
            'current_price': info.get('currentPrice', info.get('regularMarketPrice', 0)),
            'fifty_two_week_high': info.get('fiftyTwoWeekHigh', 0),
            'fifty_two_week_low': info.get('fiftyTwoWeekLow', 0),
            'avg_volume': info.get('averageVolume', 0),
            'pe_ratio': info.get('trailingPE', None),
            'forward_pe': info.get('forwardPE', None),
            'dividend_yield': info.get('dividendYield', None),
            'beta': info.get('beta', None),
        }
    except Exception as e:
        return {
            'name': symbol,
            'sector': 'N/A',
            'industry': 'N/A',
            'exchange': 'N/A',
            'market_cap': 0,
            'market_cap_fmt': 'N/A',
            'description': 'Unable to fetch company information.',
            'website': '',
            'employees': 'N/A',
            'country': 'N/A',
            'current_price': 0,
        }


def format_market_cap(value):
    """Format market cap in human readable form."""
    if not value or value == 0:
        return 'N/A'
    if value >= 1e12:
        return f"${value/1e12:.2f}T"
    elif value >= 1e9:
        return f"${value/1e9:.2f}B"
    elif value >= 1e6:
        return f"${value/1e6:.2f}M"
    else:
        return f"${value:,.0f}"


# ════════════════════════════════════════════════════════════════
# OPTIONS STRATEGY: IV-AWARE STRATEGY SELECTOR
# ════════════════════════════════════════════════════════════════

def calculate_approx_delta(strike, current_price, days_to_exp, is_call=True):
    """
    Approximate delta using a simplified model.
    For ATM options, delta ≈ 0.5. Adjusts based on moneyness.
    """
    if days_to_exp <= 0:
        days_to_exp = 1

    moneyness = current_price / strike if is_call else strike / current_price
    time_factor = min(1.0, days_to_exp / 90)

    if is_call:
        if moneyness >= 1.0:
            base_delta = 0.5 + (moneyness - 1.0) * 2
            delta = min(0.95, base_delta)
        else:
            base_delta = 0.5 * moneyness
            delta = max(0.05, base_delta)
    else:
        delta = -1 * calculate_approx_delta(strike, current_price, days_to_exp, is_call=True) + 1

    return round(delta, 2)


def calculate_iv_rank(symbol):
    """Calculate IV rank (0-100) using 52-week IV range."""
    try:
        ticker = yf.Ticker(symbol)
        expirations = ticker.options
        if not expirations:
            return 50
        
        ivs = []
        for exp in expirations[:12]:  # Sample first 12 expirations
            try:
                chain = ticker.option_chain(exp)
                calls_iv = chain.calls['impliedVolatility'].dropna()
                if len(calls_iv) > 0:
                    ivs.append(calls_iv.median())
            except:
                continue
        
        if len(ivs) < 3:
            return 50
        
        current_iv = ivs[0] if ivs else 0.3
        iv_low = min(ivs)
        iv_high = max(ivs)
        
        if iv_high == iv_low:
            return 50
        
        iv_rank = ((current_iv - iv_low) / (iv_high - iv_low)) * 100
        return round(max(0, min(100, iv_rank)), 1)
    except:
        return 50


def get_vix():
    """Fetch current VIX level."""
    try:
        vix = yf.Ticker("^VIX")
        hist = vix.history(period="1d")
        if not hist.empty:
            return round(hist['Close'].iloc[-1], 2)
    except:
        pass
    return 20


def classify_regime(df, adx_value, cto_bullish):
    """Classify market regime using ADX and CTO Larsson."""
    if adx_value is None:
        return 'UNKNOWN', 'Insufficient data'
    
    if adx_value > 25:
        if cto_bullish:
            return 'TRENDING_BULLISH', f'Strong bullish trend (ADX {adx_value:.1f})'
        else:
            return 'TRENDING_BEARISH', f'Strong bearish trend (ADX {adx_value:.1f})'
    elif adx_value < 20:
        return 'RANGE_BOUND', f'Range-bound market (ADX {adx_value:.1f})'
    else:
        return 'TRANSITIONING', f'Transitioning regime (ADX {adx_value:.1f})'


def suggest_bull_call_spread(symbol, current_price, analysis=None, budget=375, df=None):
    """IV-aware options strategy selector with regime detection."""
    try:
        ticker = yf.Ticker(symbol)
        try:
            expirations = ticker.options
        except:
            return {'status': 'no_options', 'message': f'Options data unavailable for {symbol} — consider equity position sizing instead.'}
        
        if not expirations:
            return {'status': 'no_options', 'message': f'Options data unavailable for {symbol} — consider equity position sizing instead.'}
        
        # Get IV rank and VIX
        iv_rank = calculate_iv_rank(symbol)
        vix = get_vix()
        
        # Regime detection using existing data
        regime_type = 'UNKNOWN'
        regime_desc = 'Unknown'
        adx_value = None
        cto_bullish = None
        
        if df is not None and len(df) >= 60:
            # Get ADX from analysis if available, otherwise compute
            if analysis and 'adx' in analysis:
                adx_value = analysis['adx']
            else:
                adx_data = ta.adx(df['High'], df['Low'], df['Close'], length=14)
                if adx_data is not None and 'ADX_14' in adx_data.columns:
                    adx_value = adx_data['ADX_14'].iloc[-1]
            
            # Get CTO Larsson bullish/bearish status
            hl2 = (df['High'] + df['Low']) / 2
            cto1 = ta.ema(hl2, length=15)
            cto2 = ta.ema(hl2, length=29)
            if cto1 is not None and cto2 is not None:
                cto_bullish = cto1.iloc[-1] >= cto2.iloc[-1]
            
            regime_type, regime_desc = classify_regime(df, adx_value, cto_bullish)
        
        # Apply regime override rules
        if regime_type == 'TRENDING_BEARISH':
            return {
                'status': 'regime_override',
                'symbol': symbol,
                'current_price': round(current_price, 2),
                'iv_rank': iv_rank,
                'vix': vix,
                'regime': 'IV Analysis',
                'trend_regime': regime_type,
                'trend_regime_desc': regime_desc,
                'message': f'⚠️ Bearish regime detected (ADX {adx_value:.1f}, CTO bearish). Pattern signal conflicts with trend. Options play not recommended — review chart before trading.',
            }
        
        # Determine IV-based strategy
        if iv_rank < 35 and vix < 20:
            iv_regime = 'Low IV'
            
            # Range-bound override for long calls
            if regime_type == 'RANGE_BOUND':
                return _build_iron_condor(ticker, symbol, current_price, budget, iv_rank, vix, iv_regime, regime_type, regime_desc, analysis)
            
            return _build_long_call(ticker, symbol, current_price, budget, iv_rank, vix, iv_regime, regime_type, regime_desc, analysis)
        elif iv_rank >= 65:
            iv_regime = 'Elevated IV'
            return _build_cash_secured_put(ticker, symbol, current_price, budget, iv_rank, vix, iv_regime, regime_type, regime_desc, analysis)
        else:
            iv_regime = 'Moderate IV'
            return _build_pmcc(ticker, symbol, current_price, budget, iv_rank, vix, iv_regime, regime_type, regime_desc, analysis)
    
    except Exception as e:
        import traceback
        return {'status': 'error', 'message': f'Error: {str(e)}', 'traceback': traceback.format_exc()}


def _build_iron_condor(ticker, symbol, current_price, budget, iv_rank, vix, regime, trend_regime, trend_regime_desc, analysis):
    """Build Iron Condor for range-bound markets."""
    rationale = 'Range-bound regime detected. Credit spread or iron condor more appropriate than directional long call in this environment.'
    today = datetime.today()
    expirations = ticker.options
    
    # Find 7-14 DTE
    target_exps = []
    for exp in expirations:
        try:
            exp_date = datetime.strptime(exp, '%Y-%m-%d')
            days = (exp_date - today).days
            if 7 <= days <= 14:
                target_exps.append({'date': exp, 'days': days})
        except:
            continue
    
    if not target_exps:
        return {'status': 'error', 'message': 'No suitable short-term expirations for iron condor'}
    
    target_exp = min(target_exps, key=lambda x: abs(x['days'] - 10))
    exp_date_str = target_exp['date']
    days_to_exp = target_exp['days']
    
    calls = ticker.option_chain(exp_date_str).calls
    puts = ticker.option_chain(exp_date_str).puts
    
    if calls.empty or puts.empty:
        return {'status': 'error', 'message': 'Empty options chain'}
    
    # Calculate 1 SD using ATM IV
    calls_copy = calls.copy()
    atm_call = calls_copy.iloc[(calls_copy['strike'] - current_price).abs().argsort()[:1]]
    iv = float(atm_call['impliedVolatility'].iloc[0]) if pd.notna(atm_call['impliedVolatility'].iloc[0]) else 0.3
    
    import math
    sd = current_price * iv * math.sqrt(days_to_exp/365)
    
    # Short strikes at 1 SD
    short_call_strike_target = current_price + sd
    short_put_strike_target = current_price - sd
    
    # Find short call
    short_call = calls.iloc[(calls['strike'] - short_call_strike_target).abs().argsort()[:1]].iloc[0]
    short_call_strike = float(short_call['strike'])
    short_call_bid = float(short_call['bid']) if pd.notna(short_call['bid']) and short_call['bid'] > 0 else float(short_call['lastPrice']) * 0.95
    short_call_premium = short_call_bid
    
    # Find long call (5 points higher)
    long_call_strike_target = short_call_strike + 5
    long_call = calls.iloc[(calls['strike'] - long_call_strike_target).abs().argsort()[:1]].iloc[0]
    long_call_strike = float(long_call['strike'])
    long_call_ask = float(long_call['ask']) if pd.notna(long_call['ask']) and long_call['ask'] > 0 else float(long_call['lastPrice'])
    long_call_premium = long_call_ask
    
    # Find short put
    short_put = puts.iloc[(puts['strike'] - short_put_strike_target).abs().argsort()[:1]].iloc[0]
    short_put_strike = float(short_put['strike'])
    short_put_bid = float(short_put['bid']) if pd.notna(short_put['bid']) and short_put['bid'] > 0 else float(short_put['lastPrice']) * 0.95
    short_put_premium = short_put_bid
    
    # Find long put (5 points lower)
    long_put_strike_target = short_put_strike - 5
    long_put = puts.iloc[(puts['strike'] - long_put_strike_target).abs().argsort()[:1]].iloc[0]
    long_put_strike = float(long_put['strike'])
    long_put_ask = float(long_put['ask']) if pd.notna(long_put['ask']) and long_put['ask'] > 0 else float(long_put['lastPrice'])
    long_put_premium = long_put_ask
    
    # Net credit
    net_credit = (short_call_premium + short_put_premium - long_call_premium - long_put_premium)
    credit_per_contract = net_credit * 100
    
    # Max risk is width of widest spread minus credit
    call_spread_width = long_call_strike - short_call_strike
    put_spread_width = short_put_strike - long_put_strike
    max_width = max(call_spread_width, put_spread_width)
    max_risk = (max_width - net_credit) * 100
    
    contracts = max(1, int(budget / max_risk)) if max_risk > 0 else 1
    total_credit = credit_per_contract * contracts
    total_risk = max_risk * contracts
    
    return {
        'status': 'success',
        'symbol': symbol,
        'current_price': round(current_price, 2),
        'strategy': 'Iron Condor',
        'iv_rank': iv_rank,
        'vix': vix,
        'regime': regime,
        'trend_regime': trend_regime,
        'trend_regime_desc': trend_regime_desc,
        'rationale': rationale,
        'expiration': exp_date_str,
        'days_to_exp': days_to_exp,
        'short_call_strike': short_call_strike,
        'long_call_strike': long_call_strike,
        'short_put_strike': short_put_strike,
        'long_put_strike': long_put_strike,
        'net_credit': round(net_credit, 2),
        'credit_per_contract': round(credit_per_contract, 2),
        'contracts': contracts,
        'total_credit': round(total_credit, 2),
        'max_risk': round(total_risk, 2),
        'budget': budget,
        'signal_score': analysis.get('signal_score', 50) if analysis else 50,
    }


def _build_long_call(ticker, symbol, current_price, budget, iv_rank, vix, regime, trend_regime, trend_regime_desc, analysis):
    """Build Long Call strategy."""
    rationale = 'Low IV environment — buy premium, don\'t sell it. Spread caps upside on a breakout setup.'
    today = datetime.today()
    expirations = ticker.options
    
    # Find 45 DTE expiration
    target_exps = []
    for exp in expirations:
        try:
            exp_date = datetime.strptime(exp, '%Y-%m-%d')
            days = (exp_date - today).days
            if days >= 40:
                target_exps.append({'date': exp, 'days': days})
        except:
            continue
    
    if not target_exps:
        return {'status': 'error', 'message': 'No suitable expirations found'}
    
    target_exp = min(target_exps, key=lambda x: abs(x['days'] - 45))
    exp_date_str = target_exp['date']
    days_to_exp = target_exp['days']
    
    chain = ticker.option_chain(exp_date_str).calls
    if chain.empty:
        return {'status': 'error', 'message': 'Empty options chain'}
    
    # Get ATM IV for SD calculation
    chain = chain.copy()
    atm_option = chain.iloc[(chain['strike'] - current_price).abs().argsort()[:1]]
    iv = float(atm_option['impliedVolatility'].iloc[0]) if pd.notna(atm_option['impliedVolatility'].iloc[0]) else 0.3
    
    # Calculate 1 SD strike
    import math
    sd = current_price * iv * math.sqrt(45/365)
    target_strike = current_price + sd
    
    # Find closest strike
    option = chain.iloc[(chain['strike'] - target_strike).abs().argsort()[:1]].iloc[0]
    strike = float(option['strike'])
    ask = float(option['ask']) if pd.notna(option['ask']) and option['ask'] > 0 else float(option['lastPrice'])
    bid = float(option['bid']) if pd.notna(option['bid']) else ask * 0.95
    mid = (ask + bid) / 2
    delta = calculate_approx_delta(strike, current_price, days_to_exp)
    volume = int(option['volume']) if pd.notna(option['volume']) else 0
    oi = int(option['openInterest']) if pd.notna(option['openInterest']) else 0
    
    contracts = max(1, int(budget / (mid * 100)))
    total_cost = mid * 100 * contracts
    
    return {
        'status': 'success',
        'symbol': symbol,
        'current_price': round(current_price, 2),
        'strategy': 'Long Call',
        'iv_rank': iv_rank,
        'vix': vix,
        'regime': regime,
        'trend_regime': trend_regime,
        'trend_regime_desc': trend_regime_desc,
        'rationale': rationale,
        'expiration': exp_date_str,
        'days_to_exp': days_to_exp,
        'buy_strike': strike,
        'buy_premium': round(mid, 2),
        'buy_delta': delta,
        'buy_iv': round(iv * 100, 1),
        'buy_volume': volume,
        'buy_oi': oi,
        'contracts': contracts,
        'total_cost': round(total_cost, 2),
        'max_loss_total': round(total_cost, 2),
        'max_gain_total': 'Unlimited',
        'budget': budget,
        'signal_score': analysis.get('signal_score', 50) if analysis else 50,
    }


def _build_cash_secured_put(ticker, symbol, current_price, budget, iv_rank, vix, regime, trend_regime, trend_regime_desc, analysis):
    """Build Cash-Secured Put strategy."""
    rationale = 'Elevated IV — sell rich premium. Get paid to wait for pullback to your entry price.'
    today = datetime.today()
    expirations = ticker.options
    
    # Find 30-45 DTE
    target_exps = []
    for exp in expirations:
        try:
            exp_date = datetime.strptime(exp, '%Y-%m-%d')
            days = (exp_date - today).days
            if 30 <= days <= 45:
                target_exps.append({'date': exp, 'days': days})
        except:
            continue
    
    if not target_exps:
        return {'status': 'error', 'message': 'No suitable expirations'}
    
    target_exp = min(target_exps, key=lambda x: abs(x['days'] - 37))
    exp_date_str = target_exp['date']
    days_to_exp = target_exp['days']
    
    chain = ticker.option_chain(exp_date_str).puts
    if chain.empty:
        return {'status': 'error', 'message': 'Empty puts chain'}
    
    # Find ATM put
    chain = chain.copy()
    option = chain.iloc[(chain['strike'] - current_price).abs().argsort()[:1]].iloc[0]
    strike = float(option['strike'])
    bid = float(option['bid']) if pd.notna(option['bid']) and option['bid'] > 0 else float(option['lastPrice']) * 0.95
    ask = float(option['ask']) if pd.notna(option['ask']) else bid * 1.05
    mid = (ask + bid) / 2
    delta = calculate_approx_delta(strike, current_price, days_to_exp, is_call=False)
    iv = float(option['impliedVolatility']) if pd.notna(option['impliedVolatility']) else None
    volume = int(option['volume']) if pd.notna(option['volume']) else 0
    oi = int(option['openInterest']) if pd.notna(option['openInterest']) else 0
    
    premium_collected = mid * 100
    effective_entry = strike - mid
    breakeven = strike - mid
    
    return {
        'status': 'success',
        'symbol': symbol,
        'current_price': round(current_price, 2),
        'strategy': 'Cash-Secured Put',
        'iv_rank': iv_rank,
        'vix': vix,
        'regime': regime,
        'trend_regime': trend_regime,
        'trend_regime_desc': trend_regime_desc,
        'rationale': rationale,
        'expiration': exp_date_str,
        'days_to_exp': days_to_exp,
        'sell_strike': strike,
        'sell_premium': round(mid, 2),
        'sell_delta': delta,
        'sell_iv': round(iv * 100, 1) if iv else None,
        'sell_volume': volume,
        'sell_oi': oi,
        'premium_collected': round(premium_collected, 2),
        'effective_entry': round(effective_entry, 2),
        'breakeven': round(breakeven, 2),
        'max_gain_total': round(premium_collected, 2),
        'max_loss_total': round((strike * 100) - premium_collected, 2),
        'budget': budget,
        'signal_score': analysis.get('signal_score', 50) if analysis else 50,
    }


def _build_pmcc(ticker, symbol, current_price, budget, iv_rank, vix, regime, trend_regime, trend_regime_desc, analysis):
    """Build Poor Man's Covered Call (diagonal spread)."""
    rationale = 'Moderate IV — diagonal gives long delta exposure with reduced capital vs. shares, and short leg offsets cost.'
    today = datetime.today()
    expirations = ticker.options
    
    # Find long leg: 90+ DTE
    long_exps = []
    for exp in expirations:
        try:
            exp_date = datetime.strptime(exp, '%Y-%m-%d')
            days = (exp_date - today).days
            if days >= 90:
                long_exps.append({'date': exp, 'days': days})
        except:
            continue
    
    if not long_exps:
        return {'status': 'error', 'message': 'No long-dated expirations'}
    
    long_exp = min(long_exps, key=lambda x: abs(x['days'] - 120))
    long_exp_str = long_exp['date']
    long_days = long_exp['days']
    
    # Find short leg: 30-45 DTE
    short_exps = []
    for exp in expirations:
        try:
            exp_date = datetime.strptime(exp, '%Y-%m-%d')
            days = (exp_date - today).days
            if 30 <= days <= 45:
                short_exps.append({'date': exp, 'days': days})
        except:
            continue
    
    if not short_exps:
        return {'status': 'error', 'message': 'No short-dated expirations'}
    
    short_exp = min(short_exps, key=lambda x: abs(x['days'] - 37))
    short_exp_str = short_exp['date']
    short_days = short_exp['days']
    
    # Long leg: Deep ITM (0.80+ delta)
    long_chain = ticker.option_chain(long_exp_str).calls
    if long_chain.empty:
        return {'status': 'error', 'message': 'Empty long chain'}
    
    long_chain = long_chain.copy()
    long_chain['approx_delta'] = long_chain['strike'].apply(lambda s: calculate_approx_delta(s, current_price, long_days))
    long_candidates = long_chain[long_chain['approx_delta'] >= 0.75]
    
    if long_candidates.empty:
        long_option = long_chain.iloc[(long_chain['strike'] - current_price * 0.85).abs().argsort()[:1]].iloc[0]
    else:
        long_option = long_candidates.iloc[(long_candidates['approx_delta'] - 0.80).abs().argsort()[:1]].iloc[0]
    
    long_strike = float(long_option['strike'])
    long_ask = float(long_option['ask']) if pd.notna(long_option['ask']) and long_option['ask'] > 0 else float(long_option['lastPrice'])
    long_bid = float(long_option['bid']) if pd.notna(long_option['bid']) else long_ask * 0.95
    long_mid = (long_ask + long_bid) / 2
    long_delta = calculate_approx_delta(long_strike, current_price, long_days)
    long_iv = float(long_option['impliedVolatility']) if pd.notna(long_option['impliedVolatility']) else None
    long_volume = int(long_option['volume']) if pd.notna(long_option['volume']) else 0
    long_oi = int(long_option['openInterest']) if pd.notna(long_option['openInterest']) else 0
    
    # Short leg: OTM (0.30 delta)
    short_chain = ticker.option_chain(short_exp_str).calls
    if short_chain.empty:
        return {'status': 'error', 'message': 'Empty short chain'}
    
    short_chain = short_chain.copy()
    short_chain['approx_delta'] = short_chain['strike'].apply(lambda s: calculate_approx_delta(s, current_price, short_days))
    short_candidates = short_chain[(short_chain['approx_delta'] >= 0.25) & (short_chain['approx_delta'] <= 0.35)]
    
    if short_candidates.empty:
        short_option = short_chain.iloc[(short_chain['strike'] - current_price * 1.05).abs().argsort()[:1]].iloc[0]
    else:
        short_option = short_candidates.iloc[(short_candidates['approx_delta'] - 0.30).abs().argsort()[:1]].iloc[0]
    
    short_strike = float(short_option['strike'])
    short_bid = float(short_option['bid']) if pd.notna(short_option['bid']) and short_option['bid'] > 0 else float(short_option['lastPrice']) * 0.95
    short_ask = float(short_option['ask']) if pd.notna(short_option['ask']) else short_bid * 1.05
    short_mid = (short_ask + short_bid) / 2
    short_delta = calculate_approx_delta(short_strike, current_price, short_days)
    short_iv = float(short_option['impliedVolatility']) if pd.notna(short_option['impliedVolatility']) else None
    short_volume = int(short_option['volume']) if pd.notna(short_option['volume']) else 0
    short_oi = int(short_option['openInterest']) if pd.notna(short_option['openInterest']) else 0
    
    net_debit = long_mid - short_mid
    contracts = max(1, int(budget / (net_debit * 100)))
    total_cost = net_debit * 100 * contracts
    max_profit = (short_strike - long_strike - net_debit) * 100 * contracts
    
    return {
        'status': 'success',
        'symbol': symbol,
        'current_price': round(current_price, 2),
        'strategy': 'Poor Man\'s Covered Call',
        'iv_rank': iv_rank,
        'vix': vix,
        'regime': regime,
        'trend_regime': trend_regime,
        'trend_regime_desc': trend_regime_desc,
        'rationale': rationale,
        'long_expiration': long_exp_str,
        'long_days_to_exp': long_days,
        'short_expiration': short_exp_str,
        'short_days_to_exp': short_days,
        'buy_strike': long_strike,
        'buy_premium': round(long_mid, 2),
        'buy_delta': long_delta,
        'buy_iv': round(long_iv * 100, 1) if long_iv else None,
        'buy_volume': long_volume,
        'buy_oi': long_oi,
        'sell_strike': short_strike,
        'sell_premium': round(short_mid, 2),
        'sell_delta': short_delta,
        'sell_iv': round(short_iv * 100, 1) if short_iv else None,
        'sell_volume': short_volume,
        'sell_oi': short_oi,
        'net_debit': round(net_debit, 2),
        'contracts': contracts,
        'total_cost': round(total_cost, 2),
        'max_gain_total': round(max_profit, 2) if max_profit > 0 else 'Variable',
        'max_loss_total': round(total_cost, 2),
        'budget': budget,
        'signal_score': analysis.get('signal_score', 50) if analysis else 50,
    }
    """Build Long Call strategy."""
    today = datetime.today()
    expirations = ticker.options
    
    # Find 45 DTE expiration
    target_exps = []
    for exp in expirations:
        try:
            exp_date = datetime.strptime(exp, '%Y-%m-%d')
            days = (exp_date - today).days
            if days >= 40:
                target_exps.append({'date': exp, 'days': days})
        except:
            continue
    
    if not target_exps:
        return {'status': 'error', 'message': 'No suitable expirations found'}
    
    target_exp = min(target_exps, key=lambda x: abs(x['days'] - 45))
    exp_date_str = target_exp['date']
    days_to_exp = target_exp['days']
    
    chain = ticker.option_chain(exp_date_str).calls
    if chain.empty:
        return {'status': 'error', 'message': 'Empty options chain'}
    
    # Get ATM IV for SD calculation
    chain = chain.copy()
    atm_option = chain.iloc[(chain['strike'] - current_price).abs().argsort()[:1]]
    iv = float(atm_option['impliedVolatility'].iloc[0]) if pd.notna(atm_option['impliedVolatility'].iloc[0]) else 0.3
    
    # Calculate 1 SD strike
    import math
    sd = current_price * iv * math.sqrt(45/365)
    target_strike = current_price + sd
    
    # Find closest strike
    option = chain.iloc[(chain['strike'] - target_strike).abs().argsort()[:1]].iloc[0]
    strike = float(option['strike'])
    ask = float(option['ask']) if pd.notna(option['ask']) and option['ask'] > 0 else float(option['lastPrice'])
    bid = float(option['bid']) if pd.notna(option['bid']) else ask * 0.95
    mid = (ask + bid) / 2
    delta = calculate_approx_delta(strike, current_price, days_to_exp)
    volume = int(option['volume']) if pd.notna(option['volume']) else 0
    oi = int(option['openInterest']) if pd.notna(option['openInterest']) else 0
    
    contracts = max(1, int(budget / (mid * 100)))
    total_cost = mid * 100 * contracts
    
    return {
        'status': 'success',
        'symbol': symbol,
        'current_price': round(current_price, 2),
        'strategy': 'Long Call',
        'iv_rank': iv_rank,
        'vix': vix,
        'regime': regime,
        'rationale': rationale,
        'expiration': exp_date_str,
        'days_to_exp': days_to_exp,
        'buy_strike': strike,
        'buy_premium': round(mid, 2),
        'buy_delta': delta,
        'buy_iv': round(iv * 100, 1),
        'buy_volume': volume,
        'buy_oi': oi,
        'contracts': contracts,
        'total_cost': round(total_cost, 2),
        'max_loss_total': round(total_cost, 2),
        'max_gain_total': 'Unlimited',
        'budget': budget,
        'signal_score': analysis.get('signal_score', 50) if analysis else 50,
    }


def calculate_expected_move(symbol, current_price, pattern_target=None):
    """Calculate expected move analysis using IV from options chain."""
    try:
        ticker = yf.Ticker(symbol)
        expirations = ticker.options
        if not expirations:
            return {'status': 'no_data'}
        
        # Get ATM IV from nearest expiration >= 30 days
        today = datetime.today()
        target_exp = None
        for exp in expirations:
            try:
                exp_date = datetime.strptime(exp, '%Y-%m-%d')
                days = (exp_date - today).days
                if days >= 30:
                    target_exp = {'date': exp, 'days': days}
                    break
            except:
                continue
        
        if not target_exp:
            return {'status': 'no_data'}
        
        chain = ticker.option_chain(target_exp['date']).calls
        if chain.empty:
            return {'status': 'no_data'}
        
        # Get ATM IV
        atm_option = chain.iloc[(chain['strike'] - current_price).abs().argsort()[:1]]
        iv = float(atm_option['impliedVolatility'].iloc[0]) if pd.notna(atm_option['impliedVolatility'].iloc[0]) else None
        
        if not iv:
            return {'status': 'no_data'}
        
        import math
        
        # Expected moves
        move_1w = current_price * iv * math.sqrt(5/252)
        move_1m = current_price * iv * math.sqrt(21/252)
        move_45d = current_price * iv * math.sqrt(45/252)
        
        # Delta-based strikes
        dte = target_exp['days']
        delta_strikes = []
        for target_delta in [0.30, 0.20, 0.15, 0.10]:
            # Find strike closest to this delta
            chain_copy = chain.copy()
            chain_copy['approx_delta'] = chain_copy['strike'].apply(
                lambda s: calculate_approx_delta(s, current_price, dte)
            )
            closest = chain_copy.iloc[(chain_copy['approx_delta'] - target_delta).abs().argsort()[:1]]
            if not closest.empty:
                strike = float(closest['strike'].iloc[0])
                actual_delta = float(closest['approx_delta'].iloc[0])
                prob_otm = (1 - actual_delta) * 100
                distance_pct = ((strike - current_price) / current_price) * 100
                delta_strikes.append({
                    'delta': target_delta,
                    'strike': round(strike, 2),
                    'prob_otm': round(prob_otm, 1),
                    'distance_pct': round(distance_pct, 1)
                })
        
        # Pattern target comparison
        target_assessment = None
        if pattern_target:
            target_pct = ((pattern_target - current_price) / current_price) * 100
            upper_bound = current_price + move_45d
            upper_pct = ((upper_bound - current_price) / current_price) * 100
            
            if pattern_target <= upper_bound:
                assessment = 'WITHIN'
                note = None
            else:
                assessment = 'EXCEEDS'
                note = 'Target exceeds expected move — consider longer dated options (60-90 DTE) to give the setup time to play out.'
            
            target_assessment = {
                'target': round(pattern_target, 2),
                'target_pct': round(target_pct, 1),
                'upper_bound': round(upper_bound, 2),
                'upper_pct': round(upper_pct, 1),
                'assessment': assessment,
                'note': note
            }
        
        return {
            'status': 'success',
            'iv': round(iv * 100, 1),
            'move_1w': round(move_1w, 2),
            'move_1m': round(move_1m, 2),
            'move_45d': round(move_45d, 2),
            'delta_strikes': delta_strikes,
            'target_assessment': target_assessment,
            'expiration': target_exp['date'],
            'dte': dte
        }
    except:
        return {'status': 'no_data'}


# ════════════════════════════════════════════════════════════════
# DCF VALUATION
# ════════════════════════════════════════════════════════════════

def calculate_dcf_value(symbol):
    """
    Calculate intrinsic value using DCF model with tiered growth, scenarios, adjusted discount, and cross-checks.
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info

        # Get free cash flow
        cashflow = ticker.cashflow
        if cashflow is None or cashflow.empty:
            return {'status': 'no_data', 'dcf_value': None, 'margin': None}

        # Find Free Cash Flow
        fcf = None
        fcf_history = []

        for row_name in ['Free Cash Flow', 'FreeCashFlow']:
            if row_name in cashflow.index:
                fcf_row = cashflow.loc[row_name]
                fcf = fcf_row.iloc[0] if len(fcf_row) > 0 else None
                fcf_history = fcf_row.tolist()[:4]  # Last 4 years
                break

        if fcf is None:
            # Try to calculate: Operating Cash Flow - CapEx
            ocf = None
            capex = None
            for row_name in ['Operating Cash Flow', 'Total Cash From Operating Activities']:
                if row_name in cashflow.index:
                    ocf = cashflow.loc[row_name].iloc[0]
                    break
            for row_name in ['Capital Expenditure', 'Capital Expenditures']:
                if row_name in cashflow.index:
                    capex = abs(cashflow.loc[row_name].iloc[0])
                    break
            if ocf is not None and capex is not None:
                fcf = ocf - capex
            else:
                return {'status': 'no_fcf', 'dcf_value': None, 'margin': None}

        if fcf is None or fcf <= 0:
            return {'status': 'negative_fcf', 'dcf_value': '-FCF', 'margin': None, 'fcf': fcf}

        # Get shares outstanding
        shares = info.get('sharesOutstanding', None)
        if not shares:
            return {'status': 'no_shares', 'dcf_value': None, 'margin': None}

        # Get beta for adjusted discount
        beta = info.get('beta', 1.0)

        # Adjusted discount rate: base 8% + beta adjustment
        base_discount = 0.08
        discount_adjustment = (beta - 1.0) * 0.02  # +2% per unit beta above 1
        discount_rate = max(0.06, base_discount + discount_adjustment)

        # Tiered growth rates: years 1-2: 15%, 3-4: 10%, 5: 5%
        growth_rates = [0.15, 0.15, 0.10, 0.10, 0.05]
        terminal_growth = 0.025
        years = 5

        # Scenarios
        scenarios = {
            'bull': {'growth_mult': 1.2, 'discount_mult': 0.8, 'label': 'Bull Case'},
            'base': {'growth_mult': 1.0, 'discount_mult': 1.0, 'label': 'Base Case'},
            'bear': {'growth_mult': 0.7, 'discount_mult': 1.2, 'label': 'Bear Case'}
        }

        results = {}
        for scenario, params in scenarios.items():
            # Adjust growth rates for scenario
            scenario_growth = [g * params['growth_mult'] for g in growth_rates]
            scenario_discount = discount_rate * params['discount_mult']

            # Project FCF
            projected_fcf = []
            current_fcf = fcf
            for year in range(1, years + 1):
                growth = scenario_growth[year-1]
                current_fcf *= (1 + growth)
                discounted = current_fcf / ((1 + scenario_discount) ** year)
                projected_fcf.append(discounted)

            # Terminal
            terminal_fcf = current_fcf * (1 + terminal_growth)
            terminal_value = terminal_fcf / (scenario_discount - terminal_growth)
            discounted_terminal = terminal_value / ((1 + scenario_discount) ** years)

            total_value = sum(projected_fcf) + discounted_terminal
            intrinsic_per_share = total_value / shares

            results[scenario] = {
                'dcf_value': round(intrinsic_per_share, 2),
                'growth_rates': [round(g*100,1) for g in scenario_growth],
                'discount_rate': round(scenario_discount * 100, 1),
                'terminal_growth': round(terminal_growth * 100, 1)
            }

        # Current price
        current_price = info.get('currentPrice', info.get('regularMarketPrice', None))

        # Margin for base case
        base_dcf = results['base']['dcf_value']
        margin = None
        if current_price:
            margin = round((base_dcf - current_price) / current_price * 100, 1)

        # Cross-checks
        # PEG
        eps = info.get('trailingEPS', None)
        peg = None
        if eps and eps > 0:
            growth_for_peg = growth_rates[0]  # use first year growth
            peg = current_price / (eps * growth_for_peg) if current_price else None

        # EV/Revenue
        revenue = info.get('totalRevenue', None)
        market_cap = info.get('marketCap', 0)
        total_debt = info.get('totalDebt', 0)
        cash = info.get('totalCash', 0)
        ev = market_cap + total_debt - cash if market_cap else None
        ev_rev = ev / revenue if ev and revenue and revenue > 0 else None

        # Cross-check analysis
        cross_checks = {}
        if peg:
            if peg < 1.5:
                cross_checks['peg'] = 'Undervalued (PEG < 1.5)'
            elif peg < 2.5:
                cross_checks['peg'] = 'Fairly valued'
            else:
                cross_checks['peg'] = 'Overvalued (PEG > 2.5)'
        if ev_rev:
            industry_avg_ev_rev = 5  # placeholder, in reality look up industry avg
            if ev_rev < industry_avg_ev_rev * 0.8:
                cross_checks['ev_rev'] = 'Potentially undervalued'
            elif ev_rev > industry_avg_ev_rev * 1.2:
                cross_checks['ev_rev'] = 'Potentially overvalued'
            else:
                cross_checks['ev_rev'] = 'Fairly valued'

        # Extract base case values for display
        base_scenario = results.get('base', {})
        base_dcf_value = base_scenario.get('dcf_value')
        base_growth_rates = base_scenario.get('growth_rates', [])
        avg_growth_rate = round(sum(base_growth_rates) / len(base_growth_rates), 1) if base_growth_rates else None
        base_discount_rate = base_scenario.get('discount_rate')
        base_terminal_growth = base_scenario.get('terminal_growth')

        return {
            'status': 'success',
            'scenarios': results,
            'dcf_value': base_dcf_value,
            'growth_rate': avg_growth_rate,
            'discount_rate': base_discount_rate,
            'terminal_growth': base_terminal_growth,
            'margin': margin,
            'fcf': fcf,
            'fcf_fmt': format_market_cap(fcf),
            'shares': shares,
            'current_price': current_price,
            'beta': beta,
            'cross_checks': cross_checks,
            'peg': round(peg, 2) if peg else None,
            'ev_rev': round(ev_rev, 2) if ev_rev else None
        }

    except Exception as e:
        return {'status': 'error', 'dcf_value': None, 'margin': None, 'error': str(e)}


def get_social_sentiment(symbol):
    """
    Social sentiment placeholder - removed due to API requirements.
    """
    return None


# ════════════════════════════════════════════════════════════════
# PATTERN DETECTION: CUP & HANDLE
# ════════════════════════════════════════════════════════════════

def detect_cup_and_handle(df, min_cup_days=20, max_cup_days=130):
    """
    Detect cup and handle pattern with U-shape and symmetry scoring.
    """
    if len(df) < max_cup_days + 30:
        return None

    closes = df['Close'].values
    highs = df['High'].values
    lows = df['Low'].values
    volumes = df['Volume'].values

    order = 10
    local_max_idx = argrelextrema(closes, np.greater_equal, order=order)[0]
    local_min_idx = argrelextrema(closes, np.less_equal, order=order)[0]

    if len(local_max_idx) < 2 or len(local_min_idx) < 1:
        return None

    lookback = min(len(closes), max_cup_days + 50)
    recent_max = [i for i in local_max_idx if i >= len(closes) - lookback]
    recent_min = [i for i in local_min_idx if i >= len(closes) - lookback]

    if len(recent_max) < 2 or len(recent_min) < 1:
        return None

    best_pattern = None
    best_score = 0

    for i, left_rim_idx in enumerate(recent_max[:-1]):
        for right_rim_idx in recent_max[i+1:]:
            cup_length = right_rim_idx - left_rim_idx

            if cup_length < min_cup_days or cup_length > max_cup_days:
                continue

            bottom_candidates = [
                m for m in recent_min if left_rim_idx < m < right_rim_idx]
            if not bottom_candidates:
                continue

            bottom_idx = min(bottom_candidates, key=lambda x: closes[x])

            left_rim_price = closes[left_rim_idx]
            right_rim_price = closes[right_rim_idx]
            bottom_price = closes[bottom_idx]

            avg_rim = (left_rim_price + right_rim_price) / 2
            cup_depth_pct = (avg_rim - bottom_price) / avg_rim * 100

            if cup_depth_pct < 12 or cup_depth_pct > 35:
                continue

            rim_diff = abs(left_rim_price - right_rim_price) / avg_rim * 100
            if rim_diff > 5:
                continue

            # Calculate U-shape score
            cup_prices = closes[left_rim_idx:right_rim_idx+1]
            cup_mid = len(cup_prices) // 2
            left_half = cup_prices[:cup_mid]
            right_half = cup_prices[cup_mid:]

            if len(left_half) > 2 and len(right_half) > 2:
                left_slope = float(
                    abs(np.polyfit(range(len(left_half)), left_half.flatten(), 1)[0]))
                right_slope = float(
                    abs(np.polyfit(range(len(right_half)), right_half.flatten(), 1)[0]))
                u_shape_score = 1 / (1 + (left_slope + right_slope) * 10)
            else:
                u_shape_score = 0.5

            # Symmetry
            left_days = bottom_idx - left_rim_idx
            right_days = right_rim_idx - bottom_idx
            symmetry = 1 - abs(left_days - right_days) / cup_length
            symmetry_pct = symmetry * 100

            # Handle check
            handle_start = right_rim_idx
            handle_data = closes[handle_start:]
            handle_volumes = volumes[handle_start:] if handle_start < len(volumes) else [
            ]

            if len(handle_data) < 5:
                continue

            handle_low = min(handle_data)
            handle_high = max(handle_data)
            handle_decline = (right_rim_price - handle_low) / \
                right_rim_price * 100

            if handle_decline < 2 or handle_decline > 15:
                continue

            # Handle volume contraction check
            cup_avg_vol = np.mean(volumes[left_rim_idx:right_rim_idx])
            handle_avg_vol = np.mean(handle_volumes) if len(
                handle_volumes) > 0 else cup_avg_vol
            handle_vol_contraction = handle_avg_vol < cup_avg_vol * 0.8

            score = 100 - abs(cup_depth_pct - 25) - \
                rim_diff - abs(handle_decline - 8)
            score += u_shape_score * 10 + symmetry * 10

            if score > best_score:
                best_score = score
                best_pattern = {
                    'left_rim_idx': int(left_rim_idx),
                    'right_rim_idx': int(right_rim_idx),
                    'bottom_idx': int(bottom_idx),
                    'left_rim_price': float(np.asarray(left_rim_price).flatten()[0]) if hasattr(left_rim_price, '__iter__') else float(left_rim_price),
                    'right_rim_price': float(np.asarray(right_rim_price).flatten()[0]) if hasattr(right_rim_price, '__iter__') else float(right_rim_price),
                    'bottom_price': float(np.asarray(bottom_price).flatten()[0]) if hasattr(bottom_price, '__iter__') else float(bottom_price),
                    'cup_depth_pct': float(np.asarray(cup_depth_pct).flatten()[0]) if hasattr(cup_depth_pct, '__iter__') else float(cup_depth_pct),
                    'cup_length_days': int(cup_length),
                    'handle_low': float(np.asarray(handle_low).flatten()[0]) if hasattr(handle_low, '__iter__') else float(handle_low),
                    'handle_high': float(np.asarray(handle_high).flatten()[0]) if hasattr(handle_high, '__iter__') else float(handle_high),
                    'handle_decline_pct': float(np.asarray(handle_decline).flatten()[0]) if hasattr(handle_decline, '__iter__') else float(handle_decline),
                    'handle_days': len(handle_data),
                    'u_shape_score': round(float(u_shape_score), 3),
                    'symmetry_pct': round(float(symmetry_pct), 1),
                    'handle_vol_contraction': bool(handle_vol_contraction),
                    'score': float(np.asarray(score).flatten()[0]) if hasattr(score, '__iter__') else float(score)
                }

    return best_pattern


# ════════════════════════════════════════════════════════════════
# PATTERN DETECTION: ASCENDING TRIANGLE
# ════════════════════════════════════════════════════════════════

def detect_ascending_triangle(df, lookback=60):
    """
    Detect ascending triangle: flat resistance + rising support.
    Returns dict with resistance, support slope, target if found.
    """
    if len(df) < lookback:
        return None

    recent = df.tail(lookback)
    highs = recent['High'].values
    lows = recent['Low'].values
    closes = recent['Close'].values
    indices = np.arange(len(recent))

    # Find resistance (multiple touches at similar high)
    order = 5
    local_highs_idx = argrelextrema(highs, np.greater_equal, order=order)[0]

    if len(local_highs_idx) < 3:
        return None

    high_prices = highs[local_highs_idx]
    resistance = np.mean(high_prices[-5:])

    # Check if highs are flat (within 3% of each other)
    high_range = (max(high_prices[-5:]) -
                  min(high_prices[-5:])) / resistance * 100
    if high_range > 3:
        return None

    # Check for rising lows (ascending support)
    local_lows_idx = argrelextrema(lows, np.less_equal, order=order)[0]
    if len(local_lows_idx) < 3:
        return None

    low_prices = lows[local_lows_idx]

    # Linear regression on lows
    if len(local_lows_idx) >= 3:
        slope, intercept, r_value, _, _ = linregress(
            local_lows_idx, low_prices)

        # Slope should be positive (rising lows) with decent fit
        if slope > 0 and r_value > 0.5:
            # Calculate target (height of triangle added to breakout)
            triangle_height = resistance - low_prices[0]
            target = resistance + triangle_height

            return {
                'resistance': round(resistance, 2),
                'support_slope': round(slope, 4),
                'target': round(target, 2),
                'r_squared': round(r_value ** 2, 3),
                'touches': len(local_highs_idx),
                'local_highs_idx': local_highs_idx.tolist(),
                'local_lows_idx': local_lows_idx.tolist(),
            }

    return None


# ════════════════════════════════════════════════════════════════
# PATTERN DETECTION: BULL FLAG / PENNANT
# ════════════════════════════════════════════════════════════════

def detect_bull_flag(df, lookback=40):
    """
    Detect bull flag: strong pole (surge) + consolidation.
    Returns dict with pole gain, flag details if found.
    """
    if len(df) < lookback:
        return None

    recent = df.tail(lookback)
    closes = recent['Close'].values
    highs = recent['High'].values
    lows = recent['Low'].values

    # Find the pole: sharp rise in first portion
    pole_period = lookback // 2
    pole_data = closes[:pole_period]

    if len(pole_data) < 5:
        return None

    pole_low_idx = np.argmin(pole_data[:len(pole_data)//2])
    pole_low = pole_data[pole_low_idx]
    pole_high_idx = np.argmax(pole_data)
    pole_high = pole_data[pole_high_idx]

    # Pole should go up (low before high)
    if pole_low_idx >= pole_high_idx:
        return None

    pole_gain = (pole_high - pole_low) / pole_low * 100

    # Pole should be significant (at least 10% gain)
    if pole_gain < 10:
        return None

    # Flag portion: consolidation
    flag_data = closes[pole_period:]
    flag_highs = highs[pole_period:]
    flag_lows = lows[pole_period:]

    if len(flag_data) < 5:
        return None

    flag_high = max(flag_highs)
    flag_low = min(flag_lows)
    flag_range = (flag_high - flag_low) / pole_high * 100

    # Flag should be tight (less than 15% range)
    if flag_range > 15:
        return None

    # Flag should not give back more than 50% of pole gains
    flag_pullback = (pole_high - flag_low) / (pole_high - pole_low) * 100
    if flag_pullback > 50:
        return None

    # Calculate flag slope (should be slightly down or flat)
    flag_indices = np.arange(len(flag_data))
    slope, _, _, _, _ = linregress(flag_indices, flag_data)

    # Target: pole height added to breakout
    target = flag_high + (pole_high - pole_low)

    return {
        'pole_gain': round(pole_gain, 1),
        'pole_low': round(pole_low, 2),
        'pole_high': round(pole_high, 2),
        'pole_days': pole_high_idx - pole_low_idx,
        'flag_high': round(flag_high, 2),
        'flag_low': round(flag_low, 2),
        'flag_range_pct': round(flag_range, 1),
        'flag_days': len(flag_data),
        'flag_slope': round(slope, 4),
        'target': round(target, 2),
        'pole_start_idx': pole_low_idx,
        'pole_end_idx': pole_high_idx,
    }


# ════════════════════════════════════════════════════════════════
# PATTERN DETECTION: DOUBLE BOTTOM
# ════════════════════════════════════════════════════════════════

def detect_double_bottom(df, lookback=90, min_gap_days=15, max_gap_days=60):
    """
    Detect double bottom (W pattern): two similar lows with a peak between them.
    Returns dict with pattern details or None if not found.
    """
    if len(df) < lookback:
        return None

    recent = df.tail(lookback)
    closes = recent['Close'].values
    lows = recent['Low'].values

    order = 5
    local_min_idx = argrelextrema(lows, np.less_equal, order=order)[0]
    local_max_idx = argrelextrema(closes, np.greater_equal, order=order)[0]

    if len(local_min_idx) < 2 or len(local_max_idx) < 1:
        return None

    best_pattern = None
    best_score = 0

    for i, first_bottom_idx in enumerate(local_min_idx[:-1]):
        for second_bottom_idx in local_min_idx[i+1:]:
            gap = second_bottom_idx - first_bottom_idx

            if gap < min_gap_days or gap > max_gap_days:
                continue

            # Find peak between bottoms
            peak_candidates = [
                m for m in local_max_idx if first_bottom_idx < m < second_bottom_idx]
            if not peak_candidates:
                continue

            peak_idx = max(peak_candidates, key=lambda x: closes[x])

            first_low = lows[first_bottom_idx]
            second_low = lows[second_bottom_idx]
            peak_price = closes[peak_idx]

            # Bottoms should be within 3% of each other
            bottom_diff_pct = abs(first_low - second_low) / first_low * 100
            if bottom_diff_pct > 3:
                continue

            # Pattern depth (peak to avg bottom) should be 10-30%
            avg_bottom = (first_low + second_low) / 2
            depth_pct = (peak_price - avg_bottom) / avg_bottom * 100
            if depth_pct < 10 or depth_pct > 30:
                continue

            # Current price for breakout check
            current_price = closes[-1]
            breakout_confirmed = current_price > peak_price

            # Calculate target (measured move)
            target = peak_price + (peak_price - avg_bottom)

            # Score based on symmetry and depth
            score = 100 - bottom_diff_pct * 5 - abs(depth_pct - 18)

            if score > best_score:
                best_score = score
                offset = len(df) - lookback
                best_pattern = {
                    'first_bottom_idx': int(first_bottom_idx + offset),
                    'second_bottom_idx': int(second_bottom_idx + offset),
                    'peak_idx': int(peak_idx + offset),
                    'first_low': float(first_low),
                    'second_low': float(second_low),
                    'neckline': float(peak_price),
                    'depth_pct': round(float(depth_pct), 1),
                    'gap_days': int(gap),
                    'breakout_confirmed': bool(breakout_confirmed),
                    'target': round(float(target), 2),
                    # 2% below lower bottom
                    'stop_loss': round(float(min(first_low, second_low) * 0.98), 2),
                    'score': round(float(score), 1)
                }

    return best_pattern


# ════════════════════════════════════════════════════════════════
# CTO LINE (Approximation)
# ════════════════════════════════════════════════════════════════

def calculate_cto_line(df):
    """
    CTO Line Approximation
    Real CTO = cumulative (advances - declines) * volume
    Since we don't have market-wide A/D data, we approximate using:
    - Price direction as advance/decline proxy
    - Volume weighting
    This creates a stock-specific cumulative volume-weighted momentum indicator
    """
    if len(df) < 20:
        return None, None

    closes = df['Close'].values
    volumes = df['Volume'].values

    cto_values = []
    cumulative_cto = 0

    for i in range(1, len(closes)):
        price_change = closes[i] - closes[i - 1]
        direction = 1 if price_change > 0 else (-1 if price_change < 0 else 0)

        # Normalize volume
        lookback = min(20, i)
        avg_volume = np.mean(
            volumes[max(0, i - lookback):i]) if lookback > 0 else volumes[i]
        normalized_volume = volumes[i] / avg_volume if avg_volume > 0 else 1

        cto_component = direction * normalized_volume
        cumulative_cto += cto_component
        cto_values.append(cumulative_cto)

    # Calculate summary
    if len(cto_values) < 20:
        return cto_values, {'status': 'insufficient_data', 'signal': 'Unknown'}

    current_cto = cto_values[-1]
    week_ago_cto = cto_values[-5] if len(cto_values) >= 5 else cto_values[0]
    month_ago_cto = cto_values[-21] if len(cto_values) >= 21 else cto_values[0]

    week_change = current_cto - week_ago_cto
    month_change = current_cto - month_ago_cto

    # Determine overall signal
    if week_change > 2 and month_change > 5:
        signal = 'Strong Bullish'
        strength = 'Strong'
    elif week_change > 1 and month_change > 2:
        signal = 'Bullish'
        strength = 'Moderate'
    elif week_change > 0 and month_change > 0:
        signal = 'Slightly Bullish'
        strength = 'Weak'
    elif week_change < -2 and month_change < -5:
        signal = 'Strong Bearish'
        strength = 'Strong'
    elif week_change < -1 and month_change < -2:
        signal = 'Bearish'
        strength = 'Moderate'
    elif week_change < 0 and month_change < 0:
        signal = 'Slightly Bearish'
        strength = 'Weak'
    else:
        signal = 'Neutral'
        strength = 'Weak'

    # Divergence detection
    price_week_change = (closes[-1] - closes[-5]) / \
        closes[-5] * 100 if len(closes) >= 5 else 0
    divergence = None
    if price_week_change > 2 and week_change < -1:
        divergence = 'Bearish Divergence (price up, CTO down) - Caution'
    elif price_week_change < -2 and week_change > 1:
        divergence = 'Bullish Divergence (price down, CTO up) - Potential reversal'

    summary = {
        'status': 'success',
        'current_cto': round(current_cto, 2),
        'signal': signal,
        'strength': strength,
        'week_change': round(week_change, 2),
        'month_change': round(month_change, 2),
        'divergence': divergence
    }

    return cto_values, summary


# ════════════════════════════════════════════════════════════════
# GOLDEN CROSS DETECTION
# ════════════════════════════════════════════════════════════════

def detect_golden_cross(df, lookback_days=20):
    """
    Detect golden cross (50 SMA crosses above 200 SMA) within lookback period.
    Also detects death cross (50 crosses below 200).
    Returns dict with cross info or None.
    """
    if len(df) < 200:
        return None

    df_calc = df.copy()
    df_calc['SMA50'] = df_calc['Close'].rolling(50).mean()
    df_calc['SMA200'] = df_calc['Close'].rolling(200).mean()

    # Get recent data where both SMAs exist
    df_valid = df_calc.dropna(
        subset=['SMA50', 'SMA200']).tail(lookback_days + 1)

    if len(df_valid) < 2:
        return None

    # Check for crossovers in the lookback period
    golden_cross_date = None
    death_cross_date = None

    for i in range(1, len(df_valid)):
        prev_row = df_valid.iloc[i-1]
        curr_row = df_valid.iloc[i]

        # Golden cross: 50 crosses above 200
        if prev_row['SMA50'] <= prev_row['SMA200'] and curr_row['SMA50'] > curr_row['SMA200']:
            golden_cross_date = df_valid.index[i]

        # Death cross: 50 crosses below 200
        if prev_row['SMA50'] >= prev_row['SMA200'] and curr_row['SMA50'] < curr_row['SMA200']:
            death_cross_date = df_valid.index[i]

    # Current state
    last = df_valid.iloc[-1]
    sma50_above_200 = last['SMA50'] > last['SMA200']

    # Days since cross
    days_since_golden = None
    days_since_death = None

    if golden_cross_date is not None:
        days_since_golden = (df_valid.index[-1] - golden_cross_date).days
    if death_cross_date is not None:
        days_since_death = (df_valid.index[-1] - death_cross_date).days

    return {
        'golden_cross': golden_cross_date is not None,
        'golden_cross_date': golden_cross_date,
        'days_since_golden': days_since_golden,
        'death_cross': death_cross_date is not None,
        'death_cross_date': death_cross_date,
        'days_since_death': days_since_death,
        'sma50_above_200': sma50_above_200,
    }


# ════════════════════════════════════════════════════════════════
# BREAKOUT ANALYSIS
# ════════════════════════════════════════════════════════════════

def check_breakout_criteria(df, pattern, asc_triangle=None, bull_flag=None):
    """
    Validate breakout with comprehensive criteria.
    """
    if pattern is None:
        return None

    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else last

    resistance = pattern['right_rim_price']
    buy_point = resistance * 1.001
    current_price = last['Close']

    # Calculate indicators
    df_calc = df.copy()
    df_calc['SMA50'] = df_calc['Close'].rolling(50).mean()
    df_calc['SMA200'] = df_calc['Close'].rolling(200).mean()
    df_calc['RSI'] = ta.rsi(df_calc['Close'], length=14)

    # ADX
    adx_data = ta.adx(df_calc['High'], df_calc['Low'],
                      df_calc['Close'], length=14)
    if adx_data is not None and 'ADX_14' in adx_data.columns:
        df_calc['ADX'] = adx_data['ADX_14']
    else:
        df_calc['ADX'] = None

    # MACD
    macd = ta.macd(df_calc['Close'], fast=12, slow=26, signal=9)
    if macd is not None:
        df_calc['MACD'] = macd['MACD_12_26_9']
        df_calc['MACD_signal'] = macd['MACDs_12_26_9']
    else:
        df_calc['MACD'] = None
        df_calc['MACD_signal'] = None

    last = df_calc.iloc[-1]
    prev = df_calc.iloc[-2] if len(df_calc) > 1 else last

    # Get values
    sma50 = last['SMA50'] if not pd.isna(last.get('SMA50')) else None
    sma200 = last['SMA200'] if not pd.isna(last.get('SMA200')) else None
    rsi = last['RSI'] if not pd.isna(last.get('RSI')) else None
    adx = last['ADX'] if not pd.isna(last.get('ADX')) else None
    macd_val = last['MACD'] if not pd.isna(last.get('MACD')) else None
    macd_sig = last['MACD_signal'] if not pd.isna(
        last.get('MACD_signal')) else None

    # Volume analysis
    handle_start = pattern['right_rim_idx']
    avg_20_vol = df['Volume'].rolling(20).mean().iloc[-1]
    current_vol = last['Volume']
    vol_ratio = current_vol / avg_20_vol if avg_20_vol > 0 else 1

    # Volume requirement: 2x average for breakout
    volume_requirement = 2.0
    volume_spike = vol_ratio >= volume_requirement

    # Handle volume contraction
    handle_vol_contraction = pattern.get('handle_vol_contraction', False)

    # Calculate stop loss and target
    handle_low = pattern['handle_low']
    stop_loss = handle_low * 0.97

    cup_height = pattern['right_rim_price'] - pattern['bottom_price']
    target = buy_point + cup_height

    risk = buy_point - stop_loss
    reward = target - buy_point
    rr_ratio = reward / risk if risk > 0 else 0

    # Criteria checks with detailed info
    criteria = {
        'breakout_confirmed': {
            'passed': current_price > buy_point,
            'value': f"${current_price:.2f}",
            'requirement': f">${buy_point:.2f}",
        },
        'above_sma50': {
            'passed': current_price > sma50 if sma50 else False,
            'value': f"${sma50:.2f}" if sma50 else 'N/A',
        },
        'above_sma200': {
            'passed': current_price > sma200 if sma200 else False,
            'value': f"${sma200:.2f}" if sma200 else 'N/A',
        },
        'volume_spike': {
            'passed': volume_spike,
            'value': f"{vol_ratio:.2f}x",
            'requirement': f"(req: {volume_requirement}x)",
        },
        'handle_vol_contraction': {
            'passed': handle_vol_contraction,
            'value': 'Yes' if handle_vol_contraction else 'No',
        },
        'macd_bullish': {
            'passed': (macd_val > macd_sig) if (macd_val and macd_sig) else False,
            'value': f"{macd_val:.3f}" if macd_val else 'N/A',
        },
        'adx_strong': {
            'passed': adx > 25 if adx else False,
            'value': f"{adx:.1f}" if adx else 'N/A',
            'requirement': '(>25)',
        },
        'rsi_healthy': {
            'passed': 50 <= rsi <= 70 if rsi else False,
            'value': f"{rsi:.1f}" if rsi else 'N/A',
            'requirement': '(50-70)',
        },
    }

    # Detect golden cross
    golden_cross_info = detect_golden_cross(df, lookback_days=20)

    # Signal score
    signal_score = sum([
        criteria['breakout_confirmed']['passed'] * 25,
        criteria['above_sma50']['passed'] * 15,
        criteria['above_sma200']['passed'] * 15,
        criteria['rsi_healthy']['passed'] * 10,
        criteria['volume_spike']['passed'] * 15,
        criteria['macd_bullish']['passed'] * 10,
        criteria['adx_strong']['passed'] * 5,
        criteria['handle_vol_contraction']['passed'] * 5,
    ])

    # Bonus for recent golden cross
    if golden_cross_info and golden_cross_info['golden_cross']:
        signal_score += 5

    # Status
    if criteria['breakout_confirmed']['passed'] and criteria['above_sma50']['passed'] and criteria['above_sma200']['passed']:
        if signal_score >= 75:
            status = "STRONG BUY"
        elif signal_score >= 55:
            status = "BUY"
        else:
            status = "WATCH"
    elif not criteria['breakout_confirmed']['passed'] and current_price > resistance * 0.97:
        status = "FORMING - NEAR BREAKOUT"
    elif not criteria['breakout_confirmed']['passed']:
        status = "FORMING"
    else:
        status = "WATCH"

    return {
        'buy_point': round(buy_point, 2),
        'current_price': round(current_price, 2),
        'resistance': round(resistance, 2),
        'sma50': round(sma50, 2) if sma50 else None,
        'sma200': round(sma200, 2) if sma200 else None,
        'rsi': round(rsi, 1) if rsi else None,
        'adx': round(adx, 1) if adx else None,
        'volume_ratio': round(vol_ratio, 2),
        'stop_loss': round(stop_loss, 2),
        'target': round(target, 2),
        'rr_ratio': round(rr_ratio, 2),
        'criteria': criteria,
        'signal_score': signal_score,
        'status': status,
        'pattern': pattern,
        'golden_cross': golden_cross_info,
    }


# ════════════════════════════════════════════════════════════════
# UNIFIED CHART GENERATION
# ════════════════════════════════════════════════════════════════

def generate_unified_chart(symbol, df, pattern, asc_triangle, bull_flag, double_bottom, buy_point, show_smas=None, show_cto=False, show_supertrend=False, show_smc=False):
    """Generate single chart with all patterns overlaid + volume.

    Args:
        show_smas: List of SMA periods to display, e.g. [50, 200] or None for all
    """

    # Default: show 50 and 200. Use show_smas=[] to hide all, or specific list
    if show_smas is None:
        show_smas = [50, 200]  # Default to just 50 and 200

    # Debug info

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(
        14, 8), height_ratios=[3, 1], sharex=True)
    fig.suptitle(f'{symbol} - Pattern Analysis', fontsize=14,
                 fontweight='bold', color='white')
    fig.patch.set_facecolor('#1a1a2e')

    # Set dark background
    ax1.set_facecolor('#0f0f23')
    ax2.set_facecolor('#0f0f23')

    # Main price chart
    ax1.plot(df.index, df['Close'], 'cyan',
             linewidth=1.5, label='Price', zorder=2)

    # Add SMAs based on show_smas parameter
    # All available SMAs with their styling (period, color, width, alpha)
    all_sma_configs = {
        13:  ('#ff6b6b', 1.2, 0.9),   # Red - fast
        26:  ('#ffd93d', 1.2, 0.9),   # Yellow
        40:  ('#6bcb77', 1.2, 0.9),   # Green
        50:  ('#4d96ff', 1.5, 1.0),   # Blue
        200: ('#ff8c00', 1.8, 1.0),   # Orange - slow
    }

    for period in show_smas:
        if period in all_sma_configs:
            color, width, alpha = all_sma_configs[period]
            # Use pre-calculated SMA if available, otherwise calculate
            sma_col = f'SMA{period}'
            if sma_col in df.columns:
                sma = df[sma_col].copy()
                # Count valid (non-NaN) values for debugging
                valid_count = sma.notna().sum()
            elif len(df) >= period:
                sma = df['Close'].rolling(period).mean()
                valid_count = sma.notna().sum()
            else:
                continue
            # Plot only if we have valid data
            if sma.notna().any():
                ax1.plot(df.index, sma, color, linewidth=width,
                         alpha=alpha, label=f'SMA {period}')

    # Add CTO Larsson Lines if requested (v1 and v2 with fill)
    if show_cto:
        hl2 = (df['High'] + df['Low']) / 2
        cto1 = ta.ema(hl2, length=15)
        cto2 = ta.ema(hl2, length=29)
        if cto1 is not None and cto1.notna().any() and cto2 is not None and cto2.notna().any():
            ax1.plot(df.index, cto1, label='CTO V1 (15)',
                     color='orange', linewidth=1.5)
            ax1.plot(df.index, cto2, label='CTO V2 (29)',
                     color='silver', linewidth=1.5)
            # Simple fill: yellow for bullish (v1 > v2), blue for bearish
            ax1.fill_between(df.index, cto1, cto2, where=(
                cto1 >= cto2), color='yellow', alpha=0.3)
            ax1.fill_between(df.index, cto1, cto2, where=(
                cto1 < cto2), color='blue', alpha=0.3)

    # Add SuperTrend if requested
    if show_supertrend:
        supertrend_df = ta.supertrend(df['High'], df['Low'], df['Close'], length=10, multiplier=3.0)
        if supertrend_df is not None and not supertrend_df.empty:
            supertrend = supertrend_df['SUPERT_10_3.0']
            direction = supertrend_df['SUPERTd_10_3.0']  # 1 for up, -1 for down
            # Plot SuperTrend line with color based on trend
            colors = ['green' if d == 1 else 'red' for d in direction]
            # To plot with changing colors, use segments
            current_color = None
            start_idx = 0
            for i in range(len(df)):
                if pd.isna(supertrend.iloc[i]):
                    continue
                color = colors[i]
                if color != current_color:
                    if current_color is not None and start_idx < i:
                        ax1.plot(df.index[start_idx:i], supertrend.iloc[start_idx:i], color=current_color, linewidth=1.5, alpha=0.8)
                    current_color = color
                    start_idx = i
            # Last segment
            if start_idx < len(df):
                ax1.plot(df.index[start_idx:], supertrend.iloc[start_idx:], color=current_color, linewidth=1.5, alpha=0.8, label='SuperTrend')

            # Highlight trend direction
            ax1.fill_between(df.index, df['Low'].min(), df['High'].max(), where=(direction == 1), color='green', alpha=0.05, label='Uptrend')
            ax1.fill_between(df.index, df['Low'].min(), df['High'].max(), where=(direction == -1), color='red', alpha=0.05, label='Downtrend')

            # Add signals on trend changes
            for i in range(1, len(direction)):
                if direction.iloc[i] != direction.iloc[i-1]:
                    if direction.iloc[i] == 1:  # Buy signal
                        ax1.scatter([df.index[i]], [supertrend.iloc[i]], color='lime', marker='^', s=80, zorder=10, edgecolors='black', linewidths=1)
                    else:  # Sell signal
                        ax1.scatter([df.index[i]], [supertrend.iloc[i]], color='red', marker='v', s=80, zorder=10, edgecolors='black', linewidths=1)

    # Add SMC if requested
    if show_smc:
        # Calculate pivot points for market structure
        window = 5  # Lookback for pivots
        high_pivots = argrelextrema(df['High'].values, comparator=np.greater, order=window)[0]
        low_pivots = argrelextrema(df['Low'].values, comparator=np.less, order=window)[0]
        
        df['Pivot_High'] = np.nan
        df['Pivot_Low'] = np.nan
        df.iloc[high_pivots, df.columns.get_loc('Pivot_High')] = df['High'].iloc[high_pivots].values
        df.iloc[low_pivots, df.columns.get_loc('Pivot_Low')] = df['Low'].iloc[low_pivots].values

        # Market Structure: BOS and CHoCH
        bullish_bos = []
        bearish_bos = []
        choch = []

        for i in range(window, len(df)):
            # Bullish BOS: Break above previous pivot high
            if not pd.isna(df['Pivot_High'].iloc[i-window]) and df['High'].iloc[i] > df['Pivot_High'].iloc[i-window]:
                bullish_bos.append((df.index[i], df['High'].iloc[i]))

            # Bearish BOS: Break below previous pivot low
            if not pd.isna(df['Pivot_Low'].iloc[i-window]) and df['Low'].iloc[i] < df['Pivot_Low'].iloc[i-window]:
                bearish_bos.append((df.index[i], df['Low'].iloc[i]))

            # CHoCH: Change of character (direction change)
            if i > window*2:
                prev_highs = df['Pivot_High'].iloc[i-window*2:i-window].dropna()
                prev_lows = df['Pivot_Low'].iloc[i-window*2:i-window].dropna()
                if len(prev_highs) > 1 and len(prev_lows) > 1:
                    if prev_highs.iloc[-1] < prev_highs.iloc[-2] and prev_lows.iloc[-1] > prev_lows.iloc[-2]:
                        choch.append((df.index[i], df['Close'].iloc[i]))

        # Plot BOS
        if bullish_bos:
            bos_x, bos_y = zip(*bullish_bos)
            ax1.scatter(bos_x, bos_y, color='#ff00ff', marker='^', s=100, zorder=10, label='Bullish BOS')

        if bearish_bos:
            bos_x, bos_y = zip(*bearish_bos)
            ax1.scatter(bos_x, bos_y, color='#00ffff', marker='v', s=100, zorder=10, label='Bearish BOS')

        # Plot CHoCH
        if choch:
            choch_x, choch_y = zip(*choch)
            ax1.scatter(choch_x, choch_y, color='#ffff00', marker='o', s=100, zorder=10, label='CHoCH')

        # Order Blocks: Simplified - high volume candles with strong move
        df['Body'] = abs(df['Close'] - df['Open'])
        avg_volume = df['Volume'].rolling(20).mean()
        avg_body = df['Body'].rolling(20).mean()

        bullish_ob = []
        bearish_ob = []

        for i in range(len(df)):
            if df['Volume'].iloc[i] > avg_volume.iloc[i] * 1.5 and df['Body'].iloc[i] > avg_body.iloc[i] * 1.5:
                if df['Close'].iloc[i] > df['Open'].iloc[i]:  # Bullish candle
                    # Bullish OB: Bottom of the candle
                    bullish_ob.append((df.index[i], df['Low'].iloc[i], df['High'].iloc[i]))
                else:  # Bearish candle
                    # Bearish OB: Top of the candle
                    bearish_ob.append((df.index[i], df['Low'].iloc[i], df['High'].iloc[i]))

        # Plot Order Blocks as boxes
        for idx, low, high in bullish_ob:
            ax1.add_patch(plt.Rectangle((idx - pd.Timedelta(days=1), low), width=pd.Timedelta(days=2), height=high-low,
                                        color='#00ff00', alpha=0.3, zorder=5))

        for idx, low, high in bearish_ob:
            ax1.add_patch(plt.Rectangle((idx - pd.Timedelta(days=1), low), width=pd.Timedelta(days=2), height=high-low,
                                        color='#ff0000', alpha=0.3, zorder=5))

        # Fair Value Gaps: Gaps between candles
        fvgs = []
        for i in range(1, len(df)):
            prev_high = df['High'].iloc[i-1]
            prev_low = df['Low'].iloc[i-1]
            curr_high = df['High'].iloc[i]
            curr_low = df['Low'].iloc[i]

            if curr_low > prev_high:  # Bullish FVG
                fvgs.append((df.index[i-1], prev_high, curr_low))
            elif curr_high < prev_low:  # Bearish FVG
                fvgs.append((df.index[i-1], curr_high, prev_low))

        # Plot FVGs as yellow boxes
        for idx, bottom, top in fvgs:
            ax1.add_patch(plt.Rectangle((idx, bottom), width=pd.Timedelta(days=1), height=top-bottom,
                                        color='#ffff00', alpha=0.2, zorder=5))

        # Equal Highs/Lows: Levels with multiple touches
        tolerance = df['High'].std() * 0.01  # 1% tolerance

        high_levels = {}
        low_levels = {}

        for i in range(len(df)):
            high = df['High'].iloc[i]
            low = df['Low'].iloc[i]

            # Check for equal highs
            for level in high_levels:
                if abs(high - level) <= tolerance:
                    high_levels[level].append(i)
                    break
            else:
                high_levels[high] = [i]

            # Check for equal lows
            for level in low_levels:
                if abs(low - level) <= tolerance:
                    low_levels[level].append(i)
                    break
            else:
                low_levels[low] = [i]

        # Plot levels with 3+ touches
        for level, indices in high_levels.items():
            if len(indices) >= 3:
                ax1.axhline(y=level, color='#ffa500', linestyle='--', alpha=0.7, linewidth=1)

        for level, indices in low_levels.items():
            if len(indices) >= 3:
                ax1.axhline(y=level, color='#ffa500', linestyle='--', alpha=0.7, linewidth=1)

        # Premium/Discount Zones: Based on VWAP
        df['VWAP'] = (df['Volume'] * (df['High'] + df['Low'] + df['Close']) / 3).cumsum() / df['Volume'].cumsum()

        # Shade premium (above VWAP) and discount (below VWAP)
        ax1.fill_between(df.index, df['VWAP'], df['High'], where=(df['Close'] > df['VWAP']), color='green', alpha=0.1)
        ax1.fill_between(df.index, df['Low'], df['VWAP'], where=(df['Close'] < df['VWAP']), color='red', alpha=0.1)

    # Plot other detected patterns
    if asc_triangle and 'resistance' in asc_triangle:
        ax1.axhline(y=asc_triangle['resistance'], color='red',
                    linestyle='--', linewidth=1, label='Asc Triangle Resistance')
    if bull_flag and 'pole_high' in bull_flag:
        ax1.axhline(y=bull_flag['pole_high'], color='green',
                    linestyle=':', linewidth=1, label='Bull Flag Pole')
    if double_bottom and 'neckline_price' in double_bottom:
        ax1.axhline(y=double_bottom['neckline_price'], color='purple',
                    linestyle='-.', linewidth=1, label='Double Bottom Neck')
        if 'first_bottom_idx' in double_bottom:
            ax1.scatter(df.index[double_bottom['first_bottom_idx']], double_bottom['first_bottom_price'],
                        color='red', marker='v', s=50, label='Double Bottoms')
        if 'second_bottom_idx' in double_bottom:
            ax1.scatter(df.index[double_bottom['second_bottom_idx']],
                        double_bottom['second_bottom_price'], color='red', marker='v', s=50)

    # Mark Golden Cross if detected (50 crosses above 200) - only if both SMAs are displayed
    if 50 in show_smas and 200 in show_smas:
        # Use pre-calculated SMAs if available
        if 'SMA50' in df.columns and 'SMA200' in df.columns:
            sma50 = df['SMA50']
            sma200 = df['SMA200']
        elif len(df) >= 200:
            sma50 = df['Close'].rolling(50).mean()
            sma200 = df['Close'].rolling(200).mean()
        else:
            sma50 = None
            sma200 = None

        # Find golden/death crosses
        if sma50 is not None and sma200 is not None:
            for i in range(1, len(df)):
                if pd.notna(sma50.iloc[i]) and pd.notna(sma200.iloc[i]) and pd.notna(sma50.iloc[i-1]) and pd.notna(sma200.iloc[i-1]):
                    # Golden cross
                    if sma50.iloc[i-1] <= sma200.iloc[i-1] and sma50.iloc[i] > sma200.iloc[i]:
                        ax1.axvline(
                            x=df.index[i], color='gold', linestyle='--', linewidth=1.5, alpha=0.8)
                        ax1.scatter([df.index[i]], [sma50.iloc[i]], color='gold', s=150, marker='*',
                                    zorder=10, edgecolors='white', linewidths=1)
                        ax1.annotate('Golden Cross', xy=(df.index[i], sma50.iloc[i]),
                                     xytext=(10, 20), textcoords='offset points',
                                     fontsize=9, color='gold', fontweight='bold',
                                     arrowprops=dict(arrowstyle='->', color='gold', lw=1))
                    # Death cross
                    elif sma50.iloc[i-1] >= sma200.iloc[i-1] and sma50.iloc[i] < sma200.iloc[i]:
                        ax1.axvline(
                            x=df.index[i], color='red', linestyle='--', linewidth=1.5, alpha=0.6)
                        ax1.scatter([df.index[i]], [sma50.iloc[i]], color='red', s=100, marker='x',
                                    zorder=10, linewidths=2)

    # Draw Cup & Handle pattern
    if pattern:
        left_idx = pattern['left_rim_idx']
        right_idx = pattern['right_rim_idx']
        bottom_idx = pattern['bottom_idx']

        if left_idx < len(df) and right_idx < len(df) and bottom_idx < len(df):
            # Cup outline
            cup_dates = df.index[left_idx:right_idx+1]
            cup_prices = df['Close'].iloc[left_idx:right_idx+1]
            ax1.fill_between(cup_dates, cup_prices, pattern['bottom_price'],
                             alpha=0.15, color='lime', label='Cup Formation')

            # Mark key points
            ax1.scatter([df.index[left_idx]], [pattern['left_rim_price']],
                        color='lime', s=120, zorder=5, marker='^', edgecolors='white', linewidths=1)
            ax1.scatter([df.index[right_idx]], [pattern['right_rim_price']],
                        color='lime', s=120, zorder=5, marker='^', edgecolors='white', linewidths=1)
            ax1.scatter([df.index[bottom_idx]], [pattern['bottom_price']],
                        color='red', s=120, zorder=5, marker='v', edgecolors='white', linewidths=1)

            # Resistance line (neckline)
            ax1.axhline(y=pattern['right_rim_price'], color='lime', linestyle='--',
                        linewidth=1.5, alpha=0.8, label=f"Resistance ${pattern['right_rim_price']:.2f}")

    # Draw Buy Point
    if buy_point:
        ax1.axhline(y=buy_point, color='#00ff00', linestyle='-', linewidth=2,
                    alpha=0.9, label=f"BUY POINT ${buy_point:.2f}")
        # Add arrow annotation
        ax1.annotate(f'  BUY ${buy_point:.2f}', xy=(df.index[-1], buy_point),
                     fontsize=10, fontweight='bold', color='#00ff00',
                     verticalalignment='center')

    # Draw Ascending Triangle (pink/magenta)
    if asc_triangle:
        # Resistance line
        ax1.axhline(y=asc_triangle['resistance'], color='magenta', linestyle='-',
                    linewidth=2, alpha=0.8, label=f"△ Resistance ${asc_triangle['resistance']:.2f}")

        # Rising support line - draw across recent data
        lookback = 60
        if len(df) > lookback:
            recent_idx = np.arange(len(df) - lookback, len(df))
            support_line = asc_triangle['support_slope'] * np.arange(lookback) + \
                (df['Close'].iloc[-lookback] -
                 asc_triangle['support_slope'] * lookback/2)
            ax1.plot(df.index[-lookback:], support_line, 'magenta', linestyle='--',
                     linewidth=1.5, alpha=0.7, label='△ Support')

        # Target line
        ax1.axhline(y=asc_triangle['target'], color='magenta', linestyle=':',
                    linewidth=1, alpha=0.5, label=f"△ Target ${asc_triangle['target']:.2f}")

    # Draw Bull Flag (orange)
    if bull_flag:
        lookback = 40
        start_idx = max(0, len(df) - lookback)

        # Pole
        pole_start = start_idx + bull_flag.get('pole_start_idx', 0)
        pole_end = start_idx + bull_flag.get('pole_end_idx', 10)

        if pole_start < len(df) and pole_end < len(df):
            ax1.plot([df.index[pole_start], df.index[pole_end]],
                     [bull_flag['pole_low'], bull_flag['pole_high']],
                     'orange', linewidth=3, alpha=0.8, label=f"Flag Pole +{bull_flag['pole_gain']:.0f}%")

        # Flag boundaries
        ax1.axhline(y=bull_flag['flag_high'], color='orange', linestyle='--',
                    linewidth=1.5, alpha=0.6)
        ax1.axhline(y=bull_flag['flag_low'], color='orange', linestyle='--',
                    linewidth=1.5, alpha=0.6)

        # Flag target
        ax1.axhline(y=bull_flag['target'], color='orange', linestyle=':',
                    linewidth=1, alpha=0.5, label=f"Flag Target ${bull_flag['target']:.2f}")

    # Styling
    ax1.set_ylabel('Price ($)', color='white', fontsize=10)
    ax1.tick_params(colors='white')
    ax1.legend(loc='upper left', fontsize=8, facecolor='#16213e',
               edgecolor='gray', labelcolor='white')
    ax1.grid(True, alpha=0.2, color='gray')
    ax1.spines['bottom'].set_color('gray')
    ax1.spines['top'].set_color('gray')
    ax1.spines['left'].set_color('gray')
    ax1.spines['right'].set_color('gray')

    # Volume chart
    colors = ['#00c853' if df['Close'].iloc[i] >= df['Open'].iloc[i] else '#f44336'
              for i in range(len(df))]
    ax2.bar(df.index, df['Volume'], color=colors, alpha=0.7, width=0.8)

    # Volume average
    vol_avg = df['Volume'].rolling(20).mean()
    ax2.plot(df.index, vol_avg, 'yellow', linewidth=1,
             alpha=0.8, label='20-day Avg')

    ax2.set_ylabel('Volume', color='white', fontsize=10)
    ax2.set_xlabel('Date', color='white', fontsize=10)
    ax2.tick_params(colors='white')
    ax2.legend(loc='upper left', fontsize=8, facecolor='#16213e',
               edgecolor='gray', labelcolor='white')
    ax2.grid(True, alpha=0.2, color='gray')
    ax2.spines['bottom'].set_color('gray')
    ax2.spines['top'].set_color('gray')
    ax2.spines['left'].set_color('gray')
    ax2.spines['right'].set_color('gray')

    # Format x-axis
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    plt.xticks(rotation=45)

    plt.tight_layout()

    # Save to base64
    buffer = BytesIO()
    plt.savefig(buffer, format='png', dpi=120, bbox_inches='tight',
                facecolor='#1a1a2e', edgecolor='none')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode()
    plt.close(fig)

    return image_base64


# ════════════════════════════════════════════════════════════════
# MAIN SCANNER (BATCH DOWNLOAD FOR SPEED)
# ════════════════════════════════════════════════════════════════

def scan_for_patterns(tickers=None, progress_callback=None):
    if tickers is None:
        tickers = get_sp500_tickers()

    results = []
    total = len(tickers)

    # Batch download all data at once - MUCH faster than individual calls

    # Download in chunks to avoid timeout
    chunk_size = 100
    all_data = {}

    for i in range(0, len(tickers), chunk_size):
        chunk = tickers[i:i+chunk_size]
        chunk_str = ' '.join(chunk)
        try:
            data = yf.download(chunk_str, period="1y", group_by='ticker',
                               progress=False, threads=True)

            # Handle single vs multiple tickers
            if len(chunk) == 1:
                all_data[chunk[0]] = data
            else:
                for symbol in chunk:
                    if symbol in data.columns.get_level_values(0):
                        all_data[symbol] = data[symbol].dropna()
        except Exception as e:
            pass

        if progress_callback:
            progress_callback(min(i + chunk_size, total), total,
                              f"Downloaded {min(i + chunk_size, total)}/{total}")

    # Now analyze each stock
    for idx, (symbol, df) in enumerate(all_data.items()):
        if progress_callback and idx % 50 == 0:
            progress_callback(idx, len(all_data), symbol)

        try:
            if df.empty or len(df) < 150:
                continue

            # Detect all patterns
            cup_pattern = detect_cup_and_handle(df)
            asc_triangle = detect_ascending_triangle(df)
            bull_flag = detect_bull_flag(df)
            double_bottom = detect_double_bottom(df)

            # Skip if no patterns found
            if cup_pattern is None and asc_triangle is None and bull_flag is None and double_bottom is None:
                continue

            # Count patterns
            pattern_count = 0
            if cup_pattern:
                pattern_count += 1
            if asc_triangle:
                pattern_count += 1
            if bull_flag:
                pattern_count += 1
            if double_bottom:
                pattern_count += 1

            # Check breakout criteria (uses cup pattern if available)
            analysis = check_breakout_criteria(
                df.copy(), cup_pattern, asc_triangle, bull_flag)

            if analysis:
                analysis['symbol'] = symbol
                if cup_pattern:
                    analysis['cup_depth'] = round(
                        cup_pattern['cup_depth_pct'], 1)
                    analysis['cup_days'] = cup_pattern['cup_length_days']
                    analysis['handle_pullback'] = round(
                        cup_pattern['handle_decline_pct'], 1)
                    analysis['u_shape'] = cup_pattern['u_shape_score']
                    analysis['symmetry'] = cup_pattern['symmetry_pct']
                else:
                    analysis['cup_depth'] = '-'
                    analysis['cup_days'] = '-'
                    analysis['handle_pullback'] = '-'
                    analysis['u_shape'] = '-'
                    analysis['symmetry'] = '-'
                analysis['asc_triangle'] = asc_triangle
                analysis['bull_flag'] = bull_flag
                analysis['double_bottom'] = double_bottom
                analysis['pattern_count'] = pattern_count

                # Calculate DCF for stocks with patterns
                dcf_result = calculate_dcf_value(symbol)
                analysis['dcf_value'] = dcf_result.get('dcf_value')
                analysis['margin_of_safety'] = dcf_result.get('margin')

                results.append(analysis)

        except Exception as e:
            # Silent fail for individual stocks
            continue

    # Sort by: status (best first), then score (highest first), then pattern count
    status_order = {"STRONG BUY": 0, "BUY": 1,
                    "FORMING - NEAR BREAKOUT": 2, "FORMING": 3, "WATCH": 4}
    results.sort(key=lambda x: (status_order.get(
        x['status'], 5), -x['signal_score'], -x['pattern_count']))

    return results


# ════════════════════════════════════════════════════════════════
# FLASK ROUTES
# ════════════════════════════════════════════════════════════════

@app.route("/")
def home():
    return render_template_string("""
    <html>
    <head>
        <title>Stock Pattern Scanner</title>
        <style>
            body { font-family: 'Segoe UI', Arial, sans-serif; margin: 40px; background: #1a1a2e; color: #eee; }
            h1 { color: #00d4ff; }
            .container { max-width: 1000px; margin: auto; }
            .navbar { background: #16213e; padding: 10px; border-radius: 8px; margin-bottom: 20px; }
            .navbar a { color: #00d4ff; text-decoration: none; margin: 0 15px; }
            .navbar a:hover { text-decoration: underline; }
            .btn { padding: 15px 30px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                   color: white; text-decoration: none; border-radius: 8px; margin: 10px;
                   display: inline-block; font-weight: bold; transition: transform 0.2s; }
            .btn:hover { transform: scale(1.05); }
            .btn-nasdaq { background: linear-gradient(135deg, #00c9ff 0%, #92fe9d 100%); color: #000; }
            .btn-all { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
            .info { background: #16213e; padding: 20px; border-radius: 10px; margin: 20px 0; }
            .info h3 { color: #00d4ff; margin-top: 0; }
            ul { line-height: 1.8; }
            .feature-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
            .time-note { color: #888; font-size: 12px; margin-left: 10px; }
            .new-badge { background: #00c853; color: #000; padding: 2px 8px; border-radius: 4px;
                        font-size: 10px; margin-left: 5px; }
        </style>
    </head>
    <body>
    <div class="container">
        <div class="navbar">
            <a href="/">Home</a>
            <a href="/tracked">Tracked Stocks</a>
            <a href="/research">🔬 Alpha Research</a>
            <a href="/journal/">📊 Trade Journal</a>
            <a href="/saved-results">📁 Saved Results</a>
        </div>
        <h1>🏆 Stock Pattern Scanner <span class="new-badge">ENHANCED</span></h1>
        <p>Multi-pattern detection with DCF valuation and advanced charting.</p>

        <div class="feature-grid">
            <div class="info">
                <h3>📊 Pattern Detection</h3>
                <ul>
                    <li><strong>Cup & Handle</strong> - Classic W. O'Neil pattern</li>
                    <li><strong>Ascending Triangle</strong> - Flat resistance + rising support</li>
                    <li><strong>Bull Flag</strong> - Strong pole + consolidation</li>
                </ul>
            </div>
            <div class="info">
                <h3>💰 DCF Valuation</h3>
                <ul>
                    <li><span style="color:#00c853">●</span> &gt;20% = Significantly Undervalued</li>
                    <li><span style="color:#8bc34a">●</span> 0-20% = Undervalued</li>
                    <li><span style="color:#ff9800">●</span> 0 to -20% = Fairly Valued</li>
                    <li><span style="color:#f44336">●</span> &lt;-20% = Overvalued</li>
                </ul>
            </div>
        </div>

        <div class="info">
            <h3>🎯 Breakout Criteria</h3>
            <ul>
                <li>Price above resistance • Volume spike (2x+) • Above SMA50 & SMA200</li>
                <li>RSI 50-70 • MACD bullish • ADX &gt;25 • Handle volume contraction</li>
                <li><span style="color: gold;">⭐ Golden Cross</span> = 50-day crosses above 200-day (bullish signal)</li>
            </ul>
        </div>

        <div class="info">
            <h3>📈 Moving Averages on Chart</h3>
            <ul>
                <li>SMA <span style="color: #ff6b6b;">13</span>, <span style="color: #ffd93d;">26</span>, <span style="color: #6bcb77;">40</span>, <span style="color: #4d96ff;">50</span>, <span style="color: #ff8c00;">200</span> day moving averages</li>
                <li><span style="color: gold;">⭐</span> Golden Cross marked when 50 crosses above 200</li>
            </ul>
        </div>

        <div class="info">
            <h3>🔍 Search Individual Stock</h3>
            <form action="/chart" method="get" style="display: flex; gap: 10px; align-items: center;">
                <input type="text" name="symbol" placeholder="Enter symbol (e.g. AAPL)" 
                       style="padding: 12px 15px; border-radius: 8px; border: none; font-size: 16px; 
                              width: 250px; background: #16213e; color: #fff; border: 1px solid #667eea;">
                <button type="submit" class="btn" style="margin: 0; border: none; cursor: pointer;">Analyze</button>
            </form>
        </div>

        <div class="info">
            <h3>🚀 Scan Market</h3>
            <p>
                <a class="btn" href="/scan?market=sp500">S&P 500</a>
                <span class="time-note">~500 stocks, 5-10 min</span>
            </p>
            <p>
                <a class="btn btn-nasdaq" href="/scan?market=nasdaq">NASDAQ ($1B+)</a>
                <span class="time-note">~1000 stocks, 15-25 min</span>
            </p>
            <p>
                <a class="btn btn-all" href="/scan?market=all">All US ($1B+)</a>
                <span class="time-note">~2000 stocks, 30-45 min</span>
            </p>
        </div>
    </div>
    </body>
    </html>
    """)


@app.route("/scan")
def scan():
    market = request.args.get('market', 'sp500')

    if market == 'nasdaq':
        tickers = get_nasdaq_tickers(min_market_cap=1_000_000_000)
        market_name = "NASDAQ ($1B+)"
    elif market == 'all':
        tickers = get_all_us_tickers(min_market_cap=1_000_000_000)
        market_name = "All US ($1B+)"
    else:
        tickers = get_sp500_tickers()
        market_name = "S&P 500"

    def progress(current, total, symbol):
        if current % 50 == 0:
            pass

    results = scan_for_patterns(tickers=tickers, progress_callback=progress)
    
    # Save results to file
    import json
    from datetime import datetime
    scan_data = {
        'timestamp': datetime.now().isoformat(),
        'market': market_name,
        'results': results
    }
    scan_file = Path('data/last_scan_results.json')
    scan_file.parent.mkdir(exist_ok=True)
    with open(scan_file, 'w') as f:
        json.dump(scan_data, f, default=str)

    return render_template_string(SCAN_RESULTS_TEMPLATE, 
                                  results=results, 
                                  now=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                  market=market,
                                  market_name=market_name,
                                  is_saved=False)


SCAN_RESULTS_TEMPLATE = """
    <html>
    <head>
        <title>Stock Pattern Scanner Scan Results</title>
        <style>
            body { font-family: 'Segoe UI', Arial, sans-serif; margin: 20px; background: #1a1a2e; color: #eee; }
            h1 { color: #00d4ff; }
            .container { max-width: 100%; margin: auto; overflow-x: auto; }
            .navbar { background: #16213e; padding: 10px; border-radius: 8px; margin-bottom: 20px; }
            .navbar a { color: #00d4ff; text-decoration: none; margin: 0 15px; }
            .navbar a:hover { text-decoration: underline; }
            .filter-controls { background: #16213e; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
            .filter-controls button { background: #00d4ff; color: #1a1a2e; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; margin-right: 10px; font-weight: bold; }
            .filter-controls button:hover { background: #00a8cc; }
            .tier-badge { padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 11px; }
            .tier1 { background: #4caf50; color: white; }
            .tier2 { background: #2196f3; color: white; }
            .tier3 { background: #ff9800; color: white; }
            .excluded { background: #f44336; color: white; }
            table { border-collapse: collapse; width: 100%; margin-top: 20px; font-size: 12px; }
            th, td { border: 1px solid #333; padding: 8px; text-align: center; white-space: nowrap; }
            th { background: #16213e; color: #00d4ff; position: sticky; top: 0; }
            tr:nth-child(even) { background: #0f0f23; }
            tr:hover { background: #1f1f3a; }
            .strong-buy { background: #00c853 !important; color: #000; font-weight: bold; }
            .buy { background: #4caf50 !important; color: #fff; font-weight: bold; }
            .forming-near-breakout, .forming---near-breakout { background: #ff9800 !important; color: #000; font-weight: bold; }
            .forming { background: #2196f3 !important; color: #fff; }
            .watch { background: #607d8b !important; color: #fff; }
            .check { color: #00c853; }
            .cross { color: #f44336; }
            .btn { padding: 8px 15px; background: #667eea; color: white; text-decoration: none;
                   border-radius: 5px; margin: 5px; display: inline-block; }
            .view-btn { padding: 4px 8px; background: #2196f3; color: white; text-decoration: none;
                       border-radius: 4px; font-size: 11px; }
            .dcf-green { color: #00c853; }
            .dcf-lightgreen { color: #8bc34a; }
            .dcf-orange { color: #ff9800; }
            .dcf-red { color: #f44336; }
            .pattern-badge { display: inline-block; padding: 2px 6px; border-radius: 3px; 
                           font-size: 10px; margin: 1px; }
            .badge-triangle { background: #9c27b0; color: white; }
            .badge-flag { background: #e91e63; color: white; }
            .badge-golden { background: gold; color: #000; }
            .badge-double-bottom { background: #ec4899; color: white; }
            .summary { background: #16213e; padding: 15px; border-radius: 8px; margin: 20px 0; }
            .cup-analysis { font-size: 10px; line-height: 1.4; text-align: left; }
        </style>
    </head>
    <body>
    <div class="container">
        <div class="navbar">
            <a href="/">Home</a>
            <a href="/tracked">Tracked Stocks</a>
            <a href="/research">🔬 Alpha Research</a>
            <a href="/saved-results">📁 Saved Results</a>
            {% if is_saved %}
            <a href="/scan?market={{ market }}" style="background: #4caf50; padding: 8px 15px; border-radius: 5px; margin-left: 20px;">🔄 Re-run Scan</a>
            {% endif %}
        </div>
        <h1>🏆 Stock Pattern Scanner {% if is_saved %}Saved {% endif %}Results</h1>
        <p><strong>Market:</strong> {{ market_name }} | <strong>Pattern:</strong> All Patterns | 
           <strong>{% if is_saved %}Saved{% else %}Scanned{% endif %}:</strong> {{ now }} | <strong>Found:</strong> {{ results|length }} patterns</p>

        <div class="filter-controls">
            <button onclick="applyScreening()">🎯 Apply Tier Screening</button>
            <button onclick="showAll()">📋 Show All Results</button>
            <button onclick="showTier(1)">🥇 Tier 1 Only</button>
            <button onclick="showTier(2)">🥈 Tier 2 Only</button>
            <button onclick="showTier(3)">🥉 Tier 3 Only</button>
            <button onclick="toggleSettings()">⚙️ Adjust Parameters</button>
            <span id="filterStatus" style="margin-left: 20px; color: #00d4ff;"></span>
        </div>

        <div id="screeningSettings" style="display: none; background: #16213e; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
            <h3 style="color: #00d4ff; margin-top: 0;">Screening Parameters</h3>
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px;">
                <div>
                    <h4 style="color: #4caf50; margin-bottom: 10px;">🥇 Tier 1 - High Conviction</h4>
                    <label style="display: block; margin: 8px 0;">
                        Volume: <input type="number" id="t1_vol" value="0.7" step="0.1" style="width: 60px; background: #1a1a2e; color: #eee; border: 1px solid #333; padding: 4px;">x
                    </label>
                    <label style="display: block; margin: 8px 0;">
                        ADX: <input type="number" id="t1_adx" value="25" step="1" style="width: 60px; background: #1a1a2e; color: #eee; border: 1px solid #333; padding: 4px;">+
                    </label>
                    <label style="display: block; margin: 8px 0;">
                        RSI Min: <input type="number" id="t1_rsi_min" value="50" step="1" style="width: 60px; background: #1a1a2e; color: #eee; border: 1px solid #333; padding: 4px;">
                    </label>
                    <label style="display: block; margin: 8px 0;">
                        RSI Max: <input type="number" id="t1_rsi_max" value="70" step="1" style="width: 60px; background: #1a1a2e; color: #eee; border: 1px solid #333; padding: 4px;">
                    </label>
                    <label style="display: block; margin: 8px 0;">
                        U-Shape: <input type="number" id="t1_ushape" value="0.40" step="0.05" style="width: 60px; background: #1a1a2e; color: #eee; border: 1px solid #333; padding: 4px;">+
                    </label>
                    <label style="display: block; margin: 8px 0;">
                        R:R: <input type="number" id="t1_rr" value="1.5" step="0.1" style="width: 60px; background: #1a1a2e; color: #eee; border: 1px solid #333; padding: 4px;">:1+
                    </label>
                    <label style="display: block; margin: 8px 0;">
                        <input type="checkbox" id="t1_dcf" checked> Require DCF > 0%
                    </label>
                    <label style="display: block; margin: 8px 0;">
                        <input type="checkbox" id="t1_macd" checked> Require MACD ✔
                    </label>
                </div>
                
                <div>
                    <h4 style="color: #2196f3; margin-bottom: 10px;">🥈 Tier 2 - Strong Setup</h4>
                    <label style="display: block; margin: 8px 0;">
                        Volume: <input type="number" id="t2_vol" value="0.55" step="0.05" style="width: 60px; background: #1a1a2e; color: #eee; border: 1px solid #333; padding: 4px;">x
                    </label>
                    <label style="display: block; margin: 8px 0;">
                        ADX: <input type="number" id="t2_adx" value="25" step="1" style="width: 60px; background: #1a1a2e; color: #eee; border: 1px solid #333; padding: 4px;">+
                    </label>
                    <label style="display: block; margin: 8px 0;">
                        RSI Min: <input type="number" id="t2_rsi_min" value="50" step="1" style="width: 60px; background: #1a1a2e; color: #eee; border: 1px solid #333; padding: 4px;">
                    </label>
                    <label style="display: block; margin: 8px 0;">
                        RSI Max: <input type="number" id="t2_rsi_max" value="70" step="1" style="width: 60px; background: #1a1a2e; color: #eee; border: 1px solid #333; padding: 4px;">
                    </label>
                    <label style="display: block; margin: 8px 0;">
                        U-Shape: <input type="number" id="t2_ushape" value="0.35" step="0.05" style="width: 60px; background: #1a1a2e; color: #eee; border: 1px solid #333; padding: 4px;">+
                    </label>
                    <label style="display: block; margin: 8px 0;">
                        R:R: <input type="number" id="t2_rr" value="1.5" step="0.1" style="width: 60px; background: #1a1a2e; color: #eee; border: 1px solid #333; padding: 4px;">:1+
                    </label>
                    <label style="display: block; margin: 8px 0;">
                        <input type="checkbox" id="t2_dcf" checked> Require DCF > 0%
                    </label>
                    <label style="display: block; margin: 8px 0;">
                        <input type="checkbox" id="t2_macd" checked> Require MACD ✔
                    </label>
                </div>
                
                <div>
                    <h4 style="color: #ff9800; margin-bottom: 10px;">🥉 Tier 3 - Watchlist</h4>
                    <label style="display: block; margin: 8px 0;">
                        Volume: <input type="number" id="t3_vol" value="0.3" step="0.05" style="width: 60px; background: #1a1a2e; color: #eee; border: 1px solid #333; padding: 4px;">x
                    </label>
                    <label style="display: block; margin: 8px 0;">
                        ADX: <input type="number" id="t3_adx" value="25" step="1" style="width: 60px; background: #1a1a2e; color: #eee; border: 1px solid #333; padding: 4px;">+
                    </label>
                    <label style="display: block; margin: 8px 0;">
                        RSI Min: <input type="number" id="t3_rsi_min" value="50" step="1" style="width: 60px; background: #1a1a2e; color: #eee; border: 1px solid #333; padding: 4px;">
                    </label>
                    <label style="display: block; margin: 8px 0;">
                        RSI Max: <input type="number" id="t3_rsi_max" value="70" step="1" style="width: 60px; background: #1a1a2e; color: #eee; border: 1px solid #333; padding: 4px;">
                    </label>
                    <label style="display: block; margin: 8px 0;">
                        U-Shape: <input type="number" id="t3_ushape" value="0.40" step="0.05" style="width: 60px; background: #1a1a2e; color: #eee; border: 1px solid #333; padding: 4px;">+
                    </label>
                    <label style="display: block; margin: 8px 0;">
                        R:R: <input type="number" id="t3_rr" value="1.5" step="0.1" style="width: 60px; background: #1a1a2e; color: #eee; border: 1px solid #333; padding: 4px;">:1+
                    </label>
                    <label style="display: block; margin: 8px 0;">
                        <input type="checkbox" id="t3_dcf"> Require DCF > 0%
                    </label>
                    <label style="display: block; margin: 8px 0;">
                        <input type="checkbox" id="t3_macd" checked> Require MACD ✔
                    </label>
                </div>
            </div>
            
            <div style="margin-top: 20px; padding-top: 20px; border-top: 1px solid #333;">
                <h4 style="color: #f44336; margin-bottom: 10px;">❌ Auto-Disqualifiers</h4>
                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px;">
                    <label>RSI > <input type="number" id="excl_rsi_max" value="80" step="1" style="width: 50px; background: #1a1a2e; color: #eee; border: 1px solid #333; padding: 4px;"> (overbought)</label>
                    <label>RSI < <input type="number" id="excl_rsi_min" value="45" step="1" style="width: 50px; background: #1a1a2e; color: #eee; border: 1px solid #333; padding: 4px;"> (weak)</label>
                    <label>ADX < <input type="number" id="excl_adx" value="10" step="1" style="width: 50px; background: #1a1a2e; color: #eee; border: 1px solid #333; padding: 4px;"> (no trend)</label>
                    <label>U-Shape < <input type="number" id="excl_ushape" value="0.05" step="0.01" style="width: 50px; background: #1a1a2e; color: #eee; border: 1px solid #333; padding: 4px;"> (distorted)</label>
                    <label>R:R < <input type="number" id="excl_rr" value="1.0" step="0.1" style="width: 50px; background: #1a1a2e; color: #eee; border: 1px solid #333; padding: 4px;"> (poor risk)</label>
                </div>
            </div>
            
            <div style="margin-top: 20px; text-align: center;">
                <button onclick="resetDefaults()" style="background: #666; margin-right: 10px;">Reset to Defaults</button>
                <button onclick="savePreset()" style="background: #4caf50; margin-right: 10px;">Save Preset</button>
                <button onclick="toggleSettings()">Close</button>
            </div>
        </div>

        <div class="summary">
            <strong>Status:</strong>
            <span class="strong-buy" style="padding: 3px 8px; border-radius: 4px;">STRONG BUY (75+)</span>
            <span class="buy" style="padding: 3px 8px; border-radius: 4px;">BUY (55+)</span>
            <span class="forming-near-breakout" style="padding: 3px 8px; border-radius: 4px;">NEAR BREAKOUT</span>
            <span class="forming" style="padding: 3px 8px; border-radius: 4px;">FORMING</span>
            <span class="watch" style="padding: 3px 8px; border-radius: 4px;">WATCH</span>
            <br><br>
            <strong>Pattern Count:</strong> 3 = Cup&Handle + Triangle + Flag (Best) | 2 = Two patterns | 1 = Cup&Handle only
            <br><br>
            <strong>Additional Patterns:</strong> 
            <span class="pattern-badge badge-triangle">Asc Triangle</span> = Flat resistance + rising support (R = resistance level)
            <span class="pattern-badge badge-flag">Bull Flag/Pennant</span> = Strong pole + consolidation (% = pole gain)
            <span class="pattern-badge badge-double-bottom">Double Bottom</span> = W-shaped reversal pattern (neckline = breakout level)
            <br><br>
            <strong>Moving Averages:</strong> Chart shows SMA 13, 26, 40, 50, 200 day moving averages
            <br>
            <strong>Golden Cross:</strong> 
            <span style="color: gold;">⭐ YES</span> = 50-day crossed above 200-day in last 20 days (bullish signal) |
            <span style="color: #8bc34a;">50>200</span> = 50-day is above 200-day (bullish trend) |
            <span style="color: #f44336;">☠️ Death</span> = 50-day crossed below 200-day (bearish signal)
            <br><br>
            <strong>DCF Valuation:</strong>
            <span class="dcf-green">Green (&gt;20%)</span> = Significantly undervalued |
            <span class="dcf-lightgreen">Light Green (0-20%)</span> = Undervalued |
            <span class="dcf-orange">Orange (0 to -20%)</span> = Fairly valued |
            <span class="dcf-red">Red (&lt;-20%)</span> = Overvalued |
            -FCF = Negative cash flow (growth stock)
        </div>

        <p><a class="btn" href="/">Home</a> <a class="btn" href="/scan?market={{ market }}">Refresh</a></p>

        {% if results %}
        <table>
            <tr>
                <th>Symbol</th>
                <th>Chart</th>
                <th>Patterns</th>
                <th>Asc Triangle</th>
                <th>Bull Flag</th>
                <th>Dbl Bottom</th>
                <th>Golden Cross</th>
                <th>Status</th>
                <th>Score</th>
                <th>Price</th>
                <th>Buy Point</th>
                <th>Cup Analysis</th>
                <th>Handle</th>
                <th>RSI</th>
                <th>ADX</th>
                <th>Vol</th>
                <th>SMA50</th>
                <th>SMA200</th>
                <th>MACD</th>
                <th>Stop</th>
                <th>Target</th>
                <th>R:R</th>
                <th>DCF Value</th>
                <th>Margin of Safety</th>
            </tr>
            {% for r in results %}
            <tr>
                <td><strong>{{ r.symbol }}</strong></td>
                <td>
                    <a class="view-btn" href="/chart/{{ r.symbol }}">View</a>
                    <a class="view-btn" href="/journal/new?symbol={{ r.symbol }}&score={{ r.score }}&buy_point={{ r.buy_point }}&stop={{ r.stop_loss }}&target={{ r.target }}&pattern={{ r.pattern_type }}&adx={{ r.adx }}&rsi={{ r.rsi }}" style="background: #4caf50; margin-left: 5px;">Log Trade</a>
                </td>
                <td>{{ r.pattern_count }}</td>
                <td>{% if r.asc_triangle %}<span class="pattern-badge badge-triangle">YES<br>R: ${{ r.asc_triangle.resistance }}</span>{% else %}-{% endif %}</td>
                <td>{% if r.bull_flag %}<span class="pattern-badge badge-flag">FLAG<br>+{{ r.bull_flag.pole_gain|int }}%</span>{% else %}-{% endif %}</td>
                <td>{% if r.double_bottom %}<span class="pattern-badge badge-double-bottom">W<br>${{ r.double_bottom.neckline|round(0)|int }}</span>{% else %}-{% endif %}</td>
                <td>{% if r.golden_cross and r.golden_cross.golden_cross %}<span style="color: gold; font-weight: bold;">⭐ YES<br><span style="font-size:10px;">({{ r.golden_cross.days_since_golden }}d ago)</span></span>{% elif r.golden_cross and r.golden_cross.sma50_above_200 %}<span style="color: #8bc34a;">50>200</span>{% elif r.golden_cross and r.golden_cross.death_cross %}<span style="color: #f44336;">☠️ Death<br><span style="font-size:10px;">({{ r.golden_cross.days_since_death }}d ago)</span></span>{% else %}<span style="color: #888;">-</span>{% endif %}</td>
                <td class="{{ r.status.lower().replace(' ', '-') }}">{{ r.status }}</td>
                <td>{{ r.signal_score }}</td>
                <td>${{ r.current_price }}</td>
                <td>${{ r.buy_point }}</td>
                <td class="cup-analysis">Depth: {{ r.cup_depth }}% / {{ r.cup_days }}d<br>U-shape: {{ r.u_shape }}<br>Symmetry: {{ r.symmetry }}%</td>
                <td>{{ r.handle_pullback }}%</td>
                <td>{{ r.rsi if r.rsi else '-' }}</td>
                <td>{{ r.adx if r.adx else '-' }}</td>
                <td>{{ r.volume_ratio }}x</td>
                <td class="{{ 'check' if r.criteria.above_sma50.passed else 'cross' }}">{{ '✔' if r.criteria.above_sma50.passed else '✘' }}</td>
                <td class="{{ 'check' if r.criteria.above_sma200.passed else 'cross' }}">{{ '✔' if r.criteria.above_sma200.passed else '✘' }}</td>
                <td class="{{ 'check' if r.criteria.macd_bullish.passed else 'cross' }}">{{ '✔' if r.criteria.macd_bullish.passed else '✘' }}</td>
                <td>${{ r.stop_loss }}</td>
                <td>${{ r.target }}</td>
                <td>{{ r.rr_ratio }}:1</td>
                <td class="{% if r.dcf_value == '-FCF' %}dcf-orange{% elif r.margin_of_safety and r.margin_of_safety > 20 %}dcf-green{% elif r.margin_of_safety and r.margin_of_safety > 0 %}dcf-lightgreen{% elif r.margin_of_safety and r.margin_of_safety > -20 %}dcf-orange{% elif r.margin_of_safety %}dcf-red{% endif %}">
                    {% if r.dcf_value == '-FCF' %}-FCF{% elif r.dcf_value %}${{ r.dcf_value }}{% else %}-{% endif %}
                </td>
                <td class="{% if r.margin_of_safety and r.margin_of_safety > 20 %}dcf-green{% elif r.margin_of_safety and r.margin_of_safety > 0 %}dcf-lightgreen{% elif r.margin_of_safety and r.margin_of_safety > -20 %}dcf-orange{% elif r.margin_of_safety %}dcf-red{% endif %}">
                    {% if r.dcf_value == '-FCF' %}N/A{% elif r.margin_of_safety %}{{ r.margin_of_safety }}%{% else %}-{% endif %}
                </td>
            </tr>
            {% endfor %}
        </table>

        <script>
        function toggleSettings() {
            const settings = document.getElementById('screeningSettings');
            settings.style.display = settings.style.display === 'none' ? 'block' : 'none';
        }
        
        function resetDefaults() {
            document.getElementById('t1_vol').value = 0.7;
            document.getElementById('t1_adx').value = 25;
            document.getElementById('t1_rsi_min').value = 50;
            document.getElementById('t1_rsi_max').value = 70;
            document.getElementById('t1_ushape').value = 0.40;
            document.getElementById('t1_rr').value = 1.5;
            document.getElementById('t1_dcf').checked = true;
            document.getElementById('t1_macd').checked = true;
            
            document.getElementById('t2_vol').value = 0.55;
            document.getElementById('t2_adx').value = 25;
            document.getElementById('t2_rsi_min').value = 50;
            document.getElementById('t2_rsi_max').value = 70;
            document.getElementById('t2_ushape').value = 0.35;
            document.getElementById('t2_rr').value = 1.5;
            document.getElementById('t2_dcf').checked = true;
            document.getElementById('t2_macd').checked = true;
            
            document.getElementById('t3_vol').value = 0.3;
            document.getElementById('t3_adx').value = 25;
            document.getElementById('t3_rsi_min').value = 50;
            document.getElementById('t3_rsi_max').value = 70;
            document.getElementById('t3_ushape').value = 0.40;
            document.getElementById('t3_rr').value = 1.5;
            document.getElementById('t3_dcf').checked = false;
            document.getElementById('t3_macd').checked = true;
            
            document.getElementById('excl_rsi_max').value = 80;
            document.getElementById('excl_rsi_min').value = 45;
            document.getElementById('excl_adx').value = 10;
            document.getElementById('excl_ushape').value = 0.05;
            document.getElementById('excl_rr').value = 1.0;
        }
        
        function savePreset() {
            const preset = {
                t1: {
                    vol: parseFloat(document.getElementById('t1_vol').value),
                    adx: parseFloat(document.getElementById('t1_adx').value),
                    rsi_min: parseFloat(document.getElementById('t1_rsi_min').value),
                    rsi_max: parseFloat(document.getElementById('t1_rsi_max').value),
                    ushape: parseFloat(document.getElementById('t1_ushape').value),
                    rr: parseFloat(document.getElementById('t1_rr').value),
                    dcf: document.getElementById('t1_dcf').checked,
                    macd: document.getElementById('t1_macd').checked
                },
                t2: {
                    vol: parseFloat(document.getElementById('t2_vol').value),
                    adx: parseFloat(document.getElementById('t2_adx').value),
                    rsi_min: parseFloat(document.getElementById('t2_rsi_min').value),
                    rsi_max: parseFloat(document.getElementById('t2_rsi_max').value),
                    ushape: parseFloat(document.getElementById('t2_ushape').value),
                    rr: parseFloat(document.getElementById('t2_rr').value),
                    dcf: document.getElementById('t2_dcf').checked,
                    macd: document.getElementById('t2_macd').checked
                },
                t3: {
                    vol: parseFloat(document.getElementById('t3_vol').value),
                    adx: parseFloat(document.getElementById('t3_adx').value),
                    rsi_min: parseFloat(document.getElementById('t3_rsi_min').value),
                    rsi_max: parseFloat(document.getElementById('t3_rsi_max').value),
                    ushape: parseFloat(document.getElementById('t3_ushape').value),
                    rr: parseFloat(document.getElementById('t3_rr').value),
                    dcf: document.getElementById('t3_dcf').checked,
                    macd: document.getElementById('t3_macd').checked
                },
                excl: {
                    rsi_max: parseFloat(document.getElementById('excl_rsi_max').value),
                    rsi_min: parseFloat(document.getElementById('excl_rsi_min').value),
                    adx: parseFloat(document.getElementById('excl_adx').value),
                    ushape: parseFloat(document.getElementById('excl_ushape').value),
                    rr: parseFloat(document.getElementById('excl_rr').value)
                }
            };
            localStorage.setItem('screeningPreset', JSON.stringify(preset));
            alert('Preset saved! It will be loaded automatically next time.');
        }
        
        function loadPreset() {
            const saved = localStorage.getItem('screeningPreset');
            if (saved) {
                const preset = JSON.parse(saved);
                document.getElementById('t1_vol').value = preset.t1.vol;
                document.getElementById('t1_adx').value = preset.t1.adx;
                document.getElementById('t1_rsi_min').value = preset.t1.rsi_min;
                document.getElementById('t1_rsi_max').value = preset.t1.rsi_max;
                document.getElementById('t1_ushape').value = preset.t1.ushape;
                document.getElementById('t1_rr').value = preset.t1.rr;
                document.getElementById('t1_dcf').checked = preset.t1.dcf;
                document.getElementById('t1_macd').checked = preset.t1.macd;
                
                document.getElementById('t2_vol').value = preset.t2.vol;
                document.getElementById('t2_adx').value = preset.t2.adx;
                document.getElementById('t2_rsi_min').value = preset.t2.rsi_min;
                document.getElementById('t2_rsi_max').value = preset.t2.rsi_max;
                document.getElementById('t2_ushape').value = preset.t2.ushape;
                document.getElementById('t2_rr').value = preset.t2.rr;
                document.getElementById('t2_dcf').checked = preset.t2.dcf;
                document.getElementById('t2_macd').checked = preset.t2.macd;
                
                document.getElementById('t3_vol').value = preset.t3.vol;
                document.getElementById('t3_adx').value = preset.t3.adx;
                document.getElementById('t3_rsi_min').value = preset.t3.rsi_min;
                document.getElementById('t3_rsi_max').value = preset.t3.rsi_max;
                document.getElementById('t3_ushape').value = preset.t3.ushape;
                document.getElementById('t3_rr').value = preset.t3.rr;
                document.getElementById('t3_dcf').checked = preset.t3.dcf;
                document.getElementById('t3_macd').checked = preset.t3.macd;
                
                document.getElementById('excl_rsi_max').value = preset.excl.rsi_max;
                document.getElementById('excl_rsi_min').value = preset.excl.rsi_min;
                document.getElementById('excl_adx').value = preset.excl.adx;
                document.getElementById('excl_ushape').value = preset.excl.ushape;
                document.getElementById('excl_rr').value = preset.excl.rr;
            }
        }
        
        // Load preset on page load
        window.addEventListener('load', loadPreset);
        
        function applyScreening() {
            const rows = document.querySelectorAll('table tr');
            console.log('Total rows found:', rows.length);
            let tier1 = 0, tier2 = 0, tier3 = 0, excluded = 0;
            
            // Get parameters
            const t1 = {
                vol: parseFloat(document.getElementById('t1_vol').value),
                adx: parseFloat(document.getElementById('t1_adx').value),
                rsi_min: parseFloat(document.getElementById('t1_rsi_min').value),
                rsi_max: parseFloat(document.getElementById('t1_rsi_max').value),
                ushape: parseFloat(document.getElementById('t1_ushape').value),
                rr: parseFloat(document.getElementById('t1_rr').value),
                dcf: document.getElementById('t1_dcf').checked,
                macd: document.getElementById('t1_macd').checked
            };
            console.log('Tier 1 params:', t1);
            const t2 = {
                vol: parseFloat(document.getElementById('t2_vol').value),
                adx: parseFloat(document.getElementById('t2_adx').value),
                rsi_min: parseFloat(document.getElementById('t2_rsi_min').value),
                rsi_max: parseFloat(document.getElementById('t2_rsi_max').value),
                ushape: parseFloat(document.getElementById('t2_ushape').value),
                rr: parseFloat(document.getElementById('t2_rr').value),
                dcf: document.getElementById('t2_dcf').checked,
                macd: document.getElementById('t2_macd').checked
            };
            const t3 = {
                vol: parseFloat(document.getElementById('t3_vol').value),
                adx: parseFloat(document.getElementById('t3_adx').value),
                rsi_min: parseFloat(document.getElementById('t3_rsi_min').value),
                rsi_max: parseFloat(document.getElementById('t3_rsi_max').value),
                ushape: parseFloat(document.getElementById('t3_ushape').value),
                rr: parseFloat(document.getElementById('t3_rr').value),
                dcf: document.getElementById('t3_dcf').checked,
                macd: document.getElementById('t3_macd').checked
            };
            const excl = {
                rsi_max: parseFloat(document.getElementById('excl_rsi_max').value),
                rsi_min: parseFloat(document.getElementById('excl_rsi_min').value),
                adx: parseFloat(document.getElementById('excl_adx').value),
                ushape: parseFloat(document.getElementById('excl_ushape').value),
                rr: parseFloat(document.getElementById('excl_rr').value)
            };
            
            rows.forEach(row => {
                const cells = row.cells;
                if (!cells || cells.length < 10 || row.querySelector('th')) return; // Skip header row
                
                // Parse values
                const rsi = parseFloat(cells[13]?.textContent) || 0;
                const adx = parseFloat(cells[14]?.textContent) || 0;
                const volText = cells[15]?.textContent || '0';
                const volMult = parseFloat(volText.replace('x', '')) || 0;
                const cupAnalysis = cells[11]?.textContent || '';
                const uShapeMatch = cupAnalysis.match(/U-shape:\s*([\d.]+)/);
                const uShape = uShapeMatch ? parseFloat(uShapeMatch[1]) : 0;
                const rrText = cells[21]?.textContent || '0:1';
                const rr = parseFloat(rrText.split(':')[0]) || 0;
                const dcfText = cells[23]?.textContent || '0%';
                const dcfMargin = parseFloat(dcfText.replace('%', '').replace(',', '')) || 0;
                const macdCheck = cells[18]?.textContent?.includes('✔') || false;
                
                // Debug first row only
                if (cells[0]?.textContent === 'EXR') {
                    console.log('Sample values for EXR:', {
                        rsi, adx, volMult, uShape, rr, dcfMargin, macdCheck,
                        cell13: cells[13]?.textContent,
                        cell14: cells[14]?.textContent,
                        cell15: cells[15]?.textContent,
                        cell11: cells[11]?.textContent,
                        cell21: cells[21]?.textContent,
                        cell23: cells[23]?.textContent,
                        cell18: cells[18]?.textContent
                    });
                }
                
                // Remove existing badges
                const existingBadge = cells[0].querySelector('.tier-badge');
                if (existingBadge) existingBadge.remove();
                
                // Auto disqualifiers
                if (rsi > excl.rsi_max || rsi < excl.rsi_min || adx < excl.adx || 
                    uShape < excl.ushape || rr < excl.rr) {
                    row.style.opacity = '0.3';
                    row.style.backgroundColor = '';
                    row.dataset.tier = 'excluded';
                    excluded++;
                    return;
                }
                
                // Tier 1
                if (volMult >= t1.vol && adx >= t1.adx && rsi >= t1.rsi_min && rsi <= t1.rsi_max && 
                    uShape >= t1.ushape && rr >= t1.rr && 
                    (!t1.dcf || dcfMargin > 0) && (!t1.macd || macdCheck)) {
                    row.style.backgroundColor = '#1b5e20';
                    row.style.opacity = '1';
                    row.dataset.tier = '1';
                    const badge = document.createElement('span');
                    badge.className = 'tier-badge tier1';
                    badge.textContent = 'TIER 1';
                    cells[0].insertBefore(badge, cells[0].firstChild);
                    tier1++;
                }
                // Tier 2
                else if (volMult >= t2.vol && adx >= t2.adx && rsi >= t2.rsi_min && rsi <= t2.rsi_max && 
                         uShape >= t2.ushape && rr >= t2.rr && 
                         (!t2.dcf || dcfMargin > 0) && (!t2.macd || macdCheck)) {
                    row.style.backgroundColor = '#0d47a1';
                    row.style.opacity = '1';
                    row.dataset.tier = '2';
                    const badge = document.createElement('span');
                    badge.className = 'tier-badge tier2';
                    badge.textContent = 'TIER 2';
                    cells[0].insertBefore(badge, cells[0].firstChild);
                    tier2++;
                }
                // Tier 3
                else if (volMult >= t3.vol && adx >= t3.adx && rsi >= t3.rsi_min && rsi <= t3.rsi_max && 
                         uShape >= t3.ushape && rr >= t3.rr && 
                         (!t3.dcf || dcfMargin > 0) && (!t3.macd || macdCheck)) {
                    row.style.backgroundColor = '#e65100';
                    row.style.opacity = '1';
                    row.dataset.tier = '3';
                    const badge = document.createElement('span');
                    badge.className = 'tier-badge tier3';
                    badge.textContent = 'TIER 3';
                    cells[0].insertBefore(badge, cells[0].firstChild);
                    tier3++;
                }
                else {
                    row.style.opacity = '0.5';
                    row.style.backgroundColor = '';
                    row.dataset.tier = 'other';
                }
            });
            
            document.getElementById('filterStatus').innerHTML = 
                `🥇 Tier 1: ${tier1} | 🥈 Tier 2: ${tier2} | 🥉 Tier 3: ${tier3} | ❌ Excluded: ${excluded}`;
        }
        
        function showAll() {
            const rows = document.querySelectorAll('table tr');
            rows.forEach(row => {
                if (row.querySelector('th')) return; // Skip header
                row.style.display = '';
                row.style.opacity = '1';
            });
            document.getElementById('filterStatus').textContent = 'Showing all results';
        }
        
        function showTier(tier) {
            const rows = document.querySelectorAll('table tr');
            let count = 0;
            rows.forEach(row => {
                if (row.querySelector('th')) return; // Skip header
                if (row.dataset.tier === String(tier)) {
                    row.style.display = '';
                    row.style.opacity = '1';
                    count++;
                } else {
                    row.style.display = 'none';
                }
            });
            document.getElementById('filterStatus').textContent = `Showing Tier ${tier} only (${count} stocks)`;
        }
        </script>

        {% else %}
        <p style="color: #ff9800; font-size: 18px;">No cup & handle patterns found in current scan.</p>
        {% endif %}
    </div>
    </body>
    </html>
    """

@app.route("/chart")
def chart_search():
    """Handle search form - redirect to chart page."""
    symbol = request.args.get('symbol', '').strip().upper()
    if not symbol:
        return "Please enter a stock symbol", 400
    from flask import redirect
    return redirect(f"/chart/{symbol}")


@app.route("/saved-results")
def saved_results():
    """View saved scan results with adjustable screening."""
    import json
    from datetime import datetime
    
    scan_file = Path('data/last_scan_results.json')
    if not scan_file.exists():
        return """
        <html>
        <head><title>No Saved Results</title></head>
        <body style="font-family: Arial; background: #1a1a2e; color: #eee; padding: 40px; text-align: center;">
            <h1>No Saved Scan Results</h1>
            <p>Run a scan first to save results.</p>
            <a href="/" style="color: #00d4ff;">Go to Home</a>
        </body>
        </html>
        """
    
    with open(scan_file, 'r') as f:
        scan_data = json.load(f)
    
    results = scan_data['results']
    market_name = scan_data['market']
    timestamp = scan_data['timestamp']
    
    # Reuse the same HTML template from scan() but with saved data
    return render_template_string(SCAN_RESULTS_TEMPLATE, 
                                  results=results, 
                                  now=timestamp,
                                  market=market_name.lower().replace(' ', '_'),
                                  market_name=market_name,
                                  is_saved=True)


@app.route("/chart/<symbol>")
def chart(symbol):
    """Generate detailed chart view with all info."""
    try:
        # Parse SMA parameter: ?sma=50,200 or ?sma=all or ?sma=none
        sma_param = request.args.get('sma', '50,200')
        if sma_param.lower() == 'all':
            show_smas = [13, 26, 40, 50, 200]
        elif sma_param.lower() == 'none':
            show_smas = []
        else:
            try:
                show_smas = [int(x.strip())
                             for x in sma_param.split(',') if x.strip()]
            except:
                show_smas = [50, 200]

        # Parse CTO parameter
        show_cto = request.args.get('cto') == '1'

        # Parse SuperTrend parameter
        show_supertrend = request.args.get('supertrend') == '1'

        # Parse SMC parameter
        show_smc = request.args.get('smc') == '1'

        # Parse EDGAR parameter
        show_edgar = request.args.get('edgar') == '1'

        ticker = yf.Ticker(symbol)
        try:
            # Fetch enough data so 200 SMA covers the full displayed period
            # Need: 252 (display) + 200 (SMA warmup) = 452 days minimum
            # Request 500 days to be safe
            from datetime import datetime, timedelta
            end_date = datetime.now()
            start_date = end_date - timedelta(days=700)  # ~500 trading days
            df_full = ticker.history(start=start_date, end=end_date)
        except Exception as hist_err:
            return f"Error fetching history for {symbol}: {hist_err}"

        if df_full is None or df_full.empty:
            return f"No data available for {symbol}"

        # Calculate SMAs on full data first (before trimming)
        df_full['SMA13'] = df_full['Close'].rolling(13).mean()
        df_full['SMA26'] = df_full['Close'].rolling(26).mean()
        df_full['SMA40'] = df_full['Close'].rolling(40).mean()
        df_full['SMA50'] = df_full['Close'].rolling(50).mean()
        df_full['SMA200'] = df_full['Close'].rolling(200).mean()

        # Trim to ~1 year for display (SMAs are pre-calculated so 200 SMA has full coverage)
        display_days = 252  # ~1 year of trading days

        # Make sure we have enough data for SMA200 to cover display period
        min_required = display_days + 200
        if len(df_full) >= min_required:
            df = df_full.tail(display_days).copy()
        elif len(df_full) > display_days:
            # Not enough for full SMA200, but take what we can
            df = df_full.tail(display_days).copy()
        else:
            df = df_full.copy()

        # Get all data - detect patterns on the DISPLAY data so indices match
        company_info = get_company_info(symbol)
        cup_pattern = detect_cup_and_handle(df)
        asc_triangle = detect_ascending_triangle(df)
        bull_flag = detect_bull_flag(df)
        double_bottom = detect_double_bottom(df)
        dcf_data = calculate_dcf_value(symbol)

        # Get analysis
        analysis = None
        buy_point = None
        if cup_pattern:
            analysis = check_breakout_criteria(
                df.copy(), cup_pattern, asc_triangle, bull_flag)
            buy_point = analysis['buy_point'] if analysis else None

        # Get options strategy recommendation
        # Allow custom budget via ?budget=500
        options_budget = float(request.args.get('budget', 375))
        options_strategy = suggest_bull_call_spread(
            symbol,
            company_info['current_price'] or df['Close'].iloc[-1],
            analysis,
            budget=options_budget,
            df=df
        )
        
        # Calculate expected move analysis
        pattern_target = None
        if cup_pattern and 'target' in cup_pattern:
            pattern_target = cup_pattern['target']
        expected_move = calculate_expected_move(
            symbol,
            company_info['current_price'] or df['Close'].iloc[-1],
            pattern_target
        )

        # Detect double bottom
        double_bottom = detect_double_bottom(df)

        # Fetch EDGAR financials if requested
        edgar_financials = {}
        if show_edgar:
            try:
                from edgar import set_identity, Company
                set_identity("PatternScanner rjdrouse@gmail.com")
                company = Company(symbol)
                filings = company.get_filings(form='10-Q').latest(1)
                if filings:
                    filing = list(filings)[0] if hasattr(filings, '__iter__') else filings
                    edgar_financials = {
                        'filing_date': filing.filing_date,
                        'filing_url': filing.homepage_url if hasattr(filing, 'homepage_url') else f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={company.cik}&type=10-Q&dateb=&owner=exclude&count=10",
                        'accession_number': filing.accession_no,
                    }
                else:
                    edgar_financials = {'error': 'No 10-Q filings found'}
            except Exception as e:
                edgar_financials = {'error': f'EDGAR fetch failed: {str(e)}'}

        # Generate unified chart with SMA toggle
        # Pass df which now has pre-calculated SMAs
        chart_base64 = generate_unified_chart(
            symbol, df, cup_pattern, asc_triangle, bull_flag, double_bottom, buy_point, show_smas=show_smas, show_cto=show_cto, show_supertrend=show_supertrend, show_smc=show_smc)

        html = """
        <html>
        <head>
            <title>{{ symbol }} - {{ company.name }} | Pattern Analysis</title>
            <style>
                body { font-family: 'Segoe UI', Arial, sans-serif; margin: 20px; background: #1a1a2e; color: #eee; }
                h1, h2, h3 { color: #00d4ff; }
                .container { max-width: 1400px; margin: auto; }
                .btn { padding: 10px 20px; background: #667eea; color: white; text-decoration: none;
                       border-radius: 5px; margin: 5px; display: inline-block; }
                img { max-width: 100%; border-radius: 10px; margin: 20px 0; box-shadow: 0 4px 20px rgba(0,0,0,0.5); }
                
                .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 20px; margin: 20px 0; }
                .card { background: #16213e; padding: 20px; border-radius: 10px; }
                .card h3 { margin-top: 0; border-bottom: 1px solid #333; padding-bottom: 10px; }
                
                table { width: 100%; border-collapse: collapse; margin: 10px 0; }
                td, th { padding: 8px 12px; text-align: left; border-bottom: 1px solid #333; }
                th { color: #888; font-weight: normal; width: 40%; }
                
                .pass { color: #00c853; font-weight: bold; }
                .fail { color: #f44336; }
                .detected { color: #00c853; font-weight: bold; }
                .not-found { color: #888; }
                
                .company-header { display: flex; align-items: center; gap: 20px; margin-bottom: 20px; }
                .company-header h1 { margin: 0; }
                .company-meta { color: #888; font-size: 14px; }
                
                .description { background: #0f0f23; padding: 15px; border-radius: 8px; line-height: 1.6; 
                              max-height: 150px; overflow-y: auto; font-size: 14px; }
                
                .dcf-green { color: #00c853; }
                .dcf-lightgreen { color: #8bc34a; }
                .dcf-orange { color: #ff9800; }
                .dcf-red { color: #f44336; }
                
                .options-card { grid-column: span 2; }
                .options-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; }
                @media (max-width: 1200px) {
                    .options-grid { grid-template-columns: 1fr 1fr; }
                }
                @media (max-width: 800px) {
                    .options-grid { grid-template-columns: 1fr; }
                }
                
                .badge { display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; 
                        font-weight: bold; margin: 2px; }
                .badge-triangle { background: #9c27b0; color: white; }
                .badge-flag { background: #e91e63; color: white; }
                .badge-cup { background: #00c853; color: white; }
                
                .chart-legend { background: #0f0f23; padding: 10px 15px; border-radius: 8px; margin-top: 10px;
                               font-size: 12px; display: flex; gap: 20px; flex-wrap: wrap; }
                .legend-item { display: flex; align-items: center; gap: 5px; }
                .legend-color { width: 20px; height: 3px; }
                .navbar { background: #16213e; padding: 10px; border-radius: 8px; margin-bottom: 20px; }
                .navbar a { color: #00d4ff; text-decoration: none; margin: 0 15px; }
                .navbar a:hover { text-decoration: underline; }
                .track-form { background: #16213e; padding: 15px; border-radius: 8px; margin: 20px 0; }
                .track-form input, .track-form button { padding: 8px; margin: 5px; border-radius: 4px; border: none; }
                .track-form input { background: #0f0f23; color: #fff; }
                .track-form button { background: #00c853; color: #000; cursor: pointer; }
            </style>
        </head>
        <body>
        <div class="container">
            <div class="navbar">
                <a href="/">Home</a>
                <a href="/tracked">Tracked Stocks</a>
            </div>
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    {% for category, message in messages %}
                        <div style="padding: 10px; border-radius: 5px; margin: 10px 0; {% if category == 'success' %}background: #00c853; color: #000;{% else %}background: #f44336;{% endif %}">{{ message }}</div>
                    {% endfor %}
                {% endif %}
            {% endwith %}
            <p><a class="btn" href="javascript:history.back()">← Back to Results</a></p>
            
            <!-- Company Header -->
            <div class="company-header">
                <div>
                    <h1>{{ symbol }} - {{ company.name }}</h1>
                    <div class="company-meta">
                        {{ company.exchange }} | {{ company.sector }} | {{ company.industry }} | 
                        Market Cap: {{ company.market_cap_fmt }}
                    </div>
                </div>
                <div>
                    <a class="btn" href="/journal/new?symbol={{ symbol }}&planned_entry={{ company.current_price }}&pattern={{ 'cup_handle' if cup_pattern else 'mixed' }}&adx={{ analysis.criteria.adx_strong.value if analysis else '' }}&rsi={{ analysis.criteria.rsi_healthy.value if analysis else '' }}&sector={{ company.sector }}" 
                       style="background: #4caf50; padding: 12px 24px; font-size: 14px;">
                        📝 Log Trade
                    </a>
                </div>
            </div>
            
            <!-- SMA Toggle Controls -->
            <div class="card" style="margin-bottom: 15px; padding: 15px;">
                <strong>📈 Indicators:</strong>
                <a class="btn" style="padding: 5px 12px; font-size: 12px; {% if show_smas == [50, 200] %}background: #00c853;{% endif %}"
                   href="/chart/{{ symbol }}?sma=50,200">50 & 200</a>
                <a class="btn" style="padding: 5px 12px; font-size: 12px; {% if 13 in show_smas and 26 in show_smas %}background: #00c853;{% endif %}"
                   href="/chart/{{ symbol }}?sma=all">All (13,26,40,50,200)</a>
                <a class="btn" style="padding: 5px 12px; font-size: 12px;"
                   href="/chart/{{ symbol }}?sma=13,26,50">Short-term (13,26,50)</a>
                <a class="btn" style="padding: 5px 12px; font-size: 12px;"
                   href="/chart/{{ symbol }}?sma=none">None</a>
                <a class="btn" style="padding: 5px 12px; font-size: 12px; {% if show_cto %}background: #00c853;{% endif %}"
                   href="/chart/{{ symbol }}?cto=1&sma={{ show_smas|join(',') }}">CTO Larsson</a>
                <a class="btn" style="padding: 5px 12px; font-size: 12px; {% if show_supertrend %}background: #00c853;{% endif %}"
                   href="/chart/{{ symbol }}?supertrend=1&sma={{ show_smas|join(',') }}">SuperTrend</a>
                <a class="btn" style="padding: 5px 12px; font-size: 12px; {% if show_smc %}background: #00c853;{% endif %}"
                   href="/chart/{{ symbol }}?smc=1&sma={{ show_smas|join(',') }}">SMC</a>
                <span style="color: #888; font-size: 12px; margin-left: 10px;">
                    Currently showing: {% if show_smas %}{{ show_smas|join(', ') }}{% else %}None{% endif %}
                </span>
            </div>
            
            <!-- Chart -->
            <img src="data:image/png;base64,{{ chart }}" alt="{{ symbol }} Chart">
            
            <div class="chart-legend">
                <div class="legend-item"><div class="legend-color" style="background: cyan;"></div> Price</div>
                {% if 13 in show_smas %}<div class="legend-item"><div class="legend-color" style="background: #ff6b6b;"></div> SMA 13</div>{% endif %}
                {% if 26 in show_smas %}<div class="legend-item"><div class="legend-color" style="background: #ffd93d;"></div> SMA 26</div>{% endif %}
                {% if 40 in show_smas %}<div class="legend-item"><div class="legend-color" style="background: #6bcb77;"></div> SMA 40</div>{% endif %}
                {% if 50 in show_smas %}<div class="legend-item"><div class="legend-color" style="background: #4d96ff;"></div> SMA 50</div>{% endif %}
                {% if 200 in show_smas %}<div class="legend-item"><div class="legend-color" style="background: #ff8c00;"></div> SMA 200</div>{% endif %}
                {% if 50 in show_smas and 200 in show_smas %}<div class="legend-item"><div class="legend-color" style="background: gold;"></div> ⭐ Golden Cross (50>200)</div>{% endif %}
                {% if show_supertrend %}<div class="legend-item"><div class="legend-color" style="background: green;"></div> SuperTrend Up</div>
                <div class="legend-item"><div class="legend-color" style="background: red;"></div> SuperTrend Down</div>
                <div class="legend-item"><span style="color: lime;">▲</span> ST Buy</div>
                <div class="legend-item"><span style="color: red;">▼</span> ST Sell</div>{% endif %}
                {% if show_smc %}<div class="legend-item"><div class="legend-color" style="background: #00ff00;"></div> Bullish OB</div>
                <div class="legend-item"><div class="legend-color" style="background: #ff0000;"></div> Bearish OB</div>
                <div class="legend-item"><div class="legend-color" style="background: #ffff00;"></div> FVG</div>
                <div class="legend-item"><span style="color: #ff00ff;">↗</span> BOS</div>
                <div class="legend-item"><span style="color: #00ffff;">↘</span> CHoCH</div>{% endif %}
                <div class="legend-item"><div class="legend-color" style="background: lime;"></div> Cup & Handle</div>
                <div class="legend-item"><div class="legend-color" style="background: magenta;"></div> Ascending Triangle</div>
                <div class="legend-item"><div class="legend-color" style="background: #ff9800;"></div> Bull Flag</div>
                <div class="legend-item"><div class="legend-color" style="background: #00ff00; height: 3px;"></div> Buy Point</div>
            </div>

            <!-- Track Stock Form -->
            {% if analysis %}
            <div class="track-form">
                <h3>📈 Track This Stock</h3>
                <form action="/track" method="post">
                    <input type="hidden" name="ticker" value="{{ symbol }}">
                    <input type="hidden" name="buy_point" value="{{ analysis.buy_point }}">
                    <input type="hidden" name="rsi_min" value="50">
                    <input type="hidden" name="rsi_max" value="70">
                    <input type="hidden" name="volume_multiple" value="2.0">
                    <input type="hidden" name="breakeven_move" value="{% if options.breakeven_move_pct %}{{ options.breakeven_move_pct|round(1) }}{% elif cup_pattern %}{{ cup_pattern.cup_depth_pct|round(1) }}{% else %}0{% endif %}">
                    <label for="email">Email (required): </label>
                    <input type="email" name="email" id="email" required placeholder="your@email.com" value="{{ analysis.email if analysis.email else '' }}">
                    <button type="submit">Start Tracking</button>
                </form>
                <p style="font-size: 12px; color: #888; margin-top: 10px;">
                    Will track for breakout above ${{ analysis.buy_point }}, RSI 50-70, 2x volume, and email alerts.
                    Breakeven move: {% if options.breakeven_move_pct %}{{ options.breakeven_move_pct|round(1) }}%{% elif cup_pattern %}{{ cup_pattern.cup_depth_pct|round(1) }}% (cup depth){% else %}0%{% endif %}.
                </p>
            </div>
            {% endif %}

            <div class="grid">
                <!-- Breakout Criteria -->
                <div class="card">
                    <h3>📊 Breakout Criteria</h3>
                    {% if analysis %}
                    <table>
                        <tr>
                            <th>Above SMA 50</th>
                            <td class="{{ 'pass' if analysis.criteria.above_sma50.passed else 'fail' }}">
                                {{ 'Yes' if analysis.criteria.above_sma50.passed else 'No' }}
                                <span style="color:#888; font-size:12px;">({{ analysis.criteria.above_sma50.value }})</span>
                            </td>
                        </tr>
                        <tr>
                            <th>Above SMA 200</th>
                            <td class="{{ 'pass' if analysis.criteria.above_sma200.passed else 'fail' }}">
                                {{ 'Yes' if analysis.criteria.above_sma200.passed else 'No' }}
                                <span style="color:#888; font-size:12px;">({{ analysis.criteria.above_sma200.value }})</span>
                            </td>
                        </tr>
                        <tr>
                            <th>Volume Spike</th>
                            <td class="{{ 'pass' if analysis.criteria.volume_spike.passed else 'fail' }}">
                                {{ analysis.criteria.volume_spike.value }} {{ analysis.criteria.volume_spike.requirement }}
                            </td>
                        </tr>
                        <tr>
                            <th>Handle Vol Contraction</th>
                            <td class="{{ 'pass' if analysis.criteria.handle_vol_contraction.passed else 'fail' }}">
                                {{ analysis.criteria.handle_vol_contraction.value }}
                            </td>
                        </tr>
                        <tr>
                            <th>MACD Bullish</th>
                            <td class="{{ 'pass' if analysis.criteria.macd_bullish.passed else 'fail' }}">
                                {{ 'Yes' if analysis.criteria.macd_bullish.passed else 'No' }}
                            </td>
                        </tr>
                        <tr>
                            <th>ADX Strong (>25)</th>
                            <td class="{{ 'pass' if analysis.criteria.adx_strong.passed else 'fail' }}">
                                {{ 'Yes' if analysis.criteria.adx_strong.passed else 'No' }}
                                <span style="color:#888; font-size:12px;">({{ analysis.criteria.adx_strong.value }})</span>
                            </td>
                        </tr>
                        <tr>
                            <th>RSI Healthy (50-70)</th>
                            <td class="{{ 'pass' if analysis.criteria.rsi_healthy.passed else 'fail' }}">
                                {{ 'Yes' if analysis.criteria.rsi_healthy.passed else 'No' }}
                                <span style="color:#888; font-size:12px;">({{ analysis.criteria.rsi_healthy.value }})</span>
                            </td>
                        </tr>
                    </table>
                    {% else %}
                    <p>Analysis not available</p>
                    {% endif %}
                </div>
                
                <!-- Pattern Detection -->
                <div class="card">
                    <h3>🔍 Additional Pattern Detection</h3>
                    <table>
                        <tr>
                            <th>Cup & Handle</th>
                            <td>
                                {% if cup_pattern %}
                                <span class="detected">DETECTED</span>
                                <span class="badge badge-cup">✓</span>
                                {% else %}
                                <span class="not-found">Not Found</span>
                                {% endif %}
                            </td>
                        </tr>
                        <tr>
                            <th>Ascending Triangle</th>
                            <td>
                                {% if asc_triangle %}
                                <span class="detected">DETECTED</span>
                                <span class="badge badge-triangle">△</span><br>
                                <span style="color:#888; font-size:12px;">
                                    Resistance: ${{ asc_triangle.resistance }}<br>
                                    Target: ${{ asc_triangle.target }}
                                </span>
                                {% else %}
                                <span class="not-found">Not Found</span>
                                {% endif %}
                            </td>
                        </tr>
                        <tr>
                            <th>Bull Flag/Pennant</th>
                            <td>
                                {% if bull_flag %}
                                <span class="detected">DETECTED</span>
                                <span class="badge badge-flag">⚑</span><br>
                                <span style="color:#888; font-size:12px;">
                                    Pole: +{{ bull_flag.pole_gain }}%<br>
                                    Target: ${{ bull_flag.target }}
                                </span>
                                {% else %}
                                <span class="not-found">Not Found</span>
                                {% endif %}
                            </td>
                        </tr>
                        <tr>
                            <th>Double Bottom (W)</th>
                            <td>
                                {% if double_bottom %}
                                <span class="detected">DETECTED</span>
                                <span class="badge" style="background:#ec4899; color:white;">W</span><br>
                                <span style="color:#888; font-size:12px;">
                                    Neckline: ${{ double_bottom.neckline|round(2) }}<br>
                                    Target: ${{ double_bottom.target|round(2) }}<br>
                                    Depth: {{ double_bottom.depth_pct }}%<br>
                                    {% if double_bottom.breakout_confirmed %}<span style="color:#00c853;">✅ Breakout!</span>{% else %}<span style="color:#ff9800;">⏳ Forming</span>{% endif %}
                                </span>
                                {% else %}
                                <span class="not-found">Not Found</span>
                                {% endif %}
                            </td>
                        </tr>
                        <tr>
                            <th>Golden Cross (50>200)</th>
                            <td>
                                {% if analysis and analysis.golden_cross and analysis.golden_cross.golden_cross %}
                                <span style="color: gold; font-weight: bold;">⭐ DETECTED</span><br>
                                <span style="color:#888; font-size:12px;">
                                    {{ analysis.golden_cross.days_since_golden }} days ago
                                </span>
                                {% elif analysis and analysis.golden_cross and analysis.golden_cross.sma50_above_200 %}
                                <span style="color: #8bc34a;">50 > 200 (Bullish)</span>
                                {% elif analysis and analysis.golden_cross and analysis.golden_cross.death_cross %}
                                <span style="color: #f44336;">☠️ Death Cross</span><br>
                                <span style="color:#888; font-size:12px;">
                                    {{ analysis.golden_cross.days_since_death }} days ago
                                </span>
                                {% elif analysis and analysis.golden_cross %}
                                <span style="color: #f44336;">50 < 200 (Bearish)</span>
                                {% else %}
                                <span class="not-found">N/A</span>
                                {% endif %}
                            </td>
                        </tr>
                    </table>
                    <p style="color:#888; font-size:11px; margin-top:15px;">
                        Patterns are drawn on the chart if detected<br>
                        (pink = triangle, orange = flag, gold star = golden cross)
                    </p>
                </div>
                
                <!-- Cup & Handle Details -->
                <div class="card">
                    <h3>🏆 Cup & Handle Formation</h3>
                    {% if cup_pattern %}
                    <table>
                        <tr><th>Cup Depth</th><td>{{ cup_pattern.cup_depth_pct|round(1) }}%</td></tr>
                        <tr><th>Cup Duration</th><td>{{ cup_pattern.cup_length_days }} days</td></tr>
                        <tr><th>Left Rim</th><td>${{ cup_pattern.left_rim_price|round(2) }}</td></tr>
                        <tr><th>Right Rim</th><td>${{ cup_pattern.right_rim_price|round(2) }}</td></tr>
                        <tr><th>Cup Bottom</th><td>${{ cup_pattern.bottom_price|round(2) }}</td></tr>
                        <tr><th>U-Shape Score</th><td>{{ cup_pattern.u_shape_score }} (1.0 = perfect U)</td></tr>
                        <tr><th>Symmetry</th><td>{{ cup_pattern.symmetry_pct }}%</td></tr>
                        <tr><th>Handle Pullback</th><td>{{ cup_pattern.handle_decline_pct|round(1) }}%</td></tr>
                        <tr><th>Handle Days</th><td>{{ cup_pattern.handle_days }}</td></tr>
                    </table>
                    {% if analysis %}
                    <table style="margin-top:15px; border-top: 2px solid #00d4ff;">
                        <tr><th>Buy Point</th><td style="color:#00ff00; font-weight:bold;">${{ analysis.buy_point }}</td></tr>
                        <tr><th>Stop Loss</th><td style="color:#f44336;">${{ analysis.stop_loss }}</td></tr>
                        <tr><th>Target</th><td style="color:#00c853;">${{ analysis.target }}</td></tr>
                        <tr><th>Risk:Reward</th><td>{{ analysis.rr_ratio }}:1</td></tr>
                    </table>
                    {% endif %}
                    {% else %}
                    <p>Cup & Handle pattern not detected</p>
                    {% endif %}
                </div>
                
                <!-- DCF Valuation -->
                <div class="card">
                    <h3>💰 DCF Valuation</h3>
                    {% if dcf_data.status == 'success' %}
                    <table>
                        <tr><th>Intrinsic Value</th>
                            <td class="{% if dcf_data.margin and dcf_data.margin > 20 %}dcf-green{% elif dcf_data.margin and dcf_data.margin > 0 %}dcf-lightgreen{% elif dcf_data.margin and dcf_data.margin > -20 %}dcf-orange{% else %}dcf-red{% endif %}" style="font-size:18px; font-weight:bold;">
                                ${{ dcf_data.dcf_value }}
                            </td>
                        </tr>
                        <tr><th>Current Price</th><td>${{ dcf_data.current_price }}</td></tr>
                        <tr><th>Margin of Safety</th>
                            <td class="{% if dcf_data.margin and dcf_data.margin > 20 %}dcf-green{% elif dcf_data.margin and dcf_data.margin > 0 %}dcf-lightgreen{% elif dcf_data.margin and dcf_data.margin > -20 %}dcf-orange{% else %}dcf-red{% endif %}">
                                {{ dcf_data.margin }}%
                                {% if dcf_data.margin and dcf_data.margin > 20 %}(Undervalued 🟢)
                                {% elif dcf_data.margin and dcf_data.margin > 0 %}(Slightly Undervalued)
                                {% elif dcf_data.margin and dcf_data.margin > -20 %}(Fairly Valued 🟡)
                                {% else %}(Overvalued 🔴){% endif %}
                            </td>
                        </tr>
                        <tr><th>Free Cash Flow</th><td>{{ dcf_data.fcf_fmt }}</td></tr>
                        <tr><th>Growth Rate (5yr)</th><td>{{ dcf_data.growth_rate }}%</td></tr>
                        <tr><th>Discount Rate</th><td>{{ dcf_data.discount_rate }}%</td></tr>
                        <tr><th>Terminal Growth</th><td>{{ dcf_data.terminal_growth }}%</td></tr>
                    </table>
                    {% elif dcf_data.status == 'negative_fcf' %}
                    <p style="color:#ff9800;">⚠️ Negative Free Cash Flow</p>
                    <p style="color:#888; font-size:13px;">This is common for growth companies reinvesting heavily. DCF not applicable.</p>
                    {% else %}
                    <p style="color:#888;">DCF data not available</p>
                    {% endif %}
                </div>
                
                <!-- Options Strategy: IV-Aware Selector -->
                <div class="card" style="grid-column: span 2;">
                    <h3>📈 Options Strategy: {{ options.strategy if options.status == 'success' else 'Analysis' }}</h3>
                    {% if options.status == 'success' or options.status == 'regime_override' %}
                    <!-- Options Conditions Summary -->
                    <div style="margin-bottom: 15px; padding: 12px; background: #0a0a1a; border-radius: 8px; border-left: 3px solid #00d4ff;">
                        <strong style="color: #00d4ff;">Options Conditions:</strong>
                        <span style="color: #fff;">IV Rank: {{ options.iv_rank }}% | VIX: {{ options.vix }} | Regime: {{ options.regime }}</span><br>
                        {% if options.trend_regime %}
                        <strong style="color: #ff9800;">Trend Regime: {{ options.trend_regime }}</strong>
                        <span style="font-size: 11px; color: #aaa;">({{ options.trend_regime_desc }})</span><br>
                        {% endif %}
                        {% if options.status == 'regime_override' %}
                        <div style="margin-top: 10px; padding: 10px; background: #3d1a1a; border-left: 3px solid #f44336; border-radius: 5px;">
                            <span style="color: #f44336; font-weight: bold;">{{ options.message }}</span>
                        </div>
                        {% else %}
                        <strong style="color: #00c853;">Strategy Selected: {{ options.strategy }}</strong><br>
                        <span style="font-size: 12px; color: #aaa;">{{ options.rationale }}</span>
                        {% endif %}
                    </div>
                    
                    {% if options.status == 'success' %}
                    {% if options.strategy == 'Long Call' %}
                    <!-- Long Call Strategy -->
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                        <div>
                            <h4 style="color: #00d4ff; margin-top: 0;">📋 Trade Setup</h4>
                            <table>
                                <tr><th>Expiration</th><td>{{ options.expiration }} ({{ options.days_to_exp }} days)</td></tr>
                                <tr><th>Strategy</th><td style="color: #00c853; font-weight: bold;">{{ options.strategy }}</td></tr>
                                <tr>
                                    <th>BUY Call</th>
                                    <td style="color: #4caf50;">
                                        ${{ options.buy_strike }} @ ${{ options.buy_premium }}<br>
                                        <span style="font-size: 11px; color: #888;">
                                            Δ {{ options.buy_delta }} | Vol: {{ options.buy_volume }} | OI: {{ options.buy_oi }}
                                            {% if options.buy_iv %}| IV: {{ options.buy_iv }}%{% endif %}
                                        </span>
                                    </td>
                                </tr>
                                <tr><th>Contracts</th><td style="font-weight: bold;">{{ options.contracts }}</td></tr>
                                <tr><th>Total Cost</th><td style="color: #ff9800;">${{ options.total_cost }}</td></tr>
                            </table>
                        </div>
                        <div>
                            <h4 style="color: #00d4ff; margin-top: 0;">💰 Risk & Reward</h4>
                            <table>
                                <tr><th>Max Loss</th><td style="color: #f44336;">${{ options.max_loss_total }}</td></tr>
                                <tr><th>Max Gain</th><td style="color: #00c853; font-weight: bold;">{{ options.max_gain_total }}</td></tr>
                                <tr><th>Budget</th><td>${{ options.budget }}</td></tr>
                            </table>
                        </div>
                    </div>
                    
                    {% elif options.strategy == 'Cash-Secured Put' %}
                    <!-- Cash-Secured Put Strategy -->
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                        <div>
                            <h4 style="color: #00d4ff; margin-top: 0;">📋 Trade Setup</h4>
                            <table>
                                <tr><th>Expiration</th><td>{{ options.expiration }} ({{ options.days_to_exp }} days)</td></tr>
                                <tr><th>Strategy</th><td style="color: #00c853; font-weight: bold;">{{ options.strategy }}</td></tr>
                                <tr>
                                    <th>SELL Put</th>
                                    <td style="color: #f44336;">
                                        ${{ options.sell_strike }} @ ${{ options.sell_premium }}<br>
                                        <span style="font-size: 11px; color: #888;">
                                            Δ {{ options.sell_delta }} | Vol: {{ options.sell_volume }} | OI: {{ options.sell_oi }}
                                            {% if options.sell_iv %}| IV: {{ options.sell_iv }}%{% endif %}
                                        </span>
                                    </td>
                                </tr>
                                <tr><th>Premium Collected</th><td style="color: #00c853; font-weight: bold;">${{ options.premium_collected }}</td></tr>
                                <tr><th>Effective Entry</th><td>${{ options.effective_entry }}</td></tr>
                                <tr><th>Breakeven</th><td>${{ options.breakeven }}</td></tr>
                            </table>
                        </div>
                        <div>
                            <h4 style="color: #00d4ff; margin-top: 0;">💰 Risk & Reward</h4>
                            <table>
                                <tr><th>Max Gain</th><td style="color: #00c853; font-weight: bold;">${{ options.max_gain_total }}</td></tr>
                                <tr><th>Max Loss</th><td style="color: #f44336;">${{ options.max_loss_total }}</td></tr>
                                <tr><th>Budget</th><td>${{ options.budget }}</td></tr>
                            </table>
                            <p style="font-size: 11px; color: #888; margin-top: 10px;">
                                <strong>Note:</strong> Requires cash collateral of ${{ options.sell_strike * 100 }} per contract.
                            </p>
                        </div>
                    </div>
                    
                    {% elif options.strategy == "Poor Man's Covered Call" %}
                    <!-- PMCC Strategy -->
                    <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px;">
                        <div>
                            <h4 style="color: #00d4ff; margin-top: 0;">📋 Long Leg (LEAP)</h4>
                            <table>
                                <tr><th>Expiration</th><td>{{ options.long_expiration }} ({{ options.long_days_to_exp }} days)</td></tr>
                                <tr>
                                    <th>BUY Call</th>
                                    <td style="color: #4caf50;">
                                        ${{ options.buy_strike }} @ ${{ options.buy_premium }}<br>
                                        <span style="font-size: 11px; color: #888;">
                                            Δ {{ options.buy_delta }} | Vol: {{ options.buy_volume }} | OI: {{ options.buy_oi }}
                                            {% if options.buy_iv %}| IV: {{ options.buy_iv }}%{% endif %}
                                        </span>
                                    </td>
                                </tr>
                            </table>
                        </div>
                        <div>
                            <h4 style="color: #00d4ff; margin-top: 0;">📋 Short Leg</h4>
                            <table>
                                <tr><th>Expiration</th><td>{{ options.short_expiration }} ({{ options.short_days_to_exp }} days)</td></tr>
                                <tr>
                                    <th>SELL Call</th>
                                    <td style="color: #f44336;">
                                        ${{ options.sell_strike }} @ ${{ options.sell_premium }}<br>
                                        <span style="font-size: 11px; color: #888;">
                                            Δ {{ options.sell_delta }} | Vol: {{ options.sell_volume }} | OI: {{ options.sell_oi }}
                                            {% if options.sell_iv %}| IV: {{ options.sell_iv }}%{% endif %}
                                        </span>
                                    </td>
                                </tr>
                            </table>
                        </div>
                        <div>
                            <h4 style="color: #00d4ff; margin-top: 0;">💰 Position</h4>
                            <table>
                                <tr><th>Net Debit</th><td style="font-weight: bold;">${{ options.net_debit }}</td></tr>
                                <tr><th>Contracts</th><td>{{ options.contracts }}</td></tr>
                                <tr><th>Total Cost</th><td style="color: #ff9800;">${{ options.total_cost }}</td></tr>
                                <tr><th>Max Gain</th><td style="color: #00c853;">${{ options.max_gain_total }}</td></tr>
                                <tr><th>Max Loss</th><td style="color: #f44336;">${{ options.max_loss_total }}</td></tr>
                            </table>
                        </div>
                    </div>
                    
                    {% elif options.strategy == 'Iron Condor' %}
                    <!-- Iron Condor Strategy -->
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                        <div>
                            <h4 style="color: #00d4ff; margin-top: 0;">📋 Trade Setup</h4>
                            <table>
                                <tr><th>Expiration</th><td>{{ options.expiration }} ({{ options.days_to_exp }} days)</td></tr>
                                <tr><th>Strategy</th><td style="color: #00c853; font-weight: bold;">{{ options.strategy }}</td></tr>
                                <tr><th colspan="2" style="color: #4caf50; padding-top: 10px;">Call Spread</th></tr>
                                <tr><th>SELL Call</th><td style="color: #f44336;">${{ options.short_call_strike }}</td></tr>
                                <tr><th>BUY Call</th><td style="color: #4caf50;">${{ options.long_call_strike }}</td></tr>
                                <tr><th colspan="2" style="color: #4caf50; padding-top: 10px;">Put Spread</th></tr>
                                <tr><th>SELL Put</th><td style="color: #f44336;">${{ options.short_put_strike }}</td></tr>
                                <tr><th>BUY Put</th><td style="color: #4caf50;">${{ options.long_put_strike }}</td></tr>
                                <tr><th>Net Credit</th><td style="color: #00c853; font-weight: bold;">${{ options.net_credit }} per contract</td></tr>
                            </table>
                        </div>
                        <div>
                            <h4 style="color: #00d4ff; margin-top: 0;">💰 Risk & Reward</h4>
                            <table>
                                <tr><th>Contracts</th><td style="font-weight: bold;">{{ options.contracts }}</td></tr>
                                <tr><th>Total Credit</th><td style="color: #00c853; font-weight: bold;">${{ options.total_credit }}</td></tr>
                                <tr><th>Max Risk</th><td style="color: #f44336;">${{ options.max_risk }}</td></tr>
                                <tr><th>Budget</th><td>${{ options.budget }}</td></tr>
                            </table>
                            <p style="font-size: 11px; color: #888; margin-top: 10px;">
                                <strong>Profit Zone:</strong> Stock stays between ${{ options.short_put_strike }} and ${{ options.short_call_strike }} at expiration.
                            </p>
                        </div>
                    </div>
                    {% endif %}
                    
                    {% if options.status == 'success' %}
                    
                    <!-- Budget Adjustment -->
                    <div style="margin-top: 10px;">
                        <form style="display: inline-flex; gap: 10px; align-items: center;">
                            <span style="color: #888; font-size: 12px;">Adjust budget:</span>
                            <a class="btn" style="padding: 4px 10px; font-size: 11px;" href="/chart/{{ symbol }}?budget=150&sma={{ show_smas|join(',') }}">$150</a>
                            <a class="btn" style="padding: 4px 10px; font-size: 11px;" href="/chart/{{ symbol }}?budget=250&sma={{ show_smas|join(',') }}">$250</a>
                            <a class="btn" style="padding: 4px 10px; font-size: 11px;" href="/chart/{{ symbol }}?budget=375&sma={{ show_smas|join(',') }}">$375</a>
                            <a class="btn" style="padding: 4px 10px; font-size: 11px;" href="/chart/{{ symbol }}?budget=500&sma={{ show_smas|join(',') }}">$500</a>
                            <a class="btn" style="padding: 4px 10px; font-size: 11px;" href="/chart/{{ symbol }}?budget=1000&sma={{ show_smas|join(',') }}">$1000</a>
                        </form>
                    </div>
                    {% endif %}
                    {% endif %}
                    
                    {% elif options.status == 'no_options' or options.status == 'no_suitable_exp' %}
                    <p style="color: #ff9800;">⚠️ {{ options.message }}</p>
                    <p style="color: #888; font-size: 13px;">Options trading not available for this symbol or no suitable expirations found.</p>
                    {% else %}
                    <p style="color: #f44336;">❌ {{ options.message if options.message else 'Unable to calculate options strategy' }}</p>
                    {% if options.traceback %}
                    <details style="font-size: 11px; color: #888;">
                        <summary>Debug Info</summary>
                        <pre>{{ options.traceback }}</pre>
                    </details>
                    {% endif %}
                    {% endif %}
                </div>
                
                <!-- Expected Move Analysis -->
                {% if expected_move.status == 'success' %}
                <div class="card" style="grid-column: span 2;">
                    <h3>📊 Expected Move Analysis</h3>
                    <p style="color: #888; font-size: 12px; margin-bottom: 15px;">Based on {{ expected_move.iv }}% IV from {{ expected_move.expiration }} expiration ({{ expected_move.dte }} DTE)</p>
                    
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                        <!-- Expected Moves -->
                        <div>
                            <h4 style="color: #00d4ff; margin-top: 0;">📈 Expected Moves (±1 SD)</h4>
                            <table>
                                <tr><th>1-Week</th><td style="color: #00c853;">± ${{ expected_move.move_1w }}</td></tr>
                                <tr><th>1-Month</th><td style="color: #00c853;">± ${{ expected_move.move_1m }}</td></tr>
                                <tr><th>45-Day</th><td style="color: #00c853;">± ${{ expected_move.move_45d }}</td></tr>
                            </table>
                        </div>
                        
                        <!-- Pattern Target Comparison -->
                        {% if expected_move.target_assessment %}
                        <div>
                            <h4 style="color: #00d4ff; margin-top: 0;">🎯 Pattern Target vs Expected Move</h4>
                            <table>
                                <tr><th>Pattern Target</th><td>${{ expected_move.target_assessment.target }} ({{ expected_move.target_assessment.target_pct }}% above)</td></tr>
                                <tr><th>45-Day Upper Bound</th><td>${{ expected_move.target_assessment.upper_bound }} ({{ expected_move.target_assessment.upper_pct }}% above)</td></tr>
                                <tr>
                                    <th>Assessment</th>
                                    <td style="color: {% if expected_move.target_assessment.assessment == 'WITHIN' %}#00c853{% else %}#ff9800{% endif %}; font-weight: bold;">
                                        Target {{ expected_move.target_assessment.assessment }} expected move
                                    </td>
                                </tr>
                            </table>
                            {% if expected_move.target_assessment.note %}
                            <p style="font-size: 11px; color: #ff9800; margin-top: 10px; padding: 8px; background: rgba(255,152,0,0.1); border-radius: 5px;">
                                ⚠️ {{ expected_move.target_assessment.note }}
                            </p>
                            {% endif %}
                        </div>
                        {% endif %}
                    </div>
                    
                    <!-- Delta-Based Probability Table -->
                    {% if expected_move.delta_strikes %}
                    <div style="margin-top: 20px;">
                        <h4 style="color: #00d4ff; margin-top: 0;">🎲 Delta-to-Probability Translation</h4>
                        <table style="width: 100%;">
                            <thead>
                                <tr style="background: #0a0a1a;">
                                    <th>Delta</th>
                                    <th>Strike</th>
                                    <th>Prob OTM</th>
                                    <th>Distance from Current</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for row in expected_move.delta_strikes %}
                                <tr>
                                    <td>{{ row.delta }}</td>
                                    <td>${{ row.strike }}</td>
                                    <td>{{ row.prob_otm }}%</td>
                                    <td style="color: {% if row.distance_pct > 0 %}#00c853{% else %}#f44336{% endif %};">
                                        {{ row.distance_pct }}%
                                    </td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                    {% endif %}
                </div>
                {% elif expected_move.status == 'no_data' %}
                <div class="card" style="grid-column: span 2;">
                    <h3>📊 Expected Move Analysis</h3>
                    <p style="color: #888;">Expected move data unavailable — options chain not found for this ticker.</p>
                </div>
                {% endif %}
                
                <!-- Company Info -->
                <div class="card">
                    <h3>🏢 Company Overview</h3>
                    <table>
                        <tr><th>Sector</th><td>{{ company.sector }}</td></tr>
                        <tr><th>Industry</th><td>{{ company.industry }}</td></tr>
                        <tr><th>Market Cap</th><td>{{ company.market_cap_fmt }}</td></tr>
                        <tr><th>Employees</th><td>{{ company.employees }}</td></tr>
                        <tr><th>Country</th><td>{{ company.country }}</td></tr>
                        {% if company.pe_ratio %}<tr><th>P/E Ratio</th><td>{{ company.pe_ratio|round(1) }}</td></tr>{% endif %}
                        {% if company.forward_pe %}<tr><th>Forward P/E</th><td>{{ company.forward_pe|round(1) }}</td></tr>{% endif %}
                        {% if company.beta %}<tr><th>Beta</th><td>{{ company.beta|round(2) }}</td></tr>{% endif %}
                        <tr><th>52-Week Range</th><td>${{ company.fifty_two_week_low|round(2) }} - ${{ company.fifty_two_week_high|round(2) }}</td></tr>
                    </table>
                </div>
            </div>
            
            <!-- Business Description -->
            <div class="card" style="margin-top: 20px;">
                <h3>📝 Business Description</h3>
                <div class="description">{{ company.description }}</div>
            </div>

            <!-- External Links -->
            <div class="card" style="margin-top: 20px;">
                <h3>🔗 External Resources</h3>
                <div style="display: flex; gap: 15px; flex-wrap: wrap;">
                    <a href="https://finance.yahoo.com/quote/{{ symbol }}" target="_blank" style="color: #00d4ff; text-decoration: none; padding: 8px 15px; background: rgba(0,212,255,0.1); border-radius: 5px; border: 1px solid #00d4ff;">
                        📊 Yahoo Finance
                    </a>
                    <a href="https://seekingalpha.com/symbol/{{ symbol }}" target="_blank" style="color: #00d4ff; text-decoration: none; padding: 8px 15px; background: rgba(0,212,255,0.1); border-radius: 5px; border: 1px solid #00d4ff;">
                        📰 Seeking Alpha
                    </a>
                    <a href="/chart/{{ symbol }}?edgar=1&sma={{ show_smas|join(',') }}&cto={{ '1' if show_cto else '' }}" style="color: #00d4ff; text-decoration: none; padding: 8px 15px; background: rgba(0,212,255,0.1); border-radius: 5px; border: 1px solid #00d4ff;">
                        📄 EDGAR Financials
                    </a>
                </div>
            </div>

            <!-- Trading Panel -->
            <div class="card" style="margin-top: 20px; background: #1a2332;">
                <h3>📈 Alpaca Paper Trading <span style="background: #ff9800; color: #000; padding: 2px 8px; border-radius: 4px; font-size: 12px; margin-left: 10px;">{{ alpaca_mode }}</span></h3>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                    <div>
                        <h4 style="color: #00c853;">Buy {{ symbol }}</h4>
                        <form id="buyForm" style="display: flex; flex-direction: column; gap: 10px;">
                            <input type="number" id="buyQty" placeholder="Quantity (e.g., 1 or 0.5)" step="0.01" min="0.01" style="padding: 10px; background: #0f0f23; color: #fff; border: 1px solid #333; border-radius: 5px;">
                            <input type="number" id="buyLimit" placeholder="Limit Price (optional)" step="0.01" style="padding: 10px; background: #0f0f23; color: #fff; border: 1px solid #333; border-radius: 5px;">
                            <button type="button" onclick="placeBuyOrder()" style="padding: 12px; background: #00c853; color: #000; border: none; border-radius: 5px; cursor: pointer; font-weight: bold;">Buy Market</button>
                            <button type="button" onclick="placeBuyLimit()" style="padding: 12px; background: #4caf50; color: #fff; border: none; border-radius: 5px; cursor: pointer;">Buy Limit</button>
                        </form>
                    </div>
                    <div>
                        <h4 style="color: #f44336;">Sell {{ symbol }}</h4>
                        <form id="sellForm" style="display: flex; flex-direction: column; gap: 10px;">
                            <input type="number" id="sellQty" placeholder="Quantity (e.g., 1 or 0.5)" step="0.01" min="0.01" style="padding: 10px; background: #0f0f23; color: #fff; border: 1px solid #333; border-radius: 5px;">
                            <input type="number" id="sellLimit" placeholder="Limit Price (optional)" step="0.01" style="padding: 10px; background: #0f0f23; color: #fff; border: 1px solid #333; border-radius: 5px;">
                            <button type="button" onclick="placeSellOrder()" style="padding: 12px; background: #f44336; color: #fff; border: none; border-radius: 5px; cursor: pointer; font-weight: bold;">Sell Market</button>
                            <button type="button" onclick="placeSellLimit()" style="padding: 12px; background: #ff5722; color: #fff; border: none; border-radius: 5px; cursor: pointer;">Sell Limit</button>
                        </form>
                    </div>
                </div>
                <div id="tradeStatus" style="margin-top: 15px; padding: 10px; border-radius: 5px; display: none;"></div>
            </div>

        </div>
        <script>
            const symbol = '{{ symbol }}';
            
            function showStatus(message, isError = false) {
                const status = document.getElementById('tradeStatus');
                status.textContent = message;
                status.style.display = 'block';
                status.style.background = isError ? '#f44336' : '#00c853';
                status.style.color = isError ? '#fff' : '#000';
            }
            
            async function placeBuyOrder() {
                const qty = document.getElementById('buyQty').value;
                if (!qty) { showStatus('Enter quantity', true); return; }
                try {
                    const res = await fetch('/api/order/market', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({symbol, qty: parseFloat(qty), side: 'buy'})
                    });
                    const data = await res.json();
                    showStatus(data.error || `Buy order placed: ${data.id}`, !!data.error);
                } catch (e) {
                    showStatus('Error: ' + e.message, true);
                }
            }
            
            async function placeSellOrder() {
                const qty = document.getElementById('sellQty').value;
                if (!qty) { showStatus('Enter quantity', true); return; }
                try {
                    const res = await fetch('/api/order/market', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({symbol, qty: parseFloat(qty), side: 'sell'})
                    });
                    const data = await res.json();
                    showStatus(data.error || `Sell order placed: ${data.id}`, !!data.error);
                } catch (e) {
                    showStatus('Error: ' + e.message, true);
                }
            }
            
            async function placeBuyLimit() {
                const qty = document.getElementById('buyQty').value;
                const limit = document.getElementById('buyLimit').value;
                if (!qty || !limit) { showStatus('Enter quantity and limit price', true); return; }
                try {
                    const res = await fetch('/api/order/limit', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({symbol, qty: parseFloat(qty), side: 'buy', limit_price: parseFloat(limit)})
                    });
                    const data = await res.json();
                    showStatus(data.error || `Buy limit order placed: ${data.id}`, !!data.error);
                } catch (e) {
                    showStatus('Error: ' + e.message, true);
                }
            }
            
            async function placeSellLimit() {
                const qty = document.getElementById('sellQty').value;
                const limit = document.getElementById('sellLimit').value;
                if (!qty || !limit) { showStatus('Enter quantity and limit price', true); return; }
                try {
                    const res = await fetch('/api/order/limit', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({symbol, qty: parseFloat(qty), side: 'sell', limit_price: parseFloat(limit)})
                    });
                    const data = await res.json();
                    showStatus(data.error || `Sell limit order placed: ${data.id}`, !!data.error);
                } catch (e) {
                    showStatus('Error: ' + e.message, true);
                }
            }
        </script>
        </body>
        </html>
        """

        return render_template_string(html,
                                      symbol=symbol,
                                      chart=chart_base64,
                                      company=company_info,
                                      cup_pattern=cup_pattern,
                                      asc_triangle=asc_triangle,
                                      bull_flag=bull_flag,
                                      double_bottom=double_bottom,
                                      analysis=analysis,
                                      dcf_data=dcf_data,
                                      show_smas=show_smas,
                                      show_cto=show_cto,
                                      show_supertrend=show_supertrend,
                                      show_smc=show_smc,
                                      options=options_strategy,
                                      options_budget=options_budget,
                                      expected_move=expected_move,
                                      edgar_financials=edgar_financials,
                                      alpaca_mode=os.getenv('ALPACA_MODE', 'paper').upper())

    except Exception as e:
        import traceback
        return f"Error generating chart for {symbol}: {e}<br><pre>{traceback.format_exc()}</pre>"

@app.route('/track', methods=['POST'])
def track_stock():
    try:
        ticker = request.form.get('ticker', '').strip().upper()
        email = request.form.get('email', '').strip()
        buy_point = request.form.get('buy_point')
        rsi_min = request.form.get('rsi_min', 50.0)
        rsi_max = request.form.get('rsi_max', 70.0)
        volume_multiple = request.form.get('volume_multiple', 2.0)
        breakeven_move = request.form.get('breakeven_move')

        # Validation
        if not ticker or not email:
            flash('Ticker and email are required.', 'error')
            return redirect(request.referrer or '/')

        if not buy_point:
            flash('Buy point is required.', 'error')
            return redirect(request.referrer or '/')

        try:
            buy_point = float(buy_point)
            rsi_min = float(rsi_min)
            rsi_max = float(rsi_max)
            volume_multiple = float(volume_multiple)
            breakeven_move = float(breakeven_move) if breakeven_move else None
        except ValueError:
            flash('Invalid numeric values.', 'error')
            return redirect(request.referrer or '/')

        # Load existing
        stocks = load_tracked_stocks()

        # Check if already tracked
        if any(s['ticker'] == ticker for s in stocks):
            flash(f'{ticker} is already being tracked.', 'error')
            return redirect(request.referrer or '/')

        # Add new
        new_stock = {
            'ticker': ticker,
            'buy_point': buy_point,
            'rsi_min': rsi_min,
            'rsi_max': rsi_max,
            'volume_multiple': volume_multiple,
            'breakeven_move': breakeven_move,
            'email': email,
            'added_at': datetime.utcnow().isoformat(),
            'notified': False
        }
        stocks.append(new_stock)
        save_tracked_stocks(stocks)

        flash(f'Successfully started tracking {ticker}.', 'success')
        return redirect('/tracked')

    except Exception as e:
        flash(f'Error tracking stock: {str(e)}', 'error')
        return redirect(request.referrer or '/')

@app.route('/tracked')
def tracked():
    try:
        stocks = load_tracked_stocks()
        # Sort by added_at desc
        stocks.sort(key=lambda x: x['added_at'], reverse=True)
        # Fetch current metrics for each
        for stock in stocks:
            try:
                ticker = yf.Ticker(stock['ticker'])
                hist = ticker.history(period='60d')
                if not hist.empty:
                    stock['current_price'] = round(hist['Close'].iloc[-1], 2)
                    stock['current_rsi'] = round(ta.rsi(hist['Close'], length=14).iloc[-1], 1) if len(hist) > 14 else None
                    stock['avg_volume'] = int(hist['Volume'].tail(50).mean())
                    stock['current_volume'] = int(hist['Volume'].iloc[-1])  # Today's volume
                else:
                    stock['current_price'] = None
                    stock['current_rsi'] = None
                    stock['avg_volume'] = None
                    stock['current_volume'] = None
            except Exception as e:
                stock['current_price'] = None
                stock['current_rsi'] = None
                stock['avg_volume'] = None
                stock['current_volume'] = None
        html = """
        <html>
        <head>
            <title>Tracked Stocks</title>
            <style>
                body { font-family: 'Segoe UI', Arial, sans-serif; margin: 20px; background: #1a1a2e; color: #eee; }
                h1 { color: #00d4ff; }
                .container { max-width: 1200px; margin: auto; }
                table { border-collapse: collapse; width: 100%; margin-top: 20px; font-size: 14px; }
                th, td { border: 1px solid #333; padding: 10px; text-align: center; }
                th { background: #16213e; color: #00d4ff; }
                tr:nth-child(even) { background: #0f0f23; }
                tr:hover { background: #1f1f3a; }
                .btn { padding: 8px 15px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; margin: 5px; display: inline-block; }
                .btn-danger { background: #f44336; }
                .btn:hover { opacity: 0.8; }
                .navbar { background: #16213e; padding: 10px; border-radius: 8px; margin-bottom: 20px; }
                .navbar a { color: #00d4ff; text-decoration: none; margin: 0 15px; }
                .navbar a:hover { text-decoration: underline; }
                .flash { padding: 10px; border-radius: 5px; margin: 10px 0; }
                .flash-success { background: #00c853; color: #000; }
                .flash-error { background: #f44336; }
                .status { padding: 4px 8px; border-radius: 4px; font-size: 12px; }
                .status-active { background: #00c853; color: #000; }
                .status-inactive { background: #f44336; }
                th[title] { cursor: help; text-decoration: underline dotted; }
            </style>
        </head>
        <body>
        <div class="container">
            <div class="navbar">
                <a href="/">Home</a>
                <a href="/tracked">Tracked Stocks</a>
            </div>
            <h1>📈 Tracked Stocks</h1>
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    {% for category, message in messages %}
                        <div class="flash flash-{{ category }}">{{ message }}</div>
                    {% endfor %}
                {% endif %}
            {% endwith %}
            {% if tracks %}
            <table>
                <tr>
                    <th>Ticker</th>
                    <th title="Ideal entry price based on pattern analysis">Buy Point</th>
                    <th title="RSI range for optimal entry (typically 50-70)">RSI Range</th>
                    <th title="Volume multiplier required for confirmation (e.g., 2x = double average volume)">Volume Req</th>
                    <th title="Percentage move needed to cover typical spread/commission costs">Breakeven %</th>
                    <th>Added Date</th>
                    <th>Status</th>
                    <th>Actions</th>
                </tr>
                {% for track in tracks %}
                <tr {% if track['avg_volume'] and track['current_volume'] and track['current_volume'] >= (track['avg_volume'] * track['volume_multiple']) %}style="background: rgba(76, 175, 80, 0.2);"{% endif %}>
                    <td><a href="/chart/{{ track['ticker'] }}" style="color: #00d4ff;">{{ track['ticker'] }}</a></td>
                    <td>${{ track['buy_point'] }}{% if track['current_price'] %}<br><small style="color:#888;">(Curr: ${{ track['current_price'] }})</small>{% endif %}</td>
                    <td>{{ track['rsi_min'] }}-{{ track['rsi_max'] }}{% if track['current_rsi'] %}<br><small style="color:#888;">(Curr: {{ track['current_rsi'] }})</small>{% endif %}</td>
                    <td>{{ track['volume_multiple'] }}x{% if track['avg_volume'] %}<br><small style="color:{% if track['current_volume'] and track['current_volume'] >= (track['avg_volume'] * track['volume_multiple']) %}#4caf50{% else %}#888{% endif %};">(Avg: {{ track['avg_volume']|round(0) }} req: {{ (track['avg_volume'] * track['volume_multiple']) |round(0) }})</small>{% endif %}</td>
                    <td>{% if track['breakeven_move'] %}{{ track['breakeven_move'] }}%{% else %}-{% endif %}</td>
                    <td>{{ track['added_at'][:10] }}</td>
                    <td><span class="status status-active">Active</span></td>
                    <td>
                        <form method="post" action="/tracked/{{ track['ticker'] }}/delete" style="display: inline;">
                            <button type="submit" class="btn btn-danger" onclick="return confirm('Remove {{ track['ticker'] }} from tracking?')">Remove</button>
                        </form>
                    </td>
                </tr>
                {% endfor %}
            </table>
            {% else %}
            <p>No stocks are currently being tracked. <a href="/" class="btn">Start Tracking</a></p>
            {% endif %}
        </div>
        </body>
        </html>
        """
        return render_template_string(html, tracks=stocks)
    except Exception as e:
        return f"Error loading tracked stocks: {e}"

@app.route('/tracked/<ticker>/delete', methods=['POST'])
def remove_tracked(ticker):
    try:
        stocks = load_tracked_stocks()
        stocks = [s for s in stocks if s['ticker'] != ticker.upper()]
        save_tracked_stocks(stocks)
        flash(f'Removed {ticker.upper()} from tracking.', 'success')
    except Exception as e:
        flash(f'Error removing stock: {str(e)}', 'error')
    return redirect('/tracked')

# Trading API Routes
@app.route('/api/order/market', methods=['POST'])
def api_market_order():
    try:
        data = request.get_json()
        symbol = data.get('symbol')
        qty = data.get('qty')
        side = data.get('side')
        
        if not all([symbol, qty, side]):
            return {'error': 'Missing required fields'}, 400
        
        result = order_manager.place_market_order(symbol, float(qty), side)
        
        # Auto-log to trade journal
        try:
            from journal.models import Trade, get_session
            from datetime import date
            
            # Get current price for the symbol
            ticker = yf.Ticker(symbol)
            current_price = ticker.info.get('currentPrice') or ticker.info.get('regularMarketPrice', 0)
            
            session = get_session()
            trade = Trade(
                symbol=symbol,
                entry_date=date.today(),
                entry_price=current_price,
                shares=float(qty),
                trade_type='stock',
                status='open' if side.lower() == 'buy' else 'closed',
                notes=f"Auto-logged from Alpaca {result.get('type', 'market')} order. Order ID: {result.get('order_id', 'N/A')}"
            )
            
            # If selling, try to close an existing open position
            if side.lower() == 'sell':
                open_trade = session.query(Trade).filter_by(
                    symbol=symbol, 
                    status='open'
                ).order_by(Trade.entry_date.desc()).first()
                
                if open_trade:
                    open_trade.exit_date = date.today()
                    open_trade.exit_price = current_price
                    open_trade.exit_reason = 'manual_exit'
                    open_trade.status = 'closed'
                    open_trade.compute_metrics()
                    session.commit()
                    session.close()
                    result['journal_logged'] = True
                    result['journal_action'] = 'closed_existing_trade'
                    return result
            
            session.add(trade)
            session.commit()
            session.close()
            result['journal_logged'] = True
        except Exception as journal_err:
            result['journal_error'] = str(journal_err)
        
        return result
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/api/order/limit', methods=['POST'])
def api_limit_order():
    try:
        data = request.get_json()
        symbol = data.get('symbol')
        qty = data.get('qty')
        side = data.get('side')
        limit_price = data.get('limit_price')
        
        if not all([symbol, qty, side, limit_price]):
            return {'error': 'Missing required fields'}, 400
        
        result = order_manager.place_limit_order(symbol, float(qty), side, float(limit_price))
        
        # Auto-log to trade journal (using limit price as entry)
        try:
            from journal.models import Trade, get_session
            from datetime import date
            
            session = get_session()
            trade = Trade(
                symbol=symbol,
                entry_date=date.today(),
                entry_price=float(limit_price),
                shares=float(qty),
                trade_type='stock',
                status='open' if side.lower() == 'buy' else 'closed',
                notes=f"Auto-logged from Alpaca limit order @ ${limit_price}. Order ID: {result.get('order_id', 'N/A')}"
            )
            
            # If selling, try to close an existing open position
            if side.lower() == 'sell':
                open_trade = session.query(Trade).filter_by(
                    symbol=symbol, 
                    status='open'
                ).order_by(Trade.entry_date.desc()).first()
                
                if open_trade:
                    open_trade.exit_date = date.today()
                    open_trade.exit_price = float(limit_price)
                    open_trade.exit_reason = 'manual_exit'
                    open_trade.status = 'closed'
                    open_trade.compute_metrics()
                    session.commit()
                    session.close()
                    result['journal_logged'] = True
                    result['journal_action'] = 'closed_existing_trade'
                    return result
            
            session.add(trade)
            session.commit()
            session.close()
            result['journal_logged'] = True
        except Exception as journal_err:
            result['journal_error'] = str(journal_err)
        
        return result
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/api/positions', methods=['GET'])
def api_positions():
    try:
        result = order_manager.get_positions()
        return result
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/api/orders', methods=['GET'])
def api_orders():
    try:
        result = order_manager.get_orders()
        return result
    except Exception as e:
        return {'error': str(e)}, 500

# Register research API blueprint
try:
    from research_api import research_bp
    app.register_blueprint(research_bp)
    
    # Register journal blueprint
    from journal.routes import journal_bp
    app.register_blueprint(journal_bp)
    from research_dashboard import add_research_routes
    add_research_routes(app)
except ImportError:
    pass  # Research API not available

if __name__ == "__main__":
    # Disable reloader to prevent crashes during long scans
    app.run(debug=True, host="0.0.0.0", port=5004, use_reloader=False)
