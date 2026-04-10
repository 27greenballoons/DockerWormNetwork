# DockerWormNetwork - User Guide

## 📋 Overview

**DockerWormNetwork** is an isolated network security lab designed for the CS 499 Capstone project. It simulates a corporate network with vulnerable services, allowing authorized testing of network worm propagation and IDS detection.

**Authorization Status**: ✅ Authorized for CS 499 Capstone testing (ID: ticq7)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         YOUR VM (HOST)                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │  Dashboard   │  │   Browser    │  │   reset.sh Script    │   │
│  │  (Monitor)   │  │   (Upload)   │  │   (Clean Slate)      │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │              Docker Network: micro_internet                  ││
│  │  ┌──────────┐ ┌──────────┐ ┌─────────┐ ┌──────────┐        ││
│  │  │   api    │ │webserver │ │ victim  │ │   ids    │        ││
│  │  │  :8000   │ │  :80     │ │  :8888  │ │ (Snort)  │        ││
│  │  │  [FLASK] │ │[VULNERABLE]│ │[HTTP]   │ │  [IDS]   │        ││
│  │  └──────────┘ └──────────┘ └─────────┘ └──────────┘        ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### Container Descriptions

| Container | Purpose | Vulnerabilities |
|-----------|---------|-----------------|
| `api` | Flask web interface for uploading/executing scripts | File upload + RCE |
| `webserver` | Vulnerable Python HTTP server | Command injection (`/ping?ip=`), RCE (`/exec`) |
| `victim` | Standard Python HTTP server | None (infection target) |
| `ids` | Snort intrusion detection system | None (monitoring only) |

---

## 🚀 Quick Start

### Step 1: Initial Setup (First Time Only)

```bash
cd /home/greenballoons/499/DockerWormNetwork

# Make reset script executable
chmod +x script/reset.sh

# Copy worm.py to shared data (for easy access)
cp python/worm.py shared_data/
```

### Step 2: Deploy the Lab

```bash
# Run the reset script (builds and starts everything)
sudo ./script/reset.sh
```

**What this does:**
- Kills any running background processes
- Destroys old containers (cleans infected state)
- Purges logs and uploaded files
- Rebuilds containers with latest code
- Starts fresh environment

### Step 3: Verify Everything is Running

```bash
sudo docker ps
```

You should see 4 containers: `api`, `webserver`, `victim`, `ids`

---

## 🎮 Running the Worm Attack

### Method 1: Web Interface (Recommended)

1. **Open browser** to: `http://YOUR_VM_IP:8000`
   - Or locally: `http://localhost:8000`

2. **You will see**: "Internal Document Management System - Acme Corp"

3. **Upload worm.py**:
   - Click the upload area or drag-and-drop `worm.py`
   - **worm.py auto-executes** upon upload!
   - You'll see: "✅ worm.py uploaded! Network propagation started automatically"

4. **Watch propagation**:
   - The worm spreads to `webserver`, `victim`, `dns`, `fileshare`
   - Infected containers run worm in background

### Method 2: Command Line (curl)

```bash
# Upload and auto-execute
curl -X POST -F "file=@shared_data/worm.py" http://localhost:8000/upload
```

### Method 3: Manual Execution

1. Upload any file (doesn't auto-execute unless named `worm.py`)
2. Click the **"▶ Execute"** button next to the file

---

## 📊 Monitoring the Attack

### Terminal 1: Real-Time Dashboard

```bash
cd /home/greenballoons/499/DockerWormNetwork
python3 python/dashboard.py
```

**Shows**: Color-coded logs from all containers in real-time

### Terminal 2: Snort IDS Alerts

```bash
sudo tail -f /home/greenballoons/499/DockerWormNetwork/docker/ids/logs/alert.log
```

**Shows**: IDS alerts when worm activity is detected

### Terminal 3: Individual Container Logs

```bash
# Watch API container
sudo docker logs -f api

# Watch webserver (first victim)
sudo docker logs -f webserver

# Watch victim container
sudo docker logs -f victim
```

---

## 🔄 Resetting the Lab

When you want to start fresh (kill all worms, clean everything):

```bash
sudo /home/greenballoons/499/DockerWormNetwork/script/reset.sh
```

**Why you need this:**
- Worms run in **background** (`&`) on infected containers
- Simply stopping the main process doesn't kill spawned worms
- `reset.sh` destroys containers completely (nuclear option)
- Creates fresh containers from clean images

---

## 🛡️ Safety Features

### 1. Network Isolation
- Docker bridge network (`micro_internet`) contains all traffic
- No connection to host network or internet (unless configured)
- Worm's `verify_isolation()` function aborts if internet detected

### 2. Auto-Containment
- All containers are ephemeral
- `reset.sh` destroys and recreates them
- No persistence between reset cycles

### 3. Port Mapping
Only port `8000` (Flask API) is exposed to host:
```yaml
ports:
  - "8000:8000"  # Only this is accessible from outside
```

---

## 🐛 Troubleshooting

### "Permission Denied" Errors
```bash
# Always use sudo for reset.sh
sudo ./script/reset.sh

# Or add yourself to docker group (then logout/login)
sudo usermod -aG docker $USER
```

### "Cannot connect to Docker daemon"
```bash
# Start Docker service
sudo systemctl start docker

# Enable auto-start
sudo systemctl enable docker
```

### Worm Not Propagating
1. Check if containers can talk to each other:
   ```bash
   sudo docker exec api ping webserver -c 3
   ```

2. Check if worm.py is in uploads:
   ```bash
   sudo docker exec api ls -la /uploads/
   ```

3. Check logs for errors:
   ```bash
   sudo docker logs api
   ```

### Snort Not Alerting
1. Verify IDS container is running:
   ```bash
   sudo docker ps | grep ids
   ```

2. Check Snort logs exist:
   ```bash
   ls -la docker/ids/logs/
   ```

3. Trigger a test alert:
   ```bash
   curl "http://localhost:8000/ping?ip=;whoami"
   ```

---

## 📁 File Locations

| File | Purpose |
|------|---------|
| `script/reset.sh` | **Main reset tool** - Clean/reset entire lab |
| `script/check_infection.sh` | **Infection status** - Check all containers |
| `script/monitor.sh` | **Container monitor** - Watch specific container logs |
| `script/snort_watch.sh` | **IDS monitor** - Color-coded Snort alerts |
| `docker/flask/app.py` | Flask API backend |
| `docker/flask/templates/index.html` | Web interface |
| `python/worm.py` | **The worm** - Upload this via web UI |
| `python/vulnerable_server.py` | Vulnerable target service |
| `python/dashboard.py` | Multi-container dashboard |
| `docker/ids/rules/local.rules` | Snort detection rules |
| `shared_data/` | Upload landing zone |

---

## 🎯 Testing Workflow

### Typical Attack Sequence

```bash
# 1. Start fresh environment
sudo ./script/reset.sh

# 2. In Terminal 1: Start monitoring
python3 python/dashboard.py

# 3. In Terminal 2: Watch IDS
sudo tail -f docker/ids/logs/alert.log

# 4. In Browser: Upload worm.py
# Navigate to http://localhost:8000
# Upload -> worm.py auto-executes

# 5. Watch propagation in dashboard
# You should see infection messages

# 6. When done, reset
sudo ./script/reset.sh
```

---

## 🔐 Authorization

**Project**: CS 499 Capstone - Network Security  
**Scope**: Isolated Docker Lab Environment  
**Authorization ID**: ticq7  
**Status**: ✅ Authorized for testing

This environment is designed for:
- Educational network security research
- IDS/IPS testing and validation
- Controlled worm propagation studies
- Incident response training

---

## 📊 Monitoring the Infection (8 Different Methods)

The lab provides **multiple ways** to observe worm propagation, from simple commands to comprehensive dashboards.

### Method 1: `check_infection.sh` (Recommended - Complete Status)
**One command shows everything: infection status, running processes, IDS alerts.**

```bash
./script/check_infection.sh
```

**Shows:**
- ✅ Which containers are infected (worm.py in /tmp)
- 🐛 Running worm processes
- 🌐 Active HTTP drop servers
- 🚨 Recent Snort alerts
- 🔗 Network connections

---

### Method 2: `monitor.sh` (Watch Specific Container)
**Real-time logs from any single container:**

```bash
# Watch API (where worm starts)
./script/monitor.sh api

# Watch first victim being exploited
./script/monitor.sh webserver

# Watch secondary infection
./script/monitor.sh victim

# Watch IDS alerts
./script/monitor.sh ids
```

---

### Method 3: `snort_watch.sh` (IDS Alert Focus)
**Color-coded Snort alerts with real-time updates:**

```bash
./script/snort_watch.sh
```

**Color coding:**
- 🐛 **Red** = Worm activity detected
- 💥 **Purple** = Exploit/Injection attempts
- 🔍 **Yellow** = Port scanning
- 🔌 **Blue** = Service exploitation (Redis, SSH, etc.)

---

### Method 4: `dashboard.py` (Visual Multi-Stream)
**Real-time color-coded logs from ALL containers:**

```bash
# With sudo (if not in docker group)
sudo python3 python/dashboard.py

# Without sudo (if in docker group)
python3 python/dashboard.py
```

**Shows:**
- Color-coded output per container
- Container start/stop events
- Continuous streaming from all nodes

---

### Method 5: Direct Docker Commands
**Manual container inspection:**

```bash
# Check if specific container is infected
sudo docker exec webserver ls -la /tmp/worm.py

# Check running processes
sudo docker exec webserver ps aux | grep python

# View logs
sudo docker logs -f webserver
```

---

### Method 6: Web Interface Status
**Browser-based monitoring:**

1. Go to `http://localhost:8000`
2. Observe:
   - **"Active Nodes"** count
   - **"Network Status"** indicator
   - Script list with auto-execution badges

---

### Method 7: Manual Log Inspection
**Check raw log files:**

```bash
# Snort alerts
sudo tail -f docker/ids/logs/alert.log

# Container logs location
sudo find docker/ids/logs/ -type f
```

---

### Method 8: Network Evidence
**Verify propagation activity:**

```bash
# Check worm HTTP server (port 8080) on each container
for c in api webserver victim; do
  echo "=== $c ==="
  sudo docker exec $c ss -tln | grep 8080 || echo "No server"
done

# Check established connections
sudo docker exec api ss -t -o state established
```

---

## 🎯 Recommended Monitoring Setup

**For the best observation experience, open 4 terminals:**

| Terminal | Command | Purpose |
|----------|---------|---------|
| **1** | `./script/check_infection.sh` | Run periodically to see infection spread |
| **2** | `./script/monitor.sh webserver` | Watch first victim get exploited |
| **3** | `./script/snort_watch.sh` | See IDS alerts in real-time |
| **4** | Browser at `localhost:8000` | Upload worm and watch UI updates |

Then upload `worm.py` and watch infection propagate across all views!

---

## 📝 Quick Command Reference

| Action | Command |
|--------|---------|
| **Reset Lab** | `sudo ./script/reset.sh` |
| **Check Infection Status** | `./script/check_infection.sh` |
| **Watch Container Logs** | `./script/monitor.sh <container>` |
| **Watch IDS Alerts** | `./script/snort_watch.sh` |
| **View Dashboard** | `sudo python3 python/dashboard.py` |
| **View IDS Logs** | `sudo tail -f docker/ids/logs/alert.log` |
| **List Containers** | `sudo docker ps` |
| **Container Logs** | `sudo docker logs -f <container>` |
| **Exec into Container** | `sudo docker exec -it <container> bash` |
| **Upload via curl** | `curl -F "file=@worm.py" http://localhost:8000/upload` |
| **Stop All** | `sudo docker-compose down` |

---

## 🎓 For Instructors/Reviewers

To verify the worm works:
1. Run `sudo ./script/reset.sh`
2. Open browser to `http://VM_IP:8000`
3. Upload `worm.py` (it will auto-execute)
4. Watch `dashboard.py` show infection across nodes
5. Check Snort logs for detection alerts
6. Run `reset.sh` again to clean

---

*Generated for CS 499 Capstone Project*  
*DockerWormNetwork v1.0*


