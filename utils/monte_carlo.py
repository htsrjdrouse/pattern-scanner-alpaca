import numpy as np
from datetime import date

_cache = {}

def run_monte_carlo(ticker, num_trials=5000):
    cache_key = (ticker.upper(), str(date.today()))
    if cache_key in _cache:
        return _cache[cache_key]

    import yfinance as yf

    t = yf.Ticker(ticker)
    info = t.info
    current_price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose')
    if not current_price:
        return {'error': 'Current price unavailable'}

    fin = t.financials  # annual
    bs = t.balance_sheet
    cf = t.cashflow

    if fin is None or fin.empty or len(fin.columns) < 2:
        return {'error': 'Insufficient data'}

    # Extract annual data (columns are dates, most recent first)
    def get_row(df, key, fallback=None):
        if df is None or df.empty:
            return []
        for k in ([key] + ([fallback] if fallback else [])):
            if k in df.index:
                vals = df.loc[k].dropna().values
                return [float(v) for v in vals]
        return []

    revenues = get_row(fin, 'Total Revenue')
    fcfs = get_row(cf, 'Free Cash Flow')
    shares_out = info.get('sharesOutstanding')
    total_debt = get_row(bs, 'Total Debt', 'Long Term Debt')
    cash = get_row(bs, 'Cash And Cash Equivalents', 'Cash')

    if len(revenues) < 2 or not shares_out:
        return {'error': 'Insufficient data'}

    # Revenue growth rates (most recent first, so reverse for chronological)
    revs = list(reversed(revenues))
    growth_rates = [(revs[i] - revs[i-1]) / abs(revs[i-1]) for i in range(1, len(revs)) if revs[i-1] != 0]

    # FCF margins
    fcf_list = list(reversed(fcfs))
    rev_for_margin = revs[:len(fcf_list)]
    fcf_margins = [fcf_list[i] / rev_for_margin[i] for i in range(len(fcf_list)) if rev_for_margin[i] != 0]

    if not growth_rates or not fcf_margins:
        return {'error': 'Insufficient data'}

    growth_mean, growth_std = np.mean(growth_rates), max(np.std(growth_rates), 0.02)
    fcf_margin_mean, fcf_margin_std = np.mean(fcf_margins), max(np.std(fcf_margins), 0.01)

    latest_revenue = revs[-1]
    net_cash = (cash[0] if cash else 0) - (total_debt[0] if total_debt else 0)

    # Run simulations
    rng = np.random.default_rng()
    simulated_values = np.empty(num_trials)

    for i in range(num_trials):
        rev_growth = np.clip(rng.normal(growth_mean, growth_std), -0.5, 1.0)
        fcf_margin = np.clip(rng.normal(fcf_margin_mean, fcf_margin_std), -0.3, 0.5)
        terminal_growth = rng.uniform(0.01, 0.04)
        wacc = np.clip(rng.normal(0.10, 0.02), 0.06, 0.20)

        # Project 5-year FCF
        rev = latest_revenue
        pv_fcf = 0.0
        for yr in range(1, 6):
            rev *= (1 + rev_growth)
            fcf = rev * fcf_margin
            pv_fcf += fcf / (1 + wacc) ** yr

        # Terminal value
        terminal_fcf = rev * (1 + rev_growth) * fcf_margin
        if wacc > terminal_growth:
            tv = terminal_fcf * (1 + terminal_growth) / (wacc - terminal_growth)
            pv_tv = tv / (1 + wacc) ** 5
        else:
            pv_tv = 0

        equity_value = pv_fcf + pv_tv + net_cash
        intrinsic = equity_value / shares_out
        simulated_values[i] = intrinsic

    # Percentiles
    p10, p25, p50, p75, p90 = np.percentile(simulated_values, [10, 25, 50, 75, 90])
    current_price_percentile = float(np.sum(simulated_values <= current_price) / num_trials * 100)
    margin_of_safety = (p50 - current_price) / p50 * 100 if p50 != 0 else 0

    result = {
        'ticker': ticker.upper(),
        'simulated_values': simulated_values.tolist(),
        'percentiles': {
            'P10': round(float(p10), 2),
            'P25': round(float(p25), 2),
            'P50': round(float(p50), 2),
            'P75': round(float(p75), 2),
            'P90': round(float(p90), 2),
        },
        'current_price': round(float(current_price), 2),
        'current_price_percentile': round(current_price_percentile, 1),
        'margin_of_safety_p50': round(float(margin_of_safety), 1),
    }

    _cache[cache_key] = result
    return result
