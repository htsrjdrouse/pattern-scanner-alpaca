#!/usr/bin/env python3
"""
Automated sector analysis using Alpha Research Platform.
"""
import json
import argparse
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from pathlib import Path
import time
import schedule
import threading
import signals
import backtest

DATA_DIR = Path(__file__).parent / 'data'
BASKETS_FILE = Path(__file__).parent / 'sectors.json'  # Use same file as sector manager
LOG_FILE = DATA_DIR / 'scan_log.txt'
DROPPED_FILE = DATA_DIR / 'dropped_tickers.log'
SCHEDULE_FILE = DATA_DIR / 'scan_schedule.json'

DAILY_SIGNALS = ['momentum_20', 'ma_cross_50_200', 'adx_14', 'cto_larsson']
PATTERN_SIGNALS = ['cup_handle', 'bull_flag', 'asc_triangle', 'double_bottom']

# Global scheduler state
scheduler_running = False
scheduler_thread = None

def log(msg):
    """Write to log file and print."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_msg = f"[{timestamp}] {msg}"
    print(log_msg)
    with open(LOG_FILE, 'a') as f:
        f.write(log_msg + '\n')

def load_sectors():
    """Load sector baskets from JSON."""
    with open(BASKETS_FILE, 'r') as f:
        data = json.load(f)
    return data.get('sectors', {})

def validate_ticker(symbol, start_date, end_date):
    """Validate ticker has sufficient data. Returns df or None."""
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start_date, end=end_date)
        if df.empty:
            return None
        
        # Check for >10% missing data
        expected_days = (end_date - start_date).days * 0.7  # ~70% for trading days
        if len(df) < expected_days * 0.9:
            return None
        
        df = df.reset_index()
        df['symbol'] = symbol
        df.columns = [c.lower() for c in df.columns]
        if 'date' in df.columns and hasattr(df['date'].dtype, 'tz') and df['date'].dt.tz:
            df['date'] = df['date'].dt.tz_localize(None)
        return df[['symbol', 'date', 'open', 'high', 'low', 'close', 'volume']]
    except Exception as e:
        return None

def fetch_sector_data(sector_id, tickers, start_date, end_date, min_stocks=15):
    """Fetch and validate data for a sector."""
    valid_data = []
    dropped = []
    
    for symbol in tickers:
        df = validate_ticker(symbol, start_date, end_date)
        if df is not None:
            valid_data.append(df)
        else:
            dropped.append(symbol)
    
    if dropped:
        with open(DROPPED_FILE, 'a') as f:
            f.write(f"{datetime.now().date()} - {sector_id}: {', '.join(dropped)}\n")
    
    if len(valid_data) < min_stocks:
        log(f"WARNING: {sector_id} has only {len(valid_data)} valid tickers (min {min_stocks}), skipping")
        return None
    
    return pd.concat(valid_data, ignore_index=True)

def run_sector_backtest(sector_id, df_prices, signal_names, horizon_days):
    """Run backtest for all signals on a sector."""
    results = {}
    
    for signal_name in signal_names:
        try:
            signal = signals.get_signal(signal_name)
            if not signal:
                continue
            
            df_signals = signal.compute(df_prices)
            if df_signals.empty:
                continue
            
            bt_result = backtest.run_signal_backtest(df_signals, df_prices, horizon_days)
            if 'error' not in bt_result:
                results[signal_name] = bt_result
        except Exception as e:
            log(f"Error running {signal_name} on {sector_id}: {e}")
    
    return results

def calculate_composite_score(results):
    """Calculate composite score from backtest results."""
    if not results:
        return 0.0, 0.0, 0.0, 0
    
    ics = [r.get('ic_pearson_mean', 0) for r in results.values()]
    hit_rates = [r.get('hit_rate', 0.5) for r in results.values()]
    sharpes = [r.get('long_short_sharpe', 0) for r in results.values()]
    obs = sum([r.get('n_observations', 0) for r in results.values()])
    
    avg_ic = sum(ics) / len(ics) if ics else 0
    avg_hit = sum(hit_rates) / len(hit_rates) if hit_rates else 0.5
    avg_sharpe = sum(sharpes) / len(sharpes) if sharpes else 0
    
    # Composite: IC (35%), normalized hit rate (30%), Sharpe (35%)
    hit_normalized = (avg_hit - 0.5) * 2  # Convert 50-60% to 0-0.2 scale
    composite = (avg_ic * 0.35) + (hit_normalized * 0.30) + (avg_sharpe * 0.35)
    
    return composite, avg_hit, avg_sharpe, obs

def classify_trend(composite, hit_rate, sharpe):
    """Classify sector trend signal."""
    if composite > 0.05 and hit_rate > 0.53 and sharpe > 0.5:
        return 'GREEN'
    elif composite > 0.02 or hit_rate > 0.51:
        return 'YELLOW'
    return 'RED'

def run_scan(mode='daily', min_stocks=15, signal_names=None):
    """Run sector scan."""
    start_time = datetime.now()
    log(f"Starting {mode} scan")
    
    # Configuration
    if signal_names is None:
        if mode == 'weekly':
            signal_names = DAILY_SIGNALS + PATTERN_SIGNALS
        else:
            signal_names = DAILY_SIGNALS
    
    if mode == 'weekly':
        timeframe_days = 730  # 2 years
    else:
        timeframe_days = 365  # 1 year
    
    horizon_days = 20
    end_date = datetime.now()
    start_date = end_date - timedelta(days=timeframe_days)
    
    # Load sectors
    sectors = load_sectors()
    log(f"Loaded {len(sectors)} sectors")
    
    # Process each sector
    scorecard = []
    processed = 0
    skipped = 0
    
    for sector_id, sector_data in sectors.items():
        log(f"Processing {sector_id}...")
        
        df_prices = fetch_sector_data(
            sector_id, 
            sector_data['tickers'], 
            start_date, 
            end_date, 
            min_stocks
        )
        
        if df_prices is None:
            skipped += 1
            continue
        
        results = run_sector_backtest(sector_id, df_prices, signal_names, horizon_days)
        composite, hit_rate, sharpe, obs = calculate_composite_score(results)
        trend = classify_trend(composite, hit_rate, sharpe)
        
        row = {
            'sector': sector_data['name'],
            'sector_id': sector_id,
            'composite_score': composite,
            'avg_hit_rate': hit_rate,
            'avg_sharpe': sharpe,
            'observations': obs,
            'trend_signal': trend
        }
        
        # Add individual signal ICs
        for sig_name in signal_names:
            if sig_name in results:
                row[f'{sig_name}_ic'] = results[sig_name].get('ic_pearson_mean', 0)
        
        scorecard.append(row)
        processed += 1
    
    if processed < 10:
        log(f"WARNING: Only {processed} sectors processed - results may not be reliable")
    
    # Sort by composite score
    scorecard.sort(key=lambda x: x['composite_score'], reverse=True)
    
    # Add rank
    for i, row in enumerate(scorecard, 1):
        row['rank'] = i
    
    # Save CSV
    df_scorecard = pd.DataFrame(scorecard)
    csv_file = DATA_DIR / f"sector_scorecard_{datetime.now().strftime('%Y%m%d')}.csv"
    df_scorecard.to_csv(csv_file, index=False)
    
    # Print summary
    print("\n" + "="*60)
    print(f"SECTOR SCORECARD - {mode.upper()} SCAN")
    print("="*60)
    print(f"{'Rank':<6} {'Sector':<30} {'Score':<10} {'Signal':<8}")
    print("-"*60)
    for row in scorecard:
        print(f"{row['rank']:<6} {row['sector']:<30} {row['composite_score']:>8.3f}  {row['trend_signal']:<8}")
    print("="*60)
    
    runtime = (datetime.now() - start_time).total_seconds()
    log(f"Scan complete: {processed} processed, {skipped} skipped, {runtime:.1f}s")
    
    return scorecard

def load_schedule_config():
    """Load scheduler configuration."""
    if SCHEDULE_FILE.exists():
        with open(SCHEDULE_FILE, 'r') as f:
            return json.load(f)
    return {
        'enabled': False,
        'daily_time': '16:30',
        'weekly_day': 'sunday',
        'weekly_time': '18:00',
        'min_stocks': 15,
        'signals': ['momentum_20', 'ma_cross_50_200', 'adx_14', 'cto_larsson']
    }

def save_schedule_config(config):
    """Save scheduler configuration."""
    with open(SCHEDULE_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def scheduled_daily_scan():
    """Wrapper for scheduled daily scan."""
    log("Running scheduled daily scan")
    try:
        run_scan(mode='daily')
    except Exception as e:
        log(f"ERROR in scheduled daily scan: {e}")

def scheduled_weekly_scan():
    """Wrapper for scheduled weekly scan."""
    log("Running scheduled weekly scan")
    try:
        run_scan(mode='weekly')
    except Exception as e:
        log(f"ERROR in scheduled weekly scan: {e}")

def run_scheduler():
    """Run the scheduler loop."""
    global scheduler_running
    scheduler_running = True
    log("Scheduler started")
    
    while scheduler_running:
        schedule.run_pending()
        time.sleep(60)  # Check every minute
    
    log("Scheduler stopped")

def start_scheduler(daily_time='16:30', weekly_day='sunday', weekly_time='18:00'):
    """Start the background scheduler."""
    global scheduler_thread, scheduler_running
    
    if scheduler_running:
        log("Scheduler already running")
        return
    
    # Clear any existing jobs
    schedule.clear()
    
    # Schedule daily scan (Monday-Friday)
    schedule.every().monday.at(daily_time).do(scheduled_daily_scan)
    schedule.every().tuesday.at(daily_time).do(scheduled_daily_scan)
    schedule.every().wednesday.at(daily_time).do(scheduled_daily_scan)
    schedule.every().thursday.at(daily_time).do(scheduled_daily_scan)
    schedule.every().friday.at(daily_time).do(scheduled_daily_scan)
    
    # Schedule weekly scan
    getattr(schedule.every(), weekly_day.lower()).at(weekly_time).do(scheduled_weekly_scan)
    
    # Start scheduler thread
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    log(f"Scheduler configured: Daily at {daily_time} (weekdays), Weekly on {weekly_day} at {weekly_time}")

def stop_scheduler():
    """Stop the background scheduler."""
    global scheduler_running
    scheduler_running = False
    schedule.clear()
    log("Scheduler stop requested")

def get_scheduler_status():
    """Get current scheduler status."""
    config = load_schedule_config()
    
    next_daily = None
    next_weekly = None
    
    if scheduler_running:
        jobs = schedule.get_jobs()
        for job in jobs:
            if 'daily' in str(job.job_func):
                if next_daily is None or job.next_run < next_daily:
                    next_daily = job.next_run
            elif 'weekly' in str(job.job_func):
                next_weekly = job.next_run
    
    return {
        'running': scheduler_running,
        'config': config,
        'next_daily': next_daily.isoformat() if next_daily else None,
        'next_weekly': next_weekly.isoformat() if next_weekly else None
    }

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Automated sector analysis')
    parser.add_argument('--mode', choices=['daily', 'weekly'], default='daily')
    parser.add_argument('--min-stocks', type=int, default=15)
    parser.add_argument('--schedule', action='store_true', help='Run in scheduled mode')
    args = parser.parse_args()
    
    if args.schedule:
        # Load config and start scheduler
        config = load_schedule_config()
        if config.get('enabled', False):
            start_scheduler(
                daily_time=config.get('daily_time', '16:30'),
                weekly_day=config.get('weekly_day', 'sunday'),
                weekly_time=config.get('weekly_time', '18:00')
            )
            print("Scheduler running. Press Ctrl+C to stop.")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                stop_scheduler()
                print("\nScheduler stopped.")
        else:
            print("Scheduler is disabled in config. Enable it first.")
    else:
        # Run once immediately
        run_scan(mode=args.mode, min_stocks=args.min_stocks)

