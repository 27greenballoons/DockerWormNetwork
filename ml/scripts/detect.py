#!/usr/bin/env python3
"""
Real-Time Worm Detection Monitor
CS 499 Capstone - Authorized Pentest Environment (ID: ticq7)

Uses trained XGBoost model to detect worm propagation in real-time.
"""

import docker
import joblib
import json
import time
import os
import pandas as pd
from datetime import datetime

client = docker.from_env()
MODEL_DIR = "/home/greenballoons/499/DockerWormNetwork/ml/models"

model = joblib.load(os.path.join(MODEL_DIR, "worm_detector.pkl"))
with open(os.path.join(MODEL_DIR, "features.json")) as f:
    FEATURES = json.load(f)

history = {}

def get_stats(container):
    try:
        stats = container.stats(stream=False)

        cpu_delta    = stats["cpu_stats"]["cpu_usage"]["total_usage"] - stats["precpu_stats"]["cpu_usage"]["total_usage"]
        system_delta = stats["cpu_stats"]["system_cpu_usage"] - stats["precpu_stats"]["system_cpu_usage"]
        cpu_pct      = (cpu_delta / system_delta) * 100.0 if system_delta > 0 else 0.0

        mem_stats = stats.get("memory_stats", {})
        mem_usage = mem_stats.get("usage", 0)
        mem_limit = mem_stats.get("limit", 1)
        mem_pct   = (mem_usage / mem_limit) * 100.0 if mem_limit > 0 else 0.0
        mem_detail = mem_stats.get("stats", {})
        mem_rss   = mem_detail.get("rss", 0)

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
            "cpu_percent":   round(cpu_pct, 4),
            "mem_percent":   round(mem_pct, 4),
            "mem_rss_bytes": mem_rss,
            "net_rx_bytes":  net_rx,
            "net_tx_bytes":  net_tx,
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

def detect():
    print("="*60)
    print("REAL-TIME WORM DETECTION MONITOR")
    print("="*60)
    print("Analyzing container behavior every 5 seconds...")
    print("Press Ctrl+C to stop\n")

    while True:
        for container in client.containers.list():
            name = container.name
            raw  = get_stats(container)
            established, listen, time_wait, close_wait = get_connections(container)
            procs = get_procs(container)

            prev = history.get(name, {})
            tx_vel       = raw["net_tx_bytes"]   - prev.get("net_tx_bytes",   raw["net_tx_bytes"])
            rx_vel       = raw["net_rx_bytes"]    - prev.get("net_rx_bytes",   raw["net_rx_bytes"])
            blk_write_vel = raw["blk_write_bytes"] - prev.get("blk_write_bytes", raw["blk_write_bytes"])
            pids_delta   = raw["pids_count"]      - prev.get("pids_count",     raw["pids_count"])
            history[name] = raw.copy()

            row = {
                # Raw
                "cpu_percent":              raw["cpu_percent"],
                "mem_percent":              raw["mem_percent"],
                "mem_rss_bytes":            raw["mem_rss_bytes"],
                "net_rx_bytes":             raw["net_rx_bytes"],
                "net_tx_bytes":             raw["net_tx_bytes"],
                "net_rx_packets":           raw["net_rx_packets"],
                "net_tx_packets":           raw["net_tx_packets"],
                "blk_read_bytes":           raw["blk_read_bytes"],
                "blk_write_bytes":          raw["blk_write_bytes"],
                "pids_count":               raw["pids_count"],
                "process_count":            procs,
                "connections_established":  established,
                "connections_listen":       listen,
                "connections_time_wait":    time_wait,
                "connections_close_wait":   close_wait,
                # Engineered
                "net_tx_velocity":    tx_vel,
                "net_rx_velocity":    rx_vel,
                "blk_write_velocity": blk_write_vel,
                "conn_ratio":    (established + 1) / (listen + 1),
                "scan_ratio":    (time_wait + 1)   / (established + 1),
                "proc_density":  procs / (raw["mem_percent"] + 1),
                "pids_delta":    pids_delta,
                "cpu_net_ratio": raw["cpu_percent"] / (raw["net_tx_bytes"] + 1),
            }

            X = pd.DataFrame([row])[FEATURES]
            proba      = model.predict_proba(X)[0][1]
            prediction = model.predict(X)[0]

            status = "WORM DETECTED" if prediction == 1 else "NORMAL"
            ts = datetime.now().strftime("%H:%M:%S")
            print(f"{ts} | {name:15} | {status:14} | Confidence: {proba:.2%}")

        time.sleep(5)

if __name__ == "__main__":
    try:
        detect()
    except KeyboardInterrupt:
        print("\n[*] Detection monitor stopped.")
