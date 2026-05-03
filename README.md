# CTMonitor

> **Notice:** This repository is explicitly **not intended for external people's use**. No license or permissions are granted for copying, distribution, or modification.

**Production-grade, local-first certificate transparency monitoring engine** that detects phishing, typosquatting, and malicious TLS certificate issuance in real time.

## Vision

CTMonitor ingests the live global CT log stream (~12 certs/sec) via Certstream WebSocket, runs every incoming certificate through a registry of detectors, combines evidence via Dempster-Shafer theory, and exports verdicts via FastAPI REST + Server-Sent Events, persisting all results locally in SQLite. Zero cloud dependency. Zero data leaves the machine.

## Key Features

- **Local-First Architecture:** All verdicts, models, and certificates persist on SQLite. No cloud upload.
- **Real-Time Ingestion:** ~12 certs/sec from global CT logs via Certstream.
- **Hybrid Detection:** 5 heuristic detectors + 5 ML detectors unified by quorum engine.
- **Calibrated Probabilities:** Isotonic calibration ensures `risk_score=0.87` means "87% of domains like this are malicious."
- **Conformal Predictions:** Mathematically guaranteed coverage intervals for every verdict.
- **ONNX Runtime:** ML models export to ONNX for <2ms CPU inference (no torch at serve time).
- **Vanilla JS Dashboard:** Real-time frontend served by FastAPI (~150MB storage savings vs Streamlit).
- **SARIF 2.1.0 Export:** Plugs directly into GitHub Advanced Security, Splunk, any SIEM.
- **Manifest V3 Extension:** Browser extension for live verdict badges on navigation.

## Installation

**Prerequisites:** Python ≥3.10, pip, (optionally) conda env

```bash
# Clone and setup (CPU-only torch to respect 3GB storage constraint)
git clone <repo>
cd ctmonitor

# (Optional) Create venv
python -m venv venv
source venv/bin/activate  # or: venv\Scripts\activate on Windows

# Install dependencies (note: torch is CPU-only)
pip install -e .
# Or with full dev dependencies:
pip install -e ".[dev]"
```

## Quick Start

```bash
# Phase 1: Minimal end-to-end test (heuristics only)
ctmonitor analyze paypal-secure-login.com

# Phase 2: Start the API server (FastAPI on :8000)
ctmonitor serve

# Phase 3: Launch CLI live stream viewer
ctmonitor stream

# Train ML models (Phase 11+)
ctmonitor train

# Export verdicts to SARIF 2.1.0
ctmonitor export-sarif
```

## Project Structure

```
ctmonitor/
├── pyproject.toml              # Dependencies + build config
├── README.md                   # You are here
├── PROGRESS.md                 # Phase tracker for agents
├── TECH_STACK_STRATEGY.md      # Storage & tech constraints
│
├── ctmonitor/
│   ├── __init__.py
│   ├── ingestion/              # Certificate stream ingestion
│   │   ├── models.py           # CertEvent, NormalisedCert dataclasses
│   │   ├── stream.py           # Certstream WebSocket consumer
│   │   ├── poller.py           # RFC 6962 CT log poller
│   │   └── crtsh.py            # crt.sh REST client
│   ├── pipeline/               # Certificate processing
│   │   ├── ring.py             # BoundedRing async queue
│   │   ├── normaliser.py       # Punycode, tldextract, dedup
│   │   └── processor.py        # Stream processor
│   ├── detectors/              # Threat detectors
│   │   ├── base.py             # BaseDetector ABC
│   │   ├── heuristic/          # 5 heuristics
│   │   │   ├── levenshtein.py
│   │   │   ├── homograph.py
│   │   │   ├── tld_keyword.py
│   │   │   ├── san_anomaly.py
│   │   │   └── domain_age.py
│   │   └── ml/                 # 5 ML detectors
│   │       ├── ngram_lm.py
│   │       ├── vae.py
│   │       ├── transformer.py
│   │       ├── hawkes.py
│   │       ├── gnn.py
│   │       └── conformal.py
│   ├── quorum/                 # Evidence combination
│   │   ├── dempster_shafer.py
│   │   ├── calibration.py
│   │   └── engine.py           # QuorumEngine (coordinator)
│   ├── ml/                     # Training & export
│   │   ├── train.py
│   │   ├── export.py           # ONNX export + quantization
│   │   └── inference.py        # ONNX runtime wrapper
│   ├── storage/                # Local persistence
│   │   └── db.py               # SQLite schema + CRUD
│   ├── serving/                # FastAPI REST + SSE
│   │   └── api.py
│   ├── dashboard/              # Vanilla JS frontend
│   │   ├── index.html
│   │   ├── main.js
│   │   ├── styles.css
│   │   └── [Chart.js library]
│   ├── reporter/               # SARIF export
│   │   └── sarif.py
│   ├── extension/              # Manifest V3 browser extension
│   │   ├── manifest.json
│   │   ├── background.js       # Service worker
│   │   ├── popup.html
│   │   ├── popup.js
│   │   └── content.js
│   ├── data/                   # Static data
│   │   ├── brands_10k.txt
│   │   └── tld_rules.yaml
│   ├── cli.py                  # Typer CLI entry point
│   └── __init__.py
│
├── models/                     # Dynamically generated (gitignored)
│   ├── ngram_4gram.pkl.gz
│   ├── vae.onnx
│   ├── transformer.onnx
│   └── [...ONNX + calibrators...]
│
└── tests/
    ├── conftest.py
    ├── test_ingestion.py
    ├── test_heuristic_detectors.py
    ├── test_ml_detectors.py
    ├── test_quorum.py
    ├── test_api.py
    ├── test_storage.py
    └── test_sarif.py
```

## Architecture Pillars

### 1. Local-First, Zero Cloud
Every verdict, every model, every certificate stays on the machine. No external API calls except Certstream (standard CT log stream). SQLite persistence ensures you can query historical verdicts without cloud sync.

### 2. Calibrated Evidence
Raw detector scores mean nothing. After isotonic calibration, `risk_score=0.87` is statistically grounded: "87% of domains in the calibration set with this profile turned out to be malicious."

### 3. Conformal Prediction Intervals
The `[confidence_lower, confidence_upper]` band comes with a mathematical guarantee: if we set α=0.05, then 95% of test set verdicts fall within the interval. Enterprise-grade credibility.

### 4. Identical Detector Interface
Heuristics and ML detectors share `BaseDetector` ABC. Adding a new detector = one file + one registration line in the quorum engine.

### 5. ONNX Edge Runtime
Transformer and VAE models export to ONNX opset 17 with INT8 quantization. Inference runs via `onnxruntime` (no `torch` at serve time), enabling future WebAssembly / browser-native deployment.

### 6. SARIF + MITRE ATT&CK
Verdicts map cleanly to SARIF 2.1.0 JSON and MITRE ATT&CK T1588.004 (Supply Chain Compromise: Malicious Software). Plugs directly into GitHub Advanced Security, Splunk, Fortify, any SIEM.

## Implementation Phases

See [`PROGRESS.md`](PROGRESS.md) for the 18-phase build sequence. Each phase has success criteria and must pass tests before proceeding.

## Storage & Performance Notes

- **3GB Constraint:** Torch is CPU-only. Datasets are compressed. Streamlit replaced with Vanilla JS (~150MB savings).
- **No Docker:** Zero Docker images. Everything runs natively.
- **Inference Latency:** Target <2ms per cert after ONNX quantization. Measured with onnxruntime on CPU.

## Standards & Compliance

- **SARIF 2.1.0:** JSON Schema validation enforced.
- **MITRE ATT&CK:** T1588.004 mappings in verdict evidence.
- **Unicode & Internationalization:** Full Punycode support for IDN domains.

## Contact

Raja Viknesh — `rajaviknesh.off@gmail.com`
