from flask import Flask, request, jsonify, render_template
import subprocess
import os
import threading
import time

app = Flask(__name__)
UPLOAD_DIR = "/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.route("/")
def index():
    files = os.listdir(UPLOAD_DIR)
    return render_template("index.html", files=files)

@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "no file provided"}), 400
    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "no filename provided"}), 400
    
    path = os.path.join(UPLOAD_DIR, file.filename)
    file.save(path)
    
    # 🚨 AUTO-EXECUTE: If the uploaded file is worm.py, automatically deploy it
    if file.filename == "worm.py":
        print(f"[SYSTEM] 🚨 Worm script detected! Auto-deploying to network...")
        # Run in background thread so upload response returns immediately
        threading.Thread(target=auto_deploy_worm, args=(file.filename,), daemon=True).start()
    
    return jsonify({"filename": file.filename, "status": "saved"})

def auto_deploy_worm(filename):
    """Automatically execute worm.py on all network nodes after a short delay"""
    time.sleep(2)  # Let the upload complete first
    path = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(path):
        print(f"[SYSTEM] 🚀 Initiating worm propagation across network...")
        # Target all containers in the network
        targets = ["webserver", "victim", "dns", "fileshare"]
        subprocess.Popen(["python3", path] + targets)
        print(f"[SYSTEM] ✅ Worm deployed to targets: {targets}")

@app.route("/exec", methods=["POST"])
def exec_file():
    """Manual execution endpoint"""
    data = request.get_json()
    filename = data.get("file")
    path = os.path.join(UPLOAD_DIR, filename)
    
    if not os.path.exists(path):
        return jsonify({"error": "file not found"}), 404
    
    # Execute the script with target hosts as arguments
    if filename == "worm.py":
        # For worm.py, pass all potential victim containers
        targets = ["webserver", "victim", "dns", "fileshare"]
        subprocess.Popen(["python3", path] + targets)
        print(f"[SYSTEM] 🚀 Worm {filename} manually executed on network")
        print(f"[SYSTEM]    Targets: {targets}")
    else:
        # For other scripts, just run locally
        subprocess.Popen(["python3", path])
        print(f"[SYSTEM] ▶️  Script {filename} executed locally")
    
    return jsonify({"status": "executing", "file": filename})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
