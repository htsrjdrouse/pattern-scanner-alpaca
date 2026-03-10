"""
Flask API endpoints for alpha research platform.
Extends existing pattern_scanner.py without breaking current functionality.
"""
from flask import Blueprint, jsonify, request
import pandas as pd
from datetime import datetime, timedelta
import signals
import backtest
import analytics
from alpaca_data import fetch_stock_data

research_bp = Blueprint('research', __name__, url_prefix='/signals')

import json
import os

SECTORS_FILE = 'sectors.json'

def load_sectors():
    """Load sectors from JSON file."""
    if os.path.exists(SECTORS_FILE):
        with open(SECTORS_FILE, 'r') as f:
            return json.load(f)
    return {"sectors": {}}

def save_sectors(sectors_data):
    """Save sectors to JSON file."""
    with open(SECTORS_FILE, 'w') as f:
        json.dump(sectors_data, f, indent=2)

def fetch_price_data(symbols, start_date, end_date):
    """Fetch price data for symbols using Alpaca."""
    data = []
    for symbol in symbols:
        try:
            df = fetch_stock_data(symbol, start_date, end_date)
            if df is None or df.empty:
                continue
            # Remove timezone if present
            if 'date' in df.columns and hasattr(df['date'].dtype, 'tz') and df['date'].dt.tz is not None:
                df['date'] = df['date'].dt.tz_localize(None)
            data.append(df[['symbol', 'date', 'open', 'high', 'low', 'close', 'volume']])
        except:
            continue
    
    if not data:
        return pd.DataFrame()
    
    return pd.concat(data, ignore_index=True)


@research_bp.route('/list', methods=['GET'])
def list_signals():
    """List all available signals with metadata."""
    signal_list = signals.list_signals()
    return jsonify(signal_list)


@research_bp.route('/backtest', methods=['POST'])
def run_backtest():
    """
    Run backtest for a signal.
    
    Request JSON:
    {
        "signal_name": "rsi_14",
        "symbols": ["AAPL", "MSFT", ...],
        "horizon_days": 20,
        "start_date": "2024-01-01",
        "end_date": "2025-12-31"
    }
    """
    data = request.get_json()
    
    signal_name = data.get('signal_name')
    symbols = data.get('symbols', [])
    horizon_days = data.get('horizon_days', 20)
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    
    if not signal_name or not symbols:
        return jsonify({'error': 'signal_name and symbols required'}), 400
    
    # Get signal
    signal = signals.get_signal(signal_name)
    if not signal:
        return jsonify({'error': f'Signal {signal_name} not found'}), 404
    
    # Fetch price data
    df_prices = fetch_price_data(symbols, start_date, end_date)
    if df_prices.empty:
        return jsonify({'error': 'No price data available', 'details': 'Alpaca returned no data'}), 400
    
    # Compute signal
    df_signals = signal.compute(df_prices)
    if df_signals.empty:
        return jsonify({'error': 'Signal computation failed', 'details': 'No signal values generated'}), 400
    
    # Run backtest
    results = backtest.run_signal_backtest(df_signals, df_prices, horizon_days, start_date, end_date)
    
    # Check for error
    if 'error' in results:
        return jsonify(results), 400
    
    # Convert non-serializable objects
    response = {k: v for k, v in results.items() if k not in ['ic_series', 'quantile_returns']}
    response['date_range'] = [str(d) for d in results.get('date_range', [])]
    
    # Replace NaN with None for JSON serialization
    import math
    for key, value in response.items():
        if isinstance(value, float) and math.isnan(value):
            response[key] = None
    
    return jsonify(response)


@research_bp.route('/decay', methods=['POST'])
def run_decay_analysis():
    """
    Run decay analysis for a signal.
    
    Request JSON:
    {
        "signal_name": "rsi_14",
        "symbols": ["AAPL", "MSFT", ...],
        "horizons": [1, 5, 10, 20, 60],
        "start_date": "2024-01-01",
        "end_date": "2025-12-31"
    }
    """
    data = request.get_json()
    
    signal_name = data.get('signal_name')
    symbols = data.get('symbols', [])
    horizons = data.get('horizons', [1, 5, 10, 20, 60])
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    
    if not signal_name or not symbols:
        return jsonify({'error': 'signal_name and symbols required'}), 400
    
    # Get signal
    signal = signals.get_signal(signal_name)
    if not signal:
        return jsonify({'error': f'Signal {signal_name} not found'}), 404
    
    # Fetch price data
    df_prices = fetch_price_data(symbols, start_date, end_date)
    if df_prices.empty:
        return jsonify({'error': 'No price data available'}), 400
    
    # Compute signal
    df_signals = signal.compute(df_prices)
    
    # Run decay analysis
    decay_df = backtest.run_decay_analysis(df_signals, df_prices, horizons, start_date, end_date)
    
    return jsonify(decay_df.to_dict(orient='records'))


@research_bp.route('/correlation', methods=['POST'])
def compute_correlation():
    """
    Compute correlation matrix of signals.
    
    Request JSON:
    {
        "signal_names": ["rsi_14", "macd", "momentum_20"],
        "symbols": ["AAPL", "MSFT", ...],
        "start_date": "2024-01-01",
        "end_date": "2025-12-31"
    }
    """
    data = request.get_json()
    
    signal_names = data.get('signal_names', [])
    symbols = data.get('symbols', [])
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    
    if not signal_names or not symbols:
        return jsonify({'error': 'signal_names and symbols required'}), 400
    
    # Fetch price data
    df_prices = fetch_price_data(symbols, start_date, end_date)
    if df_prices.empty:
        return jsonify({'error': 'No price data available'}), 400
    
    # Compute all signals
    all_signals = []
    for signal_name in signal_names:
        signal = signals.get_signal(signal_name)
        if signal:
            df_sig = signal.compute(df_prices)
            all_signals.append(df_sig)
    
    if not all_signals:
        return jsonify({'error': 'No valid signals computed'}), 400
    
    df_all_signals = pd.concat(all_signals, ignore_index=True)
    
    # Compute correlation matrix
    corr_matrix = analytics.signal_correlation_matrix(df_all_signals)
    
    return jsonify(corr_matrix.to_dict())


@research_bp.route('/composite', methods=['POST'])
def build_composite():
    """
    Build composite signal from multiple signals.
    
    Request JSON:
    {
        "signal_names": ["rsi_14", "macd", "momentum_20"],
        "signal_weights": {"rsi_14": 0.4, "macd": 0.3, "momentum_20": 0.3},
        "symbols": ["AAPL", "MSFT", ...],
        "start_date": "2024-01-01",
        "end_date": "2025-12-31"
    }
    """
    data = request.get_json()
    
    signal_names = data.get('signal_names', [])
    signal_weights = data.get('signal_weights')
    symbols = data.get('symbols', [])
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    
    if not signal_names or not symbols:
        return jsonify({'error': 'signal_names and symbols required'}), 400
    
    # Fetch price data
    df_prices = fetch_price_data(symbols, start_date, end_date)
    if df_prices.empty:
        return jsonify({'error': 'No price data available'}), 400
    
    # Compute all signals
    all_signals = []
    for signal_name in signal_names:
        signal = signals.get_signal(signal_name)
        if signal:
            df_sig = signal.compute(df_prices)
            all_signals.append(df_sig)
    
    if not all_signals:
        return jsonify({'error': 'No valid signals computed'}), 400
    
    df_all_signals = pd.concat(all_signals, ignore_index=True)
    
    # Build composite
    df_composite = analytics.build_composite_signal(df_all_signals, signal_weights, start_date, end_date)
    
    # Run backtest on composite
    horizon_days = data.get('horizon_days', 20)
    results = backtest.run_signal_backtest(df_composite, df_prices, horizon_days, start_date, end_date)
    
    response = {k: v for k, v in results.items() if k not in ['ic_series', 'quantile_returns']}
    response['date_range'] = [str(d) for d in results.get('date_range', [])]
    
    return jsonify(response)


@research_bp.route('/regime', methods=['POST'])
def analyze_regime():
    """
    Analyze signal performance by market regime.
    
    Request JSON:
    {
        "signal_names": ["rsi_14", "macd"],
        "symbols": ["AAPL", "MSFT", ...],
        "index_symbol": "SPY",
        "horizon_days": 20,
        "start_date": "2024-01-01",
        "end_date": "2025-12-31"
    }
    """
    data = request.get_json()
    
    signal_names = data.get('signal_names', [])
    symbols = data.get('symbols', [])
    index_symbol = data.get('index_symbol', 'SPY')
    horizon_days = data.get('horizon_days', 20)
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    
    if not signal_names or not symbols:
        return jsonify({'error': 'signal_names and symbols required'}), 400
    
    # Fetch price data (including index)
    all_symbols = list(set(symbols + [index_symbol]))
    df_prices = fetch_price_data(all_symbols, start_date, end_date)
    if df_prices.empty:
        return jsonify({'error': 'No price data available'}), 400
    
    # Detect regimes
    df_regimes = analytics.detect_market_regime(df_prices, index_symbol)
    
    # Compute all signals
    all_signals = []
    for signal_name in signal_names:
        signal = signals.get_signal(signal_name)
        if signal:
            df_sig = signal.compute(df_prices)
            all_signals.append(df_sig)
    
    if not all_signals:
        return jsonify({'error': 'No valid signals computed'}), 400
    
    df_all_signals = pd.concat(all_signals, ignore_index=True)
    
    # Compute regime-conditional IC
    regime_ic = analytics.compute_regime_conditional_ic(df_all_signals, df_prices, df_regimes, horizon_days)
    
    return jsonify(regime_ic.to_dict(orient='records'))


@research_bp.route('/turnover', methods=['POST'])
def analyze_turnover_endpoint():
    """
    Analyze turnover for a signal.
    
    Request JSON:
    {
        "signal_name": "rsi_14",
        "symbols": ["AAPL", "MSFT", ...],
        "rebalance_freq": 20,
        "top_pct": 0.2,
        "start_date": "2024-01-01",
        "end_date": "2025-12-31"
    }
    """
    data = request.get_json()
    
    signal_name = data.get('signal_name')
    symbols = data.get('symbols', [])
    rebalance_freq = data.get('rebalance_freq', 20)
    top_pct = data.get('top_pct', 0.2)
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    
    if not signal_name or not symbols:
        return jsonify({'error': 'signal_name and symbols required'}), 400
    
    # Get signal
    signal = signals.get_signal(signal_name)
    if not signal:
        return jsonify({'error': f'Signal {signal_name} not found'}), 404
    
    # Fetch price data
    df_prices = fetch_price_data(symbols, start_date, end_date)
    if df_prices.empty:
        return jsonify({'error': 'No price data available'}), 400
    
    # Compute signal
    df_signals = signal.compute(df_prices)
    
    # Analyze turnover
    turnover_metrics = analytics.analyze_turnover(df_signals, rebalance_freq, top_pct)
    
    return jsonify(turnover_metrics)


@research_bp.route('/sectors', methods=['GET'])
def get_sectors():
    """Get all sectors."""
    sectors_data = load_sectors()
    return jsonify(sectors_data)


@research_bp.route('/sectors/<sector_id>', methods=['GET'])
def get_sector(sector_id):
    """Get specific sector."""
    sectors_data = load_sectors()
    sector = sectors_data.get('sectors', {}).get(sector_id)
    if not sector:
        return jsonify({'error': 'Sector not found'}), 404
    return jsonify(sector)


@research_bp.route('/sectors', methods=['POST'])
def create_sector():
    """Create new sector."""
    data = request.get_json()
    sector_id = data.get('id')
    name = data.get('name')
    tickers = data.get('tickers', [])
    
    if not sector_id or not name:
        return jsonify({'error': 'id and name required'}), 400
    
    sectors_data = load_sectors()
    if sector_id in sectors_data.get('sectors', {}):
        return jsonify({'error': 'Sector already exists'}), 400
    
    sectors_data.setdefault('sectors', {})[sector_id] = {
        'name': name,
        'tickers': tickers
    }
    save_sectors(sectors_data)
    return jsonify({'success': True, 'sector': sectors_data['sectors'][sector_id]})


@research_bp.route('/sectors/<sector_id>', methods=['PUT'])
def update_sector(sector_id):
    """Update existing sector."""
    data = request.get_json()
    sectors_data = load_sectors()
    
    if sector_id not in sectors_data.get('sectors', {}):
        return jsonify({'error': 'Sector not found'}), 404
    
    if 'name' in data:
        sectors_data['sectors'][sector_id]['name'] = data['name']
    if 'tickers' in data:
        sectors_data['sectors'][sector_id]['tickers'] = data['tickers']
    
    save_sectors(sectors_data)
    return jsonify({'success': True, 'sector': sectors_data['sectors'][sector_id]})


@research_bp.route('/sectors/<sector_id>', methods=['DELETE'])
def delete_sector(sector_id):
    """Delete sector."""
    sectors_data = load_sectors()
    
    if sector_id not in sectors_data.get('sectors', {}):
        return jsonify({'error': 'Sector not found'}), 404
    
    del sectors_data['sectors'][sector_id]
    save_sectors(sectors_data)
    return jsonify({'success': True})


# Sector Scan API Endpoints
import sector_scan
import os
from threading import Thread

# Global scan state
current_scan_job = None
scan_results_cache = None

@research_bp.route('/sector/config', methods=['GET'])
def get_sector_config():
    """Get current scan configuration."""
    config = sector_scan.load_schedule_config()
    return jsonify(config)

@research_bp.route('/sector/config', methods=['POST'])
def save_sector_config():
    """Save scan configuration."""
    data = request.get_json()
    sector_scan.save_schedule_config(data)
    return jsonify({'success': True})

@research_bp.route('/sector/results', methods=['GET'])
def get_sector_results():
    """Get most recent scorecard."""
    # Find most recent CSV
    data_dir = sector_scan.DATA_DIR
    csv_files = list(data_dir.glob('sector_scorecard_*.csv'))
    
    if not csv_files:
        return jsonify({'error': 'No results found'}), 404
    
    latest_file = max(csv_files, key=lambda p: p.stat().st_mtime)
    df = pd.read_csv(latest_file)
    
    return jsonify({
        'timestamp': latest_file.stat().st_mtime,
        'filename': latest_file.name,
        'results': df.to_dict(orient='records')
    })

@research_bp.route('/sector/run', methods=['POST'])
def run_sector_scan():
    """Trigger immediate scan."""
    global current_scan_job
    
    data = request.get_json()
    mode = data.get('mode', 'daily')
    min_stocks = data.get('min_stocks', 15)
    signal_names = data.get('signals')  # Optional custom signals
    
    if current_scan_job and current_scan_job.is_alive():
        return jsonify({'error': 'Scan already running'}), 400
    
    job_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    def run_async():
        try:
            sector_scan.run_scan(mode=mode, min_stocks=min_stocks, signal_names=signal_names)
        except Exception as e:
            sector_scan.log(f"Scan error: {e}")
    
    current_scan_job = Thread(target=run_async, daemon=True)
    current_scan_job.start()
    
    return jsonify({'success': True, 'job_id': job_id})

@research_bp.route('/sector/status/<job_id>', methods=['GET'])
def get_scan_status(job_id):
    """Get scan status."""
    global current_scan_job
    
    if current_scan_job and current_scan_job.is_alive():
        return jsonify({'status': 'running', 'job_id': job_id})
    else:
        return jsonify({'status': 'completed', 'job_id': job_id})

@research_bp.route('/sector/cancel/<job_id>', methods=['POST'])
def cancel_scan(job_id):
    """Cancel running scan (not implemented - scans run to completion)."""
    return jsonify({'success': False, 'message': 'Cancellation not supported'})

@research_bp.route('/sector/schedule', methods=['GET'])
def get_schedule_status():
    """Get scheduler status."""
    status = sector_scan.get_scheduler_status()
    return jsonify(status)

@research_bp.route('/sector/schedule', methods=['POST'])
def update_schedule():
    """Update scheduler configuration."""
    data = request.get_json()
    
    # Save config
    sector_scan.save_schedule_config(data)
    
    # Start or stop scheduler
    if data.get('enabled', False):
        sector_scan.start_scheduler(
            daily_time=data.get('daily_time', '16:30'),
            weekly_day=data.get('weekly_day', 'sunday'),
            weekly_time=data.get('weekly_time', '18:00')
        )
    else:
        sector_scan.stop_scheduler()
    
    return jsonify({'success': True})

@research_bp.route('/sector/baskets', methods=['GET'])
def get_sector_baskets():
    """Get all sector baskets."""
    baskets = sector_scan.load_sectors()
    return jsonify({'sectors': baskets})

@research_bp.route('/sector/baskets', methods=['POST'])
def update_sector_basket():
    """Update a sector basket."""
    data = request.get_json()
    sector_id = data.get('sector_id')
    tickers = data.get('tickers', [])
    
    baskets_file = sector_scan.BASKETS_FILE
    with open(baskets_file, 'r') as f:
        baskets_data = json.load(f)
    
    if sector_id in baskets_data.get('sectors', {}):
        baskets_data['sectors'][sector_id]['tickers'] = tickers
        
        with open(baskets_file, 'w') as f:
            json.dump(baskets_data, f, indent=2)
        
        return jsonify({'success': True})
    
    return jsonify({'error': 'Sector not found'}), 404



# ============================================================================
# REGIME CLASSIFIER ROUTES
# ============================================================================
import regime_classifier

@research_bp.route('/regime/analysis', methods=['GET'])
def get_regime_analysis():
    """Get current regime analysis (cached if fresh)"""
    try:
        result = regime_classifier.run_regime_analysis(force_refresh=False)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@research_bp.route('/regime/refresh', methods=['POST'])
def refresh_regime_analysis():
    """Force refresh regime analysis"""
    try:
        result = regime_classifier.run_regime_analysis(force_refresh=True)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@research_bp.route('/regime/history', methods=['GET'])
def get_regime_history():
    """Get last 30 daily regime verdicts"""
    try:
        history = regime_classifier.get_regime_history()
        return jsonify({'history': history})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# RISK MANAGER ROUTES
# ============================================================================
import risk_manager

@research_bp.route('/risk/snapshot', methods=['GET'])
def get_risk_snapshot():
    """Get current risk snapshot"""
    try:
        result = risk_manager.get_risk_snapshot(force_refresh=False)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@research_bp.route('/risk/refresh', methods=['POST'])
def refresh_risk_snapshot():
    """Force refresh risk snapshot"""
    try:
        result = risk_manager.get_risk_snapshot(force_refresh=True)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@research_bp.route('/risk/config', methods=['GET'])
def get_risk_config():
    """Get risk configuration"""
    try:
        config = risk_manager.load_config()
        return jsonify(config)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@research_bp.route('/risk/config', methods=['POST'])
def update_risk_config():
    """Update risk configuration"""
    try:
        config = request.get_json()
        risk_manager.save_config(config)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@research_bp.route('/risk/history', methods=['GET'])
def get_risk_history():
    """Get 30-day risk history"""
    try:
        history = risk_manager.get_risk_history()
        return jsonify({'history': history})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@research_bp.route('/risk/positions/manual', methods=['POST'])
def add_manual_position():
    """Add manual position"""
    try:
        position_data = request.get_json()
        result = risk_manager.add_manual_position(position_data)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@research_bp.route('/risk/positions/manual/<position_id>', methods=['PUT'])
def update_manual_position(position_id):
    """Update manual position"""
    try:
        position_data = request.get_json()
        result = risk_manager.update_manual_position(position_id, position_data)
        if result:
            return jsonify(result)
        return jsonify({'error': 'Position not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@research_bp.route('/risk/positions/manual/<position_id>', methods=['DELETE'])
def delete_manual_position(position_id):
    """Delete manual position"""
    try:
        risk_manager.delete_manual_position(position_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@research_bp.route('/risk/recovery/reset', methods=['POST'])
def reset_recovery_mode():
    """Reset recovery mode"""
    try:
        risk_manager.reset_recovery_mode()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@research_bp.route('/risk/reset-baseline', methods=['POST'])
def reset_start_of_day():
    """Reset start of day baseline to current portfolio value"""
    try:
        result = risk_manager.reset_start_of_day()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@research_bp.route('/risk/eod', methods=['POST'])
def end_of_day_close():
    """End of day close"""
    try:
        result = risk_manager.end_of_day_close()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
