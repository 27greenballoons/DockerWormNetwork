# DockerWormNetwork - Dependencies Report

## Executive Summary
This report documents all dependencies required to deploy the DockerWormNetwork project on a virtual machine.

---

## 1. System-Level Dependencies

### Required Software
| Package | Version | Purpose | Source |
|---------|---------|---------|--------|
| Docker Engine | 20.10+ | Container orchestration | docker.io or docker-ce |
| Docker Compose | 1.29+ / 2.x | Multi-container management | Included with Docker or separate |
| Python | 3.9+ | Host-side scripting | python3, python3-pip |
| pip | 21+ | Python package management | python3-pip |

### Ubuntu/Debian Installation Commands
```bash
# Update package lists
sudo apt-get update

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Or via apt
sudo apt-get install -y docker.io docker-compose

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Install Python and pip
sudo apt-get install -y python3 python3-pip python3-venv
```

---

## 2. Docker Images (Auto-Downloaded)

The following images are pulled automatically by `docker-compose`:

| Image | Tag | Purpose | Size |
|-------|-----|---------|------|
| python | 3.9-slim | Base for Flask API, webserver, victim | ~45MB |
| busybox | latest | DNS and fileshare containers | ~1MB |
| jasonish/snort | latest | IDS/IPS container (optional) | ~200MB |

**Note:** If the Snort IDS service is uncommented in docker-compose.yaml, the Snort image will be downloaded.

---

## 3. Python Dependencies

### 3.1 Docker Container Dependencies (Installed via Dockerfile)

**APT Packages:**
```
iproute2          # Network interface management (worm IP discovery)
wget              # HTTP downloading
curl              # HTTP requests and worm propagation
sshpass           # SSH brute-force attempts
```

**Python Packages:**
```
flask>=2.0        # Web API framework
requests>=2.25    # HTTP client for worm propagation
```

### 3.2 Host Machine Python Dependencies

For running `dashboard.py` and other host-side tools:

| Package | Version | Purpose | Installation |
|---------|---------|---------|--------------|
| docker | 6.0+ | Docker SDK for Python | `pip3 install docker` |

**Installation Command:**
```bash
pip3 install docker
```

### 3.3 Optional Python Dependencies (for extended functionality)

| Package | Purpose | Usage Location |
|---------|---------|----------------|
| mysql-connector-python | MySQL exploitation | worm.py (commented) |
| psycopg2 | PostgreSQL exploitation | worm.py (commented) |
| redis | Redis exploitation | worm.py (commented) |
| paramiko | SSH operations | worm.py (alternative to sshpass) |

---

## 4. Standard Library Dependencies (Built-in)

The following Python standard library modules are used (no installation required):

### worm.py
- `socket` - Network communication
- `subprocess` - Command execution
- `threading` - Concurrent operations
- `time` - Timing and delays
- `random` - Randomization
- `os` - File system operations
- `sys` - System interface
- `json` - Data serialization
- `base64` - Encoding
- `concurrent.futures` - Thread pool
- `itertools` - Iteration utilities
- `urllib.parse` - URL parsing
- `ssl` - SSL/TLS support
- `http.server` - HTTP server hosting
- `socketserver` - Socket server base

### vulnerable_server.py
- `http.server` - HTTP request handling
- `socketserver` - TCP server
- `urllib.parse` - Query parameter parsing
- `subprocess` - Command execution (vulnerability)
- `os` - OS operations (vulnerability)

### app.py (Flask)
- Standard Flask dependencies only

### dashboard.py
- `sys` - System interface
- `datetime` - Timestamp formatting

---

## 5. Network Dependencies

### Ports Used

| Port | Protocol | Service | Description |
|------|----------|---------|-------------|
| 22 | TCP | SSH | SSH brute-force target |
| 80 | TCP | HTTP | Vulnerable webserver |
| 8000 | TCP | HTTP | Flask API (exposed to host) |
| 8080 | TCP | HTTP | Worm self-hosting server |
| 8888 | TCP | HTTP | Victim HTTP server |
| 3306 | TCP | MySQL | MySQL exploitation target |
| 5432 | TCP | PostgreSQL | PostgreSQL target |
| 6379 | TCP | Redis | Redis exploitation target |

---

## 6. Complete Setup Script

Create a setup script `setup_vm.sh`:

```bash
#!/bin/bash
# DockerWormNetwork VM Setup Script

set -e

echo "[*] Updating package lists..."
sudo apt-get update

echo "[*] Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
fi

echo "[*] Installing Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    sudo apt-get install -y docker-compose
fi

echo "[*] Installing Python and pip..."
sudo apt-get install -y python3 python3-pip

echo "[*] Installing host Python dependencies..."
pip3 install docker

echo "[*] Verifying installations..."
docker --version
docker-compose --version
python3 --version

echo "[+] Setup complete! Log out and log back in for group changes to take effect."
echo "[*] To start the lab: cd /path/to/DockerWormNetwork/docker && docker-compose up --build"
```

Run with:
```bash
chmod +x setup_vm.sh
./setup_vm.sh
```

---

## 7. Offline/Air-Gapped Deployment

For VMs without internet access, pre-download:

1. **Docker Images:**
```bash
docker pull python:3.9-slim
docker pull busybox:latest
docker pull jasonish/snort:latest
docker save python:3.9-slim busybox:latest jasonish/snort:latest > wormnet_images.tar
```

2. **Transfer to VM and load:**
```bash
docker load < wormnet_images.tar
```

3. **Python Wheels (for host-side tools):**
```bash
pip3 download docker -d ./wheels
pip3 install --no-index --find-links=./wheels docker
```

---

## 8. Verification Checklist

After setup, verify with:

```bash
# Test Docker
docker run hello-world

# Test Docker Compose
docker-compose version

# Test Python imports
python3 -c "import docker; print('docker SDK OK')"

# Test network capability (inside container)
docker run --rm python:3.9-slim python3 -c "import socket; print('Network OK')"
```

---

## 9. File Structure Requirements

Ensure this directory structure exists:

```
/home/greenballoons/499/DockerWormNetwork/
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.yaml
│   ├── flask/
│   │   ├── app.py
│   │   ├── templates/
│   │   │   └── index.html
│   │   └── static/
│   │       └── style.css
│   └── ids/
│       └── rules/
│           ├── local.rules
│           └── snort-local.conf
├── python/
│   ├── worm.py
│   ├── vulnerable_server.py
│   └── dashboard.py
├── shared_data/
│   └── (empty directory for uploads)
└── DEPENDENCIES_REPORT.md (this file)
```

---

## 10. Security Considerations

- **Isolated Network**: The `micro_internet` bridge network should be isolated
- **Privileged Containers**: Snort IDS requires `--cap-add=NET_ADMIN --cap-add=NET_RAW`
- **Root Access**: The Flask API container runs as root (required for worm execution)

---

*Report Generated: April 2025*
*Project: DockerWormNetwork - CS 499 Capstone*

