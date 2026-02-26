import docker
import sys
from datetime import datetime

# Initialize Docker client
client = docker.from_env()

# ANSI colors for the "Beast" look
COLORS = {
    "malware": "\033[91m",    # Red
    "webserver": "\033[92m",  # Green
    "c2_server": "\033[94m",  # Blue
    "victim": "\033[93m",     # Yellow
    "RESET": "\033[0m"
}

print("--- MISSION CONTROL ACTIVE: MONITORING MICRO_INTERNET ---", flush=True)

def stream_logs():
    # We follow all containers in our network
    containers = client.containers.list()
    
    # Using a generator to stream logs from all active containers
    for container in containers:
        print(f"[*] Attached to {container.name}", flush=True)

    # Simple multi-stream log tailing
    # Note: For a true real-time multi-view, we'd use threads, 
    # but this simple loop shows how to capture events.
    try:
        for event in client.events(decode=True):
            if event['Type'] == 'container' and event['Action'] == 'exec_start':
                print(f"[!] EVENT: {event['from']} executed a command", flush=True)
            
            # For this lab, it's easier to just tail the logs of our main services
            for container in containers:
                color = COLORS.get(container.name, "")
                log_lines = container.logs(tail=1).decode('utf-8').strip()
                if log_lines:
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    print(f"{timestamp} | {color}{container.name:10}{COLORS['RESET']} | {log_lines}", flush=True)
    except KeyboardInterrupt:
        print("\nShutting down Mission Control.")

if __name__ == "__main__":
    stream_logs()