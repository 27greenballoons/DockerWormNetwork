#!/bin/bash
# DockerWormNetwork - Deploy Worm + Launch Dashboard
# CS 499 Capstone - Authorized Pentest Tool (ID: ticq7)
# Usage: ./script/deploy_and_watch_worm.sh
#        STRATEGY=random ./script/deploy_and_watch_worm.sh

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
BLINK='\033[5m'
REVERSE='\033[7m'
NC='\033[0m'

# Bright red background + white bold text for alerts
ALERT_BG='\033[1;41;97m'
ALERT_CLEAR='\033[1;42;97m'

API_PORT="${PORT:-8000}"
STRATEGY="${STRATEGY:-exhaustive}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
WORM="$BASE_DIR/python/worm.py"
COOKIE_JAR="/tmp/worm_session.jar"
ALERT_LOG="$BASE_DIR/docker/detector/logs/alerts.log"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_DIR="$BASE_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/worm_run_${TIMESTAMP}.log"

exec > >(tee "$LOG_FILE") 2>&1

# ── Alert watcher (runs in background, tails detector alert log) ──────────────
watch_alerts() {
    mkdir -p "$(dirname "$ALERT_LOG")"
    touch "$ALERT_LOG"
    > "$ALERT_LOG"   # clear old alerts from previous run
    tail -f "$ALERT_LOG" 2>/dev/null | while IFS= read -r line; do
        [ -z "$line" ] && continue
        if echo "$line" | grep -qi "WORM DETECTED"; then
            echo ""
            echo -e "${BLINK}${ALERT_BG}                                                              ${NC}"
            echo -e "${ALERT_BG}   🚨🚨🚨  M L   D E T E C T O R   A L E R T  🚨🚨🚨           ${NC}"
            echo -e "${BLINK}${ALERT_BG}                                                              ${NC}"
            echo -e "${ALERT_BG}   $line   ${NC}"
            echo -e "${BLINK}${ALERT_BG}                                                              ${NC}"
            echo ""
        elif echo "$line" | grep -qi "CLEARED"; then
            echo ""
            echo -e "${ALERT_CLEAR}   ✅  DETECTOR: HOST CLEARED — $line   ${NC}"
            echo ""
        else
            echo -e "${YELLOW}[DETECTOR] $line${NC}"
        fi
    done
}

# ── Header ────────────────────────────────────────────────────────────────────

echo ""
echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${CYAN}║       DockerWormNetwork — Worm Deployment Console            ║${NC}"
echo -e "${BOLD}${CYAN}║       CS 499 Capstone  ·  Auth ID: ticq7                     ║${NC}"
echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo -e "${CYAN}  Strategy : ${BOLD}${STRATEGY}${NC}"
echo -e "${CYAN}  Log      : ${LOG_FILE}${NC}"
echo -e "${CYAN}  Time     : $(date)${NC}"
echo ""

# ── Preflight checks ──────────────────────────────────────────────────────────

if [ ! -f "$WORM" ]; then
    echo -e "${RED}[!] worm.py not found at $WORM${NC}"; exit 1
fi

if ! docker ps --format "{{.Names}}" 2>/dev/null | grep -q "^api$"; then
    echo -e "${RED}[!] 'api' container is not running.${NC}"
    echo -e "${YELLOW}    Start the lab: cd docker && docker compose up -d --build${NC}"
    exit 1
fi

echo -e "${GREEN}[✓] Lab is running${NC}"
echo -e "${GREEN}[✓] worm.py found${NC}"

if docker ps --format "{{.Names}}" 2>/dev/null | grep -q "^detector$"; then
    echo -e "${GREEN}[✓] ML detector container is running${NC}"
else
    echo -e "${YELLOW}[!] Detector container not running — alerts will be silent${NC}"
    echo -e "${YELLOW}    Start it: cd docker && docker compose up -d --build detector${NC}"
fi
echo ""

# ── Authenticate ──────────────────────────────────────────────────────────────

echo -e "${BOLD}${MAGENTA}[STAGE 1/3] Authentication${NC}"
echo -e "${MAGENTA}────────────────────────────────────────${NC}"
rm -f "$COOKIE_JAR"

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -c "$COOKIE_JAR" \
    -d "username=admin&password=password123" \
    "http://localhost:${API_PORT}/login")

if [ "$HTTP_CODE" != "200" ] && [ "$HTTP_CODE" != "302" ]; then
    echo -e "${RED}[!] Login failed (HTTP $HTTP_CODE).${NC}"
    echo -e "${YELLOW}    Is the lab running? Try: cd docker && docker compose up -d --build${NC}"
    exit 1
fi

echo -e "${GREEN}[✓] Authenticated as admin (HTTP $HTTP_CODE)${NC}"
echo ""

# ── Deploy worm ───────────────────────────────────────────────────────────────

echo -e "${BOLD}${MAGENTA}[STAGE 2/3] Worm Deployment${NC}"
echo -e "${MAGENTA}────────────────────────────────────────${NC}"

docker cp "$WORM" api:/uploads/worm.py
echo -e "${GREEN}[✓] worm.py staged in api:/uploads/${NC}"

RESPONSE=$(curl -s \
    -b "$COOKIE_JAR" \
    -X POST \
    -H "Content-Type: application/json" \
    -d "{\"file\":\"worm.py\",\"strategy\":\"${STRATEGY}\"}" \
    "http://localhost:${API_PORT}/exec")

if echo "$RESPONSE" | grep -q '"status":"executing"'; then
    echo -e "${GREEN}[✓] Worm launched — strategy: ${BOLD}${STRATEGY}${NC}"
else
    echo -e "${RED}[!] Exec failed: $RESPONSE${NC}"; exit 1
fi

rm -f "$COOKIE_JAR"
echo ""

# ── Start alert watcher in background ─────────────────────────────────────────

watch_alerts &
WATCHER_PID=$!
trap "kill $WATCHER_PID 2>/dev/null; wait $WATCHER_PID 2>/dev/null" EXIT

# ── Launch dashboard ──────────────────────────────────────────────────────────

echo -e "${BOLD}${MAGENTA}[STAGE 3/3] Live Monitoring Dashboard${NC}"
echo -e "${MAGENTA}────────────────────────────────────────${NC}"
echo -e "${YELLOW}[*] Strategy  : ${STRATEGY}${NC}"
echo -e "${YELLOW}[*] Dashboard : watching container logs for 🦠 infection events${NC}"
echo -e "${YELLOW}[*] Detector  : ML alerts will flash red above when worm found${NC}"
echo -e "${YELLOW}[*] Press Ctrl+C to stop${NC}"
echo ""
sleep 1

python3 -u "$BASE_DIR/python/dashboard.py"

# ── Reset lab after dashboard exits ──────────────────────────────────────────

echo ""
echo -e "${BOLD}${CYAN}════════════════════════════════════════${NC}"
echo -e "${CYAN}[*] Session ended — resetting lab...${NC}"
echo -e "${CYAN}[*] Log saved to: ${LOG_FILE}${NC}"
echo -e "${BOLD}${CYAN}════════════════════════════════════════${NC}"
sudo "$SCRIPT_DIR/reset_compatible.sh"
