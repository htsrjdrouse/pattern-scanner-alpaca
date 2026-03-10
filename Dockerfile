# Stock Pattern Scanner - Docker (Alpaca-powered)
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for matplotlib
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY pattern_scanner.py .
COPY research_api.py .
COPY research_dashboard.py .
COPY signals.py .
COPY backtest.py .
COPY analytics.py .
COPY alpaca_client.py .
COPY alpaca_data.py .
COPY stream_manager.py .
COPY order_manager.py .
COPY regime_classifier.py .
COPY sectors.json .
COPY sector_scan.py .
COPY .env.example .
COPY data/ ./data/
COPY journal/ ./journal/

# Note: .env file must be provided at runtime with Alpaca credentials
# Copy .env.example as template - users must create .env with real keys

# Expose port
EXPOSE 5004

# Run the scanner
CMD ["python", "pattern_scanner.py"]
