#!/bin/bash
# DockerWormNetwork - Quick Log Monitor
# CS 499 Capstone - Authorized Pentest Tool (ID: ticq7)

if [ -z "$1" ]; then
    echo "Usage: ./script/monitor.sh <container_name>"
    echo ""
    echo "Examples:"
    echo "  ./script/monitor.sh api        # Watch API/web interface"
    echo "  ./script/monitor.sh webserver  # Watch first victim"
    echo "  ./script/monitor.sh victim     # Watch second victim"
    echo "  ./script/monitor.sh ids        # Watch Snort alerts"
    echo ""
    echo "Available containers:"
    sudo docker ps --format "  - {{.Names}}"
    exit 1
fi

CONTAINER=$1

echo "📡 Attaching to '$CONTAINER' logs..."
echo "Press Ctrl+C to exit"
echo ""

sudo docker logs -f --tail=50 "$CONTAINER"
