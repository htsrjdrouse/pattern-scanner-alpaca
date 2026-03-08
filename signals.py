"""
Signal abstraction for alpha research platform.
Each signal produces standardized output: symbol, date, signal_name, signal_value.
"""
from abc import ABC, abstractmethod
import pandas as pd
import numpy as np
import pandas_ta as ta
from scipy.signal import argrelextrema
from scipy.stats import linregress


class Signal(ABC):
    """Base class for all trading signals."""
    
    def __init__(self, name, description, lookback_window=252, holding_period=20):
        self.name = name
        self.description = description
        self.lookback_window = lookback_window
        self.holding_period = holding_period
    
    @abstractmethod
    def compute(self, df_prices, df_fundamentals=None, df_alt=None):
        """
        Compute signal values.
        
        Args:
            df_prices: DataFrame with columns [symbol, date, open, high, low, close, volume]
            df_fundamentals: Optional DataFrame with fundamental data
            df_alt: Optional DataFrame with alternative data
            
        Returns:
            DataFrame with columns [symbol, date, signal_name, signal_value]
        """
        pass
    
    def metadata(self):
        return {
            'name': self.name,
            'description': self.description,
            'lookback_window': self.lookback_window,
            'holding_period': self.holding_period
        }


# ═══════════════════════════════════════════════════════════════
# PATTERN SIGNALS
# ═══════════════════════════════════════════════════════════════

class CupAndHandleSignal(Signal):
    def __init__(self):
        super().__init__('cup_handle', 'Cup & Handle pattern strength', lookback_window=130, holding_period=20)
    
    def compute(self, df_prices, df_fundamentals=None, df_alt=None):
        results = []
        for symbol in df_prices['symbol'].unique():
            df = df_prices[df_prices['symbol'] == symbol].copy()
            df = df.sort_values('date').reset_index(drop=True)
            
            if len(df) < 60:
                continue
            
            # Compute signal for each date with sufficient history
            for i in range(60, len(df)):
                window = df.iloc[:i+1]
                
                # Use last 130 days or available data
                lookback = min(130, len(window))
                recent = window.iloc[-lookback:]
                
                # Find cup low
                cup_low_idx = recent['low'].idxmin()
                cup_low = recent.loc[cup_low_idx, 'low']
                
                # Cup depth
                left_high = recent['high'].iloc[:lookback//2].max()
                right_high = recent['high'].iloc[-20:].max()
                depth = (left_high - cup_low) / left_high if left_high > 0 else 0
                
                # Handle: recent pullback
                handle_start_idx = recent['high'].iloc[-20:].idxmax()
                handle_low = recent['low'].iloc[handle_start_idx:].min() if handle_start_idx < len(recent) else cup_low
                handle_depth = (recent.loc[handle_start_idx, 'high'] - handle_low) / recent.loc[handle_start_idx, 'high'] if recent.loc[handle_start_idx, 'high'] > 0 else 0
                
                # Score
                score = 0
                if 0.12 <= depth <= 0.33:
                    score += 50
                if handle_depth < 0.15:
                    score += 30
                if len(recent) >= 30 and recent['volume'].iloc[-5:].mean() > recent['volume'].iloc[-30:-5].mean():
                    score += 20
                
                results.append({
                    'symbol': symbol,
                    'date': window['date'].iloc[-1],
                    'signal_name': self.name,
                    'signal_value': score
                })
        
        return pd.DataFrame(results)


class AscendingTriangleSignal(Signal):
    def __init__(self):
        super().__init__('asc_triangle', 'Ascending triangle pattern strength', lookback_window=60, holding_period=15)
    
    def compute(self, df_prices, df_fundamentals=None, df_alt=None):
        results = []
        for symbol in df_prices['symbol'].unique():
            df = df_prices[df_prices['symbol'] == symbol].copy()
            df = df.sort_values('date').reset_index(drop=True)
            
            if len(df) < 40:
                continue
            
            for i in range(40, len(df)):
                window = df.iloc[:i+1]
                lookback = min(60, len(window))
                recent = window.iloc[-lookback:]
                
                highs = recent['high'].values
                lows = recent['low'].values
                
                # Flat resistance
                resistance = highs.max()
                resistance_std = highs[-20:].std() / resistance if resistance > 0 else 1
                
                # Rising support
                x = np.arange(len(lows))
                slope, _, r_val, _, _ = linregress(x, lows)
                
                score = 0
                if resistance_std < 0.02:
                    score += 40
                if slope > 0 and r_val**2 > 0.5:
                    score += 40
                if len(recent) >= 30 and recent['volume'].iloc[-5:].mean() > recent['volume'].iloc[-30:-5].mean():
                    score += 20
                
                results.append({
                    'symbol': symbol,
                    'date': window['date'].iloc[-1],
                    'signal_name': self.name,
                    'signal_value': score
                })
        
        return pd.DataFrame(results)


class BullFlagSignal(Signal):
    def __init__(self):
        super().__init__('bull_flag', 'Bull flag pattern strength', lookback_window=40, holding_period=10)
    
    def compute(self, df_prices, df_fundamentals=None, df_alt=None):
        results = []
        for symbol in df_prices['symbol'].unique():
            df = df_prices[df_prices['symbol'] == symbol].copy()
            df = df.sort_values('date').reset_index(drop=True)
            
            if len(df) < 35:
                continue
            
            for i in range(35, len(df)):
                window = df.iloc[:i+1]
                
                # Pole: strong move up
                pole_start = max(0, len(window) - 30)
                pole_end = max(0, len(window) - 10)
                pole_gain = (window['close'].iloc[pole_end] - window['close'].iloc[pole_start]) / window['close'].iloc[pole_start] if window['close'].iloc[pole_start] > 0 else 0
                
                # Flag: consolidation
                flag_prices = window['close'].iloc[-10:].values
                x = np.arange(len(flag_prices))
                slope, _, _, _, _ = linregress(x, flag_prices)
                flag_drift = slope / window['close'].iloc[-10] if window['close'].iloc[-10] > 0 else 0
                
                score = 0
                if pole_gain > 0.15:
                    score += 50
                if -0.02 < flag_drift < 0.005:
                    score += 30
                if len(window) >= 30 and window['volume'].iloc[-10:].mean() < window['volume'].iloc[-30:-10].mean():
                    score += 20
                
                results.append({
                    'symbol': symbol,
                    'date': window['date'].iloc[-1],
                    'signal_name': self.name,
                    'signal_value': score
                })
        
        return pd.DataFrame(results)


class DoubleBottomSignal(Signal):
    def __init__(self):
        super().__init__('double_bottom', 'Double bottom pattern strength', lookback_window=90, holding_period=20)
    
    def compute(self, df_prices, df_fundamentals=None, df_alt=None):
        results = []
        for symbol in df_prices['symbol'].unique():
            df = df_prices[df_prices['symbol'] == symbol].copy()
            df = df.sort_values('date').reset_index(drop=True)
            
            if len(df) < 50:
                continue
            
            for i in range(50, len(df)):
                window = df.iloc[:i+1]
                lookback = min(90, len(window))
                recent = window.iloc[-lookback:]
                
                lows = recent['low'].values
                
                # Find two lowest points
                local_min_idx = argrelextrema(lows, np.less, order=5)[0]
                if len(local_min_idx) < 2:
                    results.append({'symbol': symbol, 'date': window['date'].iloc[-1], 'signal_name': self.name, 'signal_value': 0})
                    continue
                
                sorted_mins = sorted([(idx, lows[idx]) for idx in local_min_idx], key=lambda x: x[1])
                bottom1_idx, bottom1_val = sorted_mins[0]
                bottom2_idx, bottom2_val = sorted_mins[1]
                
                # Check similarity
                similarity = abs(bottom1_val - bottom2_val) / bottom1_val if bottom1_val > 0 else 1
                gap = abs(bottom2_idx - bottom1_idx)
                
                score = 0
                if similarity < 0.03:
                    score += 50
                if 15 <= gap <= 60:
                    score += 30
                if len(recent) >= 30 and recent['volume'].iloc[-5:].mean() > recent['volume'].iloc[-30:-5].mean():
                    score += 20
                
                results.append({
                    'symbol': symbol,
                    'date': window['date'].iloc[-1],
                    'signal_name': self.name,
                    'signal_value': score
                })
        
        return pd.DataFrame(results)


# ═══════════════════════════════════════════════════════════════
# TECHNICAL INDICATOR SIGNALS
# ═══════════════════════════════════════════════════════════════

class RSISignal(Signal):
    def __init__(self, period=14):
        super().__init__(f'rsi_{period}', f'RSI {period} oversold/overbought', lookback_window=period*3, holding_period=5)
        self.period = period
    
    def compute(self, df_prices, df_fundamentals=None, df_alt=None):
        results = []
        for symbol in df_prices['symbol'].unique():
            df = df_prices[df_prices['symbol'] == symbol].copy()
            df = df.sort_values('date').reset_index(drop=True)
            
            if len(df) < self.period + 1:
                continue
            
            rsi = ta.rsi(df['close'], length=self.period)
            if rsi is None or len(rsi) == 0:
                continue
            
            # Return signal for ALL dates, not just the last one
            for i in range(len(df)):
                if pd.notna(rsi.iloc[i]):
                    results.append({
                        'symbol': symbol,
                        'date': df['date'].iloc[i],
                        'signal_name': self.name,
                        'signal_value': 50 - rsi.iloc[i]
                    })
        
        return pd.DataFrame(results)


class MACDSignal(Signal):
    def __init__(self):
        super().__init__('macd', 'MACD histogram momentum', lookback_window=60, holding_period=10)
    
    def compute(self, df_prices, df_fundamentals=None, df_alt=None):
        results = []
        for symbol in df_prices['symbol'].unique():
            df = df_prices[df_prices['symbol'] == symbol].copy()
            df = df.sort_values('date').reset_index(drop=True)
            
            if len(df) < 35:
                continue
            
            macd = ta.macd(df['close'])
            if macd is None or macd.empty:
                continue
            
            for i in range(len(df)):
                if pd.notna(macd['MACDh_12_26_9'].iloc[i]):
                    results.append({
                        'symbol': symbol,
                        'date': df['date'].iloc[i],
                        'signal_name': self.name,
                        'signal_value': macd['MACDh_12_26_9'].iloc[i] * 100
                    })
        
        return pd.DataFrame(results)


class ADXSignal(Signal):
    def __init__(self, period=14):
        super().__init__(f'adx_{period}', f'ADX {period} trend strength', lookback_window=period*3, holding_period=10)
        self.period = period
    
    def compute(self, df_prices, df_fundamentals=None, df_alt=None):
        results = []
        for symbol in df_prices['symbol'].unique():
            df = df_prices[df_prices['symbol'] == symbol].copy()
            df = df.sort_values('date').reset_index(drop=True)
            
            if len(df) < self.period * 2:
                continue
            
            adx = ta.adx(df['high'], df['low'], df['close'], length=self.period)
            if adx is None or adx.empty:
                continue
            
            for i in range(len(df)):
                if pd.notna(adx[f'ADX_{self.period}'].iloc[i]):
                    results.append({
                        'symbol': symbol,
                        'date': df['date'].iloc[i],
                        'signal_name': self.name,
                        'signal_value': adx[f'ADX_{self.period}'].iloc[i] - 25
                    })
        
        return pd.DataFrame(results)


class VolumeSignal(Signal):
    def __init__(self, lookback=20):
        super().__init__(f'volume_surge_{lookback}', f'Volume surge vs {lookback}d avg', lookback_window=lookback*2, holding_period=5)
        self.lookback = lookback
    
    def compute(self, df_prices, df_fundamentals=None, df_alt=None):
        results = []
        for symbol in df_prices['symbol'].unique():
            df = df_prices[df_prices['symbol'] == symbol].copy()
            df = df.sort_values('date').reset_index(drop=True)
            
            if len(df) < self.lookback + 5:
                continue
            
            for i in range(self.lookback + 5, len(df)):
                recent_vol = df['volume'].iloc[i-5:i].mean()
                avg_vol = df['volume'].iloc[i-self.lookback-5:i-5].mean()
                
                if avg_vol > 0:
                    signal_value = (recent_vol / avg_vol - 1) * 100
                else:
                    signal_value = 0
                
                results.append({
                    'symbol': symbol,
                    'date': df['date'].iloc[i],
                    'signal_name': self.name,
                    'signal_value': signal_value
                })
        
        return pd.DataFrame(results)


class CTOLarssonSignal(Signal):
    def __init__(self):
        super().__init__('cto_larsson', 'CTO Larsson line momentum', lookback_window=60, holding_period=10)
    
    def compute(self, df_prices, df_fundamentals=None, df_alt=None):
        results = []
        for symbol in df_prices['symbol'].unique():
            df = df_prices[df_prices['symbol'] == symbol].copy()
            df = df.sort_values('date').reset_index(drop=True)
            
            if len(df) < 30:
                continue
            
            hl_avg = (df['high'] + df['low']) / 2
            ema15 = hl_avg.ewm(span=15, adjust=False).mean()
            ema29 = hl_avg.ewm(span=29, adjust=False).mean()
            
            for i in range(29, len(df)):
                if ema29.iloc[i] > 0:
                    signal_value = (ema15.iloc[i] - ema29.iloc[i]) / ema29.iloc[i] * 100
                else:
                    signal_value = 0
                
                results.append({
                    'symbol': symbol,
                    'date': df['date'].iloc[i],
                    'signal_name': self.name,
                    'signal_value': signal_value
                })
        
        return pd.DataFrame(results)


class MovingAverageCrossSignal(Signal):
    def __init__(self, fast=50, slow=200):
        super().__init__(f'ma_cross_{fast}_{slow}', f'SMA {fast}/{slow} cross', lookback_window=slow+20, holding_period=20)
        self.fast = fast
        self.slow = slow
    
    def compute(self, df_prices, df_fundamentals=None, df_alt=None):
        results = []
        for symbol in df_prices['symbol'].unique():
            df = df_prices[df_prices['symbol'] == symbol].copy()
            df = df.sort_values('date').reset_index(drop=True)
            
            if len(df) < self.slow + 1:
                continue
            
            sma_fast = df['close'].rolling(window=self.fast).mean()
            sma_slow = df['close'].rolling(window=self.slow).mean()
            
            for i in range(self.slow, len(df)):
                if sma_slow.iloc[i] > 0:
                    signal_value = (sma_fast.iloc[i] - sma_slow.iloc[i]) / sma_slow.iloc[i] * 100
                else:
                    signal_value = 0
                
                results.append({
                    'symbol': symbol,
                    'date': df['date'].iloc[i],
                    'signal_name': self.name,
                    'signal_value': signal_value
                })
        
        return pd.DataFrame(results)


class MomentumSignal(Signal):
    def __init__(self, period=20):
        super().__init__(f'momentum_{period}', f'{period}d price momentum', lookback_window=period*2, holding_period=10)
        self.period = period
    
    def compute(self, df_prices, df_fundamentals=None, df_alt=None):
        results = []
        for symbol in df_prices['symbol'].unique():
            df = df_prices[df_prices['symbol'] == symbol].copy()
            df = df.sort_values('date').reset_index(drop=True)
            
            if len(df) < self.period + 1:
                continue
            
            for i in range(self.period, len(df)):
                if df['close'].iloc[i - self.period] > 0:
                    momentum = (df['close'].iloc[i] - df['close'].iloc[i - self.period]) / df['close'].iloc[i - self.period] * 100
                else:
                    momentum = 0
                
                results.append({
                    'symbol': symbol,
                    'date': df['date'].iloc[i],
                    'signal_name': self.name,
                    'signal_value': momentum
                })
        
        return pd.DataFrame(results)


# ═══════════════════════════════════════════════════════════════
# SIGNAL REGISTRY
# ═══════════════════════════════════════════════════════════════

SIGNAL_REGISTRY = {
    'rsi_14': RSISignal(14),
    'macd': MACDSignal(),
    'adx_14': ADXSignal(14),
    'volume_surge_20': VolumeSignal(20),
    'cto_larsson': CTOLarssonSignal(),
    'ma_cross_50_200': MovingAverageCrossSignal(50, 200),
    'momentum_20': MomentumSignal(20),
    'cup_handle': CupAndHandleSignal(),
    'asc_triangle': AscendingTriangleSignal(),
    'bull_flag': BullFlagSignal(),
    'double_bottom': DoubleBottomSignal(),
}


def get_signal(signal_name):
    """Get signal instance by name."""
    return SIGNAL_REGISTRY.get(signal_name)


def list_signals():
    """List all available signals with metadata."""
    return {name: sig.metadata() for name, sig in SIGNAL_REGISTRY.items()}
