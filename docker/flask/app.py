from flask import Flask, request, jsonify, send_from_directory, render_template
import subprocess
import os

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
    return jsonify({"filename": file.filename, "status": "saved"})

@app.route("/exec", methods=["POST"])
def exec_file():
    data = request.get_json()
    filename = data.get("file")
    path = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(path):
        subprocess.Popen(["python3", path, "webserver", "victim"])
        return jsonify({"status": "executing", "file": filename})
    return jsonify({"error": "file not found"}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)