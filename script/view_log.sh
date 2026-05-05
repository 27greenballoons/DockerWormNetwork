#!/bin/bash
# Convert the latest worm run log to HTML and open in browser

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$(dirname "$SCRIPT_DIR")/logs"

# Pick log file: arg or latest
if [ -n "$1" ]; then
    LOG_FILE="$1"
else
    LOG_FILE=$(ls -t "$LOG_DIR"/worm_run_*.log 2>/dev/null | head -1)
fi

if [ -z "$LOG_FILE" ] || [ ! -f "$LOG_FILE" ]; then
    echo "No log file found in $LOG_DIR"
    exit 1
fi

HTML_FILE="${LOG_FILE%.log}.html"

ansi2html --dark-bg < "$LOG_FILE" > "$HTML_FILE"

echo "Saved: $HTML_FILE"
xdg-open "$HTML_FILE" 2>/dev/null || echo "Open in browser: file://$HTML_FILE"
