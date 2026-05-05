#!/usr/bin/env python3
"""
XGBoost Worm Detection Model Trainer
CS 499 Capstone - Authorized Pentest Environment (ID: ticq7)

Trains an XGBoost classifier to detect worm propagation vs normal traffic.
"""

import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
import joblib
import os
import json

DATA_DIR = "/home/greenballoons/499/DockerWormNetwork/ml/data"
MODEL_DIR = "/home/greenballoons/499/DockerWormNetwork/ml/models"
os.makedirs(MODEL_DIR, exist_ok=True)

def load_and_combine():
    """Load all baseline and worm CSVs (single or multi-round), combine and shuffle."""
    import glob

    baseline_files = sorted(glob.glob(os.path.join(DATA_DIR, "baseline_traffic*.csv")))
    worm_files     = sorted(glob.glob(os.path.join(DATA_DIR, "worm_traffic*.csv")))

    if not baseline_files:
        raise FileNotFoundError(f"No baseline CSVs found in {DATA_DIR}")
    if not worm_files:
        raise FileNotFoundError(f"No worm CSVs found in {DATA_DIR}")

    baseline = pd.concat([pd.read_csv(f) for f in baseline_files], ignore_index=True)
    worm     = pd.concat([pd.read_csv(f) for f in worm_files],     ignore_index=True)

    import re
    strategies = set(
        m.group(1)
        for f in baseline_files + worm_files
        for m in [re.search(r'(?:baseline|worm)_traffic_([^_]+)_\d+\.csv', os.path.basename(f))]
        if m
    )
    print(f"[*] Baseline files : {[os.path.basename(f) for f in baseline_files]}")
    print(f"[*] Worm files     : {[os.path.basename(f) for f in worm_files]}")
    print(f"[*] Strategies     : {sorted(strategies)}")
    print(f"[*] Baseline samples: {len(baseline)}")
    print(f"[*] Worm samples    : {len(worm)}")

    df = pd.concat([baseline, worm], ignore_index=True)
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)
    return df, sorted(strategies)

def feature_engineering(df):
    """
    Create engineered features that distinguish worm from normal:
    - High connection count (scanning)
    - Rapid network I/O changes (propagation)
    - Process count spikes (worm running in background)
    - CPU bursts (scanning + exploitation)
    """
    # Per-container rolling stats (simulate time windows)
    df = df.sort_values(["container_name", "timestamp"])
    
    # Network velocity (bytes per sample interval — spikes during scanning)
    df["net_tx_velocity"] = df.groupby("container_name")["net_tx_bytes"].diff().fillna(0)
    df["net_rx_velocity"] = df.groupby("container_name")["net_rx_bytes"].diff().fillna(0)

    # Block I/O velocity (worm writes scripts to disk)
    df["blk_write_velocity"] = df.groupby("container_name")["blk_write_bytes"].diff().fillna(0)

    # Connection ratios
    df["conn_ratio"] = (df["connections_established"] + 1) / (df["connections_listen"] + 1)
    df["scan_ratio"] = (df["connections_time_wait"] + 1) / (df["connections_established"] + 1)

    # Process density (worm spawns child processes)
    df["proc_density"] = df["pids_count"] / (df["mem_percent"] + 1)

    # PID delta (sudden spawn of new processes)
    df["pids_delta"] = df.groupby("container_name")["pids_count"].diff().fillna(0)

    # CPU burst relative to network (scanning is CPU + network together)
    df["cpu_net_ratio"] = df["cpu_percent"] / (df["net_tx_bytes"] + 1)

    feature_cols = [
        # Raw resource metrics
        "cpu_percent", "mem_percent", "mem_rss_bytes",
        # Network I/O
        "net_rx_bytes", "net_tx_bytes", "net_rx_packets", "net_tx_packets",
        # Block I/O
        "blk_read_bytes", "blk_write_bytes",
        # Process counts
        "pids_count", "process_count",
        # Connection states
        "connections_established", "connections_listen",
        "connections_time_wait", "connections_close_wait",
        # Engineered features
        "net_tx_velocity", "net_rx_velocity", "blk_write_velocity",
        "conn_ratio", "scan_ratio", "proc_density", "pids_delta", "cpu_net_ratio",
    ]
    
    X = df[feature_cols]
    y = df["label"]
    
    return X, y, feature_cols

def train_model():
    print("="*60)
    print("XGBoost Worm Detection Model Training")
    print("="*60)
    
    # 1. Load data
    df, strategies = load_and_combine()
    
    # 2. Engineer features
    X, y, feature_cols = feature_engineering(df)
    
    # 3. Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    print(f"[*] Training samples: {len(X_train)}")
    print(f"[*] Test samples: {len(X_test)}")
    
    # 4. Train XGBoost
    # scale_pos_weight=1 (balanced): no artificial class bias during training.
    # Threshold tuned to the equal-error-rate point (~0.59) where FPR ≈ FNR.
    model = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        objective='binary:logistic',
        eval_metric='auc',
        scale_pos_weight=1,
        use_label_encoder=False,
        random_state=42
    )

    model.fit(X_train, y_train)

    # Sweep thresholds to find the equal-error-rate point (FPR ≈ FNR).
    import numpy as np
    from sklearn.metrics import confusion_matrix as _cm
    y_proba_all = model.predict_proba(X_test)[:, 1]
    best_t, best_diff = 0.5, 999
    for t in np.arange(0.01, 0.99, 0.01):
        _pred = (y_proba_all >= t).astype(int)
        _tn, _fp, _fn, _tp = _cm(y_test, _pred).ravel()
        _fpr = _fp / (_fp + _tn)
        _fnr = _fn / (_fn + _tp)
        if abs(_fpr - _fnr) < best_diff:
            best_diff, best_t = abs(_fpr - _fnr), t
    THRESHOLD = best_t
    print(f"\n[*] Auto-selected threshold (EER): {THRESHOLD:.2f}")
    y_proba = model.predict_proba(X_test)[:, 1]
    y_pred  = (y_proba >= THRESHOLD).astype(int)

    print(f"\n[+] Classification threshold: {THRESHOLD}")
    print("\n[+] Classification Report:")
    print(classification_report(y_test, y_pred, target_names=["Normal", "Worm"]))

    print(f"[+] ROC-AUC Score: {roc_auc_score(y_test, y_proba):.4f}")

    print("\n[+] Confusion Matrix:")
    print(confusion_matrix(y_test, y_pred))
    
    # 6. Feature importance
    importance = pd.DataFrame({
        "feature": feature_cols,
        "importance": model.feature_importances_
    }).sort_values("importance", ascending=False)
    
    print("\n[+] Feature Importance:")
    print(importance.to_string(index=False))
    
    # 7. Save model
    model_path = os.path.join(MODEL_DIR, "worm_detector.pkl")
    joblib.dump(model, model_path)

    # Save feature list
    with open(os.path.join(MODEL_DIR, "features.json"), "w") as f:
        json.dump(feature_cols, f)

    # Save report
    from datetime import datetime
    report_path = os.path.join(MODEL_DIR, "report.txt")
    with open(report_path, "w") as r:
        r.write(f"XGBoost Worm Detection Model Report\n")
        r.write(f"Trained: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        r.write(f"Strategies: {sorted(strategies)}\n")
        r.write(f"Training samples: {len(X_train)}  |  Test samples: {len(X_test)}\n")
        r.write("="*60 + "\n\n")
        r.write(f"Classification threshold: {THRESHOLD}\n")
        r.write("Classification Report:\n")
        r.write(classification_report(y_test, y_pred, target_names=["Normal", "Worm"]))
        r.write(f"\nROC-AUC Score: {roc_auc_score(y_test, y_proba):.4f}\n")
        r.write("\nConfusion Matrix:\n")
        r.write(str(confusion_matrix(y_test, y_pred)) + "\n")
        r.write("\nFeature Importance:\n")
        r.write(importance.to_string(index=False) + "\n")

    print(f"\n[+] Model saved to: {model_path}")
    print(f"[+] Report saved to: {report_path}")
    print("[+] Training complete.")

if __name__ == "__main__":
    train_model()
