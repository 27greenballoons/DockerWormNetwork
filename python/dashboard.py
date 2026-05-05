#!/usr/bin/env python3
"""
DockerWormNetwork - Mission Control Dashboard
Real-time multi-container log streaming with worm infection tracking.
CS 499 Capstone - Authorized Pentest Environment (ID: ticq7)
"""

import docker
import re
import sys
import threading
import time
from datetime import datetime

try:
    client = docker.from_env()
    client.ping()
except Exception as e:
    print(f"[ERROR] Cannot connect to Docker: {e}")
    print("[HINT] Try: sudo python3 dashboard.py")
    sys.exit(1)

# ── Colors ────────────────────────────────────────────────────────────────────
C = {
    # Entry point
    "api":          "\033[94m",   # Blue
    # HTTP exploit targets
    "webserver":    "\033[92m",   # Green
    "victim":       "\033[93m",   # Yellow
    # Database targets
    "db":           "\033[35m",   # Magenta
    "postgres":     "\033[95m",   # Bright Magenta
    # New exploit targets
    "redis":        "\033[91m",   # Red
    "jumpbox":      "\033[33m",   # Orange/Dark Yellow
    # Infrastructure
    "dns":          "\033[96m",   # Cyan
    "fileshare":    "\033[36m",   # Dark Cyan
    "traffic_gen":  "\033[90m",   # Dark Gray (noisy, de-emphasised)
    # System messages
    "WORM":         "\033[1;31m", # Bold Red
    "EVENT":        "\033[1;36m", # Bold Cyan
    "SYSTEM":       "\033[37m",   # Light Gray
    "RESET":        "\033[0m",
    "BOLD":         "\033[1m",
    "DIM":          "\033[2m",
}

# ── Infection state ───────────────────────────────────────────────────────────
infected_hosts: set  = set()
infection_log: list  = []        # [(timestamp, host, method)]
worm_cycle: int      = 0
worm_active: bool    = False
state_lock           = threading.Lock()

# Patterns that indicate a successful infection
INFECTION_PATTERNS = [
    (re.compile(r"\[>\] 🦠 Infecting (\S+)"),                          "attempting"),
    (re.compile(r"\[\+\] HTTP→(\S+?):\d+ payload delivered"),           "HTTP RCE"),
    (re.compile(r"\[\+\] SSH→(\S+?):\S+ Infected"),                     "SSH"),
    (re.compile(r"\[\+\] MySQL→(\S+?):\d+ .* File Written"),            "MySQL"),
    (re.compile(r"\[\+\] PostgreSQL→(\S+?):\d+ .* Infected"),           "PostgreSQL"),
    (re.compile(r"\[\+\] Redis→(\S+?):\d+ Infected"),                   "Redis"),
    (re.compile(r"\[💀\] MySQL→(\S+?) Harvested"),                      "cred-harvest"),
]

CYCLE_RE    = re.compile(r"=== CYCLE (\d+)/\d+ ===")
TOTAL_RE    = re.compile(r"Total infected: (\d+)")
WORM_START  = re.compile(r"DYNAMIC WORM|🪱")

# Lines too noisy to show (traffic_gen chatter, MySQL startup spam)
NOISE_RE = re.compile(
    r"Browsing:|Ping check:|Health probe:|API health check:|"
    r"mbind: Operation not permitted|"
    r"\[Note\]|InnoDB:|mysqld.*started"
)

# ── Shared state ──────────────────────────────────────────────────────────────
active_streams: dict = {}
print_lock           = threading.Lock()

# ── Helpers ───────────────────────────────────────────────────────────────────

def ts() -> str:
    return datetime.now().strftime("%H:%M:%S")

def print_line(container: str, text: str, override_color: str = ""):
    color = override_color or C.get(container, "\033[37m")
    with print_lock:
        print(f"{ts()} │ {color}{container:12}{C['RESET']} │ {text}")

def print_divider(label: str = ""):
    bar = "─" * 70
    with print_lock:
        if label:
            pad = (68 - len(label)) // 2
            print(f"\n{'─'*pad} {C['BOLD']}{label}{C['RESET']} {'─'*(68-pad-len(label))}\n")
        else:
            print(f"\n{bar}\n")

def parse_infection(line: str, container: str):
    global worm_cycle, worm_active
    if WORM_START.search(line):
        with state_lock:
            worm_active = True
    m = CYCLE_RE.search(line)
    if m:
        with state_lock:
            worm_cycle = int(m.group(1))
    for pattern, method in INFECTION_PATTERNS:
        m = pattern.search(line)
        if m:
            host = m.group(1).rstrip(":")
            with state_lock:
                if method != "attempting":
                    infected_hosts.add(host)
                infection_log.append((ts(), host, method))
            flag = "🦠 INFECTING" if method == "attempting" else f"💀 PWNED via {method}"
            print_line("WORM", f"{flag} → {C['BOLD']}{host}{C['RESET']}", C["WORM"])
            return

def is_worm_line(line: str) -> bool:
    return any(tok in line for tok in [
        "[+]", "[>]", "[*]", "[!]", "🦠", "💀", "📊", "🎯",
        "CYCLE", "infected", "Infected", "WORM", "payload", "Harvested",
    ])

# ── Log streaming ─────────────────────────────────────────────────────────────

def stream_container_logs(container_name: str):
    while True:
        try:
            container = client.containers.get(container_name)
            for raw in container.logs(stream=True, follow=True, tail=20):
                try:
                    line = raw.decode("utf-8", errors="replace").strip()
                    if not line:
                        continue
                    # Drop high-frequency noise
                    if NOISE_RE.search(line):
                        continue
                    # Intercept and highlight worm events from any container
                    parse_infection(line, container_name)
                    # Dim traffic_gen output; highlight worm lines from api
                    if container_name == "traffic_gen":
                        continue          # already too noisy; state is tracked above
                    if container_name == "api" and is_worm_line(line):
                        print_line(container_name, f"{C['BOLD']}{line}{C['RESET']}")
                    else:
                        print_line(container_name, line)
                except Exception:
                    pass
        except docker.errors.NotFound:
            print_line("SYSTEM", f"'{container_name}' not found — retrying in 5s…")
            time.sleep(5)
        except Exception as e:
            print_line("SYSTEM", f"{container_name} stream error: {str(e)[:60]}")
            time.sleep(3)

# ── Docker event monitor ──────────────────────────────────────────────────────

def monitor_events():
    try:
        for event in client.events(decode=True):
            if event.get("Type") != "container":
                continue
            action = event.get("Action", "")
            name   = event.get("Actor", {}).get("Attributes", {}).get("name", "unknown")
            if action in ("start", "die", "stop", "kill"):
                emoji = "🟢" if action == "start" else "🔴"
                print_line("EVENT", f"{emoji} {name} → {action.upper()}", C["EVENT"])
                if action == "start" and name not in active_streams:
                    start_streaming(name)
    except Exception as e:
        print_line("EVENT", f"Event monitor error: {e}")

# ── Infection status panel ────────────────────────────────────────────────────

def status_panel():
    while True:
        time.sleep(30)
        with state_lock:
            hosts  = sorted(infected_hosts)
            cycle  = worm_cycle
            active = worm_active
            recent = infection_log[-5:]

        print_divider("INFECTION STATUS")
        with print_lock:
            status = f"{C['WORM']}ACTIVE{C['RESET']}" if active else f"{C['DIM']}idle{C['RESET']}"
            print(f"  Worm status  : {status}   Cycle: {C['BOLD']}{cycle}{C['RESET']}")
            print(f"  Infected ({len(hosts)}) : {C['WORM']}{', '.join(hosts) if hosts else 'none yet'}{C['RESET']}")
            if recent:
                print(f"  Recent events:")
                for t, h, m in recent:
                    print(f"    {C['DIM']}{t}{C['RESET']}  {h:20} via {m}")
        print_divider()

# ── Startup ───────────────────────────────────────────────────────────────────

def start_streaming(container_name: str):
    if container_name in active_streams:
        return
    t = threading.Thread(target=stream_container_logs, args=(container_name,), daemon=True)
    active_streams[container_name] = t
    t.start()
    print_line("SYSTEM", f"📡 Attached to '{container_name}'")

def main():
    with print_lock:
        print("\n" + "═" * 70)
        print(f"  {C['BOLD']}MISSION CONTROL — DockerWormNetwork{C['RESET']}")
        print("  CS 499 Capstone  │  Authorized Lab (ID: ticq7)")
        print("  Containers: api · webserver · victim · db · dns · fileshare")
        print("              redis · postgres · jumpbox · traffic_gen")
        print("  Ctrl+C to exit")
        print("═" * 70 + "\n")

    # All containers in the network
    all_containers = [
        "api", "webserver", "victim", "db",
        "redis", "postgres", "jumpbox",
        "dns", "fileshare", "traffic_gen",
    ]

    # Attach to whatever is currently running
    running = {c.name for c in client.containers.list()}
    for name in all_containers:
        if name in running:
            start_streaming(name)
        else:
            print_line("SYSTEM", f"'{name}' not running (will attach if it starts)")

    threading.Thread(target=monitor_events, daemon=True).start()
    threading.Thread(target=status_panel,   daemon=True).start()

    try:
        while True:
            time.sleep(5)
            # Auto-attach to any new containers that appeared
            try:
                running = {c.name for c in client.containers.list() if c.name}
                for name in running:
                    if name not in active_streams:
                        start_streaming(name)
            except Exception:
                pass
    except KeyboardInterrupt:
        with print_lock:
            print("\n" + "═" * 70)
            with state_lock:
                hosts = sorted(infected_hosts)
            print(f"  Final infected hosts ({len(hosts)}): {', '.join(hosts) if hosts else 'none'}")
            print(f"  Goodbye.")
            print("═" * 70 + "\n")
        sys.exit(0)

if __name__ == "__main__":
    main()
