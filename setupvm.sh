#!/bin/bash
# DockerWormNetwork - Unified Deployment & Airgap Preparation Script
# Target: Ubuntu VM (Authorized for CS 499 Capstone)
set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}[*] Phase 1: Installing System Dependencies...${NC}"
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y \
    curl wget git python3 python3-pip python3-venv \
    iproute2 sshpass net-tools tree default-mysql-client \
    docker.io docker-compose

# Configure Docker permissions for future sessions
sudo usermod -aG docker $USER

echo -e "${BLUE}[*] Phase 2: Installing Host-Side Python SDK...${NC}"
# Use break-system-packages for newer Ubuntu versions (23.04+)
pip3 install docker requests flask --break-system-packages || pip3 install docker requests flask

echo -e "${BLUE}[*] Phase 3: Pre-pulling Docker Images...${NC}"
# Use frapsoft/snort as a more reliable base image for Snort 2.x rules
sudo docker pull python:3.9-slim
sudo docker pull busybox:latest
sudo docker pull frapsoft/snort

echo -e "${BLUE}[*] Phase 4: Creating Airgap Portable Bundle...${NC}"
mkdir -p ./airgap_bundle/python_wheels

# 1. Export Docker Images to Tarball
echo "[>] Saving Docker images to airgap_bundle/wormnet_images.tar..."
sudo docker save -o ./airgap_bundle/wormnet_images.tar \
    frapsoft/snort \
    python:3.9-slim \
    busybox:latest

# 2. Download Python Wheels with all sub-dependencies
echo "[>] Downloading recursive Python wheels to airgap_bundle/python_wheels/..."
pip3 download docker requests flask -d ./airgap_bundle/python_wheels/

echo -e "${GREEN}==================================================================${NC}"
echo -e "${GREEN}SUCCESS: Lab setup and Airgap Bundle ready!${NC}"
echo -e "${GREEN}==================================================================${NC}"
echo -e "${BLUE}TO DEPLOY IN AIRGAP ENVIRONMENT:${NC}"
echo -e "1. Move the 'airgap_bundle' folder to your isolated VM."
echo -e "2. Load images: ${NC}sudo docker load -i ./airgap_bundle/wormnet_images.tar"
echo -e "3. Setup Venv:  ${NC}python3 -m venv lab_env && source lab_env/bin/activate"
echo -e "4. Install Libs: ${NC}pip install --no-index --find-links=./airgap_bundle/python_wheels/ docker requests flask"
echo -e "${GREEN}==================================================================${NC}"
echo -e "Note: To use docker without 'sudo', please log out and back in now."