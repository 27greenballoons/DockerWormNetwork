#!/usr/bin/env python3
"""
4-Hour Mass Data Collection Orchestrator
CS 499 Capstone - Authorized Pentest Environment (ID: ticq7)

Calibrated to run in ~4 hours (6 rounds × 2 strategies × 7.7 min/phase).
Auto-detects the next round number so it always continues from wherever
the existing CSVs left off.

Expected output: ~36,000 new samples on top of whatever exists.
"""

import os
import re
import sys
import time
import subprocess
import glob
from datetime import datetime

BASE_DIR = "/home/greenballoons/499/DockerWormNetwork"
DATA_DIR = f"{BASE_DIR}/ml/data"
LOG_FILE = f"{BASE_DIR}/ml/mass_collect_4h.log"
WORM_SRC = f"{BASE_DIR}/python/worm.py"
SHARED   = f"{BASE_DIR}/shared_data/worm.py"

# ── Parameters calibrated for 4 hours ─────────────────────────────────────────
# 6 rounds × 2 strategies × (2 × 460s collection + 280s overhead) ≈ 4.0 h
DURATION   = 460    # seconds per collection phase (baseline or worm)
INTERVAL   = 3      # polling interval in seconds
NUM_ROUNDS = 6
STRATEGIES = ["random", "exhaustive"]

# ── Logging ────────────────────────────────────────────────────────────────────
def log(msg):
    ts   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

# ── Round auto-detection ───────────────────────────────────────────────────────
def next_start_round() -> int:
    """Return the first round number not already present for any strategy."""
    existing = glob.glob(os.path.join(DATA_DIR, "baseline_traffic_*_*.csv"))
    if not existing:
        return 1
    rounds = set()
    for f in existing:
        m = re.search(r"baseline_traffic_[^_]+_(\d+)\.csv", os.path.basename(f))
        if m:
            rounds.add(int(m.group(1)))
    return max(rounds) + 1

# ── Lab management ─────────────────────────────────────────────────────────────
def wait_for_api(timeout=180):
    log("Waiting for api container...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = subprocess.run(
            ["sudo", "docker", "ps", "--format", "{{.Names}}"],
            capture_output=True, text=True
        )
        if "api" in r.stdout:
            time.sleep(15)  # Flask needs a moment to bind after container starts
            log("api container ready.")
            return True
        time.sleep(5)
    log("WARNING: api container did not appear — continuing anyway")
    return False

def reset_lab():
    log("Resetting lab...")
    r = subprocess.run(
        ["sudo", f"{BASE_DIR}/script/reset_compatible.sh"],
        capture_output=True, text=True, timeout=360
    )
    log(f"Reset exit={r.returncode}")
    wait_for_api()

def kill_worm_processes():
    targets = ["api", "webserver", "victim", "db", "redis",
               "postgres", "dns", "fileshare", "jumpbox", "traffic_gen"]
    for ct in targets:
        subprocess.run(
            ["sudo", "docker", "exec", ct, "pkill", "-f", "worm.py"],
            capture_output=True, timeout=5
        )

def deploy_worm(strategy: str):
    log(f"Copying worm.py → shared_data/")
    subprocess.run(["sudo", "cp", WORM_SRC, SHARED], check=True)
    subprocess.run(["sudo", "chmod", "644", SHARED])
    log(f"Launching worm inside api (strategy={strategy})...")
    subprocess.Popen([
        "sudo", "docker", "exec", "api",
        "python3", "/uploads/worm.py", "--strategy", strategy
    ])
    time.sleep(15)
    log("Worm deployed — beginning worm-traffic collection.")

# ── Data collection ────────────────────────────────────────────────────────────
def _run_collector(phase: str, outfile: str, env_key: str):
    script = "collect_baseline" if phase == "baseline" else "collect_worm"
    func   = "collect_baseline" if phase == "baseline" else "collect_worm_traffic"

    inline = (
        f"import sys; sys.path.insert(0, '{BASE_DIR}/ml/scripts'); "
        f"import {script} as m; "
        f"m.{func}(duration_seconds={DURATION}, interval={INTERVAL})"
    )

    env          = os.environ.copy()
    env[env_key] = outfile

    log(f"  [{phase}] → {os.path.basename(outfile)}")
    subprocess.run(["python3", "-c", inline], env=env)

def collect_baseline(outfile: str):
    _run_collector("baseline", outfile, "BASELINE_OUT")

def collect_worm(outfile: str):
    _run_collector("worm", outfile, "WORM_OUT")

# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    start_round   = next_start_round()
    end_round     = start_round + NUM_ROUNDS - 1
    total_phases  = NUM_ROUNDS * len(STRATEGIES)
    est_samples   = NUM_ROUNDS * len(STRATEGIES) * 2 * (DURATION // INTERVAL) * 10
    est_secs      = total_phases * (2 * DURATION + 280)

    log("=" * 65)
    log("4-Hour Mass Collection — CS 499 DockerWormNetwork")
    log(f"  Rounds:         {start_round}–{end_round}  ({NUM_ROUNDS} rounds)")
    log(f"  Strategies:     {STRATEGIES}")
    log(f"  Phase duration: {DURATION}s ({DURATION/60:.1f} min) baseline + worm")
    log(f"  Poll interval:  {INTERVAL}s")
    log(f"  Est. new samples: ~{est_samples:,}")
    log(f"  Est. wall time:   ~{est_secs/3600:.1f} h")
    log(f"  Log: {LOG_FILE}")
    log("=" * 65)

    completed = 0
    t_start   = time.time()

    for rnd in range(start_round, start_round + NUM_ROUNDS):
        for strategy in STRATEGIES:
            elapsed = (time.time() - t_start) / 3600
            remaining = total_phases - completed
            log(f"\n{'─'*65}")
            log(f"Round {rnd}  strategy={strategy}  |  "
                f"{completed}/{total_phases} done  |  {elapsed:.2f}h elapsed")
            log(f"{'─'*65}")

            b_file = os.path.join(DATA_DIR, f"baseline_traffic_{strategy}_{rnd}.csv")
            w_file = os.path.join(DATA_DIR, f"worm_traffic_{strategy}_{rnd}.csv")

            collect_baseline(b_file)
            deploy_worm(strategy)
            collect_worm(w_file)
            kill_worm_processes()
            reset_lab()

            completed += 1

    total_elapsed = (time.time() - t_start) / 3600
    log("\n" + "=" * 65)
    log(f"Collection complete in {total_elapsed:.2f}h. Training model...")
    log("=" * 65)
    subprocess.run(["python3", f"{BASE_DIR}/ml/scripts/train_model.py"])
    log("Done — results in ml/models/report.txt")

if __name__ == "__main__":
    main()
