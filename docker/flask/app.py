from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import subprocess
import os
import threading
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'six-seven-six-seven'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:root@db/testdb'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

UPLOAD_DIR = "/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username).first()
        if user and password and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for("index"))
        flash("Invalid credentials")
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def index():
    files = os.listdir(UPLOAD_DIR)
    return render_template("index.html", files=files, username=current_user.username)


@app.route("/upload", methods=["POST"])
@login_required
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "no file provided"}), 400
    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "no filename provided"}), 400

    path = os.path.join(UPLOAD_DIR, file.filename)
    file.save(path)

    if file.filename == "worm.py":
        print("[SYSTEM] Worm script detected! Auto-deploying to network...")
        threading.Thread(target=auto_deploy_worm, args=(file.filename,), daemon=True).start()

    return jsonify({"filename": file.filename, "status": "saved"})


def auto_deploy_worm(filename):
    time.sleep(2)
    path = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(path):
        strategy = os.environ.get("WORM_STRATEGY", "exhaustive")
        print(f"[SYSTEM] Initiating worm propagation — strategy={strategy}")
        subprocess.Popen(["python3", path, "--strategy", strategy])


@app.route("/exec", methods=["POST"])
@login_required
def exec_file():
    data = request.get_json()
    filename = data.get("file")
    path = os.path.join(UPLOAD_DIR, filename)

    if not os.path.exists(path):
        return jsonify({"error": "file not found"}), 404

    if filename == "worm.py":
        strategy = data.get("strategy", os.environ.get("WORM_STRATEGY", "exhaustive"))
        subprocess.Popen(["python3", path, "--strategy", strategy])
        print(f"[SYSTEM] Worm {filename} executed by {current_user.username} — strategy={strategy}")
    else:
        subprocess.Popen(["python3", path])
        print(f"[SYSTEM] Script {filename} executed by {current_user.username}")

    return jsonify({"status": "executing", "file": filename})


def init_db():
    vulnerable_accounts = [
        ("admin", "password123"),
        ("root", "root"),
        ("ubuntu", "ubuntu"),
        ("user", "user"),
        ("postgres", "postgres"),
        ("mysql", "mysql"),
        ("guest", "guest123"),
        ("operator", "operator"),
        ("sysadmin", "company2024"),
        ("it_support", "123456"),
    ]

    for attempt in range(1, 11):
        try:
            with app.app_context():
                db.create_all()
                for username, password in vulnerable_accounts:
                    if not User.query.filter_by(username=username).first():
                        db.session.add(User(
                            username=username,
                            password_hash=generate_password_hash(password)
                        ))
                db.session.commit()
                print(f"[DB] Connected to MySQL. Seeded {len(vulnerable_accounts)} accounts.")
                return
        except Exception as e:
            print(f"[DB] Attempt {attempt}/10 failed: {e}. Retrying in 3s...")
            time.sleep(3)

    print("[DB] CRITICAL: Could not connect to MySQL after 10 attempts.")


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=8000)
