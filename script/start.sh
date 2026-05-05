#!/bin/bash
# DockerWormNetwork - Lab Startup Script
# Usage: ./script/start_lab.sh [port]

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

API_PORT="${1:-8000}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}[*] DockerWormNetwork Lab Startup${NC}"
echo -e "${BLUE}[*] API will be exposed on host port: ${API_PORT}${NC}"
echo ""

echo -e "${BLUE}[*] Phase 1: Checking for port ${API_PORT} conflicts...${NC}"
CONFLICT_PID=$(ss -tlnp "sport = :${API_PORT}" 2>/dev/null | grep -oP 'pid=\K[0-9]+' | head -1 || true)
if [ -n "$CONFLICT_PID" ]; then
    CONFLICT_CMD=$(ps -p "$CONFLICT_PID" -o comm= 2>/dev/null || echo "unknown")
    echo -e "${YELLOW}    ⚠ Port ${API_PORT} is already in use by:${NC}"
    echo -e "${YELLOW}       PID ${CONFLICT_PID}: ${CONFLICT_CMD}${NC}"
    echo ""
    echo -e "${YELLOW}    Options:${NC}"
    echo -e "${YELLOW}      1) Kill the process: kill ${CONFLICT_PID}${NC}"
    echo -e "${YELLOW}      2) Use a different port: ./script/start_lab.sh 8001${NC}"
    exit 1
fi
echo -e "${GREEN}    ✓ Port ${API_PORT} is free${NC}"

echo -e "${BLUE}[*] Phase 2: Ensuring shared_data directory exists...${NC}"
mkdir -p "$BASE_DIR/shared_data"
touch "$BASE_DIR/shared_data/.gitkeep"
echo -e "${GREEN}    ✓ shared_data ready${NC}"

echo -e "${BLUE}[*] Phase 3: Configuring Docker Compose...${NC}"
COMPOSE_FILE="$BASE_DIR/docker/docker-compose.yaml"
if [ "$API_PORT" != "8000" ]; then
    sed -i "s/- \"8000:8000\"/- \"${API_PORT}:8000\"/" "$COMPOSE_FILE"
    echo -e "${GREEN}    ✓ Updated compose to use port ${API_PORT}${NC}"
else
    sed -i 's/- "[0-9]\+:8000"/- "8000:8000"/' "$COMPOSE_FILE"
    echo -e "${GREEN}    ✓ Using default port 8000${NC}"
fi

echo -e "${BLUE}[*] Phase 4: Starting containers...${NC}"
cd "$BASE_DIR/docker"
docker compose up --build -d
echo -e "${GREEN}    ✓ Containers started${NC}"

echo -e "${BLUE}[*] Phase 5: Airgapping Docker network via iptables...${NC}"
# Get the bridge interface name Docker assigned to micro_internet
BRIDGE=$(docker network inspect docker_micro_internet --format '{{.Options.com.docker.network.bridge.name}}' 2>/dev/null \
         || docker network ls --filter name=micro_internet --format '{{.ID}}' | head -1 | xargs -I{} docker network inspect {} --format 'br-{{slice .ID 0 12}}' 2>/dev/null)
if [ -n "$BRIDGE" ]; then
    # Block forwarding from the bridge to any external interface (drops outbound internet)
    # The DOCKER-USER chain runs before Docker's own rules and persists across container restarts
    sudo iptables -I DOCKER-USER -i "$BRIDGE" -o "$BRIDGE" -j RETURN 2>/dev/null  # allow intra-bridge traffic
    sudo iptables -I DOCKER-USER -i "$BRIDGE" -j DROP 2>/dev/null                 # drop all other forwarding
    echo -e "${GREEN}    ✓ Outbound internet blocked for bridge: ${BRIDGE}${NC}"
else
    echo -e "${YELLOW}    ⚠ Could not detect bridge name — airgap not applied${NC}"
fi

echo -e "${BLUE}[*] Phase 6: Waiting for API to be ready...${NC}"
MAX_WAIT=60
for i in $(seq 1 $MAX_WAIT); do
    if curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:${API_PORT}/login" 2>/dev/null | grep -q "200"; then
        echo -e "${GREEN}    ✓ API ready after ${i}s${NC}"
        break
    fi
    if [ "$i" -eq "$MAX_WAIT" ]; then
        echo -e "${RED}    ✗ API did not become ready within ${MAX_WAIT}s${NC}"
        echo -e "${RED}    Check logs: docker logs api${NC}"
        exit 1
    fi

    sleep 1
done

echo ""
echo -e "${GREEN}==================================================================${NC}"
echo -e "${GREEN}  DockerWormNetwork Lab is RUNNING${NC}"
echo -e "${GREEN}==================================================================${NC}"
echo ""
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""
echo -e "${BLUE}Access Points:${NC}"
echo -e "  • Web UI:     ${GREEN}http://localhost:${API_PORT}${NC}"
echo -e "  • Login:      ${GREEN}admin / password123${NC}"
echo ""
echo -e "${BLUE}Useful Commands:${NC}"
echo -e "  • Monitor logs:     ${NC}./script/monitor.sh <container>"
echo -e "  • Check infection:  ${NC}./script/check_infection.sh"
echo -e "  • Full ML pipeline: ${NC}./run_full_ml.sh"
echo -e "  • Reset lab:        ${NC}sudo ./script/reset_compatible.sh"
echo -e "  • Stop lab:         ${NC}cd docker && docker compose down"
echo ""