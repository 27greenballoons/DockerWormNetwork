#!/bin/bash

# Start the Docker containers in detached mode
echo "Starting simulation containers..."
docker compose up -d

# List of services from docker-compose.yaml
services=("c2_server" "dns" "webserver" "fileshare" "victim" "malware")

echo "Opening log terminals..."
for service in "${services[@]}"; do
    gnome-terminal --title="Logs: $service" -- bash -c "docker logs -f $service; echo '[Process Finished - Press Enter to Close]'; read" &
done

echo "All terminals opened. Simulation is running."
