
# DockerWormNetwork - Lab Reset Script (Clean Slate)

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}[*] Phase 1: Cleaning Host Processes...${NC}"
# Stop any dashboard or host-side worm instances
pkill -f "python3.*dashboard.py" || true
pkill -f "python3.*worm.py" || true

echo -e "${BLUE}[*] Phase 2: Destroying Containers & Background Worms...${NC}"
# Navigate to your docker folder
cd /home/greenballoons/499/DockerWormNetwork/docker
# This kills the background processes inside the containers by destroying the instances
docker-compose down --volumes --remove-orphans

echo -e "${BLUE}[*] Phase 3: Purging Logs and Shared Data...${NC}"
# Wipe the shared uploads folder the worm infected
sudo rm -rf /home/greenballoons/499/DockerWormNetwork/shared_data/*
# Re-baseline the Snort logs
sudo rm -f ids/logs/alert.log
touch ids/logs/alert.log

echo -e "${BLUE}[*] Phase 4: Deploying Baseline Infrastructure...${NC}"
docker-compose up -d

echo -e "${GREEN}==================================================================${NC}"
echo -e "${GREEN}SUCCESS: Lab Reset. Environment is Clean.${NC}"
echo -e "${GREEN}==================================================================${NC}"
docker ps