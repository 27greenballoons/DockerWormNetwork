#!/bin/bash
# DockerWormNetwork - Lab Reset Script (Machine Compatible)
# CS 499 Capstone - Authorized Pentest Environment
# Usage: sudo ./reset_compatible.sh
#
# NOTE: This script uses 'docker compose' (modern plugin) instead of
#       the legacy 'docker-compose' binary for compatibility.

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}[*] DockerWormNetwork Lab Reset Tool (Compatible)${NC}"
echo -e "${BLUE}[*] Target: CS 499 Capstone - Authorized Environment${NC}"
echo ""

# Phase 1: Stop Host-Side Processes
echo -e "${BLUE}[*] Phase 1: Stopping host-side processes...${NC}"
sudo pkill -9 -f "python3.*dashboard.py" 2>/dev/null || true
sudo pkill -9 -f "python3.*worm.py" 2>/dev/null || true
echo -e "${GREEN}    ✓ Host processes stopped${NC}"

# Phase 2: Locate Project
echo -e "${BLUE}[*] Phase 2: Locating project directory...${NC}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"

if [ ! -d "$BASE_DIR/docker" ]; then
    echo -e "${RED}[!] Error: Could not find project at $BASE_DIR${NC}"
    echo -e "${RED}[!] Make sure reset_compatible.sh is in the script/ folder${NC}"
    exit 1
fi

echo -e "${GREEN}    ✓ Found project at: $BASE_DIR${NC}"
cd "$BASE_DIR/docker"

# Phase 3: Ensure shared_data directory exists (prevents bind mount issues)
echo -e "${BLUE}[*] Phase 3: Ensuring shared_data directory exists...${NC}"
mkdir -p "$BASE_DIR/shared_data"
touch "$BASE_DIR/shared_data/.gitkeep"
echo -e "${GREEN}    ✓ shared_data ready${NC}"

# Phase 4: Destroy Containers
echo -e "${BLUE}[*] Phase 4: Destroying containers (kills background worms)...${NC}"
sudo docker compose down --volumes --remove-orphans 2>/dev/null || echo "    ℹ Containers already down"
echo -e "${GREEN}    ✓ Containers destroyed${NC}"

# Phase 5: Clean Data
echo -e "${BLUE}[*] Phase 5: Purging shared data and logs...${NC}"
sudo rm -rf "$BASE_DIR/shared_data/"* 2>/dev/null || true
sudo touch "$BASE_DIR/shared_data/.gitkeep" 2>/dev/null || true

# Reset Snort logs
sudo rm -f "$BASE_DIR/docker/ids/logs/"*.log 2>/dev/null || true
sudo rm -f "$BASE_DIR/docker/ids/logs/"*.alert 2>/dev/null || true
sudo touch "$BASE_DIR/docker/ids/logs/alert.log" 2>/dev/null || true
sudo chmod 666 "$BASE_DIR/docker/ids/logs/alert.log" 2>/dev/null || true

echo -e "${GREEN}    ✓ Data purged${NC}"

# Phase 6: Rebuild and Deploy
echo -e "${BLUE}[*] Phase 6: Rebuilding and deploying baseline...${NC}"
sudo docker compose up --build -d
echo -e "${GREEN}    ✓ Fresh containers deployed${NC}"

# Phase 7: Verify
echo ""
echo -e "${GREEN}==================================================================${NC}"
echo -e "${GREEN}SUCCESS: Lab reset to baseline state${NC}"
echo -e "${GREEN}==================================================================${NC}"
echo ""
sudo docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""
echo -e "${BLUE}Quick Commands:${NC}"
echo -e "  • View dashboard:   ${NC}cd $BASE_DIR && python3 python/dashboard.py"
echo -e "  • View Snort logs:  ${NC}sudo tail -f $BASE_DIR/docker/ids/logs/alert.log"
echo -e "  • Web interface:    ${NC}http://localhost:8000"
echo -e "  • Reset again:      ${NC}sudo $BASE_DIR/script/reset_compatible.sh"
echo ""
echo -e "${GREEN}Ready for next test cycle.${NC}"

