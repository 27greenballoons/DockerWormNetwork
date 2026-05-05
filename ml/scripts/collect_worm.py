#!/usr/bin/env python3
"""
Worm Traffic Collector - Malicious Network Operations
CS 499 Capstone - Authorized Pentest Environment (ID: ticq7)

Collects network traffic DURING worm propagation.
Run this WHILE the worm is active.
"""

import docker
import csv
import time
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

client = docker.from_env()

DATA_DIR = "/home/greenballoons/499/DockerWormNetwork/ml/data"
os.makedirs(DATA_DIR, exist_ok=True)
WORM_FILE = os.environ.get("WORM_OUT", os.path.join(DATA_DIR, "worm_traffic.csv"))

FIELDS = [
    "timestamp", "container_name",
    "cpu_percent", "mem_percent", "mem_rss_bytes", "mem_cache_bytes",
    "net_rx_bytes", "net_tx_bytes", "net_rx_packets", "net_tx_packets",
    "blk_read_bytes", "blk_write_bytes",
    "pids_count", "process_count",
    "connections_established", "connections_listen",
    "connections_time_wait", "connections_close_wait",
    "label",
]

def collect_container(container, timestamp):
    """Collect all stats for one container. Runs in a thread."""
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
        mem_cache  = mem_detail.get("cache", 0)

        networks  = stats.get("networks", {})
        net_rx    = sum(n.get("rx_bytes",   0) for n in networks.values())
        net_tx    = sum(n.get("tx_bytes",   0) for n in networks.values())
        net_rx_pk = sum(n.get("rx_packets", 0) for n in networks.values())
        net_tx_pk = sum(n.get("tx_packets", 0) for n in networks.values())

        blk_entries = stats.get("blkio_stats", {}).get("io_service_bytes_recursive") or []
        blk_read  = sum(e["value"] for e in blk_entries if e.get("op") == "Read")
        blk_write = sum(e["value"] for e in blk_entries if e.get("op") == "Write")

        pids_count = stats.get("pids_stats", {}).get("current", 0)

    except Exception:
        cpu_pct = mem_pct = mem_rss = mem_cache = 0.0
        net_rx = net_tx = net_rx_pk = net_tx_pk = 0
        blk_read = blk_write = pids_count = 0

    established = listen = time_wait = close_wait = 0
    try:
        out = container.exec_run(
            "ss -tan 2>/dev/null || netstat -tan 2>/dev/null",
            demux=False
        ).output.decode(errors="replace")
        established = out.count("ESTABLISHED")
        listen      = out.count("LISTEN")
        time_wait   = out.count("TIME-WAIT") + out.count("TIME_WAIT")
        close_wait  = out.count("CLOSE-WAIT") + out.count("CLOSE_WAIT")
    except Exception:
        pass

    proc_count = 0
    try:
        proc_count = int(
            container.exec_run("ps aux | wc -l", demux=False).output.decode().strip()
        )
    except Exception:
        pass

    return {
        "timestamp":               timestamp,
        "container_name":          container.name,
        "cpu_percent":             round(cpu_pct, 4),
        "mem_percent":             round(mem_pct, 4),
        "mem_rss_bytes":           mem_rss,
        "mem_cache_bytes":         mem_cache,
        "net_rx_bytes":            net_rx,
        "net_tx_bytes":            net_tx,
        "net_rx_packets":          net_rx_pk,
        "net_tx_packets":          net_tx_pk,
        "blk_read_bytes":          blk_read,
        "blk_write_bytes":         blk_write,
        "pids_count":              pids_count,
        "process_count":           proc_count,
        "connections_established": established,
        "connections_listen":      listen,
        "connections_time_wait":   time_wait,
        "connections_close_wait":  close_wait,
        "label":                   1,
    }

def collect_worm_traffic(duration_seconds=300, interval=5):
    print(f"[*] Collecting WORM traffic data for {duration_seconds}s (interval={interval}s)...")
    print(f"[*] Make sure the worm is RUNNING before starting collection!")
    print(f"[*] Output: {WORM_FILE}")

    with open(WORM_FILE, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=FIELDS)
        writer.writeheader()
        csvfile.flush()

        start   = time.time()
        samples = 0

        while time.time() - start < duration_seconds:
            timestamp  = datetime.now().isoformat()
            containers = client.containers.list()

            with ThreadPoolExecutor(max_workers=len(containers)) as pool:
                futures = {pool.submit(collect_container, c, timestamp): c for c in containers}
                for fut in as_completed(futures):
                    try:
                        writer.writerow(fut.result())
                        samples += 1
                    except Exception:
                        pass

            csvfile.flush()
            print(f"[+] {samples} samples written", flush=True)
            time.sleep(interval)

    print(f"[+] Worm traffic collection complete: {samples} samples → {WORM_FILE}")

if __name__ == "__main__":
    collect_worm_traffic(duration_seconds=300, interval=5)
