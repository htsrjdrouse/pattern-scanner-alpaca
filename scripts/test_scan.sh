#!/bin/bash
# test_scan.sh
# Manually trigger an earnings scan and show results summary
# Usage: bash scripts/test_scan.sh

APP_PORT=${APP_PORT:-5004}

echo "Triggering earnings scan..."
echo ""

RESPONSE=$(curl -s -X POST http://localhost:${APP_PORT}/api/earnings-scanner/run \
  -H "Content-Type: application/json" \
  -d '{"force_refresh": true}')

if echo "$RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); print(f\"✓ Scan complete\"); print(f\"  Symbols in calendar: {d.get('total_in_calendar', 0)}\"); print(f\"  Symbols scanned: {d.get('total_scanned', 0)}\"); print(f\"  Candidates found: {d.get('total_found', 0)}\"); print(f\"  Scan duration: {d.get('scan_duration_s', 0)}s\"); [print(f\"  → {c['symbol']}: IV rank {c.get('iv_rank','?')}%, score {c['score']}\") for c in d.get('candidates', [])]" 2>/dev/null; then
    echo ""
    echo "View full results at: http://localhost:${APP_PORT}/earnings-scanner"
else
    echo "Error or no response. Is the platform running?"
    echo "Raw response: $RESPONSE"
fi
