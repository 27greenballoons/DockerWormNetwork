#!/bin/bash
# DockerWormNetwork - Infection Status Checker
# CS 499 Capstone - Authorized Pentest Tool (ID: ticq7)
# Usage: ./script/check_infection.sh

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo "🕵️  INFECTION STATUS REPORT - $(date)"
echo "==============================================================="
echo "   DockerWormNetwork - CS 499 Capstone Lab"
echo "   Authorization: ticq7 | Isolated Environment"
echo "==============================================================="

echo ""
echo "📊 CONTAINER STATUS:"
echo "-------------------"
sudo docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "🐍 WORM PERSISTENCE CHECK (/tmp/worm.py):"
echo "-----------------------------------------"
for container in api webserver victim ids dns fileshare; do
    if sudo docker ps -q -f name=$container | grep -q .; then
        if sudo docker exec $container test -f /tmp/worm.py 2>/dev/null; then
            echo -e "  $container: ${GREEN}✅ INFECTED${NC} (worm.py found)"
        else
            echo -e "  $container: ${RED}❌ CLEAN${NC} (no worm.py)"
        fi
    else
        echo -e "  $container: ${YELLOW}⚠️  DOWN${NC} (container not running)"
    fi
done

echo ""
echo "⚡ ACTIVE WORM PROCESSES:"
echo "-------------------------"
for container in api webserver victim; do
    if sudo docker ps -q -f name=$container | grep -q .; then
        count=$(sudo docker exec $container pgrep -c "python.*worm" 2>/dev/null || echo "0")
        if [ "$count" -gt 0 ]; then
            echo -e "  $container: ${GREEN}🐛 $count worm process(es) running${NC}"
        else
            echo -e "  $container: ${RED}💤 No worm processes${NC}"
        fi
    else
        echo -e "  $container: ${YELLOW}⚠️  Container down${NC}"
    fi
done

echo ""
echo "🌐 NETWORK PROPAGATION (Port 8080 - Worm Drop Server):"
echo "------------------------------------------------------"
for container in api webserver victim; do
    if sudo docker ps -q -f name=$container | grep -q .; then
        if sudo docker exec $container ss -tln 2>/dev/null | grep -q ':8080'; then
            echo -e "  $container: ${GREEN}🌐 HTTP server ACTIVE${NC} (propagating)"
        else
            echo -e "  $container: ${RED}🔌 No HTTP listener${NC}"
        fi
    fi
done

echo ""
echo "🚨 RECENT SNORT IDS ALERTS (Last 10):"
echo "--------------------------------------"
LOG_FILE="/home/greenballoons/499/DockerWormNetwork/docker/ids/logs/alert.log"
if [ -f "$LOG_FILE" ] && [ -s "$LOG_FILE" ]; then
    sudo tail -10 "$LOG_FILE" 2>/dev/null | while read line; do
        if echo "$line" | grep -q "worm\|WORM\|EXPLOIT\|exploit"; then
            echo -e "  ${RED}🚨 $line${NC}"
        elif echo "$line" | grep -q "SCAN\|scan"; then
            echo -e "  ${YELLOW}🔍 $line${NC}"
        else
            echo "  $line"
        fi
    done
else
    echo "  No alerts logged yet (Snort may still be starting...)"
fi

echo ""
echo "🔗 ACTIVE CONNECTIONS (Propagation Evidence):"
echo "---------------------------------------------"
for container in api webserver victim; do
    if sudo docker ps -q -f name=$container | grep -q .; then
        conns=$(sudo docker exec $container ss -t -o state established 2>/dev/null | wc -l)
        echo "  $container: $conns established connection(s)"
    fi
done

echo ""
echo "==============================================================="
echo "📋 INTERPRETATION GUIDE:"
echo "  ✅ INFECTED  = worm.py copied to /tmp (persistence achieved)"
echo "  🐛 RUNNING   = worm process active (currently spreading)"
echo "  🌐 HTTP ON   = drop server active (ready to infect others)"
echo "  🔍 SCAN      = port scanning activity detected"
echo "  🚨 EXPLOIT   = command injection/RCE detected"
echo "==============================================================="
echo ""

