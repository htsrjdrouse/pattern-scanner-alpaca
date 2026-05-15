"""
Earnings Scanner Routes — Page, scan runner, scheduler status, and log viewer.
"""

import json
import os
import time
import numpy as np
from datetime import datetime, date

import yfinance as yf
from flask import jsonify, request, render_template_string

CACHE_FILE = 'data/earnings_scan_cache.json'


def format_strike_for_tos(strike):
    """Strip trailing .0 from whole number strikes. 360.0 → 360"""
    if strike == int(strike):
        return str(int(strike))
    return str(strike)


def _get_earnings_calendar(days_ahead=14):
    """Get symbols with earnings in the next N days from S&P 500."""
    from pattern_scanner import get_sp500_tickers
    sp500 = get_sp500_tickers()

    upcoming = []
    for sym in sp500:
        try:
            t = yf.Ticker(sym)
            cal = t.calendar
            if cal is None:
                continue
            if isinstance(cal, dict):
                ed = cal.get('Earnings Date')
                if isinstance(ed, list) and len(ed) > 0:
                    ed = ed[0]
            elif hasattr(cal, 'columns') and 'Earnings Date' in cal.columns:
                ed = cal['Earnings Date'].iloc[0]
            else:
                continue
            if ed is None:
                continue
            if hasattr(ed, 'date'):
                ed = ed.date()
            days = (ed - date.today()).days
            if 0 <= days <= days_ahead:
                upcoming.append({'symbol': sym, 'earnings_date': str(ed), 'days_until': days})
        except Exception:
            continue
    return upcoming


def _snap_strike(chain_df, target, direction='below'):
    """Snap to nearest actual chain strike with active bid."""
    valid = chain_df[chain_df['bid'] > 0.01]
    if valid.empty:
        valid = chain_df
    if direction == 'below':
        candidates = valid[valid['strike'] <= target]
        if candidates.empty:
            candidates = valid
        return float(candidates.iloc[(candidates['strike'] - target).abs().argsort()[:1]]['strike'].iloc[0])
    else:
        candidates = valid[valid['strike'] >= target]
        if candidates.empty:
            candidates = valid
        return float(candidates.iloc[(candidates['strike'] - target).abs().argsort()[:1]]['strike'].iloc[0])


def _scan_symbol(sym):
    """Run IV/options analysis on a single symbol with strike snapping."""
    try:
        t = yf.Ticker(sym)
        hist = t.history(period='1y')
        if hist.empty or len(hist) < 30:
            return None

        price = float(hist['Close'].iloc[-1])

        # 30-day historical volatility
        returns = hist['Close'].pct_change().dropna()
        hv_30 = float(returns.tail(30).std() * (252 ** 0.5) * 100)
        hv_1y = float(returns.std() * (252 ** 0.5) * 100)

        # Get options chain
        iv_current = None
        put_strike = None
        call_strike = None
        exp_date = None
        try:
            exp_dates = t.options
            if not exp_dates:
                return None
            # Pick first expiration after earnings
            exp_date = exp_dates[0]
            chain = t.option_chain(exp_date)
            puts = chain.puts
            calls = chain.calls

            if calls.empty or puts.empty:
                return None

            # ATM IV from calls
            atm_idx = (calls['strike'] - price).abs().argsort()[:1]
            iv_current = float(calls.iloc[atm_idx]['impliedVolatility'].iloc[0]) * 100

            # Strike snapping: ~0.85x price for put, ~1.15x price for call
            put_target = price * 0.85
            call_target = price * 1.15
            put_strike = _snap_strike(puts, put_target, 'below')
            call_strike = _snap_strike(calls, call_target, 'above')

        except Exception:
            pass

        if iv_current is None:
            return None

        # IV/HV ratio (the key edge filter)
        iv_hv_ratio = round(iv_current / max(hv_30, 1), 2)

        # IV rank
        iv_rank = min(100, max(0, int((iv_current / max(hv_1y, 1)) * 50)))

        # Score
        score = 0
        if iv_rank >= 50:
            score += 2
        if iv_rank >= 70:
            score += 1
        if iv_hv_ratio >= 2.0:
            score += 3
        elif iv_hv_ratio >= 1.5:
            score += 1
        if iv_current > 40:
            score += 1

        if score >= 3:
            result = {
                'symbol': sym,
                'iv_current': round(iv_current, 1),
                'iv_rank': iv_rank,
                'hv_30': round(hv_30, 1),
                'hv': round(hv_1y, 1),
                'iv_hv_ratio': iv_hv_ratio,
                'price': round(price, 2),
                'score': score,
                'exp_date': exp_date,
            }
            if put_strike is not None:
                result['put_strike'] = put_strike
                result['put_strike_fmt'] = format_strike_for_tos(put_strike)
            if call_strike is not None:
                result['call_strike'] = call_strike
                result['call_strike_fmt'] = format_strike_for_tos(call_strike)
            # TOS string: full format
            if put_strike and call_strike and exp_date:
                from datetime import datetime as _dt
                _exp = _dt.strptime(exp_date, '%Y-%m-%d')
                _months = ['JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC']
                _exp_str = f"{_exp.day} {_months[_exp.month-1]} {str(_exp.year)[2:]}"
                result['tos_string'] = f"SELL -1 STRANGLE {sym} 100 {_exp_str} {format_strike_for_tos(put_strike)}/{format_strike_for_tos(call_strike)} CALL/PUT @LMT"
            return result
    except Exception:
        pass
    return None


def _run_scan(force_refresh=False):
    """Run the full earnings scan, using cache if fresh."""
    if not force_refresh and os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            cached = json.load(f)
        age_h = (datetime.now() - datetime.fromisoformat(cached.get('scanned_at', '2000-01-01'))).total_seconds() / 3600
        if age_h < 12:
            return cached

    start = time.time()
    calendar = _get_earnings_calendar()
    candidates = []
    for item in calendar:
        result = _scan_symbol(item['symbol'])
        if result:
            result['earnings_date'] = item['earnings_date']
            result['days_until'] = item['days_until']
            candidates.append(result)

    candidates.sort(key=lambda x: x['iv_hv_ratio'], reverse=True)
    duration = round(time.time() - start, 1)

    output = {
        'scanned_at': datetime.now().isoformat(),
        'total_in_calendar': len(calendar),
        'total_scanned': len(calendar),
        'total_found': len(candidates),
        'scan_duration_s': duration,
        'candidates': candidates,
    }

    os.makedirs('data', exist_ok=True)
    with open(CACHE_FILE, 'w') as f:
        json.dump(output, f)

    return output


EARNINGS_SCANNER_TEMPLATE = '''<!DOCTYPE html>
<html><head>
<title>Earnings Scanner</title>
<style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { background: #0a0a0f; color: #e0e0e0; font-family: -apple-system, sans-serif; }
    .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
    .navbar { display: flex; gap: 15px; padding: 12px 0; border-bottom: 1px solid #222; margin-bottom: 20px; flex-wrap: wrap; }
    .navbar a { color: #888; text-decoration: none; font-size: 13px; }
    .navbar a:hover { color: #fff; }
    h1 { margin-bottom: 8px; }
    .subtitle { color: #888; margin-bottom: 20px; font-size: 13px; }

    .scheduler-bar {
        display: flex; justify-content: space-between; align-items: center;
        background: #0d0d1a; border: 1px solid #2a2a2a; border-radius: 6px;
        padding: 10px 16px; margin-bottom: 16px; font-size: 12px;
    }
    .scheduler-left { display: flex; gap: 20px; align-items: center; }
    .cron-active { color: #00c853; }
    .cron-inactive { color: #ffaa00; }
    .btn-log {
        background: none; border: 1px solid #444; color: #888;
        padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 11px;
    }
    .btn-log:hover { border-color: #888; color: #fff; }

    .filter-card { background: #111; border: 1px solid #222; border-radius: 8px; padding: 16px; margin-bottom: 20px; }
    .filter-row { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
    .filter-row button { padding: 8px 16px; background: #667eea; color: #fff; border: none; border-radius: 4px; cursor: pointer; }
    .filter-row button:hover { background: #5a6fd6; }
    .filter-row button.secondary { background: #333; }

    table { width: 100%; border-collapse: collapse; font-size: 12px; }
    th { text-align: left; padding: 10px 8px; border-bottom: 1px solid #333; color: #888; font-weight: 600; }
    td { padding: 10px 8px; border-bottom: 1px solid #1a1a1a; }
    tr:hover { background: #1a1a2e; }
    .sym-cell { font-weight: bold; color: #fff; font-size: 14px; }
    .tos-cell { font-family: monospace; font-size: 11px; color: #aaa; }
    .ratio-green { color: #00c853; font-weight: bold; }
    .ratio-yellow { color: #ffaa00; font-weight: bold; }
    .ratio-grey { color: #666; }
    .score-badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; }
    .score-high { background: #00c853; color: #000; }
    .score-med { background: #ffaa00; color: #000; }
    .btn-track { background: #333; border: 1px solid #555; color: #ccc; padding: 3px 8px; border-radius: 3px; cursor: pointer; font-size: 10px; }
    .btn-track:hover { background: #555; color: #fff; }

    .empty-state { text-align: center; padding: 60px 20px; color: #666; }
    .loading { text-align: center; padding: 40px; color: #888; }

    .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: 1000; align-items: center; justify-content: center; }
    .modal-overlay { position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); }
    .modal-content { position: relative; background: #111; border: 1px solid #333; border-radius: 8px; padding: 20px; width: 90%; max-width: 700px; }
    .modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
    .modal-close { background: none; border: none; color: #888; font-size: 20px; cursor: pointer; }
    .log-content {
        background: #0a0a0a; border-radius: 6px; padding: 12px;
        font-family: monospace; font-size: 11px; color: #00ff88;
        max-height: 400px; overflow-y: auto; white-space: pre-wrap;
    }
    .detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin: 16px 0; font-size: 13px; }
    .detail-grid .label { color: #666; }
    .detail-grid .value { color: #fff; font-weight: 600; }
    .tos-box { background: #0a0a0a; border: 1px solid #333; border-radius: 4px; padding: 10px; font-family: monospace; font-size: 14px; color: #00ff88; margin: 12px 0; text-align: center; }
</style>
</head><body>
<div class="container">
    <div class="navbar">
        <a href="/">Home</a>
        <a href="/tracked">Tracked Stocks</a>
        <a href="/watchlist">&#128065; Watchlist</a>
        <a href="/options-tracker">&#128202; Options</a>
        <a href="/earnings-scanner">&#128225; Earnings</a>
        <a href="/research">&#128300; Alpha Research</a>
        <a href="/journal/">&#128202; Trade Journal</a>
    </div>

    <h1>&#128225; Earnings Scanner</h1>
    <p class="subtitle">High-IV earnings plays — sorted by IV/HV ratio (the edge filter)</p>

    <!-- Scheduler Status Bar -->
    <div id="scheduler-bar" class="scheduler-bar" style="display:none;">
        <div class="scheduler-left">
            <span id="scheduler-cron-status"></span>
            <span id="scheduler-last-scan"></span>
        </div>
        <div class="scheduler-right">
            <button onclick="showScanLog()" class="btn-log">&#128203; View Log</button>
        </div>
    </div>

    <!-- Scan Log Modal -->
    <div id="log-modal" class="modal" style="display:none;">
        <div class="modal-overlay" onclick="closeLogModal()"></div>
        <div class="modal-content">
            <div class="modal-header">
                <h3>Earnings Scanner Log</h3>
                <button onclick="closeLogModal()" class="modal-close">&#10005;</button>
            </div>
            <div id="log-content" class="log-content">Loading...</div>
        </div>
    </div>

    <!-- Detail Modal -->
    <div id="detail-modal" class="modal" style="display:none;">
        <div class="modal-overlay" onclick="closeDetailModal()"></div>
        <div class="modal-content">
            <div class="modal-header">
                <h3 id="detail-title"></h3>
                <button onclick="closeDetailModal()" class="modal-close">&#10005;</button>
            </div>
            <div id="detail-body"></div>
        </div>
    </div>

    <div class="filter-card">
        <div class="filter-row">
            <button onclick="runScan(false)">Load Cached Results</button>
            <button onclick="runScan(true)" class="secondary">&#128260; Force Refresh</button>
            <span id="scan-status" style="font-size:12px; color:#888;"></span>
        </div>
    </div>

    <div id="results" class="empty-state">Click "Load Cached Results" or "Force Refresh" to scan.</div>
</div>

<script>
function fmtStrike(s) {
    if (s == null) return '?';
    return s == Math.floor(s) ? Math.floor(s).toString() : s.toString();
}

function tosString(c) {
    if (!c.put_strike || !c.call_strike || !c.exp_date) return '';
    const d = new Date(c.exp_date + 'T12:00:00');
    const months = ['JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC'];
    const expStr = d.getDate() + ' ' + months[d.getMonth()] + ' ' + String(d.getFullYear()).slice(2);
    return 'SELL -1 STRANGLE ' + c.symbol + ' 100 ' + expStr + ' ' + fmtStrike(c.put_strike) + '/' + fmtStrike(c.call_strike) + ' CALL/PUT @LMT';
}

function ratioClass(r) {
    if (r >= 2.0) return 'ratio-green';
    if (r >= 1.5) return 'ratio-yellow';
    return 'ratio-grey';
}

let _candidates = [];

async function runScan(force) {
    const el = document.getElementById('results');
    const status = document.getElementById('scan-status');
    el.innerHTML = '<div class="loading">Scanning... this may take a few minutes.</div>';
    status.textContent = 'Running...';

    try {
        const res = await fetch('/api/earnings-scanner/run', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({force_refresh: force})
        });
        const data = await res.json();
        status.textContent = `Scanned ${data.total_scanned} · Found ${data.total_found} · ${data.scan_duration_s}s`;
        _candidates = data.candidates || [];

        if (_candidates.length === 0) {
            el.innerHTML = '<div class="empty-state">No high-IV earnings candidates found.</div>';
            return;
        }

        let html = `<table>
            <thead><tr>
                <th>Symbol</th><th>Earnings</th><th>Price</th><th>IV</th>
                <th>HV30</th><th>IV/HV</th><th>IV Rank</th><th>TOS String</th>
                <th>Score</th><th></th>
            </tr></thead><tbody>`;

        for (let i = 0; i < _candidates.length; i++) {
            const c = _candidates[i];
            const scoreClass = c.score >= 5 ? 'score-high' : 'score-med';
            const rc = ratioClass(c.iv_hv_ratio);
            const tos = tosString(c);
            html += `<tr onclick="showDetail(${i})" style="cursor:pointer;">
                <td class="sym-cell">${c.symbol}</td>
                <td>${c.earnings_date} (${c.days_until}d)</td>
                <td>$${c.price}</td>
                <td>${c.iv_current}%</td>
                <td>${c.hv_30}%</td>
                <td class="${rc}">${c.iv_hv_ratio}x</td>
                <td>${c.iv_rank}%</td>
                <td class="tos-cell">${tos}</td>
                <td><span class="score-badge ${scoreClass}">${c.score}</span></td>
                <td><button class="btn-track" onclick="event.stopPropagation(); copyTos(${i})">&#128203; Copy</button></td>
            </tr>`;
        }
        html += '</tbody></table>';
        el.innerHTML = html;
    } catch(e) {
        el.innerHTML = `<div class="empty-state">Error: ${e.message}</div>`;
        status.textContent = 'Error';
    }
}

function showDetail(idx) {
    const c = _candidates[idx];
    const tos = tosString(c);
    document.getElementById('detail-title').textContent = c.symbol + ' — Earnings ' + c.earnings_date;
    document.getElementById('detail-body').innerHTML = `
        <div class="detail-grid">
            <div><span class="label">Price:</span> <span class="value">$${c.price}</span></div>
            <div><span class="label">IV Current:</span> <span class="value">${c.iv_current}%</span></div>
            <div><span class="label">HV 30d:</span> <span class="value">${c.hv_30}%</span></div>
            <div><span class="label">HV 1y:</span> <span class="value">${c.hv}%</span></div>
            <div><span class="label">IV/HV Ratio:</span> <span class="value ${ratioClass(c.iv_hv_ratio)}">${c.iv_hv_ratio}x</span></div>
            <div><span class="label">IV Rank:</span> <span class="value">${c.iv_rank}%</span></div>
            <div><span class="label">Put Strike:</span> <span class="value">${fmtStrike(c.put_strike)}</span></div>
            <div><span class="label">Call Strike:</span> <span class="value">${fmtStrike(c.call_strike)}</span></div>
            <div><span class="label">Expiration:</span> <span class="value">${c.exp_date || '?'}</span></div>
            <div><span class="label">Score:</span> <span class="value">${c.score}</span></div>
        </div>
        <div class="tos-box">${tos || 'No strikes available'}</div>
        <div style="text-align:center;">
            <button class="btn-track" onclick="copyTos(${idx})" style="padding:8px 16px; font-size:12px;">&#128203; Copy TOS String</button>
        </div>
    `;
    document.getElementById('detail-modal').style.display = 'flex';
}

function closeDetailModal() {
    document.getElementById('detail-modal').style.display = 'none';
}

function copyTos(idx) {
    const c = _candidates[idx];
    const tos = tosString(c);
    if (!tos) return;
    const ta = document.createElement('textarea');
    ta.value = tos;
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
    const btn = event.target;
    const orig = btn.textContent;
    btn.textContent = '\u2713 Copied!';
    btn.style.color = '#00c853';
    setTimeout(() => { btn.textContent = orig; btn.style.color = ''; }, 1500);
}

// ── Scheduler Status ──────────────────────────────────────────────────────────
async function loadSchedulerStatus() {
    try {
        const res = await fetch('/api/earnings-scanner/status');
        const data = await res.json();

        const bar = document.getElementById('scheduler-bar');
        bar.style.display = 'flex';

        const cronEl = document.getElementById('scheduler-cron-status');
        if (data.cron_installed) {
            cronEl.innerHTML = '<span class="cron-active">&#9679; Scheduler active</span> · ' + data.schedule;
        } else {
            cronEl.innerHTML = '<span class="cron-inactive">&#9679; Scheduler not installed</span> · Run: <code>bash scripts/setup_cron.sh</code>';
        }

        const lastEl = document.getElementById('scheduler-last-scan');
        if (data.cache && data.cache.exists) {
            const scannedAt = new Date(data.cache.last_scanned).toLocaleString();
            lastEl.textContent = 'Last scan: ' + scannedAt + ' · ' + data.cache.total_found + ' candidates found';
        } else {
            lastEl.textContent = 'No scan results yet';
        }
    } catch(e) {
        console.log('Scheduler status error:', e);
    }
}

async function showScanLog() {
    document.getElementById('log-modal').style.display = 'flex';
    document.getElementById('log-content').textContent = 'Loading...';

    try {
        const res = await fetch('/api/earnings-scanner/log');
        const data = await res.json();

        if (data.lines && data.lines.length > 0) {
            document.getElementById('log-content').textContent = data.lines.join('\\n');
        } else {
            document.getElementById('log-content').textContent =
                data.message || 'No log entries yet.\\n\\nRun: bash scripts/setup_cron.sh';
        }
    } catch(e) {
        document.getElementById('log-content').textContent = 'Error: ' + e.message;
    }
}

function closeLogModal() {
    document.getElementById('log-modal').style.display = 'none';
}

loadSchedulerStatus();
</script>
</body></html>'''


def add_earnings_scanner_routes(app):
    """Register earnings scanner routes on the Flask app."""

    @app.route('/earnings-scanner')
    def earnings_scanner_page():
        return render_template_string(EARNINGS_SCANNER_TEMPLATE)

    @app.route('/api/earnings-scanner/run', methods=['POST'])
    def api_earnings_scanner_run():
        data = request.get_json(silent=True) or {}
        force = data.get('force_refresh', False)
        result = _run_scan(force_refresh=force)
        return jsonify(result)

    @app.route('/api/earnings-scanner/status')
    def api_earnings_scanner_status():
        """Return scheduler status and last scan info."""
        try:
            log_file = os.path.expanduser('~/logs/earnings_scan.log')

            cache_info = {"exists": False, "age_hours": None, "last_scanned": None}
            if os.path.exists(CACHE_FILE):
                with open(CACHE_FILE, 'r') as f:
                    cached = json.load(f)
                last_scanned = cached.get('scanned_at')
                if last_scanned:
                    age = (datetime.now() - datetime.fromisoformat(last_scanned)).total_seconds() / 3600
                    cache_info = {
                        "exists": True,
                        "age_hours": round(age, 1),
                        "last_scanned": last_scanned,
                        "total_found": cached.get('total_found', 0),
                    }

            cron_installed = False
            try:
                result = os.popen('crontab -l 2>/dev/null').read()
                cron_installed = 'earnings-scanner' in result
            except Exception:
                pass

            log_tail = []
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                log_tail = [l.strip() for l in lines[-10:] if l.strip()]

            return jsonify({
                "cache": cache_info,
                "cron_installed": cron_installed,
                "schedule": "Weekdays at 7:00 PM",
                "log_tail": log_tail,
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/api/earnings-scanner/log')
    def api_earnings_scanner_log():
        """Return last 50 lines of the earnings scan log."""
        try:
            log_file = os.path.expanduser('~/logs/earnings_scan.log')
            if not os.path.exists(log_file):
                return jsonify({"lines": [], "message": "Log file not found — run setup_cron.sh first"})
            with open(log_file, 'r') as f:
                lines = f.readlines()
            return jsonify({
                "lines": [l.strip() for l in lines[-50:] if l.strip()],
                "log_file": log_file,
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500
