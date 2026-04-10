#!/bin/bash
# cleanup_lab.sh
echo "[*] Stopping and removing containers..."
docker compose down

echo "[*] Cleaning shared_data volume..."
rm -f ./shared_data/*

echo "[*] Lab reset complete. Run 'docker compose up --build' to restart."