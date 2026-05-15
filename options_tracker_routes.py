"""
Options Tracker Routes — Parse TOS strings, track positions, view P&L.
"""

import json
import os
from datetime import datetime, date
from flask import jsonify, request, render_template_string
from options_parser import parse_multiple_tos_strings
import yfinance as yf

POSITIONS_FILE = 'data/options_positions.json'


def _load_positions():
    if os.path.exists(POSITIONS_FILE):
        with open(POSITIONS_FILE, 'r') as f:
            return json.load(f)
    return []


def _save_positions(positions):
    os.makedirs('data', exist_ok=True)
    with open(POSITIONS_FILE, 'w') as f:
        json.dump(positions, f, indent=2)


def _add_position(legs, name=None):
    positions = _load_positions()
    pos_id = max([p['id'] for p in positions], default=0) + 1
    position = {
        "id": pos_id,
        "name": name or f"{legs[0]['symbol']} {legs[0]['strategy']}",
        "legs": legs,
        "opened_at": datetime.now().isoformat(),
        "status": "open"
    }
    positions.append(position)
    _save_positions(positions)
    return position


def _enrich_position(pos):
    """Add live prices, P&L, margin, status to a position."""
    legs = pos.get('legs', [])
    if not legs:
        return pos

    symbol = legs[0].get('symbol', '')
    now = datetime.now()

    # Fetch stock price
    stock_price = None
    try:
        t = yf.Ticker(symbol)
        info = t.fast_info
        stock_price = float(info.get('lastPrice', 0) or info.get('last_price', 0))
        if stock_price == 0:
            hist = t.history(period='1d')
            if not hist.empty:
                stock_price = float(hist['Close'].iloc[-1])
    except Exception:
        pass

    # Fetch option prices for each leg
    enriched_legs = []
    total_pnl = 0.0
    cost_to_close = 0.0
    data_stale = False
    total_entry_credit = 0.0
    total_entry_debit = 0.0
    short_put_strike = None
    short_call_strike = None

    for leg in legs:
        eleg = dict(leg)
        exp = leg.get('expiration', '')
        strike = leg.get('strike', 0)
        opt_type = leg.get('option_type', 'CALL')
        action = leg.get('action', 'SELL')
        entry_premium = leg.get('entry_premium', 0) or 0

        # Track entry economics
        if action == 'SELL':
            total_entry_credit += entry_premium
            if opt_type == 'PUT':
                short_put_strike = strike
            elif opt_type == 'CALL':
                short_call_strike = strike
        else:
            total_entry_debit += entry_premium

        # DTE
        try:
            exp_date = datetime.strptime(exp, '%Y-%m-%d').date()
            dte = (exp_date - date.today()).days
        except Exception:
            dte = 0
        eleg['dte'] = max(dte, 0)

        # Fetch current option price
        current_price = None
        bid = 0.0
        ask = 0.0
        price_source = 'mid'
        price_stale = False

        try:
            t = yf.Ticker(symbol)
            chain = t.option_chain(exp)
            df = chain.puts if opt_type == 'PUT' else chain.calls
            row = df[df['strike'] == strike]
            if not row.empty:
                bid = float(row['bid'].iloc[0])
                ask = float(row['ask'].iloc[0])
                if bid > 0 and ask > 0:
                    current_price = round((bid + ask) / 2, 2)
                    price_source = 'mid'
                elif row['lastPrice'].iloc[0] > 0:
                    current_price = float(row['lastPrice'].iloc[0])
                    price_source = 'last'
                    price_stale = True
                    data_stale = True
        except Exception:
            pass

        eleg['current_price'] = current_price
        eleg['bid'] = bid
        eleg['ask'] = ask
        eleg['price_source'] = price_source
        eleg['price_stale'] = price_stale

        # P&L per leg
        if current_price is not None:
            if action == 'SELL':
                leg_pnl = round((entry_premium - current_price) * 100, 2)
            else:
                leg_pnl = round((current_price - entry_premium) * 100, 2)
            eleg['pnl'] = leg_pnl
            total_pnl += leg_pnl
            cost_to_close += current_price
        else:
            eleg['pnl'] = None

        enriched_legs.append(eleg)

    # Net entry
    net_entry_credit = total_entry_credit - total_entry_debit

    # Total P&L percentage
    total_pnl_pct = None
    if net_entry_credit > 0 and total_pnl is not None:
        total_pnl_pct = round((total_pnl / (net_entry_credit * 100)) * 100, 1)

    # Status determination
    status = 'UNKNOWN'
    alert = None
    if stock_price and short_put_strike and short_call_strike:
        if short_put_strike < stock_price < short_call_strike:
            status = 'ON_TRACK'
        elif stock_price <= short_put_strike * 1.02 or stock_price >= short_call_strike * 0.98:
            status = 'WARNING'
            alert = f'{symbol} at ${stock_price:.2f} is near a short strike'
        elif stock_price <= short_put_strike or stock_price >= short_call_strike:
            status = 'DANGER'
            alert = f'{symbol} at ${stock_price:.2f} has breached a short strike!'

    # Margin calculation (approximate Reg T for naked strangles)
    margin_required = None
    capital_at_risk = None
    return_on_collateral = None
    margin_breakdown = []

    if stock_price and (short_put_strike or short_call_strike):
        put_margin = 0
        call_margin = 0
        if short_put_strike:
            # 20% of underlying + premium - OTM amount
            otm = max(0, stock_price - short_put_strike)
            put_margin = round(stock_price * 0.20 * 100 + total_entry_credit * 100 - otm * 100)
            margin_breakdown.append({'leg': f'PUT {short_put_strike}', 'type': 'naked put', 'amount': put_margin})
        if short_call_strike:
            otm = max(0, short_call_strike - stock_price)
            call_margin = round(stock_price * 0.20 * 100 + total_entry_credit * 100 - otm * 100)
            margin_breakdown.append({'leg': f'CALL {short_call_strike}', 'type': 'naked call', 'amount': call_margin})

        margin_required = max(put_margin, call_margin)  # Reg T uses greater of the two
        capital_at_risk = round(margin_required - net_entry_credit * 100)
        if capital_at_risk > 0 and net_entry_credit > 0:
            return_on_collateral = round((net_entry_credit * 100 / capital_at_risk) * 100, 1)

    # Build enriched position
    enriched = {
        'id': pos.get('id'),
        'name': pos.get('name', ''),
        'symbol': symbol,
        'legs': enriched_legs,
        'stock_price': stock_price,
        'status': status,
        'alert': alert,
        'data_stale': data_stale,
        'date_entered': pos.get('opened_at', '')[:10],
        'total_entry_credit': total_entry_credit,
        'total_entry_debit': total_entry_debit,
        'net_entry_credit': net_entry_credit,
        'total_pnl': round(total_pnl, 2) if total_pnl != 0 or any(l['pnl'] is not None for l in enriched_legs) else None,
        'total_pnl_pct': total_pnl_pct,
        'cost_to_close': round(cost_to_close, 2) if cost_to_close > 0 else None,
        'short_put_strike': short_put_strike,
        'short_call_strike': short_call_strike,
        'margin_required': margin_required,
        'capital_at_risk': capital_at_risk,
        'return_on_collateral': return_on_collateral,
        'margin_breakdown': margin_breakdown,
        'margin_note': 'Approximate Reg T margin. Actual broker requirement will vary.',
        'last_updated': now.isoformat(),
    }
    return enriched


OPTIONS_TRACKER_TEMPLATE = '''<!DOCTYPE html>
<html><head>
<title>Options Tracker</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: #0a0a0f; color: #e0e0e0; font-family: -apple-system, sans-serif; }
.container { max-width: 1200px; margin: 0 auto; padding: 20px; }
.navbar { display: flex; gap: 15px; padding: 12px 0; border-bottom: 1px solid #222; margin-bottom: 20px; flex-wrap: wrap; }
.navbar a { color: #888; text-decoration: none; font-size: 13px; }
.navbar a:hover { color: #fff; }
h1 { margin-bottom: 8px; }
.page-subtitle { color: #888; margin-bottom: 20px; font-size: 13px; }
.input-group { margin-bottom: 16px; }
.input-group label { display: block; font-size: 11px; color: #888; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; }
.text-input { width: 100%; padding: 10px 12px; background: #111; border: 1px solid #333; border-radius: 6px; color: #fff; font-size: 14px; }
.tos-textarea { width: 100%; padding: 10px 12px; background: #111; border: 1px solid #333; border-radius: 6px; color: #00ff88; font-family: monospace; font-size: 13px; resize: vertical; min-height: 80px; }
.tos-textarea:focus, .text-input:focus { outline: none; border-color: #555; }
.button-row { display: flex; align-items: center; gap: 16px; }
.btn-primary { padding: 10px 24px; background: #2a6aff; color: #fff; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; font-weight: 600; }
.btn-primary:hover { background: #1a5aef; }
.btn-danger { padding: 6px 14px; background: transparent; color: #ff4444; border: 1px solid #ff4444; border-radius: 6px; cursor: pointer; font-size: 12px; }
.btn-danger:hover { background: rgba(255,68,68,0.1); }
.refresh-btn { background: none; border: 1px solid #444; color: #888; padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 11px; }
.refresh-btn:hover { border-color: #888; color: #fff; }
.parse-status { font-size: 13px; }
.parse-status.success { color: #00c853; }
.parse-status.error { color: #ff4444; }
.card { background: #111; border: 1px solid #222; border-radius: 8px; padding: 20px; margin-bottom: 20px; }
.position-card { background: #1a1a2e; border: 1px solid #333; border-radius: 8px; padding: 20px; margin-bottom: 20px; }
.position-card-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; }
.position-title { font-size: 16px; font-weight: 600; }
.position-meta { font-size: 12px; color: #888; margin-top: 3px; }
.position-header-right { display: flex; align-items: center; gap: 12px; }
.status-badge { padding: 3px 10px; border-radius: 10px; font-size: 11px; font-weight: 600; text-transform: uppercase; }
.status-on_track { background: rgba(0,200,83,0.15); color: #00c853; }
.status-warning { background: rgba(255,170,0,0.15); color: #ffaa00; }
.status-danger { background: rgba(255,68,68,0.15); color: #ff4444; }
.status-unknown { background: rgba(128,128,128,0.15); color: #888; }
.alert-banner { padding: 8px 12px; border-radius: 6px; margin-bottom: 12px; font-size: 12px; font-weight: 600; }
.alert-warning { background: rgba(255,170,0,0.1); border: 1px solid #ffaa00; color: #ffaa00; }
.alert-danger { background: rgba(255,68,68,0.1); border: 1px solid #ff4444; color: #ff4444; }
.stale-warning { background: rgba(255,170,0,0.08); border: 1px solid rgba(255,170,0,0.3); border-radius: 6px; padding: 8px 12px; font-size: 12px; color: #ffaa00; margin-bottom: 12px; }
.economics-section { background: #0d0d1a; border: 1px solid #2a2a2a; border-radius: 6px; padding: 14px 16px; margin-bottom: 16px; }
.econ-row { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.econ-item { flex: 1; min-width: 100px; text-align: center; }
.econ-item.highlight { background: rgba(255,255,255,0.03); border: 1px solid #333; border-radius: 6px; padding: 8px; }
.econ-label { font-size: 10px; color: #888; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }
.econ-value { font-size: 18px; font-weight: 700; }
.econ-value.green { color: #00c853; }
.econ-value.red { color: #ff4444; }
.econ-sub { font-size: 10px; color: #666; margin-top: 2px; }
.econ-divider { font-size: 20px; color: #555; flex: 0; padding: 0 4px; }
.metrics-row { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
.metric-box { flex: 1; min-width: 90px; background: #111; border: 1px solid #2a2a2a; border-radius: 6px; padding: 10px 12px; text-align: center; }
.metric-label { font-size: 10px; color: #888; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }
.metric-value { font-size: 18px; font-weight: 600; color: #fff; }
.metric-value.green { color: #00c853; }
.metric-value.red { color: #ff4444; }
.metric-value.neutral { color: #888; }
.zone-bar-wrap { margin: 12px 0 16px; }
.zone-labels { display: flex; justify-content: space-between; font-size: 10px; color: #888; margin-bottom: 4px; }
.zone-bar { position: relative; height: 20px; border-radius: 4px; overflow: visible; background: rgba(255,68,68,0.2); }
.zone-profit { position: absolute; top: 0; height: 100%; background: rgba(0,200,83,0.25); border-radius: 2px; }
.price-pin { position: absolute; top: -6px; font-size: 14px; color: #fff; transform: translateX(-50%); pointer-events: none; z-index: 10; }
.legs-table { width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 4px; }
.legs-table th { text-align: left; padding: 6px 8px; border-bottom: 1px solid #333; color: #888; font-size: 10px; text-transform: uppercase; }
.legs-table td { padding: 8px; border-bottom: 1px solid #1a1a1a; }
.legs-table .green { color: #00c853; }
.legs-table .red { color: #ff4444; }
.legs-table .buy { color: #00c853; font-weight: 600; }
.legs-table .sell { color: #ff4444; font-weight: 600; }
.price-source { font-size: 9px; padding: 1px 4px; border-radius: 3px; margin-left: 4px; }
.price-source.live { background: rgba(0,200,83,0.15); color: #00c853; }
.price-source.stale { background: rgba(255,170,0,0.15); color: #ffaa00; }
.bid-ask { font-size: 10px; color: #666; margin-top: 2px; }
.tos-section { background: #0d0d1a; border: 1px solid #2a2a2a; border-radius: 6px; padding: 12px 14px; margin-top: 12px; }
.tos-section-header { font-size: 11px; font-weight: 600; color: #888; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }
.tos-string { background: #0a0a0a; border: 1px solid #333; border-radius: 4px; padding: 8px 10px; font-family: monospace; font-size: 12px; color: #00ff88; margin: 4px 0; cursor: pointer; }
.tos-string:hover { border-color: #555; }
.tos-copy-hint { font-size: 10px; color: #555; margin-top: 6px; }
.collateral-section { background: #0d0d1a; border: 1px solid #2a2a2a; border-radius: 6px; padding: 14px 16px; margin-top: 12px; }
.collateral-header { font-size: 11px; font-weight: 600; color: #888; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 10px; }
.collateral-row { display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 10px; }
.collateral-item { flex: 1; min-width: 100px; text-align: center; }
.collateral-value { font-size: 20px; font-weight: 700; margin: 4px 0 2px; }
.collateral-value.orange { color: #ffaa00; }
.collateral-value.red { color: #ff4444; }
.collateral-value.green { color: #00c853; }
.margin-breakdown { margin-top: 8px; }
.margin-line { display: flex; justify-content: space-between; font-size: 11px; color: #888; padding: 3px 0; border-bottom: 1px solid #1a1a1a; }
.margin-note { font-size: 10px; color: #555; font-style: italic; margin-top: 8px; }
.card-footer { display: flex; justify-content: space-between; align-items: center; margin-top: 12px; font-size: 11px; color: #888; }
.loading-msg { color: #888; padding: 20px; text-align: center; }
.empty-msg { color: #888; padding: 40px; text-align: center; font-size: 14px; }
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

    <h1>&#128202; Options Tracker</h1>
    <p class="page-subtitle">Paste TOS order strings to track live P&amp;L</p>

    <div class="card">
        <div class="input-group">
            <label for="position-name">Position Name (optional)</label>
            <input type="text" id="position-name" placeholder="e.g. GOOG Diagonal May 2026" class="text-input" />
        </div>
        <div class="input-group">
            <label for="tos-input">Paste TOS Order Strings (one per line)</label>
            <textarea id="tos-input" rows="4" class="tos-textarea" placeholder="SELL -1 STRANGLE AMAT 100 20 JUN 26 360/490 PUT/CALL @12.50 LMT"></textarea>
        </div>
        <div class="button-row">
            <button onclick="addPosition()" class="btn-primary">Parse &amp; Track</button>
            <span id="parse-status" class="parse-status"></span>
        </div>
    </div>

    <div id="positions-container"><div class="loading-msg">Loading positions...</div></div>
</div>
<script>
async function addPosition() {
  const tos = document.getElementById('tos-input').value.trim();
  const name = document.getElementById('position-name').value.trim();
  const statusEl = document.getElementById('parse-status');
  if (!tos) { statusEl.textContent = 'Paste TOS strings first.'; statusEl.className = 'parse-status error'; return; }
  statusEl.textContent = 'Parsing...'; statusEl.className = 'parse-status';
  try {
    const res = await fetch('/api/options-tracker/add', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({tos_strings: tos, name: name || null}) });
    const data = await res.json();
    if (data.error) { statusEl.textContent = data.error; statusEl.className = 'parse-status error'; return; }
    statusEl.textContent = '\u2713 Position added: ' + data.position.name; statusEl.className = 'parse-status success';
    document.getElementById('tos-input').value = ''; document.getElementById('position-name').value = '';
    loadPositions();
  } catch(e) { statusEl.textContent = 'Error: ' + e.message; statusEl.className = 'parse-status error'; }
}

async function deletePosition(id) {
  if (!confirm('Remove this position?')) return;
  await fetch('/api/options-tracker/delete/' + id, { method: 'DELETE' });
  loadPositions();
}

async function loadPositions() {
  const container = document.getElementById('positions-container');
  container.innerHTML = '<div class="loading-msg">Fetching live prices...</div>';
  try {
    const res = await fetch('/api/options-tracker/positions');
    const data = await res.json();
    if (!data.positions || data.positions.length === 0) {
      container.innerHTML = '<div class="empty-msg">No active positions. Paste a TOS string above to start tracking.</div>';
      return;
    }
    container.innerHTML = data.positions.map(renderPositionCard).join('');
  } catch(e) { container.innerHTML = '<div class="loading-msg">Error: ' + e.message + '</div>'; }
}

function renderPositionCard(p) {
  const priceText = p.stock_price ? '$' + p.stock_price.toFixed(2) : '\u2014';
  const statusClass = 'status-' + (p.status || 'unknown').toLowerCase();
  const statusLabel = (p.status || 'UNKNOWN').replace('_', ' ');

  const alertHtml = p.alert ? '<div class="alert-banner alert-' + (p.status||'').toLowerCase() + '">' + p.alert + '</div>' : '';
  const staleHtml = p.data_stale ? '<div class="stale-warning">\u26a0\ufe0f Some prices use last-trade data. P&L may be inaccurate.</div>' : '';

  // Trade Economics
  const creditText = p.total_entry_credit ? '+$' + p.total_entry_credit.toFixed(2) : '+$0.00';
  const debitText = p.total_entry_debit ? '-$' + p.total_entry_debit.toFixed(2) : '$0.00';
  const netVal = p.net_entry_credit || 0;
  const netText = (netVal >= 0 ? '+' : '') + '$' + netVal.toFixed(2);
  const netClass = netVal >= 0 ? 'green' : 'red';
  const netLabel = netVal >= 0 ? 'Net Credit' : 'Net Debit';

  const economicsHtml = '<div class="economics-section"><div class="econ-row">' +
    '<div class="econ-item"><div class="econ-label">Premium Collected</div><div class="econ-value green">' + creditText + '</div><div class="econ-sub">from short legs</div></div>' +
    '<div class="econ-divider">\u2212</div>' +
    '<div class="econ-item"><div class="econ-label">Premium Paid</div><div class="econ-value red">' + debitText + '</div><div class="econ-sub">for long legs</div></div>' +
    '<div class="econ-divider">=</div>' +
    '<div class="econ-item highlight"><div class="econ-label">' + netLabel + '</div><div class="econ-value ' + netClass + '">' + netText + '</div><div class="econ-sub">cash ' + (netVal >= 0 ? 'received' : 'paid') + ' at entry</div></div>' +
    '</div></div>';

  // Metrics
  const pnlVal = p.total_pnl;
  const pnlClass = pnlVal === null ? 'neutral' : pnlVal >= 0 ? 'green' : 'red';
  const pnlText = pnlVal === null ? 'N/A' : (pnlVal >= 0 ? '+' : '') + '$' + pnlVal.toFixed(2);
  const pnlPct = p.total_pnl_pct != null ? ' (' + (p.total_pnl_pct >= 0 ? '+' : '') + p.total_pnl_pct.toFixed(1) + '%)' : '';
  const closeText = p.cost_to_close != null ? '$' + p.cost_to_close.toFixed(2) : '\u2014';

  let dteCells = '';
  (p.legs || []).forEach(function(l) {
    const dteClass = l.dte <= 7 ? 'red' : l.dte <= 21 ? 'neutral' : '';
    dteCells += '<div class="metric-box"><div class="metric-label">' + l.option_type + ' ' + l.strike + ' DTE</div><div class="metric-value ' + dteClass + '">' + l.dte + 'd</div></div>';
  });

  const metricsHtml = '<div class="metrics-row">' +
    '<div class="metric-box"><div class="metric-label">' + (p.symbol||'') + ' Price</div><div class="metric-value">' + priceText + '</div></div>' +
    '<div class="metric-box"><div class="metric-label">Cost to Close</div><div class="metric-value">' + closeText + '</div></div>' +
    '<div class="metric-box"><div class="metric-label">Net P&L</div><div class="metric-value ' + pnlClass + '">' + pnlText + pnlPct + '</div></div>' +
    dteCells + '</div>';

  // Zone Bar
  const zoneHtml = renderZoneBar(p);

  // Legs Table
  let legsRows = '';
  (p.legs || []).forEach(function(leg) {
    const pnl = leg.pnl === null ? '\u2014' : (leg.pnl >= 0 ? '+' : '') + '$' + leg.pnl.toFixed(2);
    const pnlCls = leg.pnl === null ? '' : leg.pnl >= 0 ? 'green' : 'red';
    const actCls = leg.action === 'BUY' ? 'buy' : 'sell';
    const curPrice = leg.current_price ? '$' + leg.current_price.toFixed(2) + '<span class="price-source ' + (leg.price_stale ? 'stale' : 'live') + '">' + (leg.price_source === 'mid' ? 'mid' : '\u26a0last') + '</span>' : '\u2014';
    const bidAsk = (leg.bid > 0 && leg.ask > 0) ? '<div class="bid-ask">Bid $' + leg.bid.toFixed(2) + ' / Ask $' + leg.ask.toFixed(2) + '</div>' : '';
    legsRows += '<tr><td class="' + actCls + '">' + leg.action + '</td><td>' + leg.symbol + '</td><td>$' + leg.strike + '</td><td>' + leg.option_type + '</td><td>' + leg.expiration + ' <span style="color:#888">(' + leg.dte + 'd)</span></td><td>$' + (leg.entry_premium||0).toFixed(2) + '</td><td>' + curPrice + bidAsk + '</td><td class="' + pnlCls + '">' + pnl + '</td></tr>';
  });
  const legsHtml = '<table class="legs-table"><thead><tr><th>Action</th><th>Symbol</th><th>Strike</th><th>Type</th><th>Expiry (DTE)</th><th>Entry</th><th>Current</th><th>P&L</th></tr></thead><tbody>' + legsRows + '</tbody></table>';

  // TOS Strings
  const tosStrings = buildTOSStrings(p);
  let tosHtml = '';
  if (tosStrings.length > 0) {
    let tosRows = '';
    tosStrings.forEach(function(s, i) { tosRows += '<div class="tos-string" data-tos="' + s.replace(/"/g, '&quot;') + '" onclick="copyTOS(this)">' + s + '</div>'; });
    tosHtml = '<div class="tos-section"><div class="tos-section-header">TOS Order Strings \u2014 Click to Copy</div>' + tosRows + '<div class="tos-copy-hint">Click to copy \u2192 TOS: Trade tab \u2192 Order Entry Tools \u2192 Paste from Clipboard</div></div>';
  }

  // Capital Requirements
  const marginText = p.margin_required != null ? '$' + p.margin_required.toLocaleString('en-US',{maximumFractionDigits:0}) : 'N/A';
  const capitalText = p.capital_at_risk != null ? '$' + p.capital_at_risk.toLocaleString('en-US',{maximumFractionDigits:0}) : 'N/A';
  const rocText = p.return_on_collateral != null ? p.return_on_collateral + '%' : 'N/A';
  let breakdownRows = '';
  (p.margin_breakdown || []).forEach(function(b) { breakdownRows += '<div class="margin-line"><span>' + b.leg + ' (' + b.type + ')</span><span>$' + (b.amount||0).toLocaleString('en-US',{maximumFractionDigits:0}) + '</span></div>'; });

  const collateralHtml = '<div class="collateral-section"><div class="collateral-header">Capital Requirements</div>' +
    '<div class="collateral-row">' +
    '<div class="collateral-item"><div class="econ-label">Margin Hold</div><div class="collateral-value orange">' + marginText + '</div><div class="econ-sub">broker collateral</div></div>' +
    '<div class="collateral-item"><div class="econ-label">Capital at Risk</div><div class="collateral-value red">' + capitalText + '</div><div class="econ-sub">margin minus credit</div></div>' +
    '<div class="collateral-item"><div class="econ-label">Return on Collateral</div><div class="collateral-value green">' + rocText + '</div><div class="econ-sub">if max profit</div></div>' +
    '</div><div class="margin-breakdown">' + breakdownRows + '</div>' +
    '<div class="margin-note">' + (p.margin_note || 'Approximate Reg T margin. Actual broker requirement will vary.') + '</div></div>';

  const updatedTime = p.last_updated ? new Date(p.last_updated).toLocaleTimeString() : '\u2014';

  return '<div class="position-card" id="pos-' + p.id + '">' +
    '<div class="position-card-header"><div><div class="position-title">' + p.name + '</div><div class="position-meta">Entered ' + (p.date_entered||'') + ' \u00b7 ' + (p.symbol||'') + ' @ ' + priceText + '</div></div>' +
    '<div class="position-header-right"><span class="status-badge ' + statusClass + '">' + statusLabel + '</span><button class="btn-danger" onclick="deletePosition(' + p.id + ')">Remove</button></div></div>' +
    alertHtml + staleHtml + economicsHtml + metricsHtml + zoneHtml + legsHtml + tosHtml + collateralHtml +
    '<div class="card-footer"><span>Last updated: ' + updatedTime + '</span><button class="refresh-btn" onclick="loadPositions()">\u21bb Refresh</button></div></div>';
}

function renderZoneBar(p) {
  const stockPrice = p.stock_price, putStrike = p.short_put_strike, callStrike = p.short_call_strike;
  if (!putStrike || !callStrike || !stockPrice) return '';
  const barMin = putStrike * 0.85, barMax = callStrike * 1.15, barRange = barMax - barMin;
  const putPct = ((putStrike - barMin) / barRange * 100).toFixed(1);
  const callPct = ((callStrike - barMin) / barRange * 100).toFixed(1);
  const pricePct = Math.min(Math.max(((stockPrice - barMin) / barRange * 100), 0), 100).toFixed(1);
  const profitWidth = (callPct - putPct).toFixed(1);
  return '<div class="zone-bar-wrap"><div class="zone-labels"><span>$' + (putStrike*0.85).toFixed(0) + '</span><span>PUT $' + putStrike + '</span><span>MAX PROFIT ZONE</span><span>CALL $' + callStrike + '</span><span>$' + (callStrike*1.15).toFixed(0) + '</span></div>' +
    '<div class="zone-bar"><div class="zone-profit" style="left:' + putPct + '%; width:' + profitWidth + '%"></div><div class="price-pin" style="left:' + pricePct + '%">\u25bc</div></div></div>';
}

function buildTOSStrings(p) {
  const strings = [], legs = p.legs || [];
  const shortLegs = legs.filter(function(l){return l.action==='SELL';});
  const longLegs = legs.filter(function(l){return l.action==='BUY';});
  const expGroups = {};
  shortLegs.forEach(function(l) { if (!expGroups[l.expiration]) expGroups[l.expiration]=[]; expGroups[l.expiration].push(l); });
  Object.keys(expGroups).forEach(function(exp) {
    const expLegs = expGroups[exp];
    const puts = expLegs.filter(function(l){return l.option_type==='PUT';});
    const calls = expLegs.filter(function(l){return l.option_type==='CALL';});
    if (puts.length > 0 && calls.length > 0) {
      const ps = formatStrike(puts[0].strike), cs = formatStrike(calls[0].strike);
      const expTOS = formatExpTOS(exp);
      const credit = ((puts[0].entry_premium||0) + (calls[0].entry_premium||0)).toFixed(2);
      const creditStr = parseFloat(credit) > 0 ? '@' + credit : '@LMT';
      strings.push('SELL -1 STRANGLE ' + p.symbol + ' 100 ' + expTOS + ' ' + ps + '/' + cs + ' PUT/CALL ' + creditStr + ' LMT');
    }
  });
  longLegs.forEach(function(l) {
    const expTOS = formatExpTOS(l.expiration), strike = formatStrike(l.strike);
    const premium = l.entry_premium > 0 ? '@' + l.entry_premium.toFixed(2) : '@LMT';
    strings.push('BUY +1 ' + p.symbol + ' 100 ' + expTOS + ' ' + strike + ' ' + l.option_type + ' ' + premium + ' LMT');
  });
  return strings;
}

function formatStrike(s) { return s % 1 === 0 ? Math.round(s).toString() : s.toString(); }
function formatExpTOS(dateStr) {
  const months = ['JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC'];
  const d = new Date(dateStr + 'T12:00:00');
  return d.getDate() + ' ' + months[d.getMonth()] + ' ' + String(d.getFullYear()).slice(2);
}

function copyTOS(el) {
  const text = el.getAttribute('data-tos') || el.textContent.trim();
  const ta = document.createElement('textarea');
  ta.value = text; ta.style.position = 'fixed'; ta.style.opacity = '0';
  document.body.appendChild(ta); ta.select(); document.execCommand('copy');
  document.body.removeChild(ta);
  const orig = el.textContent.trim(); el.textContent = '\u2713 Copied!'; el.style.color = '#00c853';
  setTimeout(function() { el.textContent = orig; el.style.color = ''; }, 1500);
}

loadPositions();
setInterval(loadPositions, 15 * 60 * 1000);
</script>
</body></html>
'''


def add_options_tracker_routes(app):
    """Register options tracker routes on the Flask app."""

    @app.route('/options-tracker')
    def options_tracker_page():
        return render_template_string(OPTIONS_TRACKER_TEMPLATE)

    @app.route('/api/options-tracker/add', methods=['POST'])
    def api_add_position():
        try:
            data = request.get_json()
            raw_block = data.get('tos_strings', '')
            position_name = data.get('name', None)

            if not raw_block.strip():
                return jsonify({"error": "No TOS strings provided"}), 400

            legs = parse_multiple_tos_strings(raw_block)

            if not legs:
                preview = raw_block[:200] + ('...' if len(raw_block) > 200 else '')
                return jsonify({
                    "error": f"Could not parse TOS string. Received: \'{preview}\'. "
                             f"Expected format: SELL -1 STRANGLE SYMBOL 100 DD MON YY "
                             f"PUT_STRIKE/CALL_STRIKE PUT/CALL @PRICE LMT"
                }), 400

            position = _add_position(legs, position_name)
            return jsonify({"success": True, "position": position})

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/api/options-tracker/positions')
    def api_list_positions():
        positions = _load_positions()
        enriched = []
        for pos in positions:
            try:
                enriched.append(_enrich_position(pos))
            except Exception:
                enriched.append(pos)
        return jsonify({"positions": enriched})

    @app.route('/api/options-tracker/delete/<int:pos_id>', methods=['DELETE'])
    def api_delete_position(pos_id):
        positions = _load_positions()
        positions = [p for p in positions if p['id'] != pos_id]
        _save_positions(positions)
        return jsonify({"success": True})
