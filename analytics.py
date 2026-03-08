"""
Analytics for signal correlation, combination, and regime detection.
"""
import pandas as pd
import numpy as np
from scipy.stats import zscore


def signal_correlation_matrix(df_signals, method='pearson'):
    """
    Compute cross-sectional correlation matrix of signals.
    
    Args:
        df_signals: DataFrame with [symbol, date, signal_name, signal_value]
        method: 'pearson' or 'spearman'
        
    Returns:
        Correlation matrix DataFrame
    """
    # Pivot to wide format: rows=symbol+date, cols=signal_name
    df_wide = df_signals.pivot_table(
        index=['symbol', 'date'],
        columns='signal_name',
        values='signal_value'
    )
    
    if method == 'pearson':
        corr = df_wide.corr()
    else:
        corr = df_wide.corr(method='spearman')
    
    return corr


def ic_time_series_correlation(ic_series_dict):
    """
    Compute correlation of IC time series across signals.
    
    Args:
        ic_series_dict: Dict of {signal_name: ic_series_df}
        
    Returns:
        Correlation matrix of IC time series
    """
    # Merge all IC series
    df_merged = None
    
    for signal_name, ic_df in ic_series_dict.items():
        ic_df = ic_df.copy()
        ic_df = ic_df.rename(columns={'ic': signal_name})
        
        if df_merged is None:
            df_merged = ic_df[['date', signal_name]]
        else:
            df_merged = df_merged.merge(ic_df[['date', signal_name]], on='date', how='outer')
    
    df_merged = df_merged.set_index('date')
    return df_merged.corr()


def standardize_signals(df_signals):
    """
    Z-score standardize signals cross-sectionally per date.
    
    Args:
        df_signals: DataFrame with [symbol, date, signal_name, signal_value]
        
    Returns:
        DataFrame with additional column 'signal_value_z'
    """
    df = df_signals.copy()
    
    # Group by date and signal_name, compute z-score
    df['signal_value_z'] = df.groupby(['date', 'signal_name'])['signal_value'].transform(
        lambda x: zscore(x, nan_policy='omit') if len(x.dropna()) > 1 else 0
    )
    
    return df


def build_composite_signal(df_signals, signal_weights=None, start_date=None, end_date=None):
    """
    Build composite signal from multiple signals.
    
    Args:
        df_signals: DataFrame with [symbol, date, signal_name, signal_value]
        signal_weights: Dict of {signal_name: weight}. If None, equal weights.
        start_date: Optional training start date
        end_date: Optional training end date
        
    Returns:
        DataFrame with [symbol, date, signal_name='composite', signal_value]
    """
    # Filter dates
    df = df_signals.copy()
    if start_date:
        df = df[df['date'] >= pd.to_datetime(start_date)]
    if end_date:
        df = df[df['date'] <= pd.to_datetime(end_date)]
    
    # Standardize signals
    df = standardize_signals(df)
    
    # Apply weights
    if signal_weights is None:
        # Equal weights
        signal_names = df['signal_name'].unique()
        signal_weights = {name: 1.0 / len(signal_names) for name in signal_names}
    
    df['weighted_signal'] = df.apply(
        lambda row: row['signal_value_z'] * signal_weights.get(row['signal_name'], 0),
        axis=1
    )
    
    # Aggregate by symbol, date
    composite = df.groupby(['symbol', 'date'])['weighted_signal'].sum().reset_index()
    composite['signal_name'] = 'composite'
    composite = composite.rename(columns={'weighted_signal': 'signal_value'})
    
    return composite[['symbol', 'date', 'signal_name', 'signal_value']]


def compute_ic_weights(ic_dict, correlation_matrix, correlation_penalty=0.5):
    """
    Compute signal weights based on IC and correlation.
    
    Args:
        ic_dict: Dict of {signal_name: mean_ic}
        correlation_matrix: Signal correlation matrix
        correlation_penalty: Penalty factor for correlated signals (0-1)
        
    Returns:
        Dict of {signal_name: weight}
    """
    signal_names = list(ic_dict.keys())
    
    # Start with IC-based weights
    ic_values = np.array([ic_dict[name] for name in signal_names])
    ic_values = np.maximum(ic_values, 0)  # Only positive ICs
    
    if ic_values.sum() == 0:
        # Equal weights if no positive ICs
        return {name: 1.0 / len(signal_names) for name in signal_names}
    
    weights = ic_values / ic_values.sum()
    
    # Apply correlation penalty
    for i, name_i in enumerate(signal_names):
        penalty = 0
        for j, name_j in enumerate(signal_names):
            if i != j and name_i in correlation_matrix.index and name_j in correlation_matrix.columns:
                corr = abs(correlation_matrix.loc[name_i, name_j])
                penalty += corr * weights[j]
        
        weights[i] *= (1 - correlation_penalty * penalty)
    
    # Renormalize
    weights = weights / weights.sum()
    
    return {name: weight for name, weight in zip(signal_names, weights)}


def detect_market_regime(df_prices, index_symbol='SPY', lookback=60):
    """
    Detect market regime: trending, mean-reverting, or volatile.
    
    Args:
        df_prices: DataFrame with [symbol, date, close]
        index_symbol: Symbol to use for regime detection
        lookback: Lookback window for regime calculation
        
    Returns:
        DataFrame with [date, regime, trend_strength, volatility]
    """
    df = df_prices[df_prices['symbol'] == index_symbol].copy()
    df = df.sort_values('date').reset_index(drop=True)
    
    if len(df) < lookback + 1:
        return pd.DataFrame()
    
    # Compute rolling metrics
    df['returns'] = df['close'].pct_change()
    df['rolling_mean'] = df['returns'].rolling(lookback).mean()
    df['rolling_std'] = df['returns'].rolling(lookback).std()
    df['rolling_sharpe'] = df['rolling_mean'] / df['rolling_std']
    
    # Trend strength: absolute value of rolling return
    df['trend_strength'] = df['close'].pct_change(lookback).abs()
    
    # Volatility: rolling std
    df['volatility'] = df['rolling_std']
    
    # Classify regime
    def classify_regime(row):
        if pd.isna(row['trend_strength']) or pd.isna(row['volatility']):
            return 'unknown'
        
        if row['volatility'] > df['volatility'].quantile(0.75):
            return 'volatile'
        elif row['trend_strength'] > df['trend_strength'].quantile(0.6):
            return 'trending'
        else:
            return 'mean_reverting'
    
    df['regime'] = df.apply(classify_regime, axis=1)
    
    return df[['date', 'regime', 'trend_strength', 'volatility']]


def compute_regime_conditional_ic(df_signals, df_prices, df_regimes, horizon_days=20):
    """
    Compute IC conditional on market regime.
    
    Args:
        df_signals: DataFrame with [symbol, date, signal_name, signal_value]
        df_prices: DataFrame with [symbol, date, close]
        df_regimes: DataFrame with [date, regime]
        horizon_days: Forward return horizon
        
    Returns:
        DataFrame with [signal_name, regime, ic_mean, n_observations]
    """
    from backtest import compute_forward_returns, compute_cross_sectional_ic
    
    # Compute forward returns
    df_prices_fwd = compute_forward_returns(df_prices, horizons=[horizon_days])
    
    # Merge signals with forward returns and regimes
    df_merged = df_signals.merge(
        df_prices_fwd[['symbol', 'date', f'fwd_ret_{horizon_days}']],
        on=['symbol', 'date'],
        how='inner'
    )
    df_merged = df_merged.merge(df_regimes[['date', 'regime']], on='date', how='inner')
    
    results = []
    
    for signal_name in df_merged['signal_name'].unique():
        df_signal = df_merged[df_merged['signal_name'] == signal_name]
        
        for regime in df_signal['regime'].unique():
            df_regime = df_signal[df_signal['regime'] == regime]
            
            if len(df_regime) < 10:
                continue
            
            ic_stats = compute_cross_sectional_ic(
                df_regime,
                'signal_value',
                f'fwd_ret_{horizon_days}'
            )
            
            results.append({
                'signal_name': signal_name,
                'regime': regime,
                'ic_mean': ic_stats['mean_ic'],
                'ic_std': ic_stats['std_ic'],
                'n_observations': len(df_regime)
            })
    
    return pd.DataFrame(results)


def analyze_turnover(df_signals, rebalance_freq=20, top_pct=0.2):
    """
    Analyze portfolio turnover for a signal.
    
    Args:
        df_signals: DataFrame with [symbol, date, signal_name, signal_value]
        rebalance_freq: Rebalancing frequency in days
        top_pct: Percentage of top stocks to hold
        
    Returns:
        dict with turnover metrics
    """
    df = df_signals.copy()
    df = df.sort_values(['date', 'signal_value'], ascending=[True, False])
    
    dates = sorted(df['date'].unique())
    rebalance_dates = dates[::rebalance_freq]
    
    turnovers = []
    prev_portfolio = set()
    
    for date in rebalance_dates:
        df_date = df[df['date'] == date]
        n_stocks = max(1, int(len(df_date) * top_pct))
        current_portfolio = set(df_date.head(n_stocks)['symbol'])
        
        if prev_portfolio:
            # Turnover = fraction of portfolio changed
            added = current_portfolio - prev_portfolio
            removed = prev_portfolio - current_portfolio
            turnover = (len(added) + len(removed)) / (2 * len(prev_portfolio))
            turnovers.append(turnover)
        
        prev_portfolio = current_portfolio
    
    if not turnovers:
        return {'mean_turnover': np.nan, 'std_turnover': np.nan}
    
    return {
        'mean_turnover': np.mean(turnovers),
        'std_turnover': np.std(turnovers),
        'n_rebalances': len(turnovers)
    }


def apply_transaction_costs(portfolio_returns, turnover, cost_bps=10):
    """
    Apply transaction costs to portfolio returns.
    
    Args:
        portfolio_returns: Series of portfolio returns
        turnover: Turnover rate per period
        cost_bps: Transaction cost in basis points
        
    Returns:
        Series of net returns after costs
    """
    cost_per_period = turnover * (cost_bps / 10000)
    net_returns = portfolio_returns - cost_per_period
    return net_returns
