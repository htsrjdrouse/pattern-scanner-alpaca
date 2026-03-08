"""
Backtesting engine for signal evaluation.
Computes IC, hit rate, and risk-adjusted returns.
"""
import pandas as pd
import numpy as np
from scipy.stats import pearsonr, spearmanr


def compute_forward_returns(df_prices, horizons=[1, 5, 10, 20]):
    """
    Compute forward returns for multiple horizons.
    
    Args:
        df_prices: DataFrame with [symbol, date, close]
        horizons: List of forward return periods in days
        
    Returns:
        DataFrame with [symbol, date, fwd_ret_1, fwd_ret_5, ...]
    """
    results = []
    
    for symbol in df_prices['symbol'].unique():
        df = df_prices[df_prices['symbol'] == symbol].copy()
        df = df.sort_values('date').reset_index(drop=True)
        
        for horizon in horizons:
            df[f'fwd_ret_{horizon}'] = df['close'].pct_change(horizon).shift(-horizon)
        
        results.append(df)
    
    return pd.concat(results, ignore_index=True)


def compute_ic(signal_values, forward_returns, method='pearson'):
    """
    Compute Information Coefficient (IC).
    
    Args:
        signal_values: Series of signal values
        forward_returns: Series of forward returns
        method: 'pearson' or 'spearman'
        
    Returns:
        IC value
    """
    # Remove NaN values
    mask = ~(signal_values.isna() | forward_returns.isna())
    sig = signal_values[mask]
    ret = forward_returns[mask]
    
    if len(sig) < 3:
        return np.nan
    
    if method == 'pearson':
        ic, _ = pearsonr(sig, ret)
    else:
        ic, _ = spearmanr(sig, ret)
    
    return ic


def compute_cross_sectional_ic(df_merged, signal_col, return_col, method='pearson'):
    """
    Compute cross-sectional IC per date, then average.
    Falls back to time-series IC if only one symbol.
    
    Args:
        df_merged: DataFrame with [date, signal_col, return_col]
        signal_col: Column name for signal values
        return_col: Column name for forward returns
        method: 'pearson' or 'spearman'
        
    Returns:
        dict with mean_ic, std_ic, ic_series
    """
    n_symbols = df_merged['symbol'].nunique() if 'symbol' in df_merged.columns else 1
    
    # If only one symbol, compute time-series IC instead
    if n_symbols == 1:
        ic = compute_ic(df_merged[signal_col], df_merged[return_col], method)
        return {
            'mean_ic': ic,
            'std_ic': 0.0,
            'ic_series': pd.DataFrame([{'date': df_merged['date'].iloc[0], 'ic': ic}])
        }
    
    ic_by_date = []
    
    for date in df_merged['date'].unique():
        df_date = df_merged[df_merged['date'] == date]
        
        # Need at least 3 observations for correlation
        if len(df_date) < 3:
            continue
        
        ic = compute_ic(df_date[signal_col], df_date[return_col], method)
        if not np.isnan(ic):
            ic_by_date.append({'date': date, 'ic': ic})
    
    if not ic_by_date:
        return {'mean_ic': np.nan, 'std_ic': np.nan, 'ic_series': pd.DataFrame()}
    
    ic_df = pd.DataFrame(ic_by_date)
    
    return {
        'mean_ic': ic_df['ic'].mean(),
        'std_ic': ic_df['ic'].std(),
        'ic_series': ic_df
    }


def compute_hit_rate(df_merged, signal_col, return_col):
    """
    Compute hit rate: % of times signal correctly predicts return sign.
    
    Args:
        df_merged: DataFrame with [signal_col, return_col]
        signal_col: Column name for signal values
        return_col: Column name for forward returns
        
    Returns:
        Hit rate (0-1)
    """
    mask = ~(df_merged[signal_col].isna() | df_merged[return_col].isna())
    df = df_merged[mask]
    
    if len(df) == 0:
        return np.nan
    
    correct = ((df[signal_col] > 0) & (df[return_col] > 0)) | ((df[signal_col] < 0) & (df[return_col] < 0))
    return correct.sum() / len(df)


def compute_quantile_returns(df_merged, signal_col, return_col, n_quantiles=5):
    """
    Compute returns by signal quantile.
    
    Args:
        df_merged: DataFrame with [date, signal_col, return_col]
        signal_col: Column name for signal values
        return_col: Column name for forward returns
        n_quantiles: Number of quantiles
        
    Returns:
        DataFrame with quantile returns
    """
    results = []
    
    for date in df_merged['date'].unique():
        df_date = df_merged[df_merged['date'] == date].copy()
        
        if len(df_date) < n_quantiles * 2:
            continue
        
        df_date['quantile'] = pd.qcut(df_date[signal_col], q=n_quantiles, labels=False, duplicates='drop')
        
        for q in range(n_quantiles):
            df_q = df_date[df_date['quantile'] == q]
            if len(df_q) > 0:
                results.append({
                    'date': date,
                    'quantile': q,
                    'mean_return': df_q[return_col].mean(),
                    'count': len(df_q)
                })
    
    return pd.DataFrame(results)


def compute_portfolio_metrics(df_merged, signal_col, return_col, strategy='long_only', quantile_threshold=0.8):
    """
    Compute portfolio-level metrics.
    
    Args:
        df_merged: DataFrame with [date, signal_col, return_col]
        signal_col: Column name for signal values
        return_col: Column name for forward returns
        strategy: 'long_only' (top quantile) or 'long_short' (top vs bottom)
        quantile_threshold: Threshold for top/bottom quantiles
        
    Returns:
        dict with mean_return, volatility, sharpe
    """
    portfolio_returns = []
    
    for date in df_merged['date'].unique():
        df_date = df_merged[df_merged['date'] == date].copy()
        
        if len(df_date) < 2:
            continue
        
        top_threshold = df_date[signal_col].quantile(quantile_threshold)
        
        if strategy == 'long_only':
            df_portfolio = df_date[df_date[signal_col] >= top_threshold]
            if len(df_portfolio) > 0:
                portfolio_returns.append(df_portfolio[return_col].mean())
        
        elif strategy == 'long_short':
            bottom_threshold = df_date[signal_col].quantile(1 - quantile_threshold)
            df_long = df_date[df_date[signal_col] >= top_threshold]
            df_short = df_date[df_date[signal_col] <= bottom_threshold]
            
            if len(df_long) > 0 and len(df_short) > 0:
                long_ret = df_long[return_col].mean()
                short_ret = df_short[return_col].mean()
                portfolio_returns.append(long_ret - short_ret)
    
    if not portfolio_returns:
        return {'mean_return': np.nan, 'volatility': np.nan, 'sharpe': np.nan}
    
    mean_ret = np.mean(portfolio_returns)
    vol = np.std(portfolio_returns)
    sharpe = mean_ret / vol if vol > 0 else np.nan
    
    return {
        'mean_return': mean_ret,
        'volatility': vol,
        'sharpe': sharpe,
        'n_periods': len(portfolio_returns)
    }


def run_signal_backtest(df_signals, df_prices, horizon_days=20, start_date=None, end_date=None):
    """
    Run complete backtest for a signal.
    
    Args:
        df_signals: DataFrame with [symbol, date, signal_name, signal_value]
        df_prices: DataFrame with [symbol, date, close]
        horizon_days: Forward return horizon
        start_date: Optional start date filter
        end_date: Optional end date filter
        
    Returns:
        dict with all backtest metrics
    """
    # Compute forward returns
    df_prices_fwd = compute_forward_returns(df_prices, horizons=[horizon_days])
    
    print(f"DEBUG: After forward returns: {len(df_prices_fwd)} rows")
    print(f"DEBUG: Signals: {len(df_signals)} rows")
    
    # Merge signals with forward returns
    df_merged = df_signals.merge(
        df_prices_fwd[['symbol', 'date', f'fwd_ret_{horizon_days}']],
        on=['symbol', 'date'],
        how='inner'
    )
    
    print(f"DEBUG: After merge: {len(df_merged)} rows")
    
    # Filter dates (handle timezone-aware dates)
    if start_date:
        start_dt = pd.to_datetime(start_date)
        if df_merged['date'].dt.tz is not None:
            start_dt = start_dt.tz_localize(df_merged['date'].dt.tz)
        df_merged = df_merged[df_merged['date'] >= start_dt]
        print(f"DEBUG: After start_date filter: {len(df_merged)} rows")
    if end_date:
        end_dt = pd.to_datetime(end_date)
        if df_merged['date'].dt.tz is not None:
            end_dt = end_dt.tz_localize(df_merged['date'].dt.tz)
        df_merged = df_merged[df_merged['date'] <= end_dt]
        print(f"DEBUG: After end_date filter: {len(df_merged)} rows")
    
    # Drop rows with NaN forward returns
    df_merged = df_merged.dropna(subset=[f'fwd_ret_{horizon_days}'])
    print(f"DEBUG: After dropping NaN: {len(df_merged)} rows")
    
    if len(df_merged) < 10:
        return {
            'error': 'Insufficient data for backtest',
            'details': f'Only {len(df_merged)} observations after merging signals and returns. Need at least 10.',
            'suggestions': [
                'Try a longer date range',
                'Use more symbols',
                'Check if symbols have data in the date range'
            ]
        }
    
    signal_col = 'signal_value'
    return_col = f'fwd_ret_{horizon_days}'
    
    # Debug: check data quality
    print(f"DEBUG: Signal values - min: {df_merged[signal_col].min()}, max: {df_merged[signal_col].max()}, nulls: {df_merged[signal_col].isna().sum()}")
    print(f"DEBUG: Return values - min: {df_merged[return_col].min()}, max: {df_merged[return_col].max()}, nulls: {df_merged[return_col].isna().sum()}")
    print(f"DEBUG: Unique dates: {df_merged['date'].nunique()}, Symbols per date (avg): {df_merged.groupby('date')['symbol'].count().mean():.1f}")
    
    # Compute metrics
    ic_pearson = compute_cross_sectional_ic(df_merged, signal_col, return_col, method='pearson')
    ic_spearman = compute_cross_sectional_ic(df_merged, signal_col, return_col, method='spearman')
    
    print(f"DEBUG: IC Pearson: {ic_pearson['mean_ic']}, IC Spearman: {ic_spearman['mean_ic']}")
    
    hit_rate = compute_hit_rate(df_merged, signal_col, return_col)
    
    long_only = compute_portfolio_metrics(df_merged, signal_col, return_col, strategy='long_only')
    long_short = compute_portfolio_metrics(df_merged, signal_col, return_col, strategy='long_short')
    
    quantile_rets = compute_quantile_returns(df_merged, signal_col, return_col)
    
    return {
        'signal_name': df_signals['signal_name'].iloc[0] if len(df_signals) > 0 else 'unknown',
        'horizon_days': horizon_days,
        'n_observations': len(df_merged),
        'date_range': (df_merged['date'].min(), df_merged['date'].max()),
        'ic_pearson_mean': ic_pearson['mean_ic'],
        'ic_pearson_std': ic_pearson['std_ic'],
        'ic_spearman_mean': ic_spearman['mean_ic'],
        'ic_spearman_std': ic_spearman['std_ic'],
        'hit_rate': hit_rate,
        'long_only_return': long_only['mean_return'],
        'long_only_volatility': long_only['volatility'],
        'long_only_sharpe': long_only['sharpe'],
        'long_short_return': long_short['mean_return'],
        'long_short_volatility': long_short['volatility'],
        'long_short_sharpe': long_short['sharpe'],
        'ic_series': ic_pearson['ic_series'],
        'quantile_returns': quantile_rets
    }


def run_decay_analysis(df_signals, df_prices, horizons=[1, 2, 5, 10, 20, 60], start_date=None, end_date=None):
    """
    Run backtest across multiple horizons to analyze signal decay.
    
    Args:
        df_signals: DataFrame with [symbol, date, signal_name, signal_value]
        df_prices: DataFrame with [symbol, date, close]
        horizons: List of forward return horizons
        start_date: Optional start date filter
        end_date: Optional end date filter
        
    Returns:
        DataFrame with decay curve: [horizon, ic_mean, hit_rate, sharpe]
    """
    results = []
    
    for horizon in horizons:
        metrics = run_signal_backtest(df_signals, df_prices, horizon, start_date, end_date)
        
        if 'error' not in metrics:
            results.append({
                'horizon': horizon,
                'ic_pearson': metrics['ic_pearson_mean'],
                'ic_spearman': metrics['ic_spearman_mean'],
                'hit_rate': metrics['hit_rate'],
                'long_only_sharpe': metrics['long_only_sharpe'],
                'long_short_sharpe': metrics['long_short_sharpe']
            })
    
    return pd.DataFrame(results)
