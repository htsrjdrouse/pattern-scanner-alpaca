# Stock Pattern Scanner - Docker
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
COPY sectors.json .
COPY sector_scan.py .
COPY data/ ./data/
COPY journal/ ./journal/

# Expose port
EXPOSE 5002

# Run the scanner
CMD ["python", "pattern_scanner.py"]
