# Sector Management Feature

## Overview

The Alpha Research Platform now includes sector management capabilities, allowing you to organize stocks into market sectors and quickly benchmark different sectors against your signals.

## Features

### 1. Sector Dropdown in Backtest Form
- Select a predefined sector from the dropdown
- Automatically populates the symbols field with sector tickers
- Allows quick switching between sectors for comparative analysis

### 2. Sector Manager UI
- Click "Manage" button next to the sector dropdown
- Create, edit, and delete sectors
- View all tickers in each sector

### 3. REST API Endpoints

#### Get All Sectors
```bash
GET /signals/sectors
```

#### Get Specific Sector
```bash
GET /signals/sectors/{sector_id}
```

#### Create New Sector
```bash
POST /signals/sectors
Content-Type: application/json

{
  "id": "tech_giants",
  "name": "Tech Giants",
  "tickers": ["AAPL", "MSFT", "GOOGL", "AMZN", "META"]
}
```

#### Update Sector
```bash
PUT /signals/sectors/{sector_id}
Content-Type: application/json

{
  "name": "Updated Name",
  "tickers": ["AAPL", "MSFT", "GOOGL"]
}
```

#### Delete Sector
```bash
DELETE /signals/sectors/{sector_id}
```

## Usage Workflow

### Benchmarking Sectors

1. Navigate to http://localhost:5004/research
2. In the "Quick Backtest" section, select a sector from the dropdown
3. The symbols field will auto-populate with sector tickers
4. Select your signals and timeframe
5. Click "Run Backtest"
6. Compare results across different sectors

### Managing Sectors

1. Click the "Manage" button next to the sector dropdown
2. **Create**: Fill in the form with sector ID, name, and tickers
3. **Edit**: Click "Edit" on any sector to modify name or tickers
4. **Delete**: Click "Delete" to remove a sector
5. Close the modal when done

## Pre-loaded Sectors

The system comes with 19 pre-configured sectors in `sectors.json`:

- Minerals & Mining
- Energy (Oil & Gas)
- Solar Energy
- Nuclear Energy
- Semiconductors
- Communications & Telecom
- SaaS / Cloud Software
- Biotechnology
- Healthcare (Non-Biotech)
- Cybersecurity
- Artificial Intelligence
- Data Centers & Infrastructure
- Crypto & Blockchain
- Construction & Engineering
- Agriculture
- Materials & Specialty Chemicals
- Chemicals (Industrial & Specialty)
- Financial Services
- REITs

## Data Storage

Sectors are stored in `sectors.json` in the project root. The file structure:

```json
{
  "sectors": {
    "sector_id": {
      "name": "Sector Name",
      "tickers": ["TICK1", "TICK2", "TICK3"]
    }
  }
}
```

## Example: Comparing Sectors

```python
import requests

# Backtest RSI signal on semiconductors
response = requests.post('http://localhost:5004/signals/backtest', json={
    "signal_name": "rsi_14",
    "symbols": ["NVDA", "AMD", "INTC", "AVGO", "QCOM"],
    "horizon_days": 20,
    "start_date": "2024-01-01",
    "end_date": "2025-12-31"
})
semi_results = response.json()

# Backtest same signal on energy
response = requests.post('http://localhost:5004/signals/backtest', json={
    "signal_name": "rsi_14",
    "symbols": ["XOM", "CVX", "COP", "EOG", "PXD"],
    "horizon_days": 20,
    "start_date": "2024-01-01",
    "end_date": "2025-12-31"
})
energy_results = response.json()

# Compare IC
print(f"Semiconductors IC: {semi_results['ic_pearson_mean']:.2%}")
print(f"Energy IC: {energy_results['ic_pearson_mean']:.2%}")
```

## Tips

- Use descriptive sector IDs (lowercase with underscores)
- Keep ticker lists updated as companies change
- Test signals across multiple sectors to find where they work best
- Use the correlation analysis to see if signals behave differently across sectors
