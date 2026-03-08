#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick verification script for Alpaca integration.
Run this before starting the application to verify setup.
"""
import os
import sys

def check_env_file():
    """Check if .env file exists and has required variables."""
    print("Checking .env file...")
    
    if not os.path.exists('.env'):
        print("  ❌ .env file not found")
        print("  → Run: cp .env.example .env")
        print("  → Then edit .env with your Alpaca credentials")
        return False
    
    with open('.env', 'r') as f:
        content = f.read()
    
    required = ['ALPACA_API_KEY', 'ALPACA_SECRET_KEY', 'ALPACA_MODE']
    missing = []
    
    for var in required:
        if var not in content or f'{var}=your_' in content or f'{var}=' not in content:
            missing.append(var)
    
    if missing:
        print(f"  ❌ Missing or incomplete: {', '.join(missing)}")
        print("  → Edit .env and add your Alpaca credentials")
        return False
    
    print("  ✅ .env file configured")
    return True


def check_dependencies():
    """Check if required packages are installed."""
    print("\nChecking dependencies...")
    
    required = [
        ('alpaca', 'alpaca-py'),
        ('dotenv', 'python-dotenv'),
        ('flask', 'flask'),
        ('pandas', 'pandas'),
    ]
    
    missing = []
    for module, package in required:
        try:
            __import__(module)
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"  ❌ Missing packages: {', '.join(missing)}")
        print("  → Run: pip install -r requirements.txt")
        return False
    
    print("  ✅ All dependencies installed")
    return True


def check_alpaca_connection():
    """Test Alpaca API connection."""
    print("\nTesting Alpaca connection...")
    
    try:
        from alpaca_client import trading_client, get_mode
        
        # Try to get account info
        account = trading_client.get_account()
        mode = get_mode()
        
        print(f"  ✅ Connected to Alpaca ({mode.upper()} mode)")
        print(f"     Account: {account.account_number}")
        print(f"     Equity: ${float(account.equity):,.2f}")
        print(f"     Buying Power: ${float(account.buying_power):,.2f}")
        return True
        
    except Exception as e:
        print(f"  ❌ Connection failed: {e}")
        print("  → Check your API keys in .env")
        print("  → Verify keys are active at https://alpaca.markets")
        return False


def main():
    print("=" * 60)
    print("Alpaca Integration Verification")
    print("=" * 60)
    
    checks = [
        check_env_file(),
        check_dependencies(),
        check_alpaca_connection(),
    ]
    
    print("\n" + "=" * 60)
    
    if all(checks):
        print("✅ All checks passed! Ready to start the application.")
        print("\nNext steps:")
        print("  1. Start server: python pattern_scanner.py")
        print("  2. Open browser: http://localhost:5002")
        print("  3. Check mode badge in top navigation")
        print("\n⚠️  Remember: You're in", end=" ")
        try:
            from alpaca_client import get_mode
            mode = get_mode().upper()
            print(f"{mode} mode")
            if mode == "LIVE":
                print("    Real money at risk! Switch to PAPER for testing.")
        except:
            print("mode (check .env)")
    else:
        print("❌ Some checks failed. Fix issues above before starting.")
        sys.exit(1)
    
    print("=" * 60)


if __name__ == '__main__':
    main()
