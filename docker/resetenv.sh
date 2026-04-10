# DockerWormNetwork - Robust Reset

PROJECT_DIR="/home/greenballoons/499/DockerWormNetwork"

echo "[*] Cleaning up..."
pkill -f "python3.*dashboard.py" || true

# Check if directory exists before trying to CD
if [ -d "$PROJECT_DIR/docker" ]; then
    cd "$PROJECT_DIR/docker"
    # Run down, but don't crash if it's already down
    docker-compose down --volumes --remove-orphans || echo "Containers already down."
    
    # Re-up
    docker-compose up -d
else
    echo "ERROR: Could not find $PROJECT_DIR/docker"
    exit 1
fi

echo "SUCCESS: Lab Reset."