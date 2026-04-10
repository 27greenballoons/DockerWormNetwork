#!/bin/bash
# DockerWormNetwork - Snort IDS Alert Monitor
# CS 499 Capstone - Authorized Pentest Tool (ID: ticq7)

LOG_FILE="/home/greenballoons/499/DockerWormNetwork/docker/ids/logs/alert.log"

echo "🚨 SNORT IDS ALERT MONITOR"
echo "=========================="
echo "Watching: $LOG_FILE"
echo "Press Ctrl+C to stop"
echo ""

if [ ! -f "$LOG_FILE" ]; then
    echo "Creating alert log file..."
    sudo touch "$LOG_FILE"
    sudo chmod 666 "$LOG_FILE"
fi

# Show last 20 alerts first
echo "📜 PREVIOUS ALERTS (Last 20):"
echo "------------------------------"
if [ -s "$LOG_FILE" ]; then
    sudo tail -20 "$LOG_FILE"
else
    echo "(No alerts yet - waiting for worm activity...)"
fi

echo ""
echo "🔴 REAL-TIME ALERTS:"
echo "--------------------"

# Color-code different alert types
sudo tail -f "$LOG_FILE" | while read line; do
    if echo "$line" | grep -qi "worm\|worm.py"; then
        echo -e "\033[91m🐛 WORM: $line\033[0m"
    elif echo "$line" | grep -qi "exploit\|rce\|injection"; then
        echo -e "\033[95m💥 EXPLOIT: $line\033[0m"
    elif echo "$line" | grep -qi "scan\|probe"; then
        echo -e "\033[93m🔍 SCAN: $line\033[0m"
    elif echo "$line" | grep -qi "redis\|mysql\|ssh"; then
        echo -e "\033[94m🔌 SERVICE: $line\033[0m"
    else
        echo "  $line"
    fi
done
