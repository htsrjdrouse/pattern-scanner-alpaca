"""
Watchlist Module — Manual alert watchlist with nightly EOD condition checking.

Provides:
- Add/remove tickers with custom alert conditions (floor, resistance, volume multiplier)
- Background thread runs nightly EOD checks via yfinance
- TRIGGERED badge when all conditions met
- JSON file persistence
"""

import json
import os
import threading
import time
from datetime import datetime, timedelta
from flask import request, redirect, render_template_string, flash

WATCHLIST_FILE = 'data/watchlist.json'
_checker_thread = None
_checker_running = False


# ── JSON Persistence ───────────────────────────────────────────────────────

def _load_watchlist():
    if os.path.exists(WATCHLIST_FILE):
        with open(WATCHLIST_FILE, 'r') as f:
            return json.load(f)
    return []


def _save_watchlist(entries):
    os.makedirs(os.path.dirname(WATCHLIST_FILE), exist_ok=True)
    with open(WATCHLIST_FILE, 'w') as f:
        json.dump(entries, f, indent=2, default=str)


# ── EOD Condition Checker ──────────────────────────────────────────────────

def _check_entry(entry):
    """Evaluate all alert conditions for a single watchlist entry via yfinance."""
    import yfinance as yf
    import pandas_ta as ta

    try:
        ticker = yf.Ticker(entry['ticker'])
        hist = ticker.history(period='60d')
        if hist is None or hist.empty or len(hist) < 25:
            return entry

        close = hist['Close']
        volume = hist['Volume']
        current_close = float(close.iloc[-1])

        results = {}

        # 1. Close above resistance trigger
        results['above_resistance'] = current_close > entry.get('resistance', 0)

        # 2. MACD crossed positive
        macd_df = ta.macd(close)
        if macd_df is not None and 'MACDh_12_26_9' in macd_df.columns:
            hist_vals = macd_df['MACDh_12_26_9'].dropna()
            results['macd_positive'] = (
                len(hist_vals) >= 2
                and float(hist_vals.iloc[-1]) > 0
                and float(hist_vals.iloc[-2]) <= 0
            )
        else:
            results['macd_positive'] = False

        # 3. ADX higher than prior day
        adx_df = ta.adx(hist['High'], hist['Low'], close)
        if adx_df is not None and 'ADX_14' in adx_df.columns:
            adx_vals = adx_df['ADX_14'].dropna()
            results['adx_rising'] = (
                len(adx_vals) >= 2
                and float(adx_vals.iloc[-1]) > float(adx_vals.iloc[-2])
            )
        else:
            results['adx_rising'] = False

        # 4. Volume above specified multiplier vs 20-day average
        vol_mult = entry.get('volume_multiplier', 1.5)
        avg_vol_20 = float(volume.tail(20).mean())
        current_vol = float(volume.iloc[-1])
        results['volume_surge'] = avg_vol_20 > 0 and current_vol >= avg_vol_20 * vol_mult

        # 5. Price held above support floor
        results['above_floor'] = current_close > entry.get('floor', 0)

        # Store check results
        entry['last_check'] = datetime.now().isoformat()
        entry['last_price'] = current_close
        entry['check_results'] = results
        entry['triggered'] = all(results.values())
        if entry['triggered'] and not entry.get('triggered_at'):
            entry['triggered_at'] = datetime.now().isoformat()

    except Exception as e:
        entry['last_check'] = datetime.now().isoformat()
        entry['check_error'] = str(e)

    return entry


def _eod_checker_loop():
    """Background loop: runs EOD check once daily after 4:30 PM ET."""
    global _checker_running
    while _checker_running:
        now = datetime.now()
        # Run at ~4:30 PM local time on weekdays (M-F)
        is_weekday = now.weekday() < 5
        is_eod_window = now.hour == 16 and 30 <= now.minute <= 45

        if is_weekday and is_eod_window:
            print(f'[Watchlist] Running EOD check at {now.isoformat()}')
            entries = _load_watchlist()
            for i, entry in enumerate(entries):
                if not _checker_running:
                    break
                entries[i] = _check_entry(entry)
            _save_watchlist(entries)
            print(f'[Watchlist] EOD check complete — {len(entries)} entries checked')
            # Sleep 20 min to avoid re-running in the same window
            for _ in range(1200):
                if not _checker_running:
                    break
                time.sleep(1)
        else:
            # Check every 60 seconds whether we're in the EOD window
            for _ in range(60):
                if not _checker_running:
                    break
                time.sleep(1)


def _start_checker():
    global _checker_thread, _checker_running
    if _checker_running:
        return
    _checker_running = True
    _checker_thread = threading.Thread(target=_eod_checker_loop, daemon=True)
    _checker_thread.start()
    print('[Watchlist] EOD checker thread started')


# ── HTML Template ──────────────────────────────────────────────────────────

WATCHLIST_HTML = """
<html>
<head>
    <title>Watchlist</title>
    <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; margin: 20px; background: #1a1a2e; color: #eee; }
        h1 { color: #00d4ff; }
        .container { max-width: 1200px; margin: auto; }
        .navbar { background: #16213e; padding: 10px; border-radius: 8px; margin-bottom: 20px; }
        .navbar a { color: #00d4ff; text-decoration: none; margin: 0 15px; }
        .navbar a:hover { text-decoration: underline; }
        table { border-collapse: collapse; width: 100%; margin-top: 20px; font-size: 14px; }
        th, td { border: 1px solid #333; padding: 10px; text-align: center; }
        th { background: #16213e; color: #00d4ff; }
        tr:nth-child(even) { background: #0f0f23; }
        tr:hover { background: #1f1f3a; }
        .btn { padding: 8px 15px; color: white; text-decoration: none; border-radius: 5px; border: none; cursor: pointer; font-size: 13px; }
        .btn-add { background: #667eea; }
        .btn-danger { background: #f44336; }
        .btn-check { background: #4caf50; }
        .btn:hover { opacity: 0.8; }
        .badge-triggered { background: #4caf50; color: #000; padding: 4px 10px; border-radius: 4px; font-weight: bold; font-size: 12px; animation: pulse 2s infinite; }
        .badge-watching { background: #555; color: #ccc; padding: 4px 10px; border-radius: 4px; font-size: 12px; }
        @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.6; } }
        .add-form { background: #16213e; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .add-form label { display: block; margin: 8px 0 4px; color: #aaa; font-size: 13px; }
        .add-form input, .add-form textarea { background: #1a1a2e; color: #eee; border: 1px solid #333; padding: 8px; border-radius: 4px; width: 100%; box-sizing: border-box; }
        .add-form .row { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; }
        .check-detail { font-size: 11px; }
        .check-pass { color: #4caf50; }
        .check-fail { color: #f44336; }
        .flash { padding: 10px; border-radius: 5px; margin: 10px 0; }
        .flash-success { background: #00c853; color: #000; }
        .flash-error { background: #f44336; }
        .notes-col { max-width: 150px; font-size: 12px; color: #aaa; text-align: left; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    </style>
</head>
<body>
<div class="container">
    <div class="navbar">
        <a href="/">Home</a>
        <a href="/tracked">Tracked Stocks</a>
        <a href="/watchlist">👁 Watchlist</a>
        <a href="/research">🔬 Alpha Research</a>
        <a href="/journal/">📊 Trade Journal</a>
        <a href="/saved-results">📁 Saved Results</a>
    </div>
    <h1>👁 Manual Watchlist</h1>
    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
                <div class="flash flash-{{ category }}">{{ message }}</div>
            {% endfor %}
        {% endif %}
    {% endwith %}

    <div class="add-form">
        <h3 style="color:#00d4ff; margin-top:0;">Add to Watchlist</h3>
        <form method="post" action="/watchlist/add">
            <div class="row">
                <div><label>Ticker</label><input name="ticker" required placeholder="AAPL"></div>
                <div><label>Support Floor ($)</label><input name="floor" type="number" step="0.01" required placeholder="170.00"></div>
                <div><label>Resistance Trigger ($)</label><input name="resistance" type="number" step="0.01" required placeholder="185.00"></div>
                <div><label>Volume Multiplier (vs 20d avg)</label><input name="volume_multiplier" type="number" step="0.1" value="1.5" required></div>
                <div><label>Notes (optional)</label><input name="notes" placeholder="Earnings catalyst..."></div>
            </div>
            <button type="submit" class="btn btn-add" style="margin-top:12px;">+ Add Entry</button>
        </form>
    </div>

    <div style="margin-bottom:12px;">
        <form method="post" action="/watchlist/check-now" style="display:inline;">
            <button type="submit" class="btn btn-check">⚡ Run Check Now</button>
        </form>
        <span style="color:#666; font-size:12px; margin-left:12px;">EOD auto-check runs daily ~4:30 PM</span>
    </div>

    {% if entries %}
    <table>
        <tr>
            <th>Status</th>
            <th>Ticker</th>
            <th>Last Price</th>
            <th>Floor</th>
            <th>Resistance</th>
            <th>Vol Mult</th>
            <th>Conditions</th>
            <th>Notes</th>
            <th>Last Check</th>
            <th>Actions</th>
        </tr>
        {% for e in entries %}
        <tr {% if e.triggered %}style="background: rgba(76,175,80,0.15);"{% endif %}>
            <td>
                {% if e.triggered %}
                    <span class="badge-triggered">🔔 TRIGGERED</span>
                    {% if e.triggered_at %}<br><small style="color:#888;">{{ e.triggered_at[:16] }}</small>{% endif %}
                {% else %}
                    <span class="badge-watching">👁 WATCHING</span>
                {% endif %}
            </td>
            <td><a href="/chart/{{ e.ticker }}" style="color:#00d4ff; font-weight:bold;">{{ e.ticker }}</a></td>
            <td>{% if e.last_price %}${{ '%.2f'|format(e.last_price) }}{% else %}-{% endif %}</td>
            <td>${{ '%.2f'|format(e.floor) }}</td>
            <td>${{ '%.2f'|format(e.resistance) }}</td>
            <td>{{ e.volume_multiplier }}x</td>
            <td class="check-detail">
                {% if e.check_results %}
                    <span class="{{ 'check-pass' if e.check_results.above_resistance else 'check-fail' }}">{{ '✔' if e.check_results.above_resistance else '✘' }} Resistance</span><br>
                    <span class="{{ 'check-pass' if e.check_results.macd_positive else 'check-fail' }}">{{ '✔' if e.check_results.macd_positive else '✘' }} MACD Cross</span><br>
                    <span class="{{ 'check-pass' if e.check_results.adx_rising else 'check-fail' }}">{{ '✔' if e.check_results.adx_rising else '✘' }} ADX Rising</span><br>
                    <span class="{{ 'check-pass' if e.check_results.volume_surge else 'check-fail' }}">{{ '✔' if e.check_results.volume_surge else '✘' }} Volume</span><br>
                    <span class="{{ 'check-pass' if e.check_results.above_floor else 'check-fail' }}">{{ '✔' if e.check_results.above_floor else '✘' }} Floor</span>
                {% else %}
                    <span style="color:#666;">Not checked yet</span>
                {% endif %}
            </td>
            <td class="notes-col" title="{{ e.notes or '' }}">{{ e.notes or '-' }}</td>
            <td>{{ e.last_check[:16] if e.last_check else '-' }}</td>
            <td>
                <form method="post" action="/watchlist/{{ e.ticker }}/delete" style="display:inline;">
                    <button type="submit" class="btn btn-danger" onclick="return confirm('Remove {{ e.ticker }}?')">Remove</button>
                </form>
                {% if e.triggered %}
                <form method="post" action="/watchlist/{{ e.ticker }}/reset" style="display:inline;">
                    <button type="submit" class="btn" style="background:#ff9800; margin-top:4px;">Reset</button>
                </form>
                {% endif %}
            </td>
        </tr>
        {% endfor %}
    </table>
    {% else %}
    <p style="color:#888;">No watchlist entries yet. Add a ticker above to start monitoring.</p>
    {% endif %}
</div>
</body>
</html>
"""


# ── Flask Routes ───────────────────────────────────────────────────────────

def add_watchlist_routes(app):
    """Register watchlist routes on the Flask app and start the EOD checker."""

    _start_checker()

    @app.route('/watchlist')
    def watchlist_page():
        entries = _load_watchlist()
        prefill = {}

        # Auto-add when arriving from scanner/chart with ticker param
        ticker = request.args.get('ticker', '').strip().upper()
        if ticker:
            if any(e['ticker'] == ticker for e in entries):
                flash(f'{ticker} is already on the watchlist.', 'error')
            else:
                new_entry = {
                    'ticker': ticker,
                    'floor': float(request.args.get('floor', 0)),
                    'resistance': float(request.args.get('resistance', 0)),
                    'volume_multiplier': float(request.args.get('volume_multiplier', 1.5)),
                    'notes': request.args.get('notes', '').strip() or None,
                    'added_at': datetime.now().isoformat(),
                    'triggered': False,
                    'triggered_at': None,
                    'last_check': None,
                    'last_price': None,
                    'check_results': None,
                }
                entries.append(new_entry)
                _save_watchlist(entries)
                flash(f'Added {ticker} to watchlist.', 'success')

        # Triggered first, then by added_at desc
        entries.sort(key=lambda e: (not e.get('triggered', False), e.get('added_at', '')), reverse=False)
        entries.sort(key=lambda e: e.get('triggered', False), reverse=True)
        return render_template_string(WATCHLIST_HTML, entries=entries, prefill=prefill)

    @app.route('/watchlist/add', methods=['POST'])
    def watchlist_add():
        ticker = request.form.get('ticker', '').strip().upper()
        if not ticker:
            flash('Ticker is required.', 'error')
            return redirect('/watchlist')

        entries = _load_watchlist()
        if any(e['ticker'] == ticker for e in entries):
            flash(f'{ticker} is already on the watchlist.', 'error')
            return redirect('/watchlist')

        entries.append({
            'ticker': ticker,
            'floor': float(request.form.get('floor', 0)),
            'resistance': float(request.form.get('resistance', 0)),
            'volume_multiplier': float(request.form.get('volume_multiplier', 1.5)),
            'notes': request.form.get('notes', '').strip() or None,
            'added_at': datetime.now().isoformat(),
            'triggered': False,
            'triggered_at': None,
            'last_check': None,
            'last_price': None,
            'check_results': None,
        })
        _save_watchlist(entries)
        flash(f'Added {ticker} to watchlist.', 'success')
        return redirect('/watchlist')

    @app.route('/watchlist/<ticker>/delete', methods=['POST'])
    def watchlist_delete(ticker):
        entries = [e for e in _load_watchlist() if e['ticker'] != ticker.upper()]
        _save_watchlist(entries)
        flash(f'Removed {ticker.upper()} from watchlist.', 'success')
        return redirect('/watchlist')

    @app.route('/watchlist/<ticker>/reset', methods=['POST'])
    def watchlist_reset(ticker):
        entries = _load_watchlist()
        for e in entries:
            if e['ticker'] == ticker.upper():
                e['triggered'] = False
                e['triggered_at'] = None
                e['check_results'] = None
                break
        _save_watchlist(entries)
        flash(f'Reset {ticker.upper()} trigger status.', 'success')
        return redirect('/watchlist')

    @app.route('/watchlist/check-now', methods=['POST'])
    def watchlist_check_now():
        entries = _load_watchlist()
        triggered_count = 0
        for i, entry in enumerate(entries):
            entries[i] = _check_entry(entry)
            if entries[i].get('triggered'):
                triggered_count += 1
        _save_watchlist(entries)
        flash(f'Checked {len(entries)} entries — {triggered_count} triggered.', 'success')
        return redirect('/watchlist')
