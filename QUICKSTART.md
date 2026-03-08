# Quick Start Guide - Alpaca Integration

## Prerequisites
- Python 3.12+
- Alpaca Markets account (free at https://alpaca.markets)

## Setup (5 minutes)

### 1. Get Alpaca API Keys
1. Sign up at https://alpaca.markets
2. Navigate to your dashboard
3. Generate API keys (Paper Trading)
4. Copy your API Key and Secret Key

### 2. Configure Environment
```bash
# Copy example file
cp .env.example .env

# Edit .env with your credentials
nano .env  # or use any text editor
```

Your `.env` should look like:
```
ALPACA_API_KEY=PK1234567890ABCDEF
ALPACA_SECRET_KEY=abcdef1234567890abcdef1234567890
ALPACA_MODE=paper
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Verify Setup
```bash
python verify_setup.py
```

You should see:
```
✅ All checks passed! Ready to start the application.
```

### 5. Start Application
```bash
python pattern_scanner.py
```

Open browser: http://localhost:5004

## Docker Setup

```bash
# Create .env file (same as above)
cp .env.example .env
# Edit .env with your credentials

# Build and start
docker compose up -d --build

# View logs
docker compose logs -f

# Stop
docker compose down
```

## First Steps

### 1. Check Trading Mode
Look for the mode badge in the top navigation:
- 🟡 **PAPER** - Safe testing mode (recommended)
- 🔴 **LIVE** - Real money mode

### 2. Scan for Patterns
- Select market (S&P 500, NASDAQ, All US)
- Click "Scan"
- Wait for results (may take a few minutes)

### 3. View Stock Details
- Click "View" on any result
- See chart with pattern overlays
- Review technical indicators
- Check DCF valuation

### 4. Place Test Order (Paper Mode)
- On chart page, click "Trade" panel
- View account buying power
- Select Market or Limit order
- Enter quantity
- Click "Buy" or "Sell"
- Confirm order

### 5. View Positions
Navigate to: http://localhost:5004/api/positions

### 6. Research Dashboard
Navigate to: http://localhost:5004/research
- Backtest signals
- Analyze signal decay
- Build composite signals

## API Examples

### Get Account Info
```bash
curl http://localhost:5004/api/account
```

### Place Market Order
```bash
curl -X POST http://localhost:5004/api/order/market \
  -H "Content-Type: application/json" \
  -d '{"symbol": "AAPL", "qty": 1, "side": "buy"}'
```

### Get Positions
```bash
curl http://localhost:5004/api/positions
```

### Subscribe to Real-Time Data
```bash
curl -X POST http://localhost:5004/api/stream/subscribe \
  -H "Content-Type: application/json" \
  -d '{"symbols": ["AAPL", "MSFT"]}'
```

### Get Latest Price
```bash
curl http://localhost:5004/api/stream/latest/AAPL
```

## Switching to Live Mode

⚠️ **WARNING**: Live mode uses real money!

1. Stop the application
2. Edit `.env`:
   ```
   ALPACA_MODE=live
   ```
3. Verify you have live API keys (not paper keys)
4. Restart application
5. Check mode badge shows 🔴 **LIVE**

## Troubleshooting

### "No module named 'alpaca'"
```bash
pip install alpaca-py python-dotenv websocket-client
```

### "ALPACA_API_KEY must be set"
- Check `.env` file exists
- Verify no spaces around `=` in `.env`
- Ensure keys are not wrapped in quotes

### "Connection failed"
- Verify API keys are correct
- Check keys are active at https://alpaca.markets
- Ensure you're using paper keys for paper mode

### "No data available for symbol"
- Alpaca only provides data for US stocks
- Symbol must be valid and tradable
- Check symbol exists on Alpaca

## Support

- Alpaca Docs: https://alpaca.markets/docs
- Alpaca Community: https://forum.alpaca.markets
- GitHub Issues: [your-repo]/issues

## Next Steps

1. ✅ Complete setup and verify
2. ✅ Run pattern scan in paper mode
3. ✅ Place test orders
4. ✅ Explore research dashboard
5. ✅ Review trade journal
6. ⚠️ Only switch to live mode when confident

Happy trading! 📈
