
import http.server
import socketserver
import urllib.parse
import subprocess
import os

class VulnerableHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/ping'):
            # Parse query parameters
            parsed = urllib.parse.urlparse(self.path)
            query = urllib.parse.parse_qs(parsed.query)
            
            if 'ip' in query:
                ip = query['ip'][0]
                print(f"[webserver] Ping request for IP: {ip}")
                
                # VULNERABLE: Direct command injection via os.system
                cmd = f"ping -c 1 -W 1 {ip} || echo 'pong'"
                result = os.popen(cmd).read()
                
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(f"PING RESULT:\n{result}\n".encode())
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Missing 'ip' parameter")
        else:
            super().do_GET()

    def do_POST(self):
        # Bonus: POST endpoint for reverse shell
        if self.path == '/exec':
            content_length = int(self.headers['Content-Length'])
            payload = self.rfile.read(content_length).decode()
            
            print(f"[webserver] EXEC request: {payload}")
            
            try:
                result = subprocess.check_output(payload, shell=True, 
                                               timeout=5, stderr=subprocess.STDOUT)
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(result)
            except subprocess.TimeoutExpired:
                self.send_response(408)
                self.end_headers()
                self.wfile.write(b"Timeout")
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode())
        else:
            super().do_POST()

if __name__ == '__main__':
    with socketserver.TCPServer(("", 80), VulnerableHandler) as httpd:
        print("[webserver] Vulnerable server running on port 80...")
        print("[webserver] Vulnerable endpoints:")
        print("[webserver]   GET /ping?ip=TARGET (Command Injection)")
        print("[webserver]   POST /exec (RCE)")
        httpd.serve_forever()