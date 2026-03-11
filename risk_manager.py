"""
Wolverine Risk Management System
Cross-account portfolio risk monitor with live Alpaca integration
"""
import json
import yfinance as yf
from datetime import datetime, timedelta, date
from pathlib import Path
import uuid
from alpaca_client import trading_client

# ============================================================
# DATA LAYER ABSTRACTION — TASTYTRADE UPGRADE PATH
# ============================================================
# The get_live_positions() function currently uses Alpaca API.
# To upgrade to Tastytrade for options Greeks:
#
# 1. Install: pip install tastytrade
# 2. Set env vars: TASTYTRADE_CLIENT_ID, TASTYTRADE_REFRESH_TOKEN
# 3. Replace get_alpaca_positions() with get_tastytrade_positions()
#    which should return the same position schema plus:
#    - delta (float): live Greeks from DXLink streamer
#    - gamma, theta, vega (float): full Greeks
#    - iv (float): implied volatility
# 4. Update net_delta calculation to use live Greeks instead of
#    equity delta proxy
# 5. Add Greeks aggregation: portfolio_theta, portfolio_vega
# ============================================================

CACHE_FILE = Path('data/risk_cache.json')
MANUAL_POSITIONS_FILE = Path('data/manual_positions.json')
DAILY_LOG_FILE = Path('data/risk_daily_log.json')
CONFIG_FILE = Path('data/risk_config.json')
CACHE_DURATION_MINUTES = 5

DEFAULT_CONFIG = {
    "account_size_total": 50000,
    "daily_loss_limit_dollars": 500,
    "daily_loss_limit_pct": 0.01,
    "weekly_loss_limit_dollars": 1500,
    "weekly_loss_limit_pct": 0.03,
    "monthly_loss_limit_pct": 0.10,
    "max_buying_power_usage_pct": 0.50,
    "max_single_position_risk_dollars": 250,
    "max_single_position_risk_pct": 0.005,
    "max_positions_total": 20,
    "max_positions_per_sector": 5,
    "vix_spike_threshold_pct": 0.20,
    "scanner_book_max_per_trade": 250,
    "conviction_book_max_per_trade": 5000,
    "recovery_mode_size_reduction_pct": 0.50,
    "recovery_mode_winning_days_required": 2
}

SECTOR_MAPPING = {
    'AAPL': 'Technology', 'MSFT': 'Technology', 'NVDA': 'Semiconductors',
    'GOOGL': 'Technology', 'AMZN': 'Technology', 'META': 'Technology',
    'TSLA': 'Automotive', 'BRK-B': 'Financial', 'UNH': 'Healthcare',
    'JPM': 'Financial', 'V': 'Financial', 'XOM': 'Energy',
    'JNJ': 'Healthcare', 'LLY': 'Healthcare', 'AVGO': 'Semiconductors',
    'MA': 'Financial', 'HD': 'Retail', 'PG': 'Consumer', 'MRK': 'Healthcare',
    'COST': 'Retail'
}

def _ensure_files():
    """Ensure all data files exist"""
    for f in [CACHE_FILE, MANUAL_POSITIONS_FILE, DAILY_LOG_FILE, CONFIG_FILE]:
        f.parent.mkdir(exist_ok=True)
        if not f.exists():
            if f == CONFIG_FILE:
                with open(f, 'w') as file:
                    json.dump(DEFAULT_CONFIG, file, indent=2)
            elif f == MANUAL_POSITIONS_FILE:
                with open(f, 'w') as file:
                    json.dump([], file)
            elif f == DAILY_LOG_FILE:
                with open(f, 'w') as file:
                    json.dump({
                        "start_of_day_value": None,
                        "start_of_day_vix": None,
                        "start_of_day_date": None,
                        "recovery_mode_active": False,
                        "recovery_mode_triggered_date": None,
                        "consecutive_winning_days": 0,
                        "recovery_mode_exit_date": None,
                        "daily_history": []
                    }, file, indent=2)

def load_config():
    """Load risk configuration"""
    _ensure_files()
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

def save_config(config):
    """Save risk configuration"""
    _ensure_files()
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def load_manual_positions():
    """Load manual positions"""
    _ensure_files()
    with open(MANUAL_POSITIONS_FILE, 'r') as f:
        return json.load(f)

def save_manual_positions(positions):
    """Save manual positions"""
    _ensure_files()
    with open(MANUAL_POSITIONS_FILE, 'w') as f:
        json.dump(positions, f, indent=2, default=str)

def load_daily_log():
    """Load daily log"""
    _ensure_files()
    with open(DAILY_LOG_FILE, 'r') as f:
        return json.load(f)

def save_daily_log(log):
    """Save daily log"""
    _ensure_files()
    with open(DAILY_LOG_FILE, 'w') as f:
        json.dump(log, f, indent=2, default=str)

def get_alpaca_positions():
    """Fetch live positions from Alpaca"""
    try:
        account = trading_client.get_account()
        positions = trading_client.get_all_positions()
        
        account_data = {
            "portfolio_value": float(account.portfolio_value),
            "buying_power": float(account.buying_power),
            "cash": float(account.cash),
            "equity": float(account.equity),
            "initial_margin": float(account.initial_margin) if account.initial_margin else 0,
            "maintenance_margin": float(account.maintenance_margin) if account.maintenance_margin else 0,
            "daytrade_count": int(account.daytrade_count) if hasattr(account, 'daytrade_count') else 0
        }
        
        position_list = []
        for p in positions:
            position_list.append({
                "symbol": p.symbol,
                "qty": float(p.qty),
                "side": "long" if float(p.qty) > 0 else "short",
                "market_value": float(p.market_value),
                "cost_basis": float(p.cost_basis),
                "unrealized_pl": float(p.unrealized_pl),
                "unrealized_plpc": float(p.unrealized_plpc),
                "current_price": float(p.current_price),
                "asset_class": p.asset_class.value if hasattr(p.asset_class, 'value') else str(p.asset_class),
                "account": "alpaca_scanner"
            })
        
        return account_data, position_list
    except Exception as e:
        return None, []

def evaluate_limit(current_value, limit_value, warning_threshold=0.75):
    """Evaluate limit status"""
    if limit_value == 0:
        return {"status": "OK", "usage_pct": 0, "current": current_value, "limit": limit_value}
    
    usage_pct = abs(current_value) / abs(limit_value)
    if usage_pct >= 1.0:
        status = "BREACHED"
    elif usage_pct >= warning_threshold:
        status = "WARNING"
    else:
        status = "OK"
    return {"status": status, "usage_pct": usage_pct, "current": current_value, "limit": limit_value}

def rolling_vs_closing_decision(position):
    """Evaluate whether to roll or close an options position"""
    if position.get('unrealized_pl', 0) >= 0:
        return None
    
    max_loss = position.get('max_loss')
    dte = position.get('days_to_expiration')
    unrealized_pl = position.get('unrealized_pl', 0)
    
    if not max_loss or not dte:
        return None
    
    loss_as_pct_of_max_loss = abs(unrealized_pl) / max_loss
    
    if dte <= 7:
        return {
            "recommendation": "CLOSE",
            "reason": "Too close to expiration — time decay accelerates, adjustment risk too high",
            "loss_pct_of_max": loss_as_pct_of_max_loss
        }
    elif loss_as_pct_of_max_loss >= 2.0:
        return {
            "recommendation": "CLOSE",
            "reason": "Position has reached 2x max profit loss threshold — Tastytrade rule: close immediately",
            "loss_pct_of_max": loss_as_pct_of_max_loss
        }
    elif loss_as_pct_of_max_loss >= 1.0 and dte <= 21:
        return {
            "recommendation": "CLOSE",
            "reason": "Full max loss reached with less than 21 DTE — rolling adds time but not edge",
            "loss_pct_of_max": loss_as_pct_of_max_loss
        }
    elif loss_as_pct_of_max_loss >= 0.5 and dte >= 21:
        return {
            "recommendation": "EVALUATE_ROLL",
            "reason": "50% of max loss reached with time remaining — evaluate roll to next cycle at same delta",
            "loss_pct_of_max": loss_as_pct_of_max_loss
        }
    else:
        return {
            "recommendation": "HOLD",
            "reason": "Within normal drawdown range — hold per original thesis",
            "loss_pct_of_max": loss_as_pct_of_max_loss
        }

def get_risk_snapshot(force_refresh=False):
    """Generate complete risk snapshot"""
    # Check cache
    if not force_refresh and CACHE_FILE.exists():
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
    
    _ensure_files()
    config = load_config()
    daily_log = load_daily_log()
    
    # Fetch live Alpaca data
    alpaca_account, alpaca_positions = get_alpaca_positions()
    
    # Load manual positions
    manual_positions = load_manual_positions()
    
    # Calculate total portfolio value across all accounts
    accounts = {
        "alpaca_scanner": {
            "portfolio_value": alpaca_account['portfolio_value'] if alpaca_account else 0,
            "buying_power": alpaca_account['buying_power'] if alpaca_account else 0,
            "day_pnl": 0,
            "positions_count": len(alpaca_positions)
        }
    }
    
    for account_name in ['thinkorswim', 'sofi', 'robinhood']:
        account_positions = [p for p in manual_positions if p.get('account') == account_name]
        accounts[account_name] = {
            "portfolio_value": sum(p.get('market_value', 0) for p in account_positions),
            "positions_count": len(account_positions),
            "source": "manual"
        }
    
    total_portfolio_value = sum(acc['portfolio_value'] for acc in accounts.values())
    
    # Initialize start of day if needed (use TOTAL portfolio value, not just Alpaca)
    today = date.today().isoformat()
    if daily_log.get('start_of_day_date') != today or daily_log.get('start_of_day_value') is None:
        daily_log['start_of_day_value'] = total_portfolio_value
        daily_log['start_of_day_date'] = today
        
        # Get VIX
        try:
            vix = yf.Ticker('^VIX')
            vix_hist = vix.history(period='1d')
            if not vix_hist.empty:
                daily_log['start_of_day_vix'] = float(vix_hist['Close'].iloc[-1])
        except:
            daily_log['start_of_day_vix'] = None
        
        save_daily_log(daily_log)
    # Combine all positions
    all_positions = alpaca_positions + manual_positions
    
    for account_name in ['thinkorswim', 'sofi', 'robinhood']:
        account_positions = [p for p in manual_positions if p.get('account') == account_name]
    
    for account_name in ['thinkorswim', 'sofi', 'robinhood']:
        account_positions = [p for p in manual_positions if p.get('account') == account_name]
        accounts[account_name] = {
            "portfolio_value": sum(p.get('market_value', 0) for p in account_positions),
            "positions_count": len(account_positions),
            "source": "manual"
        }
    
    # Calculate P&L
    start_of_day_value = daily_log.get('start_of_day_value', total_portfolio_value)
    daily_pnl = total_portfolio_value - start_of_day_value
    daily_pnl_pct = (daily_pnl / start_of_day_value) if start_of_day_value > 0 else 0
    
    # Weekly P&L
    weekly_pnl = sum(
        day.get('daily_pnl', 0) 
        for day in daily_log.get('daily_history', [])[-5:]
    )
    weekly_pnl_pct = (weekly_pnl / start_of_day_value) if start_of_day_value > 0 else 0
    
    # Monthly P&L
    monthly_pnl = sum(
        day.get('daily_pnl', 0)
        for day in daily_log.get('daily_history', [])[-22:]
    )
    monthly_pnl_pct = (monthly_pnl / start_of_day_value) if start_of_day_value > 0 else 0
    
    # Evaluate limits
    limits = {
        "daily_loss": evaluate_limit(daily_pnl, -config['daily_loss_limit_dollars']),
        "weekly_loss": evaluate_limit(weekly_pnl, -config['weekly_loss_limit_dollars']),
        "monthly_loss": evaluate_limit(monthly_pnl_pct, -config['monthly_loss_limit_pct']),
        "buying_power": evaluate_limit(
            (total_portfolio_value - accounts['alpaca_scanner']['buying_power']) / total_portfolio_value if total_portfolio_value > 0 else 0,
            config['max_buying_power_usage_pct']
        ),
        "position_count": evaluate_limit(len(all_positions), config['max_positions_total'])
    }
    
    # Calculate exposure
    net_delta_dollars = 0
    for pos in all_positions:
        if pos.get('asset_class') == 'us_equity' or pos.get('position_type') == 'equity':
            # Equity: delta = 1 per share
            net_delta_dollars += pos['qty'] * pos.get('current_price', 0) * (1 if pos['side'] == 'long' else -1)
        elif pos.get('delta'):
            # Options with delta
            net_delta_dollars += pos['delta'] * pos['qty'] * 100
    
    # Directional bias
    if net_delta_dollars > config['account_size_total'] * 0.15:
        bias = "SIGNIFICANT_LONG"
    elif net_delta_dollars > config['account_size_total'] * 0.05:
        bias = "MILD_LONG"
    elif net_delta_dollars < -config['account_size_total'] * 0.15:
        bias = "SIGNIFICANT_SHORT"
    elif net_delta_dollars < -config['account_size_total'] * 0.05:
        bias = "MILD_SHORT"
    else:
        bias = "NEUTRAL"
    
    # Sector concentration
    sector_exposure = {}
    for pos in all_positions:
        sector = SECTOR_MAPPING.get(pos['symbol'], 'Other')
        sector_exposure[sector] = sector_exposure.get(sector, 0) + abs(pos.get('market_value', 0))
    
    sector_concentrations = [
        {
            "sector": sector,
            "pct": (value / total_portfolio_value * 100) if total_portfolio_value > 0 else 0,
            "flagged": (value / total_portfolio_value) > 0.20 if total_portfolio_value > 0 else False
        }
        for sector, value in sector_exposure.items()
    ]
    
    # VIX monitoring
    current_vix = None
    vix_change_pct = 0
    vix_spike_detected = False
    try:
        vix = yf.Ticker('^VIX')
        vix_hist = vix.history(period='1d')
        if not vix_hist.empty:
            current_vix = float(vix_hist['Close'].iloc[-1])
            start_vix = daily_log.get('start_of_day_vix')
            if start_vix:
                vix_change_pct = (current_vix - start_vix) / start_vix
                vix_spike_detected = vix_change_pct >= config['vix_spike_threshold_pct']
    except:
        pass
    
    # PDT tracking
    pdt_info = {
        "daytrade_count": alpaca_account.get('daytrade_count', 0) if alpaca_account else 0,
        "remaining_day_trades": max(0, 3 - alpaca_account.get('daytrade_count', 0)) if alpaca_account else 3,
        "account_equity": alpaca_account.get('equity', 0) if alpaca_account else 0,
        "pdt_exempt": (alpaca_account.get('equity', 0) >= 25000) if alpaca_account else False
    }
    
    # Recovery mode
    recovery_mode = {
        "active": daily_log.get('recovery_mode_active', False),
        "triggered_date": daily_log.get('recovery_mode_triggered_date'),
        "consecutive_winning_days": daily_log.get('consecutive_winning_days', 0),
        "days_required": config['recovery_mode_winning_days_required'],
        "current_size_multiplier": config['recovery_mode_size_reduction_pct'] if daily_log.get('recovery_mode_active') else 1.0
    }
    
    # Add rolling/closing recommendations to positions
    for pos in all_positions:
        if 'option' in pos.get('position_type', '').lower() or 'option' in pos.get('asset_class', '').lower():
            pos['rolling_vs_closing'] = rolling_vs_closing_decision(pos)
        else:
            pos['rolling_vs_closing'] = None
        
        # Concentration flag
        pos['concentration_flag'] = (abs(pos.get('market_value', 0)) / total_portfolio_value) > 0.15 if total_portfolio_value > 0 else False
    
    # Generate alerts
    alerts = []
    
    # CRITICAL alerts
    if limits['daily_loss']['status'] == 'BREACHED':
        alerts.append({
            "level": "CRITICAL",
            "type": "DAILY_LOSS_LIMIT",
            "message": f"Daily loss limit BREACHED — ${abs(daily_pnl):.0f} lost vs ${config['daily_loss_limit_dollars']} limit. ACTIVATE RECOVERY MODE: close all new entries, reduce size to 50% until 2 consecutive winning days."
        })
        # Activate recovery mode
        if not daily_log.get('recovery_mode_active'):
            daily_log['recovery_mode_active'] = True
            daily_log['recovery_mode_triggered_date'] = datetime.now().isoformat()
            daily_log['consecutive_winning_days'] = 0
            save_daily_log(daily_log)
    
    if vix_spike_detected:
        alerts.append({
            "level": "CRITICAL",
            "type": "VIX_SPIKE",
            "message": f"VIX spike detected: +{vix_change_pct*100:.1f}% intraday. WOLVERINE PROTOCOL: (1) Check all short option strikes vs current SPX level. (2) Close any position where SPX is within 1% of short strike. (3) Do not open new short premium positions today. (4) Consider long VIX calls or SPX put hedge if net delta is short."
        })
    
    if pdt_info['daytrade_count'] >= 4:
        alerts.append({
            "level": "CRITICAL",
            "type": "PDT_VIOLATION_RISK",
            "message": f"PDT RISK: {pdt_info['daytrade_count']} day trades used. Next same-day close will trigger Pattern Day Trader restriction. Do not open AND close any position today."
        })
    
    if limits['monthly_loss']['status'] == 'BREACHED':
        alerts.append({
            "level": "CRITICAL",
            "type": "MONTHLY_CIRCUIT_BREAKER",
            "message": f"MONTHLY CIRCUIT BREAKER TRIGGERED — 10% monthly drawdown reached. STOP TRADING for remainder of month. Close all short-duration positions. Maintain only long-term conviction book."
        })
    
    # WARNING alerts
    if limits['daily_loss']['status'] == 'WARNING':
        alerts.append({
            "level": "WARNING",
            "type": "DAILY_LOSS_APPROACHING",
            "message": f"Approaching daily loss limit — {limits['daily_loss']['usage_pct']*100:.0f}% of limit used. Begin reducing position sizes and avoid new entries."
        })
    
    if limits['buying_power']['status'] in ['WARNING', 'BREACHED']:
        alerts.append({
            "level": "WARNING",
            "type": "BUYING_POWER",
            "message": f"Buying power usage at {limits['buying_power']['usage_pct']*100:.0f}% of account — above 50% threshold. Do not open new positions until existing ones are reduced."
        })
    
    if recovery_mode['active']:
        days_remaining = recovery_mode['days_required'] - recovery_mode['consecutive_winning_days']
        alerts.append({
            "level": "WARNING",
            "type": "RECOVERY_MODE",
            "message": f"RECOVERY MODE ACTIVE — position size capped at 50% (max ${config['scanner_book_max_per_trade'] * 0.5:.0f}/trade). {recovery_mode['consecutive_winning_days']} of {recovery_mode['days_required']} winning days completed. {days_remaining} more winning day(s) required to exit recovery mode."
        })
    
    for pos in all_positions:
        if pos.get('concentration_flag'):
            pct = (abs(pos.get('market_value', 0)) / total_portfolio_value * 100) if total_portfolio_value > 0 else 0
            alerts.append({
                "level": "WARNING",
                "type": "CONCENTRATION",
                "message": f"Concentration risk: {pos['symbol']} represents {pct:.1f}% of portfolio — above 15% threshold."
            })
    
    # Build result
    result = {
        "timestamp": datetime.now().isoformat(),
        "cache_age_minutes": 0,
        "market_open": True,  # TODO: Add market hours check
        "accounts": accounts,
        "total_portfolio_value": total_portfolio_value,
        "pnl": {
            "daily": daily_pnl,
            "daily_pct": daily_pnl_pct,
            "weekly": weekly_pnl,
            "weekly_pct": weekly_pnl_pct,
            "monthly": monthly_pnl,
            "monthly_pct": monthly_pnl_pct,
            "start_of_day_value": start_of_day_value
        },
        "limits": limits,
        "exposure": {
            "net_delta_dollars": net_delta_dollars,
            "directional_bias": bias,
            "buying_power_usage_pct": limits['buying_power']['current'],
            "largest_position_pct": max((abs(p.get('market_value', 0)) / total_portfolio_value * 100) for p in all_positions) if all_positions and total_portfolio_value > 0 else 0,
            "sector_concentrations": sector_concentrations
        },
        "vix": {
            "current": current_vix,
            "start_of_day": daily_log.get('start_of_day_vix'),
            "change_pct": vix_change_pct,
            "spike_detected": vix_spike_detected
        },
        "pdt": pdt_info,
        "recovery_mode": recovery_mode,
        "positions": all_positions,
        "alerts": alerts,
        "alert_count_critical": len([a for a in alerts if a['level'] == 'CRITICAL']),
        "alert_count_warning": len([a for a in alerts if a['level'] == 'WARNING']),
        "risk_config": config,
        "errors": []
    }
    
    # Save cache
    with open(CACHE_FILE, 'w') as f:
        json.dump(result, f, indent=2, default=str)
    
    return result

def end_of_day_close():
    """End of day processing"""
    snapshot = get_risk_snapshot(force_refresh=True)
    daily_log = load_daily_log()
    
    # Log today's P&L
    daily_entry = {
        "date": date.today().isoformat(),
        "start_value": snapshot['pnl']['start_of_day_value'],
        "end_value": snapshot['total_portfolio_value'],
        "daily_pnl": snapshot['pnl']['daily'],
        "daily_pnl_pct": snapshot['pnl']['daily_pct'],
        "recovery_mode_active": daily_log.get('recovery_mode_active', False)
    }
    
    if 'daily_history' not in daily_log:
        daily_log['daily_history'] = []
    daily_log['daily_history'].append(daily_entry)
    daily_log['daily_history'] = daily_log['daily_history'][-30:]  # Keep last 30 days
    
    # Update recovery mode
    if daily_log.get('recovery_mode_active'):
        if snapshot['pnl']['daily'] > 0:
            daily_log['consecutive_winning_days'] = daily_log.get('consecutive_winning_days', 0) + 1
            if daily_log['consecutive_winning_days'] >= load_config()['recovery_mode_winning_days_required']:
                daily_log['recovery_mode_active'] = False
                daily_log['recovery_mode_exit_date'] = datetime.now().isoformat()
        else:
            daily_log['consecutive_winning_days'] = 0
    
    # Reset for next day
    daily_log['start_of_day_value'] = None
    daily_log['start_of_day_vix'] = None
    daily_log['start_of_day_date'] = None
    
    save_daily_log(daily_log)
    return daily_entry

def add_manual_position(position_data):
    """Add a manual position"""
    positions = load_manual_positions()
    position_data['id'] = str(uuid.uuid4())
    position_data['last_updated'] = datetime.now().isoformat()
    positions.append(position_data)
    save_manual_positions(positions)
    
    # Clear cache to force refresh
    if CACHE_FILE.exists():
        CACHE_FILE.unlink()
    
    return position_data

def update_manual_position(position_id, position_data):
    """Update a manual position"""
    positions = load_manual_positions()
    for i, pos in enumerate(positions):
        if pos.get('id') == position_id:
            position_data['id'] = position_id
            position_data['last_updated'] = datetime.now().isoformat()
            positions[i] = position_data
            save_manual_positions(positions)
            
            # Clear cache to force refresh
            if CACHE_FILE.exists():
                CACHE_FILE.unlink()
            
            return position_data
    return None

def delete_manual_position(position_id):
    """Delete a manual position"""
    positions = load_manual_positions()
    positions = [p for p in positions if p.get('id') != position_id]
    save_manual_positions(positions)
    return True

def reset_recovery_mode():
    """Manually reset recovery mode"""
    daily_log = load_daily_log()
    daily_log['recovery_mode_active'] = False
    daily_log['recovery_mode_exit_date'] = datetime.now().isoformat()
    daily_log['consecutive_winning_days'] = 0
    save_daily_log(daily_log)
    return True

def reset_start_of_day():
    """Reset start of day value to current portfolio value"""
    # Get current snapshot
    alpaca_account, alpaca_positions = get_alpaca_positions()
    manual_positions = load_manual_positions()
    
    # Calculate total current value
    alpaca_value = alpaca_account['portfolio_value'] if alpaca_account else 0
    manual_value = sum(p.get('market_value', 0) for p in manual_positions)
    total_value = alpaca_value + manual_value
    
    # Update daily log
    daily_log = load_daily_log()
    daily_log['start_of_day_value'] = total_value
    daily_log['start_of_day_date'] = date.today().isoformat()
    
    # Also reset recovery mode since we're resetting the baseline
    daily_log['recovery_mode_active'] = False
    daily_log['recovery_mode_exit_date'] = datetime.now().isoformat()
    daily_log['consecutive_winning_days'] = 0
    
    # Get VIX
    try:
        vix = yf.Ticker('^VIX')
        vix_hist = vix.history(period='1d')
        if not vix_hist.empty:
            daily_log['start_of_day_vix'] = float(vix_hist['Close'].iloc[-1])
    except:
        pass
    
    save_daily_log(daily_log)
    
    # Clear cache to force refresh
    if CACHE_FILE.exists():
        CACHE_FILE.unlink()
    
    return {'start_of_day_value': total_value, 'recovery_mode_reset': True}

def get_risk_history():
    """Get 30-day risk history"""
    daily_log = load_daily_log()
    return daily_log.get('daily_history', [])
