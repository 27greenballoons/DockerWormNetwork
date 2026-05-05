# Machine Learning Worm Detection Pipeline

## Overview
This directory contains the full ML pipeline for detecting worm propagation in the DockerWormNetwork lab using XGBoost.

## Quick Start

```bash
# 1. Install dependencies
pip3 install xgboost scikit-learn pandas joblib psutil

# 2. Run the full pipeline
./ml/scripts/run_pipeline.sh
```

## Files

| File | Purpose |
|------|---------|
| `scripts/collect_baseline.py` | Collect normal traffic (label=0) |
| `scripts/collect_worm.py` | Collect worm traffic (label=1) |
| `scripts/train_model.py` | Train XGBoost classifier |
| `scripts/detect.py` | Real-time detection monitor |
| `scripts/run_pipeline.sh` | Master orchestrator |
| `data/` | Datasets storage |
| `models/` | Trained model storage |

## Workflow

1. **Collect Baseline** (5 min): Run with normal services only
2. **Collect Worm** (5 min): Run while worm is propagating
3. **Train Model**: XGBoost learns to distinguish patterns
4. **Detect**: Real-time monitoring with probability scores

## Features Used

- `cpu_percent` - CPU usage spikes during exploitation
- `mem_percent` - Memory consumption
- `net_tx/rx_bytes` - Network I/O volume
- `net_tx/rx_packets` - Packet counts
- `connections_established` - Scanning creates many connections
- `connections_listen` - Service listeners
- `process_count` - Background worm processes
- `net_tx_velocity` - Rate of outbound data (propagation speed)
- `net_rx_velocity` - Rate of inbound data
- `conn_ratio` - Established vs listen ratio
- `proc_density` - Processes relative to memory

## Expected Results

- ROC-AUC: >0.90
- Precision: >0.95 for both classes
- Real-time confidence scores displayed every 3 seconds

## Making the Worm Smarter

To evade detection, a worm could:
1. Add jitter between scans (evades velocity)
2. Rate-limit connections (evades conn_ratio)
3. Masquerade process names (evades proc_density)
4. Spread slowly over hours (evades burst detection)

See `python/smart_worm.py` (copy from guide) for implementation.

## Authorization

**ID**: ticq7 | **Scope**: Isolated Docker Lab | **Status**: Authorized
