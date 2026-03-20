# -*- coding: utf-8 -*-
"""
Trade Journal Flask Routes
"""
from flask import Blueprint, render_template_string, request, redirect, url_for, jsonify
from datetime import datetime, date
from journal.models import Trade, get_session, init_db, fetch_historical_indicators, backup_to_json, restore_from_json
from journal import analytics

journal_bp = Blueprint('journal', __name__, url_prefix='/journal')

# Initialize database on import
init_db()

@journal_bp.route('/')
@journal_bp.route('')
def dashboard():
    """Main journal dashboard"""
    import yfinance as yf
    session = get_session()
    trades = session.query(Trade).order_by(Trade.entry_date.desc()).all()
    
    # Summary stats
    total_trades = len(trades)
    open_trades_list = [t for t in trades if t.status == 'open']
    open_count = len(open_trades_list)
    closed_trades = [t for t in trades if t.status == 'closed']
    
    wins = sum(1 for t in closed_trades if t.win)
    win_rate = (wins / len(closed_trades) * 100) if closed_trades else 0
    
    avg_rr = sum(t.actual_rr for t in closed_trades if t.actual_rr) / len(closed_trades) if closed_trades else 0
    total_pnl = sum(t.pnl_dollars for t in closed_trades if t.pnl_dollars) or 0
    expectancy = analytics.calculate_expectancy(trades)
    
    # Fetch live prices for open trades
    live_data = {}
    if open_trades_list:
        symbols = list(set(t.symbol for t in open_trades_list))
        try:
            tickers = yf.Tickers(' '.join(symbols))
            for sym in symbols:
                try:
                    price = tickers.tickers[sym].fast_info.last_price
                    if price:
                        live_data[sym] = price
                except Exception:
                    pass
        except Exception:
            pass
    
    session.close()
    
    return render_template_string(DASHBOARD_TEMPLATE,
                                  trades=trades,
                                  total_trades=total_trades,
                                  open_trades=open_count,
                                  win_rate=win_rate,
                                  avg_rr=avg_rr,
                                  total_pnl=total_pnl,
                                  expectancy=expectancy,
                                  live_data=live_data,
                                  today=date.today())

@journal_bp.route('/<int:trade_id>')
def trade_detail(trade_id):
    """Trade detail view"""
    session = get_session()
    trade = session.query(Trade).get(trade_id)
    if not trade:
        session.close()
        return redirect(url_for('journal.dashboard'))
    
    # Fetch live price for open trades
    live_price = None
    if trade.status == 'open':
        try:
            import yfinance as yf
            live_price = yf.Ticker(trade.symbol).fast_info.last_price
        except Exception:
            pass
    
    session.close()
    return render_template_string(TRADE_DETAIL_TEMPLATE, trade=trade, live_price=live_price, today=date.today())

@journal_bp.route('/new', methods=['GET', 'POST'])
def new_trade():
    """Create new trade"""
    if request.method == 'POST':
        session = get_session()
        
        # Get form data
        trade_type = request.form.get('trade_type', 'stock')
        symbol = request.form.get('symbol', '').upper()
        entry_date_str = request.form.get('entry_date')
        entry_date = datetime.strptime(entry_date_str, '%Y-%m-%d').date()
        
        # Try to fetch historical indicators if not provided
        adx_val = request.form.get('adx_at_entry', '')
        rsi_val = request.form.get('rsi_at_entry', '')
        entry_price_val = request.form.get('entry_price', '')
        vol_confirmed = request.form.get('volume_confirmed') == 'on'
        gold_cross = request.form.get('golden_cross') == 'on'
        
        # Auto-fetch if any are missing
        if not adx_val or not rsi_val or not entry_price_val:
            indicators = fetch_historical_indicators(symbol, entry_date)
            if indicators:
                if not adx_val:
                    adx_val = indicators['adx']
                if not rsi_val:
                    rsi_val = indicators['rsi']
                if not entry_price_val and trade_type == 'stock':
                    entry_price_val = indicators['price']
                # Only auto-set checkboxes if they weren't manually checked
                if not vol_confirmed:
                    vol_confirmed = indicators['volume_confirmed']
                if not gold_cross:
                    gold_cross = indicators['golden_cross']
        
        trade = Trade(
            trade_type=trade_type,
            symbol=symbol,
            entry_date=entry_date,
            entry_time=request.form.get('entry_time', ''),
            entry_price=float(entry_price_val),
            shares=float(request.form.get('shares', 0) or 0),
            planned_entry=float(request.form.get('planned_entry', 0) or 0),
            pattern_type=request.form.get('pattern_type'),
            scanner_score=int(request.form.get('scanner_score', 0) or 0),
            planned_stop=float(request.form.get('planned_stop', 0) or 0),
            planned_target=float(request.form.get('planned_target', 0) or 0),
            volume_confirmed=vol_confirmed,
            golden_cross=gold_cross,
            adx_at_entry=float(adx_val) if adx_val else None,
            rsi_at_entry=float(rsi_val) if rsi_val else None,
            sector=request.form.get('sector'),
            notes=request.form.get('notes')
        )
        
        # Options-specific fields
        if trade_type == 'option':
            trade.option_strategy = request.form.get('option_strategy')
            exp_str = request.form.get('option_expiration')
            if exp_str:
                trade.option_expiration = datetime.strptime(exp_str, '%Y-%m-%d').date()
            trade.option_strike = float(request.form.get('option_strike', 0) or 0)
            trade.option_strike_2 = float(request.form.get('option_strike_2', 0) or 0) if request.form.get('option_strike_2') else None
            trade.option_type = request.form.get('option_type')
            trade.option_dte = int(request.form.get('option_dte', 0) or 0)
            trade.option_iv = float(request.form.get('option_iv', 0) or 0) if request.form.get('option_iv') else None
            trade.option_delta = float(request.form.get('option_delta', 0) or 0) if request.form.get('option_delta') else None
        
        trade.compute_metrics()
        
        # Allow manual R:R override
        manual_rr = request.form.get('planned_rr', '')
        if manual_rr:
            trade.planned_rr = float(manual_rr)
        
        session.add(trade)
        session.commit()
        backup_to_json(session)
        session.close()
        
        return redirect(url_for('journal.dashboard'))
    
    # Pre-populate from query params (from scanner)
    prepop = {
        'symbol': request.args.get('symbol', ''),
        'scanner_score': request.args.get('score', ''),
        'planned_entry': request.args.get('buy_point', ''),
        'planned_stop': request.args.get('stop', ''),
        'planned_target': request.args.get('target', ''),
        'pattern_type': request.args.get('pattern', ''),
        'adx_at_entry': request.args.get('adx', ''),
        'rsi_at_entry': request.args.get('rsi', ''),
        'sector': request.args.get('sector', '')
    }
    
    return render_template_string(NEW_TRADE_TEMPLATE, prepop=prepop, today=date.today().isoformat())

@journal_bp.route('/api/fetch-indicators', methods=['POST'])
def api_fetch_indicators():
    """API endpoint to fetch historical indicators"""
    data = request.get_json()
    symbol = data.get('symbol')
    date_str = data.get('date')
    
    if not symbol or not date_str:
        return jsonify({'error': 'Missing symbol or date'}), 400
    
    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        indicators = fetch_historical_indicators(symbol, target_date)
        
        if indicators:
            # Convert numpy bools to Python bools for JSON serialization
            return jsonify({
                'price': float(indicators['price']),
                'adx': float(indicators['adx']),
                'rsi': float(indicators['rsi']),
                'volume_confirmed': bool(indicators['volume_confirmed']),
                'golden_cross': bool(indicators['golden_cross'])
            })
        else:
            return jsonify({'error': 'No data available'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@journal_bp.route('/<int:trade_id>/close', methods=['GET', 'POST'])
def close_trade(trade_id):
    """Close a trade"""
    session = get_session()
    trade = session.query(Trade).get(trade_id)
    
    if not trade:
        session.close()
        return redirect(url_for('journal.dashboard'))
    
    if request.method == 'POST':
        trade.exit_date = datetime.strptime(request.form.get('exit_date'), '%Y-%m-%d').date()
        trade.exit_time = request.form.get('exit_time', '')
        trade.exit_price = float(request.form.get('exit_price'))
        trade.exit_reason = request.form.get('exit_reason')
        trade.status = 'closed'
        trade.notes = (trade.notes or '') + '\n' + request.form.get('exit_notes', '')
        
        trade.compute_metrics()
        session.commit()
        backup_to_json(session)
        session.close()
        
        return redirect(url_for('journal.dashboard'))
    
    session.close()
    return render_template_string(CLOSE_TRADE_TEMPLATE, trade=trade, today=date.today().isoformat())

@journal_bp.route('/<int:trade_id>/edit', methods=['GET', 'POST'])
def edit_trade(trade_id):
    """Edit a trade"""
    session = get_session()
    trade = session.query(Trade).get(trade_id)
    
    if not trade:
        session.close()
        return redirect(url_for('journal.dashboard'))
    
    if request.method == 'POST':
        trade.symbol = request.form.get('symbol', '').upper()
        trade.entry_date = datetime.strptime(request.form.get('entry_date'), '%Y-%m-%d').date()
        trade.entry_time = request.form.get('entry_time', '')
        trade.entry_price = float(request.form.get('entry_price'))
        trade.shares = float(request.form.get('shares', 0) or 0)
        trade.planned_entry = float(request.form.get('planned_entry', 0) or 0)
        trade.pattern_type = request.form.get('pattern_type')
        trade.scanner_score = int(request.form.get('scanner_score', 0) or 0)
        trade.planned_stop = float(request.form.get('planned_stop', 0) or 0)
        trade.planned_target = float(request.form.get('planned_target', 0) or 0)
        trade.volume_confirmed = request.form.get('volume_confirmed') == 'on'
        trade.golden_cross = request.form.get('golden_cross') == 'on'
        trade.adx_at_entry = float(request.form.get('adx_at_entry', 0) or 0) or None
        trade.rsi_at_entry = float(request.form.get('rsi_at_entry', 0) or 0) or None
        trade.sector = request.form.get('sector')
        trade.notes = request.form.get('notes')
        
        trade.compute_metrics()
        
        # Allow manual R:R override
        manual_rr = request.form.get('planned_rr', '')
        if manual_rr:
            trade.planned_rr = float(manual_rr)
        
        session.commit()
        backup_to_json(session)
        session.close()
        
        return redirect(url_for('journal.dashboard'))
    
    session.close()
    return render_template_string(EDIT_TRADE_TEMPLATE, trade=trade)

@journal_bp.route('/<int:trade_id>/delete', methods=['POST'])
def delete_trade(trade_id):
    """Delete a trade"""
    session = get_session()
    trade = session.query(Trade).get(trade_id)
    
    if trade:
        session.delete(trade)
        session.commit()
        backup_to_json(session)
    
    session.close()
    
    return redirect(url_for('journal.dashboard'))

@journal_bp.route('/analytics')
def analytics_dashboard():
    """Analytics dashboard"""
    session = get_session()
    trades = session.query(Trade).all()
    
    # Calculate all metrics
    closed = [t for t in trades if t.status == 'closed']
    winners = [t for t in closed if t.win]
    losers = [t for t in closed if not t.win]
    
    stats = {
        'total_trades': len(trades),
        'closed_trades': len(closed),
        'win_rate': (len(winners) / len(closed) * 100) if closed else 0,
        'avg_winner': sum(t.pnl_dollars for t in winners) / len(winners) if winners else 0,
        'avg_loser': sum(t.pnl_dollars for t in losers) / len(losers) if losers else 0,
        'expectancy': analytics.calculate_expectancy(trades),
        'profit_factor': analytics.calculate_profit_factor(trades),
        'avg_days_winners': sum(t.days_held for t in winners if t.days_held) / len(winners) if winners else 0,
        'avg_days_losers': sum(t.days_held for t in losers if t.days_held) / len(losers) if losers else 0,
        'best_trade': max((t.pnl_dollars for t in closed if t.pnl_dollars), default=0),
        'worst_trade': min((t.pnl_dollars for t in closed if t.pnl_dollars), default=0)
    }
    
    pattern_perf = analytics.win_rate_by_pattern(trades)
    score_analysis = analytics.win_rate_by_score_bracket(trades)
    volume_edge = analytics.volume_confirmation_edge(trades)
    sector_perf = analytics.sector_performance(trades)
    monthly = analytics.monthly_summary(trades)
    
    session.close()
    
    return render_template_string(ANALYTICS_TEMPLATE,
                                  stats=stats,
                                  pattern_perf=pattern_perf,
                                  score_analysis=score_analysis,
                                  volume_edge=volume_edge,
                                  sector_perf=sector_perf,
                                  monthly=monthly)

@journal_bp.route('/analytics/api')
def analytics_api():
    """JSON endpoint for chart data"""
    session = get_session()
    trades = session.query(Trade).all()
    
    data = {
        'equity_curve': analytics.equity_curve(trades),
        'rolling_win_rate': analytics.rolling_win_rate(trades, window=10)
    }
    
    session.close()
    return jsonify(data)

@journal_bp.route('/export/csv')
def export_csv():
    """Export trades as CSV"""
    import csv
    from io import StringIO
    from flask import Response
    
    session = get_session()
    trades = session.query(Trade).all()
    
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Symbol', 'Entry Date', 'Entry Price', 'Exit Date', 'Exit Price', 
                     'Pattern', 'Score', 'P&L $', 'P&L %', 'R:R', 'Days', 'Win', 'Status'])
    
    for t in trades:
        writer.writerow([t.symbol, t.entry_date, t.entry_price, t.exit_date, t.exit_price,
                        t.pattern_type, t.scanner_score, t.pnl_dollars, t.pnl_percent,
                        t.actual_rr, t.days_held, t.win, t.status])
    
    session.close()
    
    return Response(output.getvalue(), mimetype='text/csv',
                   headers={'Content-Disposition': 'attachment; filename=trades.csv'})

@journal_bp.route('/restore', methods=['GET', 'POST'])
def restore_backup():
    """Restore trades from JSON backup"""
    if request.method == 'POST':
        count = restore_from_json()
        return redirect(url_for('journal.dashboard'))
    
    # Show restore page
    import os
    backup_exists = os.path.exists('data/trade_journal_backup.json')
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Restore Backup</title>
        <style>
            body {{ font-family: Arial; background: #1a1a2e; color: #eee; margin: 20px; }}
            .btn {{ padding: 12px 30px; background: #00d4ff; color: #1a1a2e; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; }}
            .warning {{ background: #ff9800; color: white; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        </style>
    </head>
    <body>
        <h1>🔄 Restore Trade Journal Backup</h1>
        {'<div class="warning">⚠️ Backup file found. This will restore any missing trades.</div><form method="POST"><button type="submit" class="btn">Restore from Backup</button></form>' if backup_exists else '<p>❌ No backup file found.</p>'}
        <br><br>
        <a href="/journal/">← Back to Journal</a>
    </body>
    </html>
    """
    
    return html


# HTML Templates
DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Trade Journal</title>
    <style>
        body { font-family: Arial; background: #1a1a2e; color: #eee; margin: 20px; }
        .nav { background: #16213e; padding: 10px; border-radius: 5px; margin-bottom: 20px; }
        .nav a { color: #00d4ff; text-decoration: none; margin: 0 15px; }
        .summary { display: grid; grid-template-columns: repeat(6, 1fr); gap: 15px; margin-bottom: 20px; }
        .stat-card { background: #16213e; padding: 15px; border-radius: 5px; text-align: center; }
        .stat-value { font-size: 24px; font-weight: bold; color: #00d4ff; }
        .stat-label { font-size: 12px; color: #999; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #333; }
        th { background: #16213e; color: #00d4ff; }
        .win { color: #4caf50; }
        .loss { color: #ef5350; }
        .open { color: #ffc107; }
        .btn { padding: 8px 15px; background: #00d4ff; color: #1a1a2e; border: none; border-radius: 4px; cursor: pointer; text-decoration: none; display: inline-block; }
        .btn-danger { background: #ef5350; color: white; }
        tr.clickable-row { cursor: pointer; }
        tr.clickable-row:hover { background: #16213e; }
    </style>
</head>
<body>
    <div class="nav">
        <a href="/">Scanner</a>
        <a href="/journal/">Journal</a>
        <a href="/journal/analytics">Analytics</a>
        <a href="/journal/new" style="background: #4caf50; color: white; padding: 8px 15px; border-radius: 4px; text-decoration: none; display: inline-block;">+ New Trade</a>
        <a href="/journal/export/csv">Export CSV</a>
        <a href="/journal/restore">Restore Backup</a>
    </div>
    
    <h1>📊 Trade Journal</h1>
    
    <div class="summary">
        <div class="stat-card">
            <div class="stat-value">{{ total_trades }}</div>
            <div class="stat-label">Total Trades</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{{ open_trades }}</div>
            <div class="stat-label">Open Positions</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{{ "%.1f"|format(win_rate) }}%</div>
            <div class="stat-label">Win Rate</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{{ "%.2f"|format(avg_rr) }}</div>
            <div class="stat-label">Avg R:R</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${{ "%.2f"|format(total_pnl) }}</div>
            <div class="stat-label">Total P&L</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${{ "%.2f"|format(expectancy) }}</div>
            <div class="stat-label">Expectancy</div>
        </div>
    </div>
    
    <table>
        <tr>
            <th>Date</th>
            <th>Symbol</th>
            <th>Shares</th>
            <th>Pattern</th>
            <th>Score</th>
            <th>Entry</th>
            <th>Stop</th>
            <th>Target</th>
            <th>R:R</th>
            <th>P&L</th>
            <th>Days</th>
            <th>Status</th>
            <th>Actions</th>
        </tr>
        {% for t in trades %}
        {% set days_open = (today - t.entry_date).days if t.status == 'open' else t.days_held %}
        {% set live_price = live_data.get(t.symbol) if t.status == 'open' else None %}
        {% if live_price %}
            {% if t.trade_type == 'option' %}
                {% set live_pnl = (live_price - t.entry_price) * t.shares * 100 %}
            {% else %}
                {% set live_pnl = (live_price - t.entry_price) * t.shares %}
            {% endif %}
            {% set live_pct = ((live_price - t.entry_price) / t.entry_price * 100) if t.entry_price else 0 %}
        {% endif %}
        <tr class="clickable-row" onclick="window.location='/journal/{{ t.id }}'">
            <td>{{ t.entry_date }}{% if t.entry_time %}<br><small style="color:#888;">{{ t.entry_time }}</small>{% endif %}</td>
            <td><strong>{{ t.symbol }}</strong></td>
            <td>{{ t.shares or '-' }}</td>
            <td>{{ t.pattern_type or '-' }}</td>
            <td>{{ t.scanner_score or '-' }}</td>
            <td>${{ "%.2f"|format(t.entry_price) }}</td>
            <td>${{ "%.2f"|format(t.planned_stop) if t.planned_stop else '-' }}</td>
            <td>${{ "%.2f"|format(t.planned_target) if t.planned_target else '-' }}</td>
            <td>
                {% if t.status == 'closed' and t.actual_rr %}
                    {{ "%.2f"|format(t.actual_rr) }}
                {% elif t.planned_rr %}
                    <span style="color:#888;">{{ "%.2f"|format(t.planned_rr) }}p</span>
                {% else %}
                    -
                {% endif %}
            </td>
            <td class="{% if t.status == 'closed' %}{% if t.win %}win{% else %}loss{% endif %}{% elif live_price %}{% if live_pnl > 0 %}win{% else %}loss{% endif %}{% endif %}">
                {% if t.status == 'closed' and t.pnl_dollars is not none %}
                    ${{ "%.2f"|format(t.pnl_dollars) }} ({{ "%.1f"|format(t.pnl_percent) }}%)
                {% elif live_price %}
                    ${{ "%.2f"|format(live_pnl) }} ({{ "%.1f"|format(live_pct) }}%)
                {% else %}
                    -
                {% endif %}
            </td>
            <td>{{ days_open if days_open is not none else '-' }}</td>
            <td class="{% if t.status == 'open' %}open{% endif %}">{{ t.status }}</td>
            <td onclick="event.stopPropagation()">
                <a href="/journal/{{ t.id }}/edit" class="btn" style="background: #ff9800;">Edit</a>
                {% if t.status == 'open' %}
                <a href="/journal/{{ t.id }}/close" class="btn">Close</a>
                {% endif %}
                <form method="POST" action="/journal/{{ t.id }}/delete" style="display:inline;">
                    <button class="btn btn-danger" onclick="return confirm('Delete?')">Delete</button>
                </form>
            </td>
        </tr>
        {% endfor %}
    </table>
</body>
</html>
"""

TRADE_DETAIL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Trade: {{ trade.symbol }}</title>
    <style>
        body { font-family: Arial; background: #1a1a2e; color: #eee; margin: 20px; }
        .nav { background: #16213e; padding: 10px; border-radius: 5px; margin-bottom: 20px; }
        .nav a { color: #00d4ff; text-decoration: none; margin: 0 15px; }
        .detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }
        .card { background: #16213e; padding: 20px; border-radius: 8px; }
        .card h3 { color: #00d4ff; margin-top: 0; }
        .field { margin-bottom: 12px; }
        .field-label { color: #888; font-size: 12px; }
        .field-value { font-size: 16px; margin-top: 2px; }
        .win { color: #4caf50; }
        .loss { color: #ef5350; }
        .open-tag { color: #ffc107; }
        .btn { padding: 10px 20px; background: #00d4ff; color: #1a1a2e; border: none; border-radius: 4px; cursor: pointer; text-decoration: none; display: inline-block; font-weight: bold; margin-right: 8px; }
        .btn-close { background: #4caf50; color: white; }
        .btn-edit { background: #ff9800; }
        .notes-box { background: #1a1a2e; padding: 15px; border-radius: 5px; white-space: pre-wrap; line-height: 1.6; }
        .pnl-banner { padding: 20px; border-radius: 8px; text-align: center; margin-bottom: 20px; }
        .pnl-banner.positive { background: rgba(76,175,80,0.15); border: 1px solid #4caf50; }
        .pnl-banner.negative { background: rgba(239,83,80,0.15); border: 1px solid #ef5350; }
        .pnl-banner.neutral { background: #16213e; }
        .pnl-amount { font-size: 32px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="nav">
        <a href="/">Scanner</a>
        <a href="/journal/">← Journal</a>
        <a href="/journal/analytics">Analytics</a>
    </div>

    <h1>{{ trade.symbol }} — {{ trade.trade_type|capitalize }} Trade
        {% if trade.status == 'open' %}<span class="open-tag">(OPEN)</span>{% endif %}
    </h1>

    {% set days_open = (today - trade.entry_date).days if trade.status == 'open' else trade.days_held %}

    {% if trade.status == 'closed' and trade.pnl_dollars is not none %}
    <div class="pnl-banner {% if trade.pnl_dollars > 0 %}positive{% elif trade.pnl_dollars < 0 %}negative{% else %}neutral{% endif %}">
        <div class="pnl-amount {% if trade.pnl_dollars > 0 %}win{% else %}loss{% endif %}">
            ${{ "%.2f"|format(trade.pnl_dollars) }} ({{ "%.1f"|format(trade.pnl_percent) }}%)
        </div>
        <div style="color:#999;">Closed — {{ trade.days_held or 0 }} days held</div>
    </div>
    {% elif trade.status == 'open' and live_price %}
        {% if trade.trade_type == 'option' %}
            {% set lpnl = (live_price - trade.entry_price) * trade.shares * 100 %}
        {% else %}
            {% set lpnl = (live_price - trade.entry_price) * trade.shares %}
        {% endif %}
        {% set lpct = ((live_price - trade.entry_price) / trade.entry_price * 100) if trade.entry_price else 0 %}
    <div class="pnl-banner {% if lpnl > 0 %}positive{% elif lpnl < 0 %}negative{% else %}neutral{% endif %}">
        <div class="pnl-amount {% if lpnl > 0 %}win{% else %}loss{% endif %}">
            ${{ "%.2f"|format(lpnl) }} ({{ "%.1f"|format(lpct) }}%)
        </div>
        <div style="color:#999;">Live P&L — {{ days_open }} days open — Current: ${{ "%.2f"|format(live_price) }}</div>
    </div>
    {% elif trade.status == 'open' %}
    <div class="pnl-banner neutral">
        <div style="color:#ffc107; font-size: 20px;">Open — {{ days_open }} days</div>
    </div>
    {% endif %}

    <div class="detail-grid">
        <div class="card">
            <h3>📥 Entry</h3>
            <div class="field"><div class="field-label">Date</div><div class="field-value">{{ trade.entry_date }}{% if trade.entry_time %} {{ trade.entry_time }}{% endif %}</div></div>
            <div class="field"><div class="field-label">Entry Price</div><div class="field-value">${{ "%.2f"|format(trade.entry_price) }}</div></div>
            <div class="field"><div class="field-label">{{ 'Contracts' if trade.trade_type == 'option' else 'Shares' }}</div><div class="field-value">{{ trade.shares }}</div></div>
            {% if trade.planned_entry %}<div class="field"><div class="field-label">Scanner Buy Point</div><div class="field-value">${{ "%.2f"|format(trade.planned_entry) }}</div></div>{% endif %}
        </div>

        <div class="card">
            <h3>🎯 Plan</h3>
            <div class="field"><div class="field-label">Stop Loss</div><div class="field-value">{{ "$%.2f"|format(trade.planned_stop) if trade.planned_stop else '-' }}</div></div>
            <div class="field"><div class="field-label">Target</div><div class="field-value">{{ "$%.2f"|format(trade.planned_target) if trade.planned_target else '-' }}</div></div>
            <div class="field"><div class="field-label">Planned R:R</div><div class="field-value">{{ "%.2f"|format(trade.planned_rr) if trade.planned_rr else '-' }}</div></div>
            {% if trade.status == 'closed' %}<div class="field"><div class="field-label">Actual R:R</div><div class="field-value">{{ "%.2f"|format(trade.actual_rr) if trade.actual_rr else '-' }}</div></div>{% endif %}
        </div>

        <div class="card">
            <h3>📊 Indicators</h3>
            <div class="field"><div class="field-label">Pattern</div><div class="field-value">{{ trade.pattern_type or '-' }}</div></div>
            <div class="field"><div class="field-label">Scanner Score</div><div class="field-value">{{ trade.scanner_score or '-' }}</div></div>
            <div class="field"><div class="field-label">ADX</div><div class="field-value">{{ "%.1f"|format(trade.adx_at_entry) if trade.adx_at_entry else '-' }}</div></div>
            <div class="field"><div class="field-label">RSI</div><div class="field-value">{{ "%.1f"|format(trade.rsi_at_entry) if trade.rsi_at_entry else '-' }}</div></div>
            <div class="field"><div class="field-label">Volume Confirmed</div><div class="field-value">{{ '✅' if trade.volume_confirmed else '❌' }}</div></div>
            <div class="field"><div class="field-label">Golden Cross</div><div class="field-value">{{ '✅' if trade.golden_cross else '❌' }}</div></div>
            {% if trade.sector %}<div class="field"><div class="field-label">Sector</div><div class="field-value">{{ trade.sector }}</div></div>{% endif %}
        </div>

        {% if trade.trade_type == 'option' %}
        <div class="card">
            <h3>📋 Options Details</h3>
            <div class="field"><div class="field-label">Strategy</div><div class="field-value">{{ trade.option_strategy or '-' }}</div></div>
            <div class="field"><div class="field-label">Type</div><div class="field-value">{{ trade.option_type or '-' }}</div></div>
            <div class="field"><div class="field-label">Strike</div><div class="field-value">{{ "$%.2f"|format(trade.option_strike) if trade.option_strike else '-' }}</div></div>
            {% if trade.option_strike_2 %}<div class="field"><div class="field-label">Strike 2</div><div class="field-value">${{ "%.2f"|format(trade.option_strike_2) }}</div></div>{% endif %}
            <div class="field"><div class="field-label">Expiration</div><div class="field-value">{{ trade.option_expiration or '-' }}</div></div>
            <div class="field"><div class="field-label">DTE at Entry</div><div class="field-value">{{ trade.option_dte or '-' }}</div></div>
            {% if trade.option_iv %}<div class="field"><div class="field-label">IV at Entry</div><div class="field-value">{{ "%.1f"|format(trade.option_iv) }}%</div></div>{% endif %}
            {% if trade.option_delta %}<div class="field"><div class="field-label">Delta at Entry</div><div class="field-value">{{ "%.2f"|format(trade.option_delta) }}</div></div>{% endif %}
        </div>
        {% endif %}

        {% if trade.status == 'closed' %}
        <div class="card">
            <h3>📤 Exit</h3>
            <div class="field"><div class="field-label">Date</div><div class="field-value">{{ trade.exit_date }}{% if trade.exit_time %} {{ trade.exit_time }}{% endif %}</div></div>
            <div class="field"><div class="field-label">Exit Price</div><div class="field-value">${{ "%.2f"|format(trade.exit_price) }}</div></div>
            <div class="field"><div class="field-label">Reason</div><div class="field-value">{{ trade.exit_reason or '-' }}</div></div>
        </div>
        {% endif %}
    </div>

    {% if trade.notes %}
    <div class="card" style="margin-bottom: 20px;">
        <h3>📝 Notes</h3>
        <div class="notes-box">{{ trade.notes }}</div>
    </div>
    {% endif %}

    <div>
        <a href="/journal/{{ trade.id }}/edit" class="btn btn-edit">✏️ Edit</a>
        {% if trade.status == 'open' %}
        <a href="/journal/{{ trade.id }}/close" class="btn btn-close">🔒 Close Trade</a>
        {% endif %}
        <a href="/journal/" class="btn" style="background: #555; color: #eee;">← Back</a>
    </div>
</body>
</html>
"""

NEW_TRADE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>New Trade</title>
    <style>
        body { font-family: Arial; background: #1a1a2e; color: #eee; margin: 20px; }
        .nav { background: #16213e; padding: 10px; border-radius: 5px; margin-bottom: 20px; }
        .nav a { color: #00d4ff; text-decoration: none; margin: 0 15px; }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; color: #999; }
        input, select, textarea { width: 100%; padding: 10px; background: #16213e; border: 1px solid #333; color: #eee; border-radius: 4px; box-sizing: border-box; }
        .btn { padding: 12px 30px; background: #00d4ff; color: #1a1a2e; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
    </style>
</head>
<body>
    <div class="nav">
        <a href="/">Scanner</a>
        <a href="/journal">Journal</a>
        <a href="/journal/analytics">Analytics</a>
    </div>
    
    <h1>📝 New Trade</h1>
    
    <form method="POST">
        <div class="form-group">
            <label>Trade Type *</label>
            <select name="trade_type" id="trade_type" onchange="toggleOptionsFields()" required>
                <option value="stock">Stock</option>
                <option value="option">Option</option>
            </select>
        </div>
        
        <div class="grid">
            <div>
                <div class="form-group">
                    <label>Symbol *</label>
                    <input type="text" name="symbol" value="{{ prepop.symbol }}" required>
                </div>
                <div class="form-group">
                    <label>Entry Date *</label>
                    <input type="date" name="entry_date" value="{{ today }}" required>
                </div>
                <div class="form-group">
                    <label>Entry Time (e.g., 6:57 AM PST)</label>
                    <input type="text" name="entry_time" placeholder="6:57 AM PST">
                </div>
                <div class="form-group">
                    <label id="entry_price_label">Actual Entry Price *</label>
                    <input type="number" step="0.01" name="entry_price" required oninput="calcRR()">
                    <small style="color: #888;" id="entry_price_hint">Stock price or option premium per contract</small>
                </div>
                <div class="form-group">
                    <label id="shares_label">Number of Shares * (fractional OK)</label>
                    <input type="number" step="0.01" name="shares" required>
                    <small style="color: #888;" id="shares_hint">For options: number of contracts</small>
                </div>
                <div class="form-group">
                    <label>Scanner Buy Point</label>
                    <input type="number" step="0.01" name="planned_entry" value="{{ prepop.planned_entry }}">
                </div>
                <div class="form-group">
                    <label>Pattern Type</label>
                    <select name="pattern_type">
                        <option value="">Select...</option>
                        <option value="cup_handle" {% if prepop.pattern_type == 'cup_handle' %}selected{% endif %}>Cup & Handle</option>
                        <option value="bull_flag" {% if prepop.pattern_type == 'bull_flag' %}selected{% endif %}>Bull Flag</option>
                        <option value="double_bottom" {% if prepop.pattern_type == 'double_bottom' %}selected{% endif %}>Double Bottom</option>
                        <option value="ascending_triangle" {% if prepop.pattern_type == 'ascending_triangle' %}selected{% endif %}>Ascending Triangle</option>
                        <option value="mixed">Mixed</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Scanner Score (0-100)</label>
                    <input type="number" name="scanner_score" value="{{ prepop.scanner_score }}" min="0" max="100">
                </div>
            </div>
            
            <div>
                <div class="form-group">
                    <label>Planned Stop Loss</label>
                    <input type="number" step="0.01" name="planned_stop" value="{{ prepop.planned_stop }}" oninput="calcRR()">
                </div>
                <div class="form-group">
                    <label>Planned Target</label>
                    <input type="number" step="0.01" name="planned_target" value="{{ prepop.planned_target }}" oninput="calcRR()">
                </div>
                <div class="form-group">
                    <label>Planned R:R</label>
                    <input type="number" step="0.01" name="planned_rr" id="planned_rr" placeholder="Auto-calculated">
                    <small style="color: #888;">Auto-fills from entry/stop/target, or enter manually</small>
                </div>
                <div class="form-group">
                    <label>ADX at Entry</label>
                    <input type="number" step="0.1" name="adx_at_entry" id="adx_at_entry" value="{{ prepop.adx_at_entry }}">
                </div>
                <div class="form-group">
                    <label>RSI at Entry</label>
                    <input type="number" step="0.1" name="rsi_at_entry" id="rsi_at_entry" value="{{ prepop.rsi_at_entry }}">
                </div>
                <div class="form-group">
                    <button type="button" class="btn" onclick="fetchIndicators()" style="background: #ff9800; width: 100%;">
                        🔄 Auto-Fill from History
                    </button>
                    <small id="fetch-status" style="color: #888;"></small>
                </div>
                <div class="form-group">
                    <label>Sector</label>
                    <input type="text" name="sector" value="{{ prepop.sector }}">
                </div>
                <div class="form-group">
                    <label><input type="checkbox" name="volume_confirmed" id="volume_confirmed"> Volume Confirmed (2x+)</label>
                    <label><input type="checkbox" name="golden_cross" id="golden_cross"> Golden Cross Active</label>
                </div>
            </div>
        </div>
        
        <!-- Options-specific fields -->
        <div id="options_fields" style="display: none; margin-top: 20px; padding: 20px; background: #16213e; border-radius: 8px;">
            <h3 style="color: #00d4ff; margin-top: 0;">📊 Options Details</h3>
            <div class="grid">
                <div>
                    <div class="form-group">
                        <label>Strategy</label>
                        <select name="option_strategy">
                            <option value="">Select...</option>
                            <option value="long_call">Long Call</option>
                            <option value="cash_secured_put">Cash-Secured Put</option>
                            <option value="pmcc">Poor Man's Covered Call</option>
                            <option value="iron_condor">Iron Condor</option>
                            <option value="bull_call_spread">Bull Call Spread</option>
                            <option value="other">Other</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Expiration Date</label>
                        <input type="date" name="option_expiration">
                    </div>
                    <div class="form-group">
                        <label>Strike Price</label>
                        <input type="number" step="0.01" name="option_strike">
                        <small style="color: #888;">Primary strike (or short strike for spreads)</small>
                    </div>
                    <div class="form-group">
                        <label>Strike Price 2 (for spreads)</label>
                        <input type="number" step="0.01" name="option_strike_2">
                        <small style="color: #888;">Long strike for spreads (optional)</small>
                    </div>
                </div>
                <div>
                    <div class="form-group">
                        <label>Option Type</label>
                        <select name="option_type">
                            <option value="">Select...</option>
                            <option value="call">Call</option>
                            <option value="put">Put</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>DTE (Days to Expiration)</label>
                        <input type="number" name="option_dte">
                    </div>
                    <div class="form-group">
                        <label>IV at Entry (%)</label>
                        <input type="number" step="0.1" name="option_iv">
                    </div>
                    <div class="form-group">
                        <label>Delta at Entry</label>
                        <input type="number" step="0.01" name="option_delta">
                    </div>
                </div>
            </div>
        </div>
        
        <div class="form-group">
            <label>Notes</label>
            <textarea name="notes" rows="3"></textarea>
        </div>
        
        <button type="submit" class="btn">Save Trade</button>
        <a href="/journal" style="margin-left: 10px; color: #999;">Cancel</a>
    </form>
    
    <script>
    function toggleOptionsFields() {
        const tradeType = document.getElementById('trade_type').value;
        const optionsFields = document.getElementById('options_fields');
        const entryPriceLabel = document.getElementById('entry_price_label');
        const entryPriceHint = document.getElementById('entry_price_hint');
        const sharesLabel = document.getElementById('shares_label');
        const sharesHint = document.getElementById('shares_hint');
        
        if (tradeType === 'option') {
            optionsFields.style.display = 'block';
            entryPriceLabel.textContent = 'Entry Premium (per contract) *';
            entryPriceHint.textContent = 'Premium paid/received per contract';
            sharesLabel.textContent = 'Number of Contracts *';
            sharesHint.textContent = 'Each contract = 100 shares';
        } else {
            optionsFields.style.display = 'none';
            entryPriceLabel.textContent = 'Actual Entry Price *';
            entryPriceHint.textContent = 'Stock price or option premium per contract';
            sharesLabel.textContent = 'Number of Shares * (fractional OK)';
            sharesHint.textContent = 'For options: number of contracts';
        }
    }
    
    function calcRR() {
        const entry = parseFloat(document.querySelector('input[name="entry_price"]').value);
        const stop = parseFloat(document.querySelector('input[name="planned_stop"]').value);
        const target = parseFloat(document.querySelector('input[name="planned_target"]').value);
        const rrField = document.getElementById('planned_rr');
        if (entry && stop && target && entry !== stop) {
            const risk = Math.abs(entry - stop);
            const reward = Math.abs(target - entry);
            if (risk > 0) rrField.value = (reward / risk).toFixed(2);
        }
    }
    
    function fetchIndicators() {
        const symbol = document.querySelector('input[name="symbol"]').value;
        const date = document.querySelector('input[name="entry_date"]').value;
        const status = document.getElementById('fetch-status');
        
        if (!symbol || !date) {
            status.textContent = '⚠️ Enter symbol and date first';
            status.style.color = '#ff9800';
            return;
        }
        
        status.textContent = '⏳ Fetching...';
        status.style.color = '#00d4ff';
        
        fetch('/journal/api/fetch-indicators', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({symbol: symbol.toUpperCase(), date: date})
        })
        .then(r => r.json())
        .then(data => {
            if (data.error) {
                status.textContent = '❌ ' + data.error;
                status.style.color = '#ef5350';
            } else {
                // Fill price if empty
                const priceField = document.querySelector('input[name="entry_price"]');
                if (!priceField.value && data.price) {
                    priceField.value = data.price;
                }
                
                // Fill indicators
                document.getElementById('adx_at_entry').value = data.adx;
                document.getElementById('rsi_at_entry').value = data.rsi;
                
                // Check boxes if true
                if (data.volume_confirmed) {
                    document.getElementById('volume_confirmed').checked = true;
                }
                if (data.golden_cross) {
                    document.getElementById('golden_cross').checked = true;
                }
                
                status.textContent = '✅ Loaded: Price=$' + data.price + ', ADX=' + data.adx + ', RSI=' + data.rsi + 
                                    (data.volume_confirmed ? ', Vol✓' : '') + (data.golden_cross ? ', GC✓' : '');
                status.style.color = '#4caf50';
            }
        })
        .catch(e => {
            status.textContent = '❌ Error: ' + e.message;
            status.style.color = '#ef5350';
        });
    }
    </script>
</body>
</html>
"""

EDIT_TRADE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Edit Trade</title>
    <style>
        body { font-family: Arial; background: #1a1a2e; color: #eee; margin: 20px; }
        .nav { background: #16213e; padding: 10px; border-radius: 5px; margin-bottom: 20px; }
        .nav a { color: #00d4ff; text-decoration: none; margin: 0 15px; }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; color: #999; }
        input, select, textarea { width: 100%; padding: 10px; background: #16213e; border: 1px solid #333; color: #eee; border-radius: 4px; box-sizing: border-box; }
        .btn { padding: 12px 30px; background: #00d4ff; color: #1a1a2e; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
    </style>
</head>
<body>
    <div class="nav">
        <a href="/">Scanner</a>
        <a href="/journal/">Journal</a>
    </div>
    
    <h1>✏️ Edit Trade: {{ trade.symbol }}</h1>
    
    <form method="POST">
        <div class="grid">
            <div>
                <div class="form-group">
                    <label>Symbol *</label>
                    <input type="text" name="symbol" value="{{ trade.symbol }}" required>
                </div>
                <div class="form-group">
                    <label>Entry Date *</label>
                    <input type="date" name="entry_date" value="{{ trade.entry_date }}" required>
                </div>
                <div class="form-group">
                    <label>Entry Time</label>
                    <input type="text" name="entry_time" value="{{ trade.entry_time or '' }}">
                </div>
                <div class="form-group">
                    <label>Entry Price *</label>
                    <input type="number" step="0.01" name="entry_price" value="{{ trade.entry_price }}" required oninput="calcRR()">
                </div>
                <div class="form-group">
                    <label>Shares *</label>
                    <input type="number" step="0.01" name="shares" value="{{ trade.shares }}" required>
                </div>
                <div class="form-group">
                    <label>Scanner Buy Point</label>
                    <input type="number" step="0.01" name="planned_entry" value="{{ trade.planned_entry or '' }}">
                </div>
                <div class="form-group">
                    <label>Pattern Type</label>
                    <select name="pattern_type">
                        <option value="">Select...</option>
                        <option value="cup_handle" {% if trade.pattern_type == 'cup_handle' %}selected{% endif %}>Cup & Handle</option>
                        <option value="bull_flag" {% if trade.pattern_type == 'bull_flag' %}selected{% endif %}>Bull Flag</option>
                        <option value="double_bottom" {% if trade.pattern_type == 'double_bottom' %}selected{% endif %}>Double Bottom</option>
                        <option value="ascending_triangle" {% if trade.pattern_type == 'ascending_triangle' %}selected{% endif %}>Ascending Triangle</option>
                        <option value="mixed" {% if trade.pattern_type == 'mixed' %}selected{% endif %}>Mixed</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Scanner Score</label>
                    <input type="number" name="scanner_score" value="{{ trade.scanner_score or '' }}" min="0" max="100">
                </div>
            </div>
            
            <div>
                <div class="form-group">
                    <label>Planned Stop</label>
                    <input type="number" step="0.01" name="planned_stop" value="{{ trade.planned_stop or '' }}" oninput="calcRR()">
                </div>
                <div class="form-group">
                    <label>Planned Target</label>
                    <input type="number" step="0.01" name="planned_target" value="{{ trade.planned_target or '' }}" oninput="calcRR()">
                </div>
                <div class="form-group">
                    <label>Planned R:R</label>
                    <input type="number" step="0.01" name="planned_rr" id="planned_rr" value="{{ trade.planned_rr or '' }}">
                    <small style="color: #888;">Auto-fills from entry/stop/target, or enter manually</small>
                </div>
                <div class="form-group">
                    <label>ADX at Entry</label>
                    <input type="number" step="0.1" name="adx_at_entry" value="{{ trade.adx_at_entry or '' }}">
                </div>
                <div class="form-group">
                    <label>RSI at Entry</label>
                    <input type="number" step="0.1" name="rsi_at_entry" value="{{ trade.rsi_at_entry or '' }}">
                </div>
                <div class="form-group">
                    <label>Sector</label>
                    <input type="text" name="sector" value="{{ trade.sector or '' }}">
                </div>
                <div class="form-group">
                    <label><input type="checkbox" name="volume_confirmed" {% if trade.volume_confirmed %}checked{% endif %}> Volume Confirmed</label>
                    <label><input type="checkbox" name="golden_cross" {% if trade.golden_cross %}checked{% endif %}> Golden Cross</label>
                </div>
            </div>
        </div>
        
        <div class="form-group">
            <label>Notes</label>
            <textarea name="notes" rows="3">{{ trade.notes or '' }}</textarea>
        </div>
        
        <button type="submit" class="btn">Save Changes</button>
        <a href="/journal/" style="margin-left: 10px; color: #999;">Cancel</a>
    </form>
    <script>
    function calcRR() {
        const entry = parseFloat(document.querySelector('input[name="entry_price"]').value);
        const stop = parseFloat(document.querySelector('input[name="planned_stop"]').value);
        const target = parseFloat(document.querySelector('input[name="planned_target"]').value);
        const rrField = document.getElementById('planned_rr');
        if (entry && stop && target && entry !== stop) {
            const risk = Math.abs(entry - stop);
            const reward = Math.abs(target - entry);
            if (risk > 0) rrField.value = (reward / risk).toFixed(2);
        }
    }
    </script>
</body>
</html>
"""

CLOSE_TRADE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Close Trade</title>
    <style>
        body { font-family: Arial; background: #1a1a2e; color: #eee; margin: 20px; }
        .nav { background: #16213e; padding: 10px; border-radius: 5px; margin-bottom: 20px; }
        .nav a { color: #00d4ff; text-decoration: none; margin: 0 15px; }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; color: #999; }
        input, select, textarea { width: 100%; padding: 10px; background: #16213e; border: 1px solid #333; color: #eee; border-radius: 4px; box-sizing: border-box; }
        .btn { padding: 12px 30px; background: #00d4ff; color: #1a1a2e; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; }
        .trade-info { background: #16213e; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
    </style>
</head>
<body>
    <div class="nav">
        <a href="/">Scanner</a>
        <a href="/journal">Journal</a>
    </div>
    
    <h1>🔒 Close Trade: {{ trade.symbol }}</h1>
    
    <div class="trade-info">
        <p><strong>Entry:</strong> {{ trade.entry_date }} @ ${{ "%.2f"|format(trade.entry_price) }}</p>
        <p><strong>Pattern:</strong> {{ trade.pattern_type }} | <strong>Score:</strong> {{ trade.scanner_score }}</p>
        <p><strong>Stop:</strong> ${{ "%.2f"|format(trade.planned_stop) if trade.planned_stop else '-' }} | 
           <strong>Target:</strong> ${{ "%.2f"|format(trade.planned_target) if trade.planned_target else '-' }}</p>
    </div>
    
    <form method="POST">
        <div class="form-group">
            <label>Exit Date</label>
            <input type="date" name="exit_date" value="{{ today }}" required>
        </div>
        <div class="form-group">
            <label>Exit Time (e.g., 2:30 PM PST)</label>
            <input type="text" name="exit_time" placeholder="2:30 PM PST">
        </div>
        <div class="form-group">
            <label>Exit Price</label>
            <input type="number" step="0.01" name="exit_price" required>
        </div>
        <div class="form-group">
            <label>Exit Reason</label>
            <select name="exit_reason" required>
                <option value="stop_hit">Stop Hit</option>
                <option value="target_hit">Target Hit</option>
                <option value="manual_exit">Manual Exit</option>
                <option value="trailing_stop">Trailing Stop</option>
                <option value="time_stop">Time Stop</option>
            </select>
        </div>
        <div class="form-group">
            <label>Exit Notes</label>
            <textarea name="exit_notes" rows="3"></textarea>
        </div>
        
        <button type="submit" class="btn">Close Trade</button>
        <a href="/journal" style="margin-left: 10px; color: #999;">Cancel</a>
    </form>
</body>
</html>
"""


ANALYTICS_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Trade Analytics</title>
    <style>
        body { font-family: Arial; background: #1a1a2e; color: #eee; margin: 20px; }
        .nav { background: #16213e; padding: 10px; border-radius: 5px; margin-bottom: 20px; }
        .nav a { color: #00d4ff; text-decoration: none; margin: 0 15px; }
        .section { background: #16213e; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
        h2 { color: #00d4ff; margin-top: 0; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #333; }
        th { background: #1a1a2e; color: #00d4ff; }
        .stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 20px; }
        .stat-box { background: #1a1a2e; padding: 15px; border-radius: 5px; text-align: center; }
        .stat-value { font-size: 20px; font-weight: bold; color: #00d4ff; }
        .stat-label { font-size: 12px; color: #999; margin-top: 5px; }
    </style>
</head>
<body>
    <div class="nav">
        <a href="/">Scanner</a>
        <a href="/journal">Journal</a>
        <a href="/journal/analytics">Analytics</a>
    </div>
    
    <h1>📈 Trade Analytics</h1>
    
    <div class="section">
        <h2>Overview Stats</h2>
        <div class="stats-grid">
            <div class="stat-box">
                <div class="stat-value">{{ stats.total_trades }}</div>
                <div class="stat-label">Total Trades</div>
            </div>
            <div class="stat-box">
                <div class="stat-value">{{ "%.1f"|format(stats.win_rate) }}%</div>
                <div class="stat-label">Win Rate</div>
            </div>
            <div class="stat-box">
                <div class="stat-value">${{ "%.2f"|format(stats.expectancy) }}</div>
                <div class="stat-label">Expectancy</div>
            </div>
            <div class="stat-box">
                <div class="stat-value">{{ "%.2f"|format(stats.profit_factor) }}</div>
                <div class="stat-label">Profit Factor</div>
            </div>
            <div class="stat-box">
                <div class="stat-value">${{ "%.2f"|format(stats.avg_winner) }}</div>
                <div class="stat-label">Avg Winner</div>
            </div>
            <div class="stat-box">
                <div class="stat-value">${{ "%.2f"|format(stats.avg_loser) }}</div>
                <div class="stat-label">Avg Loser</div>
            </div>
            <div class="stat-box">
                <div class="stat-value">{{ "%.1f"|format(stats.avg_days_winners) }}</div>
                <div class="stat-label">Avg Days (Winners)</div>
            </div>
            <div class="stat-box">
                <div class="stat-value">{{ "%.1f"|format(stats.avg_days_losers) }}</div>
                <div class="stat-label">Avg Days (Losers)</div>
            </div>
        </div>
    </div>
    
    <div class="section">
        <h2>Pattern Performance</h2>
        <table>
            <tr>
                <th>Pattern</th>
                <th>Trades</th>
                <th>Win Rate</th>
                <th>Avg R:R</th>
                <th>Avg P&L</th>
                <th>Expectancy</th>
            </tr>
            {% for pattern, data in pattern_perf.items() %}
            <tr>
                <td>{{ pattern }}</td>
                <td>{{ data.count }}</td>
                <td>{{ "%.1f"|format(data.win_rate * 100) }}%</td>
                <td>{{ "%.2f"|format(data.avg_rr) }}</td>
                <td>${{ "%.2f"|format(data.avg_pnl) }}</td>
                <td>${{ "%.2f"|format(data.expectancy) }}</td>
            </tr>
            {% endfor %}
        </table>
    </div>
    
    <div class="section">
        <h2>Score Analysis</h2>
        <table>
            <tr>
                <th>Score Bracket</th>
                <th>Trades</th>
                <th>Win Rate</th>
            </tr>
            {% for bracket, data in score_analysis.items() %}
            <tr>
                <td>{{ bracket }}</td>
                <td>{{ data.count }}</td>
                <td>{{ "%.1f"|format(data.win_rate * 100) }}%</td>
            </tr>
            {% endfor %}
        </table>
    </div>
    
    <div class="section">
        <h2>Volume Confirmation Impact</h2>
        <table>
            <tr>
                <th>Type</th>
                <th>Trades</th>
                <th>Win Rate</th>
                <th>Avg R:R</th>
            </tr>
            <tr>
                <td>Volume Confirmed</td>
                <td>{{ volume_edge.confirmed.count }}</td>
                <td>{{ "%.1f"|format(volume_edge.confirmed.win_rate * 100) }}%</td>
                <td>{{ "%.2f"|format(volume_edge.confirmed.avg_rr) }}</td>
            </tr>
            <tr>
                <td>Not Confirmed</td>
                <td>{{ volume_edge.not_confirmed.count }}</td>
                <td>{{ "%.1f"|format(volume_edge.not_confirmed.win_rate * 100) }}%</td>
                <td>{{ "%.2f"|format(volume_edge.not_confirmed.avg_rr) }}</td>
            </tr>
        </table>
    </div>
    
    <div class="section">
        <h2>Sector Performance</h2>
        <table>
            <tr>
                <th>Sector</th>
                <th>Trades</th>
                <th>Win Rate</th>
                <th>Total P&L</th>
            </tr>
            {% for sector, data in sector_perf.items() %}
            <tr>
                <td>{{ sector }}</td>
                <td>{{ data.count }}</td>
                <td>{{ "%.1f"|format(data.win_rate * 100) }}%</td>
                <td>${{ "%.2f"|format(data.total_pnl) }}</td>
            </tr>
            {% endfor %}
        </table>
    </div>
    
    <div class="section">
        <h2>Monthly Summary</h2>
        <table>
            <tr>
                <th>Month</th>
                <th>Trades</th>
                <th>Wins</th>
                <th>Losses</th>
                <th>Win Rate</th>
                <th>P&L</th>
            </tr>
            {% for month in monthly %}
            <tr>
                <td>{{ month.month }}</td>
                <td>{{ month.trades }}</td>
                <td>{{ month.wins }}</td>
                <td>{{ month.losses }}</td>
                <td>{{ "%.1f"|format(month.win_rate * 100) }}%</td>
                <td>${{ "%.2f"|format(month.pnl) }}</td>
            </tr>
            {% endfor %}
        </table>
    </div>
</body>
</html>
"""
