#!/usr/bin/env python3
"""
Mass Data Collection Orchestrator
CS 499 Capstone - Authorized Pentest Environment (ID: ticq7)

Runs N rounds of baseline + worm collection for both strategies,
resetting the lab between each round. Designed for unattended overnight runs.

Outputs files: baseline_traffic_{strategy}_{round}.csv / worm_traffic_{strategy}_{round}.csv
"""

import os
import sys
import time
import subprocess
from datetime import datetime

BASE_DIR  = "/home/greenballoons/499/DockerWormNetwork"
DATA_DIR  = f"{BASE_DIR}/ml/data"
LOG_FILE  = f"{BASE_DIR}/ml/mass_collect.log"
WORM_SRC  = f"{BASE_DIR}/python/worm.py"
SHARED    = f"{BASE_DIR}/shared_data/worm.py"

# ── Collection parameters ──────────────────────────────────────────────────────
DURATION    = 600       # seconds per phase (10 min baseline + 10 min worm)
INTERVAL    = 3         # polling interval in seconds (was 5 → ~2x more samples)
START_ROUND = 4         # rounds 1–3 already exist
NUM_ROUNDS  = 10        # collect rounds 4–13 (10 new rounds per strategy)
STRATEGIES  = ["random", "exhaustive"]

# Derived estimates
_secs_per_round = (DURATION * 2 + 30 + 200) * len(STRATEGIES)  # ~27 min/round
_total_rounds   = NUM_ROUNDS * len(STRATEGIES)
_est_samples    = NUM_ROUNDS * len(STRATEGIES) * 2 * (DURATION // INTERVAL) * 10  # ~10 containers

# ── Logging ────────────────────────────────────────────────────────────────────
def log(msg):
    ts   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

# ── Lab management ─────────────────────────────────────────────────────────────
def wait_for_api(timeout=180):
    """Poll until the api container is up and Flask responds."""
    log("Waiting for api container...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = subprocess.run(
            ["sudo", "docker", "ps", "--format", "{{.Names}}"],
            capture_output=True, text=True
        )
        if "api" in r.stdout:
            # Give Flask a few extra seconds to bind
            time.sleep(15)
            log("api container ready.")
            return True
        time.sleep(5)
    log("WARNING: api container did not appear within timeout — continuing anyway")
    return False

def reset_lab():
    log("Resetting lab (docker compose down → rebuild → up)...")
    r = subprocess.run(
        ["sudo", f"{BASE_DIR}/script/reset_compatible.sh"],
        capture_output=True, text=True, timeout=300
    )
    log(f"Reset exit={r.returncode}")
    wait_for_api()

def kill_worm_processes():
    """Best-effort pkill worm.py inside all containers."""
    targets = ["api", "webserver", "victim", "db", "redis", "postgres",
               "dns", "fileshare", "jumpbox", "traffic_gen"]
    for ct in targets:
        subprocess.run(
            ["sudo", "docker", "exec", ct, "pkill", "-f", "worm.py"],
            capture_output=True, timeout=5
        )

def deploy_worm(strategy: str):
    """Copy worm into shared_data (mounted as /uploads in api) then exec it."""
    log(f"Copying worm.py → shared_data/")
    subprocess.run(["sudo", "cp", WORM_SRC, SHARED], check=True)
    subprocess.run(["sudo", "chmod", "644", SHARED])

    log(f"Launching worm inside api (strategy={strategy})...")
    subprocess.Popen([
        "sudo", "docker", "exec", "api",
        "python3", "/uploads/worm.py", "--strategy", strategy
    ])
    # Give the worm a head-start before collection begins
    time.sleep(15)
    log("Worm deployed — beginning worm-traffic collection phase.")

# ── Data collection ────────────────────────────────────────────────────────────
def _run_collector(phase: str, outfile: str, env_key: str):
    """
    Launch collect_baseline.py or collect_worm.py as a subprocess with
    the output file and custom duration/interval injected via env + -c.
    Running as a fresh subprocess ensures the module-level BASELINE_FILE /
    WORM_FILE picks up the correct env var each time.
    """
    script = "collect_baseline" if phase == "baseline" else "collect_worm"
    func   = "collect_baseline" if phase == "baseline" else "collect_worm_traffic"

    inline = (
        f"import sys; sys.path.insert(0, '{BASE_DIR}/ml/scripts'); "
        f"import {script} as m; "
        f"m.{func}(duration_seconds={DURATION}, interval={INTERVAL})"
    )

    env = os.environ.copy()
    env[env_key] = outfile

    log(f"  [{phase}] → {os.path.basename(outfile)}")
    subprocess.run(["python3", "-c", inline], env=env)

def collect_baseline(outfile: str):
    _run_collector("baseline", outfile, "BASELINE_OUT")

def collect_worm(outfile: str):
    _run_collector("worm", outfile, "WORM_OUT")

# ── Main loop ──────────────────────────────────────────────────────────────────
def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    end_round   = START_ROUND + NUM_ROUNDS - 1
    est_hours   = _secs_per_round * NUM_ROUNDS / 3600

    log("=" * 65)
    log("Mass Collection Orchestrator — CS 499 DockerWormNetwork")
    log(f"  Rounds:     {START_ROUND}–{end_round}  ({NUM_ROUNDS} per strategy)")
    log(f"  Strategies: {STRATEGIES}")
    log(f"  Duration:   {DURATION}s baseline + {DURATION}s worm per phase")
    log(f"  Interval:   {INTERVAL}s  (was 5s — ~{5//INTERVAL + 1}x more samples)")
    log(f"  Est. new samples: ~{_est_samples:,}")
    log(f"  Est. wall time:   ~{est_hours:.1f} hours")
    log(f"  Log file:   {LOG_FILE}")
    log("=" * 65)

    completed = 0
    for rnd in range(START_ROUND, START_ROUND + NUM_ROUNDS):
        for strategy in STRATEGIES:
            log(f"\n{'─'*65}")
            log(f"Round {rnd}  |  strategy={strategy}  |  {completed}/{_total_rounds} done")
            log(f"{'─'*65}")

            b_file = os.path.join(DATA_DIR, f"baseline_traffic_{strategy}_{rnd}.csv")
            w_file = os.path.join(DATA_DIR, f"worm_traffic_{strategy}_{rnd}.csv")

            # 1. Baseline
            collect_baseline(b_file)

            # 2. Deploy worm
            deploy_worm(strategy)

            # 3. Worm traffic
            collect_worm(w_file)

            # 4. Clean up and reset
            kill_worm_processes()
            reset_lab()

            completed += 1
            log(f"Round {rnd}/{strategy} complete. {completed}/{_total_rounds} total rounds done.")

    # ── Train on the full combined dataset ─────────────────────────────────────
    log("\n" + "=" * 65)
    log("All collection rounds complete. Training XGBoost model...")
    log("=" * 65)
    subprocess.run(["python3", f"{BASE_DIR}/ml/scripts/train_model.py"])
    log("Done. Results → ml/models/report.txt")

if __name__ == "__main__":
    main()
