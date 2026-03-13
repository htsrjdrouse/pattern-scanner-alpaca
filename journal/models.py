"""
Trade Journal Database Models
"""
from datetime import datetime, date, timedelta
import pandas as pd
import pandas_ta as ta
import json
import os
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, Date, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from alpaca_data import fetch_stock_data

Base = declarative_base()

BACKUP_FILE = 'data/trade_journal_backup.json'

def backup_to_json(session):
    """Backup all trades to JSON file"""
    try:
        from journal.models import Trade
        trades = session.query(Trade).all()
        
        backup_data = []
        for t in trades:
            backup_data.append({
                'id': t.id,
                'trade_type': t.trade_type,
                'symbol': t.symbol,
                'entry_date': t.entry_date.isoformat() if t.entry_date else None,
                'entry_time': t.entry_time,
                'entry_price': t.entry_price,
                'shares': t.shares,
                'planned_entry': t.planned_entry,
                'pattern_type': t.pattern_type,
                'scanner_score': t.scanner_score,
                'planned_stop': t.planned_stop,
                'planned_target': t.planned_target,
                'planned_rr': t.planned_rr,
                'volume_confirmed': t.volume_confirmed,
                'golden_cross': t.golden_cross,
                'adx_at_entry': t.adx_at_entry,
                'rsi_at_entry': t.rsi_at_entry,
                'sector': t.sector,
                'option_strategy': t.option_strategy,
                'option_expiration': t.option_expiration.isoformat() if t.option_expiration else None,
                'option_strike': t.option_strike,
                'option_strike_2': t.option_strike_2,
                'option_type': t.option_type,
                'option_dte': t.option_dte,
                'option_iv': t.option_iv,
                'option_delta': t.option_delta,
                'exit_date': t.exit_date.isoformat() if t.exit_date else None,
                'exit_time': t.exit_time,
                'exit_price': t.exit_price,
                'exit_reason': t.exit_reason,
                'status': t.status,
                'actual_rr': t.actual_rr,
                'pnl_dollars': t.pnl_dollars,
                'pnl_percent': t.pnl_percent,
                'days_held': t.days_held,
                'win': t.win,
                'notes': t.notes
            })
        
        os.makedirs('data', exist_ok=True)
        with open(BACKUP_FILE, 'w') as f:
            json.dump(backup_data, f, indent=2)
        
        print(f"✅ Backed up {len(backup_data)} trades to {BACKUP_FILE}")
    except Exception as e:
        print(f"⚠️ Backup failed: {e}")

def restore_from_json():
    """Restore trades from JSON backup"""
    if not os.path.exists(BACKUP_FILE):
        print(f"❌ No backup file found at {BACKUP_FILE}")
        return 0
    
    try:
        from journal.models import Trade, SessionLocal
        
        with open(BACKUP_FILE, 'r') as f:
            backup_data = json.load(f)
        
        session = SessionLocal()
        restored = 0
        
        for data in backup_data:
            # Check if trade already exists
            existing = session.query(Trade).filter_by(id=data['id']).first()
            if existing:
                continue
            
            trade = Trade(
                id=data['id'],
                trade_type=data.get('trade_type', 'stock'),
                symbol=data['symbol'],
                entry_date=datetime.fromisoformat(data['entry_date']).date() if data['entry_date'] else None,
                entry_time=data['entry_time'],
                entry_price=data['entry_price'],
                shares=data['shares'],
                planned_entry=data['planned_entry'],
                pattern_type=data['pattern_type'],
                scanner_score=data['scanner_score'],
                planned_stop=data['planned_stop'],
                planned_target=data['planned_target'],
                planned_rr=data['planned_rr'],
                volume_confirmed=data['volume_confirmed'],
                golden_cross=data['golden_cross'],
                adx_at_entry=data['adx_at_entry'],
                rsi_at_entry=data['rsi_at_entry'],
                sector=data['sector'],
                option_strategy=data.get('option_strategy'),
                option_expiration=datetime.fromisoformat(data['option_expiration']).date() if data.get('option_expiration') else None,
                option_strike=data.get('option_strike'),
                option_strike_2=data.get('option_strike_2'),
                option_type=data.get('option_type'),
                option_dte=data.get('option_dte'),
                option_iv=data.get('option_iv'),
                option_delta=data.get('option_delta'),
                exit_date=datetime.fromisoformat(data['exit_date']).date() if data['exit_date'] else None,
                exit_time=data['exit_time'],
                exit_price=data['exit_price'],
                exit_reason=data['exit_reason'],
                status=data['status'],
                actual_rr=data['actual_rr'],
                pnl_dollars=data['pnl_dollars'],
                pnl_percent=data['pnl_percent'],
                days_held=data['days_held'],
                win=data['win'],
                notes=data['notes']
            )
            session.add(trade)
            restored += 1
        
        session.commit()
        session.close()
        
        print(f"✅ Restored {restored} trades from backup")
        return restored
    except Exception as e:
        print(f"❌ Restore failed: {e}")
        return 0

def fetch_historical_indicators(symbol, target_date):
    """
    Fetch price, ADX, RSI, volume confirmation, and golden cross for a specific date using Alpaca.
    Returns dict with data, or None if unavailable.
    """
    try:
        # Fetch extra days for indicator calculation (need 200 days for SMA200)
        start = (target_date - timedelta(days=250)).strftime('%Y-%m-%d')
        end = (target_date + timedelta(days=1)).strftime('%Y-%m-%d')
        df = fetch_stock_data(symbol, start, end)
        
        if df is None or df.empty:
            return None
        
        # Convert to expected format
        df = df.set_index('date')
        df.columns = [c.capitalize() for c in df.columns if c != 'symbol']
        
        # Calculate indicators
        df.ta.adx(length=14, append=True)
        df.ta.rsi(length=14, append=True)
        
        # Calculate SMAs for golden cross
        df['SMA50'] = df['Close'].rolling(50).mean()
        df['SMA200'] = df['Close'].rolling(200).mean()
        
        # Calculate 20-day average volume for volume confirmation
        df['AvgVol20'] = df['Volume'].rolling(20).mean()
        
        # Find the target date
        target_str = target_date.strftime('%Y-%m-%d')
        matching = df[df.index.strftime('%Y-%m-%d') == target_str]
        
        if matching.empty:
            return None
        
        row = matching.iloc[0]
        
        # Volume confirmed: current volume > 2x average (convert to Python bool)
        vol_confirmed = bool(row['Volume'] > (row['AvgVol20'] * 2)) if pd.notna(row['AvgVol20']) else False
        
        # Golden cross: SMA50 > SMA200 (convert to Python bool)
        golden_cross = bool(row['SMA50'] > row['SMA200']) if (pd.notna(row['SMA50']) and pd.notna(row['SMA200'])) else False
        
        return {
            'price': float(round(row['Close'], 2)),
            'adx': float(round(row.get('ADX_14', 0), 2)),
            'rsi': float(round(row.get('RSI_14', 0), 2)),
            'volume_confirmed': vol_confirmed,
            'golden_cross': golden_cross
        }
    except Exception as e:
        print(f"Error fetching indicators for {symbol}: {e}")
        return None

class Trade(Base):
    __tablename__ = 'trades'
    
    # Primary key
    id = Column(Integer, primary_key=True)
    
    # Trade type
    trade_type = Column(String(20), default='stock')  # stock, option
    
    # Entry data
    symbol = Column(String(10), nullable=False)
    entry_date = Column(Date, nullable=False, default=date.today)
    entry_time = Column(String(20))  # e.g., "6:57 AM PST"
    entry_price = Column(Float, nullable=False)
    shares = Column(Float, nullable=False)  # Number of shares purchased (supports fractional) OR contracts for options
    planned_entry = Column(Float)
    pattern_type = Column(String(50))  # cup_handle, bull_flag, double_bottom, ascending_triangle, mixed
    scanner_score = Column(Integer)
    planned_stop = Column(Float)
    planned_target = Column(Float)
    planned_rr = Column(Float)
    volume_confirmed = Column(Boolean, default=False)
    golden_cross = Column(Boolean, default=False)
    adx_at_entry = Column(Float)
    rsi_at_entry = Column(Float)
    sector = Column(String(50))
    
    # Options-specific fields
    option_strategy = Column(String(50))  # long_call, cash_secured_put, pmcc, iron_condor, bull_call_spread
    option_expiration = Column(Date)
    option_strike = Column(Float)  # Primary strike (or short strike for spreads)
    option_strike_2 = Column(Float)  # Long strike for spreads
    option_type = Column(String(10))  # call, put
    option_dte = Column(Integer)  # Days to expiration at entry
    option_iv = Column(Float)  # IV at entry
    option_delta = Column(Float)  # Delta at entry
    
    # Exit data
    exit_date = Column(Date)
    exit_time = Column(String(20))
    exit_price = Column(Float)
    exit_reason = Column(String(50))  # stop_hit, target_hit, manual_exit, trailing_stop, time_stop
    status = Column(String(20), default='open')  # open, closed, cancelled
    
    # Computed fields
    actual_rr = Column(Float)
    pnl_dollars = Column(Float)
    pnl_percent = Column(Float)
    days_held = Column(Integer)
    win = Column(Boolean)
    
    # Notes
    notes = Column(Text)
    
    def compute_metrics(self):
        """Calculate all computed fields"""
        if self.status == 'closed' and self.exit_price:
            if self.trade_type == 'option':
                # Options: entry_price and exit_price are per-contract premiums
                # shares field contains number of contracts
                price_diff = self.exit_price - self.entry_price
                self.pnl_dollars = price_diff * self.shares * 100  # Each contract = 100 shares
                self.pnl_percent = (price_diff / self.entry_price) * 100 if self.entry_price > 0 else 0
            else:
                # Stocks: standard calculation
                price_diff = self.exit_price - self.entry_price
                self.pnl_dollars = price_diff * self.shares
                self.pnl_percent = (price_diff / self.entry_price) * 100
            
            # Win/Loss
            self.win = self.exit_price > self.entry_price
            
            # Actual R:R
            if self.planned_stop:
                risk = abs(self.entry_price - self.planned_stop)
                reward = abs(self.exit_price - self.entry_price)
                self.actual_rr = reward / risk if risk > 0 else 0
            
            # Days held
            if self.exit_date and self.entry_date:
                self.days_held = (self.exit_date - self.entry_date).days
        
        # Planned R:R
        if self.planned_target and self.planned_stop and self.entry_price:
            risk = abs(self.entry_price - self.planned_stop)
            reward = abs(self.planned_target - self.entry_price)
            self.planned_rr = reward / risk if risk > 0 else 0


class SPXObservation(Base):
    __tablename__ = 'spx_observations'
    
    id = Column(Integer, primary_key=True)
    date = Column(String(10), nullable=False)  # YYYY-MM-DD
    logged_at = Column(String(30), nullable=False)  # ISO timestamp
    
    # Regime context (auto-populated)
    regime_verdict = Column(String(10))  # GREEN / YELLOW / RED
    regime_score = Column(Float)  # 0-100
    vix_level = Column(Float)
    spx_price = Column(Float)
    term_structure = Column(String(20))  # CONTANGO / FLAT / BACKWARDATION
    adx_value = Column(Float)
    vol_spread_edge = Column(Float)
    
    # Manual observations
    spx_price_945 = Column(Float)
    vix_945 = Column(Float)
    atm_straddle_price = Column(Float)
    atm_strike = Column(Float)
    
    # Hypothetical trade
    would_trade = Column(String(10))  # yes / no / maybe
    strategy = Column(String(20))  # iron_condor / put_spread / call_spread / none
    short_put_strike = Column(Float)
    short_call_strike = Column(Float)
    spread_width = Column(Float)
    premium_collected = Column(Float)
    
    # Outcome
    spx_close = Column(Float)
    outcome = Column(String(15))  # winner / loser / scratch / not_taken
    outcome_pnl = Column(Float)
    max_adverse_move = Column(Float)
    notes = Column(Text)

# Database setup
engine = create_engine('sqlite:///trade_journal.db')
SessionLocal = sessionmaker(bind=engine)

def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(engine)

def get_session():
    """Get database session"""
    return SessionLocal()
