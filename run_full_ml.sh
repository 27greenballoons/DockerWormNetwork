#!/bin/bash
# Full ML Pipeline - 3-Round Data Collection + XGBoost Training
# CS 499 Capstone - DockerWormNetwork

cd /home/greenballoons/499/DockerWormNetwork

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

ROUNDS=3
BASELINE_SECONDS=600
STRATEGY="${STRATEGY:-exhaustive}"   # override: STRATEGY=random ./run_full_ml.sh

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  DockerWormNetwork ML Pipeline${NC}"
echo -e "${BLUE}  ${ROUNDS} rounds × (baseline + worm) — strategy: ${STRATEGY}${NC}"
echo -e "${BLUE}========================================${NC}"

# ── Sudo keepalive (refreshes every 4 min so cache never expires mid-run) ────
sudo -v
( while true; do sudo -v; sleep 240; done ) &
SUDO_KEEPALIVE_PID=$!
trap "kill $SUDO_KEEPALIVE_PID 2>/dev/null" EXIT

# ── Dependencies ─────────────────────────────────────────────────────────────
echo -e "\n${BLUE}[*] Installing Python dependencies...${NC}"
python3 -m pip install -q xgboost scikit-learn pandas joblib psutil docker || \
    pip3 install xgboost scikit-learn pandas joblib psutil docker --break-system-packages 2>/dev/null || true

# ── Collection rounds ─────────────────────────────────────────────────────────
for ROUND in $(seq 1 $ROUNDS); do
    echo -e "\n${BLUE}══════════════════════════════════════${NC}"
    echo -e "${BLUE}  ROUND ${ROUND} / ${ROUNDS}${NC}"
    echo -e "${BLUE}══════════════════════════════════════${NC}"

    # Reset lab to clean state
    echo -e "\n${BLUE}[*] Resetting lab...${NC}"
    sudo ./script/reset_compatible.sh > /dev/null

    # Wait for API
    echo -e "${BLUE}[*] Waiting for API...${NC}"
    for i in $(seq 1 60); do
        if curl -s http://localhost:8000/login > /dev/null 2>&1; then
            echo -e "${GREEN}    ✓ API ready after ${i}s${NC}"
            break
        fi
        sleep 1
        if [ "$i" -eq 60 ]; then
            echo -e "${RED}[!] API did not become ready${NC}"; exit 1
        fi
    done

    # ── Baseline ──────────────────────────────────────────────────────────────
    BASELINE_FILE="ml/data/baseline_traffic_${STRATEGY}_${ROUND}.csv"
    echo -e "\n${BLUE}[*] Round ${ROUND} — Baseline (${BASELINE_SECONDS}s)...${NC}"
    env BASELINE_OUT="$BASELINE_FILE" timeout $BASELINE_SECONDS python3 -u ml/scripts/collect_baseline.py

    if [ ! -s "$BASELINE_FILE" ]; then
        echo -e "${RED}[!] ${BASELINE_FILE} is empty — aborting${NC}"; exit 1
    fi
    ROWS=$(( $(wc -l < "$BASELINE_FILE") - 1 ))
    echo -e "${GREEN}    ✓ ${ROWS} baseline samples → ${BASELINE_FILE}${NC}"

    # ── Worm ──────────────────────────────────────────────────────────────────
    WORM_FILE="ml/data/worm_traffic_${STRATEGY}_${ROUND}.csv"
    echo -e "\n${BLUE}[*] Round ${ROUND} — Starting worm collector...${NC}"
    env WORM_OUT="$WORM_FILE" python3 -u ml/scripts/collect_worm.py &
    COLLECTOR_PID=$!
    sleep 3

    echo -e "${BLUE}[*] Round ${ROUND} — Deploying worm (strategy=${STRATEGY})...${NC}"
    # Set WORM_STRATEGY in the container so auto_deploy_worm picks it up
    sudo docker exec api bash -c "export WORM_STRATEGY=${STRATEGY}" 2>/dev/null || true
    curl -s -c /tmp/worm_cookies.txt -X POST \
        -d "username=admin&password=password123" \
        http://localhost:8000/login > /dev/null
    # Pass strategy explicitly via /exec endpoint
    curl -s -b /tmp/worm_cookies.txt -X POST \
        -H "Content-Type: application/json" \
        -d "{\"file\":\"worm.py\",\"strategy\":\"${STRATEGY}\"}" \
        http://localhost:8000/exec > /dev/null
    rm -f /tmp/worm_cookies.txt
    echo -e "${GREEN}    Worm deployed${NC}"

    echo -e "${BLUE}[*] Waiting for worm to complete (max 180s)...${NC}"
    for i in $(seq 1 36); do
        if sudo docker logs api 2>&1 | grep -q "WORM COMPLETE"; then
            echo -e "${GREEN}    ✓ Worm done after ~$((i * 5))s${NC}"
            break
        fi
        sleep 5
    done

    sleep 2
    kill "$COLLECTOR_PID" 2>/dev/null
    wait "$COLLECTOR_PID" 2>/dev/null || true

    if [ ! -s "$WORM_FILE" ]; then
        echo -e "${RED}[!] ${WORM_FILE} is empty — aborting${NC}"; exit 1
    fi
    ROWS=$(( $(wc -l < "$WORM_FILE") - 1 ))
    echo -e "${GREEN}    ✓ ${ROWS} worm samples → ${WORM_FILE}${NC}"

    # Save propagation log for this round
    PROP_LOG="ml/data/propagation_log_${STRATEGY}_${ROUND}.csv"
    if [ -f "shared_data/propagation_log.csv" ]; then
        cp shared_data/propagation_log.csv "$PROP_LOG"
        EVENTS=$(( $(wc -l < "$PROP_LOG") - 1 ))
        echo -e "${GREEN}    ✓ ${EVENTS} infection events → ${PROP_LOG}${NC}"
    else
        echo -e "${YELLOW}    ⚠ No propagation log found (worm may not have infected any hosts)${NC}"
    fi
done

# ── Train ─────────────────────────────────────────────────────────────────────
echo -e "\n${BLUE}[*] All ${ROUNDS} rounds complete. Training XGBoost model...${NC}"
python3 ml/scripts/train_model.py

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}  Pipeline complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "\n${BLUE}Next steps:${NC}"
echo -e "  1. Start the lab environment:"
echo -e "     ${YELLOW}cd docker && docker compose up -d --build${NC}"
echo -e ""
echo -e "  2. Start/reload the detector container:"
echo -e "     ${YELLOW}docker compose up -d --build detector${NC}"
echo -e "     ${YELLOW}docker restart detector${NC}  (if already running)"
echo -e ""
echo -e "  3. Watch live detections:"
echo -e "     ${YELLOW}docker logs -f detector${NC}"
echo -e ""
echo -e "  4. Deploy the worm to test detection:"
echo -e "     ${YELLOW}curl -s -c /tmp/jar -X POST -d 'username=admin&password=password123' http://localhost:8000/login${NC}"
echo -e "     ${YELLOW}curl -s -b /tmp/jar -X POST -H 'Content-Type: application/json' -d '{\"file\":\"worm.py\",\"strategy\":\"exhaustive\"}' http://localhost:8000/exec${NC}"
echo -e ""
echo -e "  5. View persisted alerts:"
echo -e "     ${YELLOW}cat docker/detector/logs/alerts.log${NC}"
