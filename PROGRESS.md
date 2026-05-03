# CTMonitor Progress

## Current Phase

UI and local serving polish on top of the initial heuristic-only release. The repository currently exposes a working local API, dashboard, and browser extension flow, but it does not yet implement the full 18-phase architecture from the original long-form spec.

## What Is Live Now

- FastAPI `/analyze`, `/report`, `/report/download`, and `/stream`
- Three heuristic detectors: Levenshtein, TLD keyword, and homograph
- Dempster-Shafer quorum engine with structured `analysis` payload
- Extension popup, banner, and report/download actions
- Local dashboard with manual lookup and SSE live stream

## Known Gaps

- The live stream is synthetic until real CT ingestion is added.
- Only three detectors are currently implemented, not the full five heuristics plus ML stack from the original spec.
- ML training, ONNX export, SQLite persistence, SARIF export, and full CT ingestion remain future work.

## Success Criteria For This Phase

- `ctmonitor serve` starts cleanly on `127.0.0.1:8000`.
- `GET /stream` emits JSON payloads that the dashboard can parse.
- The extension badge, banner, and popup all show a verdict for the active tab.
- The notification/banner can open the local report view and re-run analysis.
- `/api/report/download` returns a JSON attachment for the current domain.
- SAFE verdicts still include human-readable reasoning, even when all detector scores are near zero.

## Next Useful Work

1. Add the remaining heuristic detectors: SAN anomaly and domain age.
2. Wire real CT ingestion into the pipeline instead of synthetic stream examples.
3. Add SQLite persistence and export history endpoints.
4. Implement the ML training/export/inference stack only after the heuristic path is stable.# CT Monitor — Implementation Progress & Handover Document

## Project Overview
**CTMonitor:** A production-grade, local-first certificate transparency monitoring engine detecting phishing, typosquatting, and malicious TLS certificate issuance in real-time.

## Unique Architectural Constraints (MUST MAINTAIN)
1. **Local-first, zero cloud:** All verdicts/models/data persist locally on SQLite.
2. **Calibrated probabilities:** Isotonic calibration maps scores to real % threats.
3. **Conformal prediction intervals:** Guaranteed coverage intervals for scores.
4. **Identical detector interface:** Strict base class (`BaseDetector`) for ML & heuristics.
5. **ONNX edge runtime:** No `torch` dependency at serving time; use `onnxruntime`. 
6. **Robustness:** A failing detector must NEVER crash the quorum engine. 
7. **Standards compliance:** Emit SARIF 2.1.0 output mimicking MITRE ATT&CK T1588.004.

## Current Phase & Handoff State
**Current Phase:** `Phase 3` (COMPLETED ✓)
**Next Immediate Action:** Begin Phase 4 - Implement `detectors/base.py`.
**Frontend Architecture Change:** Replaced Streamlit with optimized Vanilla JS/FastAPI frontend (saves ~150MB storage, enables native SSE streaming)

---

## Build Sequence Tracker (Do Not Skip Steps)

- [x] **Phase 1: Project Setup & Data Models**
  - Create `pyproject.toml` based on spec.
  - Create `ctmonitor/ingestion/models.py` with full dataclasses (`CertEvent`, `NormalisedCert`, `DetectorResult`, `CertVerdict`).
  - *Success Criteria:* Type hints pass `mypy`, objects instantiable. ✓ VERIFIED

- [x] **Phase 2: Ingestion Pipeline Base**
  - Implement `pipeline/ring.py` (`BoundedRing` asyncio queue).
  - Implement `pipeline/normaliser.py` (tldextract, Punycode, dedup).
  - *Success Criteria:* Can enqueue/dequeue events; normalization logic perfectly extracts eTLD+1 and decodes Punycode. ✓ VERIFIED

- [x] **Phase 3: Storage Layer**
  - Implement `storage/db.py` (Local SQLite using `aiosqlite`).
  - Implement auto-creation for tables (`verdicts`, `whois_cache`, `brand_watchlist`, `allow_list`).
  - *Success Criteria:* Database operations execute correctly. Can init tables via `CREATE TABLE IF NOT EXISTS`. ✓ VERIFIED

- [ ] **Phase 4: Detector Base Interface**
  - Implement `detectors/base.py` (`BaseDetector` ABC).
  - *Success Criteria:* Enforces `analyze(cert) -> DetectorResult` signature and built-in exception isolation.

- [ ] **Phase 5: Heuristic Detectors**
  - Implement all 5 heuristics (Levenshtein, Homograph, TLD Keyword, SAN Anomaly, Domain Age).
  - *Success Criteria:* Mock/unit tests with 2 positive/2 negative tests per heuristic pass successfully.

- [ ] **Phase 6: Quorum & Math Backends**
  - Implement `quorum/dempster_shafer.py` and `quorum/calibration.py`.
  - *Success Criteria:* Math verifies (K combinations, high conflict handling fallbacks).

- [ ] **Phase 7: Quorum Engine Core**
  - Implement `quorum/engine.py`.
  - *Success Criteria:* End-to-end combination of mock detector results into a cohesive `CertVerdict` with correct block/warn/watch tiers.

- [ ] **Phase 8: API Server Base (Heuristics Only)**
  - Implement `serving/api.py` (FastAPI).
  - *Success Criteria:* Heuristic-only mode works; endpoints (`/health`, `/analyze`, SSE `/stream`) respond properly.

- [ ] **Phase 9: Operator Dashboard (Part 1) — Vanilla JS/FastAPI**
  - Implement `dashboard/index.html` and `dashboard/main.js` (Vanilla ES2020 JavaScript).
  - Build Pages 1 & 4 (Live Stream via SSE & Manual Lookup) with Chart.js for visualizations.
  - Serve static dashboard from FastAPI (no separate port).
  - *Success Criteria:* Dashboard loads; SSE stream auto-updates verdicts table in real-time; manual lookup POSTs to `/analyze`.

- [ ] **Phase 10: Reporter (SARIF)**
  - Implement `reporter/sarif.py`.
  - *Success Criteria:* Passes SARIF 2.1.0 JSON schema validation with correctly mapped tiers/fingerprints.

- [ ] **Phase 11: ML Training Engines**
  - Implement `ml/train.py` (start w/ Ngram, then VAE, Transformer, GNN).
  - *Success Criteria:* Capability to download seed datasets and successfully train algorithms.

- [ ] **Phase 12: ONNX Export & Inference Backend**
  - Implement `ml/export.py` and `ml/inference.py`.
  - *Success Criteria:* Generates ONNX model binaries and executes inferences exclusively using ONNX runtime (< 2ms per inference).

- [ ] **Phase 13: ML Detectors Assembly**
  - Plug inference logic into detector wrappers inside `detectors/ml/`.
  - Register in Engine.
  - *Success Criteria:* Full pipeline processes data containing both heuristic and ML logic.

- [ ] **Phase 14: Mathematical Confidence Intervals**
  - Implement `detectors/ml/conformal.py` wrapper.
  - *Success Criteria:* Intervals output mathematically valid coverage thresholds.

- [ ] **Phase 15: Operator Dashboard (Part 2) — Advanced Analytics**
  - Expand `dashboard/main.js` with pages for Threat Maps, Detector Health, Benchmarks.
  - Integrate Chart.js/ECharts for heatmaps and histograms.
  - *Success Criteria:* All 5 pages render correctly with live data from FastAPI `/metrics`.

- [ ] **Phase 16: Manifest V3 Browser Extension**
  - Develop `extension/` stack (manifest.json, background.js, popup, content script).
  - *Success Criteria:* Manual loading in Chrome works seamlessly via vanilla ES2020 JS calling localhost APIs.

- [ ] **Phase 17: CLI Assembly**
  - Implement `cli.py` (Typer interface).
  - *Success Criteria:* All CLI commands (`train`, `serve`, `analyze`, `stream`, `export-sarif`, `benchmark`) route to accurate implementations.

- [ ] **Phase 18: Security & Testing Finalization**
  - Complete `tests/` directory files and fixtures.
  - *Success Criteria:* `pytest` coverage is complete. Systems can run without torch at execution time.
