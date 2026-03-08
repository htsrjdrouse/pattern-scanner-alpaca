import yfinance as yf
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from scipy.signal import argrelextrema
from scipy.stats import linregress
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

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

        return {
            'status': 'success',
            'scenarios': results,
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

print(calculate_dcf_value('ALAB'))