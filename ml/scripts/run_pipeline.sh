#!/bin/bash
# ML Pipeline Orchestrator
# CS 499 Capstone - Authorized Pentest Environment

echo "========================================"
echo "🧠 Worm Detection ML Pipeline"
echo "========================================"
echo ""

# Install dependencies if needed
echo "[*] Checking Python dependencies..."
pip3 install xgboost scikit-learn pandas joblib psutil 2>/dev/null || pip3 install xgboost scikit-learn pandas joblib psutil --break-system-packages 2>/dev/null

cd /home/greenballoons/499/DockerWormNetwork

echo ""
echo "PHASE 1: Collect Baseline (Normal Traffic)"
echo "Make sure worm is NOT running!"
read -p "Press Enter when ready (normal services only)..."
python3 ml/scripts/collect_baseline.py

echo ""
echo "PHASE 2: Collect Worm Traffic"
echo "Deploy the worm now via web UI or docker exec"
read -p "Press Enter when worm is RUNNING..."
python3 ml/scripts/collect_worm.py

echo ""
echo "PHASE 3: Train XGBoost Model"
python3 ml/scripts/train_model.py

echo ""
echo "PHASE 4: Real-Time Detection"
read -p "Press Enter to start real-time detector..."
python3 ml/scripts/detect.py
