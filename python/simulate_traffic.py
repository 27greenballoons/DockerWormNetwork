#!/usr/bin/env python3
"""
Background Traffic Simulator
CS 499 Capstone - Authorized Pentest Environment (ID: ticq7)

Simulates normal network operations to generate baseline noise for ML training.
This makes the XGBoost model learn patterns, not just "any traffic = worm".
"""

import time
import requests
import random
import subprocess
import socket

try:
    import pymysql
    HAS_MYSQL = True
except ImportError:
    HAS_MYSQL = False

try:
    import redis as redis_lib
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False

try:
    import psycopg2
    HAS_POSTGRES = True
except ImportError:
    HAS_POSTGRES = False

try:
    import paramiko
    HAS_SSH = True
except ImportError:
    HAS_SSH = False

# Internal Docker service URLs
TARGETS = [
    "http://webserver:80/",
    "http://api:8000/",
    "http://victim:8888/",
]

# Internal hostnames for ping/probe checks
HOSTS = ["webserver", "api", "victim", "db", "dns", "fileshare"]

# Flask accounts seeded by init_db()
FLASK_ACCOUNTS = [
    ("admin", "password123"),
    ("ubuntu", "ubuntu"),
    ("user", "user"),
    ("guest", "guest123"),
]

# MySQL queries that mimic a real app: reads, writes, schema checks
MYSQL_QUERIES = [
    "SELECT 1",
    "SHOW TABLES",
    "SELECT COUNT(*) FROM user",
    "SELECT username FROM user LIMIT 5",
    "SELECT VERSION()",
]

REDIS_OPS = ["ping", "set", "get"]

PG_QUERIES = [
    "SELECT 1",
    "SELECT version()",
    "SELECT current_database()",
    "SELECT COUNT(*) FROM pg_stat_activity",
]


def simulate_normal_activity():
    print("[*] Background Traffic Simulator Started")
    print("[*] Generating normal network noise for ML baseline...")

    cycle = 0
    while True:
        try:
            cycle += 1
            action = random.randint(1, 9)

            if action == 1:
                # Web browse
                url = random.choice(TARGETS)
                print(f"[-] [Cycle {cycle}] Browsing: {url}")
                requests.get(url, timeout=5)

            elif action == 2:
                # Ping sweep (mimics a monitoring agent)
                host = random.choice(HOSTS)
                print(f"[-] [Cycle {cycle}] Ping check: {host}")
                subprocess.run(
                    ["ping", "-c", "1", "-W", "1", host],
                    capture_output=True
                )

            elif action == 3:
                # TCP health probe
                host = random.choice(HOSTS)
                port = random.choice([80, 8000, 8888, 3306])
                print(f"[-] [Cycle {cycle}] Health probe: {host}:{port}")
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(1)
                    s.connect((host, port))
                    s.close()
                except Exception:
                    pass

            elif action == 4:
                # API health check
                url = "http://api:8000/login"
                print(f"[-] [Cycle {cycle}] API health check: {url}")
                try:
                    requests.get(url, timeout=3)
                except Exception:
                    pass

            elif action == 5:
                # MySQL query — mimics app DB reads
                if not HAS_MYSQL:
                    continue
                query = random.choice(MYSQL_QUERIES)
                print(f"[-] [Cycle {cycle}] MySQL query: {query}")
                try:
                    conn = pymysql.connect(
                        host="db", port=3306,
                        user="root", password="root",
                        database="testdb", connect_timeout=3
                    )
                    with conn.cursor() as cur:
                        cur.execute(query)
                        cur.fetchall()
                    conn.close()
                except Exception:
                    pass

            elif action == 6:
                # Redis operation — mimics caching layer
                if not HAS_REDIS:
                    continue
                op = random.choice(REDIS_OPS)
                print(f"[-] [Cycle {cycle}] Redis op: {op}")
                try:
                    r = redis_lib.Redis(host="redis", port=6379, socket_timeout=2)
                    if op == "ping":
                        r.ping()
                    elif op == "set":
                        r.set(f"session:{random.randint(1000,9999)}", "active", ex=60)
                    elif op == "get":
                        r.get(f"session:{random.randint(1000,9999)}")
                except Exception:
                    pass

            elif action == 7:
                # SSH login to jumpbox — mimics admin remote access
                if not HAS_SSH:
                    continue
                print(f"[-] [Cycle {cycle}] SSH login: jumpbox")
                try:
                    client = paramiko.SSHClient()
                    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    client.connect(
                        "jumpbox", port=22,
                        username="ubuntu", password="ubuntu",
                        timeout=5, banner_timeout=5
                    )
                    _, stdout, _ = client.exec_command("whoami && uptime")
                    stdout.read()
                    client.close()
                except Exception:
                    pass

            elif action == 8:
                # Postgres query — mimics second DB tier
                if not HAS_POSTGRES:
                    continue
                query = random.choice(PG_QUERIES)
                print(f"[-] [Cycle {cycle}] Postgres query: {query}")
                try:
                    conn = psycopg2.connect(
                        host="postgres", port=5432,
                        user="postgres", password="postgres",
                        connect_timeout=3
                    )
                    cur = conn.cursor()
                    cur.execute(query)
                    cur.fetchall()
                    cur.close()
                    conn.close()
                except Exception:
                    pass

            elif action == 9:
                # Flask login session — mimics a user browsing the dashboard
                creds = random.choice(FLASK_ACCOUNTS)
                print(f"[-] [Cycle {cycle}] Flask login: user={creds[0]}")
                try:
                    sess = requests.Session()
                    sess.post(
                        "http://api:8000/login",
                        data={"username": creds[0], "password": creds[1]},
                        timeout=4, allow_redirects=True
                    )
                    sess.get("http://api:8000/", timeout=3)
                    sess.get("http://api:8000/logout", timeout=3)
                except Exception:
                    pass

            delay = random.uniform(2, 8)
            time.sleep(delay)

        except Exception as e:
            print(f"[!] Simulator error (non-critical): {e}")
            time.sleep(5)


if __name__ == "__main__":
    time.sleep(5)
    simulate_normal_activity()
