"""
Trade Journal Analytics Functions
"""
from collections import defaultdict
from datetime import datetime

def calculate_expectancy(trades):
    """(Win Rate × Avg Winner) - (Loss Rate × Avg Loser)"""
    closed = [t for t in trades if t.status == 'closed' and t.pnl_dollars is not None]
    if not closed:
        return 0
    
    winners = [t for t in closed if t.win]
    losers = [t for t in closed if not t.win]
    
    win_rate = len(winners) / len(closed) if closed else 0
    loss_rate = 1 - win_rate
    
    avg_winner = sum(t.pnl_dollars for t in winners) / len(winners) if winners else 0
    avg_loser = abs(sum(t.pnl_dollars for t in losers) / len(losers)) if losers else 0
    
    return (win_rate * avg_winner) - (loss_rate * avg_loser)

def calculate_profit_factor(trades):
    """Gross Profit / Gross Loss"""
    closed = [t for t in trades if t.status == 'closed' and t.pnl_dollars is not None]
    
    gross_profit = sum(t.pnl_dollars for t in closed if t.win)
    gross_loss = abs(sum(t.pnl_dollars for t in closed if not t.win))
    
    return gross_profit / gross_loss if gross_loss > 0 else 0

def win_rate_by_pattern(trades):
    """Group by pattern_type, return win rate per group"""
    closed = [t for t in trades if t.status == 'closed' and t.pattern_type]
    
    by_pattern = defaultdict(list)
    for t in closed:
        by_pattern[t.pattern_type].append(t)
    
    results = {}
    for pattern, pattern_trades in by_pattern.items():
        wins = sum(1 for t in pattern_trades if t.win)
        results[pattern] = {
            'count': len(pattern_trades),
            'win_rate': wins / len(pattern_trades) if pattern_trades else 0,
            'avg_rr': sum(t.actual_rr for t in pattern_trades if t.actual_rr) / len(pattern_trades) if pattern_trades else 0,
            'avg_pnl': sum(t.pnl_dollars for t in pattern_trades) / len(pattern_trades) if pattern_trades else 0,
            'expectancy': calculate_expectancy(pattern_trades)
        }
    
    return results

def win_rate_by_score_bracket(trades):
    """Group into score buckets, return win rate per bucket"""
    closed = [t for t in trades if t.status == 'closed' and t.scanner_score]
    
    brackets = {
        '40-50': [],
        '51-60': [],
        '61-70': [],
        '71-80': [],
        '81-100': []
    }
    
    for t in closed:
        score = t.scanner_score
        if 40 <= score <= 50:
            brackets['40-50'].append(t)
        elif 51 <= score <= 60:
            brackets['51-60'].append(t)
        elif 61 <= score <= 70:
            brackets['61-70'].append(t)
        elif 71 <= score <= 80:
            brackets['71-80'].append(t)
        elif 81 <= score <= 100:
            brackets['81-100'].append(t)
    
    results = {}
    for bracket, bracket_trades in brackets.items():
        if bracket_trades:
            wins = sum(1 for t in bracket_trades if t.win)
            results[bracket] = {
                'count': len(bracket_trades),
                'win_rate': wins / len(bracket_trades)
            }
    
    return results

def volume_confirmation_edge(trades):
    """Compare win rate: volume_confirmed=True vs False"""
    closed = [t for t in trades if t.status == 'closed']
    
    confirmed = [t for t in closed if t.volume_confirmed]
    not_confirmed = [t for t in closed if not t.volume_confirmed]
    
    confirmed_wins = sum(1 for t in confirmed if t.win)
    not_confirmed_wins = sum(1 for t in not_confirmed if t.win)
    
    return {
        'confirmed': {
            'count': len(confirmed),
            'win_rate': confirmed_wins / len(confirmed) if confirmed else 0,
            'avg_rr': sum(t.actual_rr for t in confirmed if t.actual_rr) / len(confirmed) if confirmed else 0
        },
        'not_confirmed': {
            'count': len(not_confirmed),
            'win_rate': not_confirmed_wins / len(not_confirmed) if not_confirmed else 0,
            'avg_rr': sum(t.actual_rr for t in not_confirmed if t.actual_rr) / len(not_confirmed) if not_confirmed else 0
        }
    }

def equity_curve(trades):
    """Cumulative P&L sorted by exit_date"""
    closed = [t for t in trades if t.status == 'closed' and t.exit_date and t.pnl_dollars is not None]
    closed.sort(key=lambda t: t.exit_date)
    
    cumulative = 0
    curve = []
    for t in closed:
        cumulative += t.pnl_dollars
        curve.append({
            'date': t.exit_date.isoformat(),
            'pnl': cumulative,
            'symbol': t.symbol
        })
    
    return curve

def rolling_win_rate(trades, window=10):
    """Rolling win rate over last N closed trades"""
    closed = [t for t in trades if t.status == 'closed' and t.exit_date]
    closed.sort(key=lambda t: t.exit_date)
    
    if len(closed) < window:
        return []
    
    rolling = []
    for i in range(window, len(closed) + 1):
        window_trades = closed[i-window:i]
        wins = sum(1 for t in window_trades if t.win)
        rolling.append({
            'trade_num': i,
            'win_rate': wins / window,
            'date': window_trades[-1].exit_date.isoformat()
        })
    
    return rolling

def sector_performance(trades):
    """Win rate and P&L by sector"""
    closed = [t for t in trades if t.status == 'closed' and t.sector]
    
    by_sector = defaultdict(list)
    for t in closed:
        by_sector[t.sector].append(t)
    
    results = {}
    for sector, sector_trades in by_sector.items():
        wins = sum(1 for t in sector_trades if t.win)
        results[sector] = {
            'count': len(sector_trades),
            'win_rate': wins / len(sector_trades) if sector_trades else 0,
            'total_pnl': sum(t.pnl_dollars for t in sector_trades)
        }
    
    return results

def monthly_summary(trades):
    """Monthly breakdown of trades"""
    closed = [t for t in trades if t.status == 'closed' and t.exit_date]
    
    by_month = defaultdict(list)
    for t in closed:
        month_key = t.exit_date.strftime('%Y-%m')
        by_month[month_key].append(t)
    
    results = []
    for month, month_trades in sorted(by_month.items()):
        wins = sum(1 for t in month_trades if t.win)
        losses = len(month_trades) - wins
        results.append({
            'month': month,
            'trades': len(month_trades),
            'wins': wins,
            'losses': losses,
            'win_rate': wins / len(month_trades) if month_trades else 0,
            'pnl': sum(t.pnl_dollars for t in month_trades)
        })
    
    return results
