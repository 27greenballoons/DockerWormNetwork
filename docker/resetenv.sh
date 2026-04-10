#!/bin/bash
# DockerWormNetwork - Elevated Reset Script
# This uses sudo to force permissions through

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}[*] Phase 1: Force-killing background processes...${NC}"
# Kill any host-side python scripts (dashboard/worm)
sudo pkill -9 -f "python3.*dashboard.py" || true
sudo pkill -9 -f "python3.*worm.py" || true

echo -e "${BLUE}[*] Phase 2: Detecting Project Path...${NC}"
# Use the absolute path from your environment
BASE_DIR="/home/worm/Project/DockerWormNetwork"

if [ ! -d "$BASE_DIR/docker" ]; then
    echo -e "${RED}[!] Error: Path $BASE_DIR/docker not found.${NC}"
    exit 1
fi

cd "$BASE_DIR/docker"

echo -e "${BLUE}[*] Phase 3: Hard Resetting Containers (using sudo)...${NC}"
# --volumes ensures even the persistent worm data is wiped
sudo docker-compose down --volumes --remove-orphans || echo "Containers already down."

echo -e "${BLUE}[*] Phase 4: Purging Shared Data & IDS Logs...${NC}"
# Sudo is required here because Docker creates these files as root
sudo rm -rf "$BASE_DIR/shared_data/"*
sudo rm -f "$BASE_DIR/docker/ids/logs/alert.log"
sudo touch "$BASE_DIR/docker/ids/logs/alert.log"
sudo chmod 666 "$BASE_DIR/docker/ids/logs/alert.log"

echo -e "${BLUE}[*] Phase 5: Re-deploying Baseline (using sudo)...${NC}"
sudo docker-compose up -d

echo -e "${GREEN}==================================================================${NC}"
echo -e "${GREEN}SUCCESS: Deep Clean Complete. Permission issues bypassed.${NC}"
echo -e "${GREEN}==================================================================${NC}"
sudo docker ps