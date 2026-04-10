#!/usr/bin/env python3
"""
DockerWormNetwork - Mission Control Dashboard
Real-time multi-container log streaming for CS 499 Capstone
"""

import docker
import sys
import threading
import time
from datetime import datetime

try:
    client = docker.from_env()
    client.ping()
except Exception as e:
    print(f"[ERROR] Cannot connect to Docker: {e}")
    print("[HINT] Try running with: sudo python3 dashboard.py")
    sys.exit(1)

# ANSI colors
COLORS = {
    "api": "\033[94m",        # Blue
    "webserver": "\033[92m",  # Green
    "victim": "\033[93m",     # Yellow
    "ids": "\033[91m",        # Red
    "dns": "\033[96m",        # Cyan
    "fileshare": "\033[95m",  # Magenta
    "RESET": "\033[0m"
}

print("\n" + "="*70)
print("🚀  MISSION CONTROL: DockerWormNetwork Monitor")
print("="*70)
print("    Real-time log streaming from all network nodes")
print("    Press Ctrl+C to exit\n")

# Track which containers we're monitoring
active_streams = {}
lock = threading.Lock()

def stream_container_logs(container_name):
    """Stream logs continuously from a single container"""
    while True:
        try:
            container = client.containers.get(container_name)
            color = COLORS.get(container_name, "\033[90m")
            
            # Stream logs continuously
            for line in container.logs(stream=True, follow=True, tail=10):
                try:
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    log_line = line.decode('utf-8').strip()
                    if log_line:
                        with lock:
                            print(f"{timestamp} | {color}{container_name:12}{COLORS['RESET']} | {log_line}")
                except Exception:
                    pass
                    
        except docker.errors.NotFound:
            with lock:
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"{timestamp} | {'SYSTEM':12} | Container '{container_name}' not found, retrying...")
            time.sleep(3)
        except Exception as e:
            with lock:
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"{timestamp} | {'ERROR':12} | {container_name}: {str(e)[:50]}")
            time.sleep(2)

def monitor_events():
    """Monitor Docker events for container lifecycle"""
    try:
        for event in client.events(decode=True):
            if event.get('Type') == 'container':
                action = event.get('Action', '')
                name = event.get('Actor', {}).get('Attributes', {}).get('name', 'unknown')
                
                if action in ['start', 'die', 'stop', 'kill']:
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    emoji = "🟢" if action == 'start' else "🔴"
                    with lock:
                        print(f"\n{timestamp} | {'EVENT':12} | {emoji} Container '{name}' {action.upper()}")
                        
                    # If a container starts, make sure we're streaming it
                    if action == 'start' and name not in active_streams:
                        start_streaming(name)
                        
    except Exception as e:
        timestamp = datetime.now().strftime("%H:%M:%S")
        with lock:
            print(f"{timestamp} | {'EVENT ERROR':12} | {e}")

def start_streaming(container_name):
    """Start a log stream thread for a container"""
    if container_name not in active_streams:
        thread = threading.Thread(
            target=stream_container_logs, 
            args=(container_name,), 
            daemon=True
        )
        active_streams[container_name] = thread
        thread.start()
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{timestamp} | {'SYSTEM':12} | 📡 Attached to '{container_name}'")

def main():
    # Get initial container list
    expected_containers = ['api', 'webserver', 'victim', 'ids', 'dns', 'fileshare']
    
    # Start streaming for each expected container
    for name in expected_containers:
        start_streaming(name)
    
    # Start event monitor in background
    event_thread = threading.Thread(target=monitor_events, daemon=True)
    event_thread.start()
    
    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
            # Refresh container list periodically
            try:
                running = {c.name for c in client.containers.list()}
                for name in running:
                    if name not in active_streams:
                        start_streaming(name)
            except Exception:
                pass
    except KeyboardInterrupt:
        print("\n\n" + "="*70)
        print("👋  Shutting down Mission Control. Goodbye!")
        print("="*70 + "\n")
        sys.exit(0)

if __name__ == "__main__":
    main()

