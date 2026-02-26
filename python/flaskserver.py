from flask import Flask, request, jsonify, send_from_directory
import subprocess
import os

app = Flask(__name__)
UPLOAD_DIR = "/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "no file provided"}), 400
    file = request.files["file"]
    path = os.path.join(UPLOAD_DIR, file.filename)
    file.save(path)
    print(f"[api] File saved: {file.filename}", flush=True)
    return jsonify({"filename": file.filename, "status": "saved"})

@app.route("/files/<filename>", methods=["GET"])
def download_file(filename):
    if os.path.exists(os.path.join(UPLOAD_DIR, filename)):
        return send_from_directory(UPLOAD_DIR, filename)
    return jsonify({"error": "not found"}), 404

@app.route("/files", methods=["GET"])
def list_files():
    files = os.listdir(UPLOAD_DIR)
    return jsonify({"files": files})

# Intentional vuln — executes any uploaded .py file by name
@app.route("/exec", methods=["POST"])
def exec_file():
    filename = request.form.get("file") or request.json.get("file")
    path = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(path):
        subprocess.Popen(
            ["python3", path, "webserver", "fileshare", "victim", "honeypot"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        print(f"[api] Executing: {filename}", flush=True)
        return jsonify({"status": "executing", "file": filename})
    return jsonify({"error": "file not found"}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)