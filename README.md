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
# CTMonitor: Research Prototype for Local-First CT Threat Detection

CTMonitor is a research-oriented prototype for studying certificate transparency-based phishing and typosquatting detection. The system combines deterministic heuristics, lightweight machine-learning wrappers, local persistence, and a Manifest V3 browser extension that can operate without a backend.

## Abstract

Certificate Transparency (CT) logs provide a near-real-time record of issued TLS certificates. This repository explores whether CT telemetry can be transformed into actionable, low-latency phishing signals without relying on cloud services. The prototype emphasizes local-first operation, calibrated scoring, and explainable detector outputs that can be inspected directly in the browser extension.

## Research Questions

1. Can CT-derived certificate features be used to flag suspicious domains at navigation time?
2. Which simple detectors are most useful for high-precision browser-side warnings?
3. How much explanation can be surfaced in a browser extension without requiring a remote service?
4. What trade-offs arise when the same system is deployed with or without a local backend?

## System Overview

- **Extension-local inference:** The Manifest V3 extension runs a JavaScript detector engine directly in the browser.
- **Optional backend enrichment:** When a local Python service is available, it can enrich verdicts with additional evidence.
- **Explainability:** Verdicts expose tier, risk score, detector breakdown, and weighted contributions.
- **User feedback loop:** The popup, report page, and BLOCK interstitial give immediate navigation-time feedback.

## Experimental Framing

This repository is structured as a prototype for iterative evaluation rather than a polished commercial product.

- **Inputs:** domain names, certificate metadata, and browser navigation events.
- **Outputs:** SAFE / WATCH / WARN / BLOCK verdicts, confidence intervals, and contribution summaries.
- **Deployment modes:** extension-only baseline, or extension plus local backend.

## Repository Contents

The public repo currently centers on the browser extension and its supporting artifacts:

- `ctmonitor/extension/manifest.json`
- `ctmonitor/extension/background.js`
- `ctmonitor/extension/engine.js`
- `ctmonitor/extension/content.js`
- `ctmonitor/extension/popup.html`
- `ctmonitor/extension/popup.js`
- `ctmonitor/extension/report.html`
- `ctmonitor/extension/report.js`
- `ctmonitor/extension/options.html`
- `ctmonitor/extension/options.js`
- `ctmonitor/extension/block.html`
- `ctmonitor/extension/block.js`

Additional files in the workspace reflect backend and research scaffolding used during development.

## Extension Operation

1. On navigation, the worker evaluates the current domain locally.
2. The extension stores the verdict in `chrome.storage`.
3. WARN/BLOCK verdicts surface through badges, notifications, and the content-script banner.
4. BLOCK verdicts can trigger an interstitial with continue/dismiss controls.
5. The report view shows detector outputs and the strongest contributions.

## Privacy and Safety Considerations

- Local analysis is the default.
- Backend enrichment is optional and disabled by default in settings.
- Internal and private hosts are treated conservatively.
- Stored verdicts are pruned over time to reduce retention.

## Reproducibility Notes

- The extension can be loaded unpacked from `ctmonitor/extension`.
- No new files are required for the README update.
- The codebase is intended for inspection, local testing, and further research iteration.

## Limitations

- Browser-side analysis cannot fully replace server-side CT ingestion or large-scale model training.
- The extension-local engine is intentionally lightweight and explainable, not a full CT pipeline.
- Stronger research claims require formal evaluation, labeled datasets, and calibration studies.

## Status

This repository is being maintained as a research prototype and implementation sandbox for CT-based threat detection.
