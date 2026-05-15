#!/bin/bash
# setup_cron.sh
# Run once on the Raspberry Pi to install the nightly earnings scanner cron job
# Usage: bash scripts/setup_cron.sh

set -e

APP_PORT=${APP_PORT:-5004}
LOG_FILE="/home/$(whoami)/logs/earnings_scan.log"
CRON_JOB="0 19 * * 1-5 curl -s -X POST http://localhost:${APP_PORT}/api/earnings-scanner/run -H 'Content-Type: application/json' -d '{\"force_refresh\": true}' >> ${LOG_FILE} 2>&1"

echo "Setting up nightly earnings scanner cron job..."

# Create log directory
mkdir -p "$(dirname $LOG_FILE)"
touch "$LOG_FILE"

# Get existing crontab (empty string if none)
EXISTING=$(crontab -l 2>/dev/null || true)

# Remove old earnings-scanner entry if present
if echo "$EXISTING" | grep -q "earnings-scanner"; then
    echo "Cron job already exists. Removing old entry..."
    EXISTING=$(echo "$EXISTING" | grep -v "earnings-scanner")
fi

# Install updated crontab
if [ -z "$EXISTING" ]; then
    echo "$CRON_JOB" | crontab -
else
    printf '%s\n%s\n' "$EXISTING" "$CRON_JOB" | crontab -
fi

echo "✓ Cron job installed successfully"
echo "✓ Log file: $LOG_FILE"
echo ""
echo "Schedule: Every weekday (Mon-Fri) at 7:00 PM local time"
echo ""
echo "To verify installation:"
echo "  crontab -l"
echo ""
echo "To view scan logs:"
echo "  tail -f $LOG_FILE"
echo ""
echo "To test immediately:"
echo "  curl -s -X POST http://localhost:${APP_PORT}/api/earnings-scanner/run \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"force_refresh\": true}'"
