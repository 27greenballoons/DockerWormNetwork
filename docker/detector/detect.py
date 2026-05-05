#!/usr/bin/env python3
"""
Worm Detection Container
CS 499 Capstone - Authorized Pentest Environment (ID: ticq7)

Runs continuously inside Docker, polls container stats every 5s,
and alerts when the XGBoost model detects worm activity.
Waits for the model to exist before starting (safe to launch before training).
"""

import docker
import joblib
import json
import time
import os
import pandas as pd
from datetime import datetime

MODEL_DIR = os.environ.get("MODEL_DIR", "/models")
LOG_DIR   = os.environ.get("LOG_DIR",   "/logs")
INTERVAL  = int(os.environ.get("DETECT_INTERVAL", "5"))
THRESHOLD = float(os.environ.get("DETECT_THRESHOLD", "0.5"))

MODEL_PATH   = os.path.join(MODEL_DIR, "worm_detector.pkl")
FEATURES_PATH = os.path.join(MODEL_DIR, "features.json")
ALERT_LOG    = os.path.join(LOG_DIR, "alerts.log")

os.makedirs(LOG_DIR, exist_ok=True)

def wait_for_model():
    print("[*] Detector waiting for trained model...", flush=True)
    while not (os.path.exists(MODEL_PATH) and os.path.exists(FEATURES_PATH)):
        time.sleep(10)
    print(f"[*] Model found at {MODEL_PATH} — starting detection", flush=True)

def load_model():
    model    = joblib.load(MODEL_PATH)
    with open(FEATURES_PATH) as f:
        features = json.load(f)
    return model, features

def get_stats(container):
    try:
        stats = container.stats(stream=False)

        cpu_delta    = stats["cpu_stats"]["cpu_usage"]["total_usage"] - stats["precpu_stats"]["cpu_usage"]["total_usage"]
        system_delta = stats["cpu_stats"]["system_cpu_usage"] - stats["precpu_stats"]["system_cpu_usage"]
        cpu_pct      = (cpu_delta / system_delta) * 100.0 if system_delta > 0 else 0.0

        mem_stats  = stats.get("memory_stats", {})
        mem_usage  = mem_stats.get("usage", 0)
        mem_limit  = mem_stats.get("limit", 1)
        mem_pct    = (mem_usage / mem_limit) * 100.0 if mem_limit > 0 else 0.0
        mem_detail = mem_stats.get("stats", {})
        mem_rss    = mem_detail.get("rss", 0)

        networks  = stats.get("networks", {})
        net_rx    = sum(n.get("rx_bytes",   0) for n in networks.values())
        net_tx    = sum(n.get("tx_bytes",   0) for n in networks.values())
        net_rx_pk = sum(n.get("rx_packets", 0) for n in networks.values())
        net_tx_pk = sum(n.get("tx_packets", 0) for n in networks.values())

        blk_entries = stats.get("blkio_stats", {}).get("io_service_bytes_recursive") or []
        blk_read  = sum(e["value"] for e in blk_entries if e.get("op") == "Read")
        blk_write = sum(e["value"] for e in blk_entries if e.get("op") == "Write")

        pids_count = stats.get("pids_stats", {}).get("current", 0)

        return {
            "cpu_percent":    round(cpu_pct, 4),
            "mem_percent":    round(mem_pct, 4),
            "mem_rss_bytes":  mem_rss,
            "net_rx_bytes":   net_rx,
            "net_tx_bytes":   net_tx,
            "net_rx_packets": net_rx_pk,
            "net_tx_packets": net_tx_pk,
            "blk_read_bytes":  blk_read,
            "blk_write_bytes": blk_write,
            "pids_count":      pids_count,
        }
    except:
        return {k: 0 for k in [
            "cpu_percent", "mem_percent", "mem_rss_bytes",
            "net_rx_bytes", "net_tx_bytes", "net_rx_packets", "net_tx_packets",
            "blk_read_bytes", "blk_write_bytes", "pids_count",
        ]}

def get_connections(container):
    try:
        out = container.exec_run(
            "ss -tan 2>/dev/null || netstat -tan 2>/dev/null", demux=False
        ).output.decode(errors="replace")
        return (
            out.count("ESTABLISHED"),
            out.count("LISTEN"),
            out.count("TIME-WAIT") + out.count("TIME_WAIT"),
            out.count("CLOSE-WAIT") + out.count("CLOSE_WAIT"),
        )
    except:
        return 0, 0, 0, 0

def get_procs(container):
    try:
        return int(container.exec_run("ps aux | wc -l", demux=False).output.decode().strip())
    except:
        return 0

def log_alert(message):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {message}"
    print(line, flush=True)
    with open(ALERT_LOG, "a") as f:
        f.write(line + "\n")

def detect():
    wait_for_model()
    model, FEATURES = load_model()
    client  = docker.from_env()
    history = {}

    print("=" * 60, flush=True)
    print("WORM DETECTION CONTAINER — ACTIVE", flush=True)
    print(f"Threshold: {THRESHOLD}  |  Interval: {INTERVAL}s", flush=True)
    print(f"Alerts → {ALERT_LOG}", flush=True)
    print("=" * 60, flush=True)

    worm_active = set()

    while True:
        try:
            containers = [c for c in client.containers.list() if c.name != "detector"]
        except Exception:
            time.sleep(INTERVAL)
            continue

        for container in containers:
            name = container.name
            raw  = get_stats(container)
            established, listen, time_wait, close_wait = get_connections(container)
            procs = get_procs(container)

            prev = history.get(name, {})
            tx_vel        = raw["net_tx_bytes"]    - prev.get("net_tx_bytes",    raw["net_tx_bytes"])
            rx_vel        = raw["net_rx_bytes"]     - prev.get("net_rx_bytes",    raw["net_rx_bytes"])
            blk_write_vel = raw["blk_write_bytes"]  - prev.get("blk_write_bytes", raw["blk_write_bytes"])
            pids_delta    = raw["pids_count"]       - prev.get("pids_count",      raw["pids_count"])
            history[name] = raw.copy()

            row = {
                "cpu_percent":             raw["cpu_percent"],
                "mem_percent":             raw["mem_percent"],
                "mem_rss_bytes":           raw["mem_rss_bytes"],
                "net_rx_bytes":            raw["net_rx_bytes"],
                "net_tx_bytes":            raw["net_tx_bytes"],
                "net_rx_packets":          raw["net_rx_packets"],
                "net_tx_packets":          raw["net_tx_packets"],
                "blk_read_bytes":          raw["blk_read_bytes"],
                "blk_write_bytes":         raw["blk_write_bytes"],
                "pids_count":              raw["pids_count"],
                "process_count":           procs,
                "connections_established": established,
                "connections_listen":      listen,
                "connections_time_wait":   time_wait,
                "connections_close_wait":  close_wait,
                "net_tx_velocity":         tx_vel,
                "net_rx_velocity":         rx_vel,
                "blk_write_velocity":      blk_write_vel,
                "conn_ratio":    (established + 1) / (listen + 1),
                "scan_ratio":    (time_wait + 1)   / (established + 1),
                "proc_density":  procs / (raw["mem_percent"] + 1),
                "pids_delta":    pids_delta,
                "cpu_net_ratio": raw["cpu_percent"] / (raw["net_tx_bytes"] + 1),
            }

            X     = pd.DataFrame([row])[FEATURES]
            proba = model.predict_proba(X)[0][1]
            pred  = model.predict(X)[0]

            ts = datetime.now().strftime("%H:%M:%S")

            if pred == 1 and name not in worm_active:
                worm_active.add(name)
                log_alert(f"WORM DETECTED on {name} — confidence {proba:.2%}")
            elif pred == 0 and name in worm_active:
                worm_active.discard(name)
                log_alert(f"CLEARED {name} — confidence {proba:.2%}")
            else:
                status = "WORM" if pred == 1 else "OK  "
                print(f"{ts} | {name:15} | {status} | {proba:.2%}", flush=True)

        time.sleep(INTERVAL)

if __name__ == "__main__":
    detect()
