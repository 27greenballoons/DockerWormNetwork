import socket
import sys
import time
import urllib.request
import os
from itertools import cycle

def scan_port(host, port):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1.0)
            s.connect((host, port))
            return True
    except:
        return False

def send_beacon(host, port, path):
    try:
        url = f"http://{host}:{port}/{path}"
        with urllib.request.urlopen(url, timeout=1) as response:
            return response.getcode()
    except urllib.error.HTTPError as e:
        return e.code  # 404, 403 etc still count as a response
    except Exception as e:
        print(f"[-] Beacon to {host}:{port} failed: {e}", flush=True)
        return None

def deploy_persistence():
    path = "/data/backdoor.txt"
    try:
        if os.path.exists("/data"):
            with open(path, "a") as f:
                f.write(f"Infected at {time.ctime()}\n")
            print(f"[+] Persistence established at {path}", flush=True)
        else:
            print(f"[-] Persistence failed: /data volume not mounted", flush=True)
    except Exception as e:
        print(f"[-] Persistence failed: {e}", flush=True)

def main():
    if len(sys.argv) < 2:
        print("Usage: python worm.py <host1> <host2> ...")
        sys.exit(1)

    print("[*] Waiting for services to initialize...", flush=True)
    time.sleep(5)

    hosts = sys.argv[1:]
    ports = [22, 80, 443, 8080, 8888]

    print(f"[*] Starting scan on {len(hosts)} host(s).", flush=True)

    host_cycle = cycle(hosts)

    while True:
        host = next(host_cycle)

        if host == "fileshare":
            deploy_persistence()
            time.sleep(0.5)
            continue

        for port in ports:
            if scan_port(host, port):
                print(f"[+] Open port found: {host}:{port}", flush=True)

                if host == "c2_server" and port == 8080:
                    code = send_beacon(host, port, "heartbeat?status=active")
                    print(f"[>] Beacon sent to c2_server → HTTP {code}", flush=True)

                elif host == "webserver" and port == 80:
                    code = send_beacon(host, port, "payload_deployed")
                    print(f"[>] Beacon sent to webserver → HTTP {code}", flush=True)

                elif host == "victim" and port == 8888:
                    code = send_beacon(host, port, "data_dump_complete")
                    print(f"[>] Beacon sent to victim → HTTP {code}", flush=True)

            else:
                print(f"[-] Closed: {host}:{port}", flush=True)

        time.sleep(0.5)

if __name__ == '__main__':
    main()